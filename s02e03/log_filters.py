# log_filters.py
import re
import json
from pathlib import Path
from typing import Literal
from datetime import datetime, timedelta
from math import floor


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
    
def chunk_by_time_window(
    file_path: str,
    output_dir: str,
    window_minutes: int = 10,
    time_pattern: str = r"\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}",
) -> dict:
    """Dzieli plik logów na chunki o stałym oknie czasowym (relatywnym od pierwszego wpisu).

    Każdy chunk trafia do osobnego pliku chunk_NNN.log w output_dir.
    Linie bez znacznika czasu są dołączane do ostatniego aktywnego chunka.

    Args:
        file_path:       Ścieżka do pliku .log lub .json (wynik severity_filter).
        output_dir:      Katalog docelowy dla plików chunk_NNN.log.
        window_minutes:  Rozmiar okna w minutach (domyślnie 10).
        time_pattern:    Regex do wyciągania znacznika czasu z linii.

    Returns:
        dict z listą chunks: [{chunk_index, file, line_count}, ...]
    """
    time_re = re.compile(time_pattern)
    src = Path(file_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_lines = _load_lines(file_path)
    for entry in raw_lines:
        content = entry["content"]

    window_secs = window_minutes * 60
    t0: datetime | None = None
    current_bucket: int = -1
    buckets: dict[int, list[str]] = {}


    for _line_no, content in raw_lines:
        m = time_re.search(content)
        if m:
            try:
                ts = datetime.fromisoformat(m.group(0))
                if t0 is None:
                    t0 = ts
                current_bucket = floor((ts - t0).total_seconds() / window_secs)
            except ValueError:
                pass
        if current_bucket < 0:
            current_bucket = 0
        buckets.setdefault(current_bucket, []).append(content)

    chunk_files = []
    for idx in sorted(buckets.keys()):
        chunk_name = f"chunk_{idx + 1:03d}.log"
        chunk_path = out_dir / chunk_name
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.writelines(line + "\n" for line in buckets[idx])
        chunk_files.append({
            "chunk_index": idx + 1,
            "file": str(chunk_path),
        })

    return {"chunks": chunk_files}

