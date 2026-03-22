# log_filters.py
import re
import json
from pathlib import Path
from typing import Literal
from datetime import datetime, timedelta


# ─────────────────────────────────────────────
# HELPERS PRYWATNE
# ─────────────────────────────────────────────

def _load_lines(file_path: str) -> list[dict]:
    """
    Wczytuje linie z .log lub .json (output severity_filter).
    Zawsze zwraca listę słowników {"line_number": int, "content": str}.
    """
    src = Path(file_path)
    if src.suffix == ".json":
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            {"line_number": m["line_number"], "content": m["content"]}
            for m in data.get("matches", [])
        ]
    else:
        with open(src, "r", encoding="utf-8", errors="replace") as f:
            raw = f.readlines()
        return [
            {"line_number": i + 1, "content": line.rstrip()}
            for i, line in enumerate(raw)
        ]



def _save_results(output_base: str, matches: list[dict]) -> dict:
    """
    Zapisuje dwa pliki z tego samego zestawu matches:
    - .log  → czyste linie (identyczne ze źródłem) — dla Compressora
    - .json → metadane (line_number, content, ...) — dla kolejnych filtrów
    Zwraca słownik z obiema ścieżkami.
    """
    base = Path(output_base).with_suffix("")  # usuń rozszerzenie jeśli jest
    log_path = base.with_suffix(".log")
    json_path = base.with_suffix(".json")

    # Płaski .log — tylko oryginalna treść linii, bez żadnych tagów
    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(m["content"] + "\n" for m in matches)

    # .json — pełne metadane
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"total_matches": len(matches), "matches": matches},
            f, ensure_ascii=False, indent=2
        )

    return {"result_log": str(log_path), "result_json": str(json_path)}


def severity_filter(
    file_path: str,
    output_file: str,
    levels: list[str] = ["WARN", "ERRO", "CRIT"],
) -> dict:
    output_path = Path(output_file)
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)

    log_path = Path(file_path)
    if not log_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(lvl) for lvl in levels) + r")\b",
        re.IGNORECASE
    )

    matches = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    for i, line in enumerate(all_lines):
        if m := pattern.search(line):
            matches.append({
                "line_number": i + 1,
                "content": line.rstrip(),
                "matched_level": m.group(1).upper(),
            })

    paths = _save_results(output_file, matches)   # Compressor needs .log  and .json for next filters

    result = {
        "total_lines_scanned": len(all_lines),
        "total_matches": len(matches),
        **paths,   # result_log + result_json
    }

    return result


def keyword_search(
    file_path: str,
    output_base: str,     
    keywords: list[str],
    mode: Literal["any", "all"] = "any",
    use_regex: bool = False,
    case_sensitive: bool = False,
) -> dict:

    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = [re.compile(kw if use_regex else re.escape(kw), flags) for kw in keywords]

    def line_matches(content: str) -> bool:
        hits = [bool(p.search(content)) for p in compiled]
        return all(hits) if mode == "all" else any(hits)

    candidate_lines = _load_lines(file_path)  # ← dict list {"line_number": int, "content": str}

    matches = [
        {
            **line,   # line_number + content bez zmian
            "matched_keywords": [kw for kw, p in zip(keywords, compiled) if p.search(line["content"])],
        }
        for line in candidate_lines
        if line_matches(line["content"])
    ]
    

    paths = _save_results(output_base, matches)  # ← wywołujący decyduje gdzie

    return {
        "total_candidates_scanned": len(candidate_lines),
        "total_matches": len(matches),
        **paths,
    }

def time_window_search(
    file_path: str,
    output_base: str,
    time_from: str,
    time_to: str,
    time_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
) -> dict:
    time_re = re.compile(time_pattern)
    t_from = datetime.fromisoformat(time_from)
    t_to = datetime.fromisoformat(time_to)

    candidate_lines = _load_lines(file_path)  # ← dict list {"line_number": int, "content": str}

    matches = []
    for line in candidate_lines:
        m = time_re.search(line["content"])
        if not m:
            continue
        try:
            ts = datetime.fromisoformat(m.group(0))
            if t_from <= ts <= t_to:
                matches.append(line)   # ← unchanged line structure
        except ValueError:
            continue

    paths = _save_results(output_base, matches)

    return {
        "total_candidates_scanned": len(candidate_lines),
        "total_matches": len(matches),
        **paths,
    }
    
def chunk_by_gap(
    file_path: str,
    output_dir: str,
    gap_minutes: int = 10,
) -> dict:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts_re = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    candidate_lines = _load_lines(file_path)  # ← lista słowników

    # Przypisz timestamp — linie bez ts dziedziczą ostatni znany
    parsed = []
    last_ts = None
    for line in candidate_lines:
        m = ts_re.search(line["content"])
        if m:
            try:
                last_ts = datetime.fromisoformat(m.group(0))
            except ValueError:
                pass
        parsed.append({**line, "ts": last_ts})   # ← unchanged line structure + ts

    # Tnij po gapach
    gap = timedelta(minutes=gap_minutes)
    incidents, current = [], []

    for entry in parsed:
        if not current:
            current.append(entry)
            continue
        prev_ts = current[-1]["ts"]
        if entry["ts"] and prev_ts and (entry["ts"] - prev_ts) > gap:
            incidents.append(current)
            current = []
        current.append(entry)

    if current:
        incidents.append(current)

    # Save every incident
    summary = []
    for idx, incident in enumerate(incidents, start=1):
        output_base = str(out_dir / f"incident_{idx:03d}")
        paths = _save_results(output_base, incident)

        timestamps = [e["ts"] for e in incident if e["ts"]]
        line_numbers = [e["line_number"] for e in incident]

        summary.append({
            "incident": idx,
            "count": len(incident),
            "line_numbers": line_numbers,
            "time_start": timestamps[0].isoformat() if timestamps else None,
            "time_end": timestamps[-1].isoformat() if timestamps else None,
            **paths,
        })

    return {
        "total_lines": len(parsed),
        "total_incidents": len(incidents),
        "gap_minutes": gap_minutes,
        "output_dir": str(out_dir),
        "incidents": summary,
    }
    