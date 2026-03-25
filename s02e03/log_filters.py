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

def _load_lines(file_path: str, strict_refs: bool = True) -> list[dict]:
    """
    Wczytuje linie z .json lub .log.
    Zawsze zwraca listę słowników {"line": int, "content": str}.

    Args:
        strict_refs: True (domyślnie) — akceptuje tylko .json, gwarantuje
                     że line odnosi się do failure.log.
                     False — akceptuje .log, line resetuje się do 1,2,3...
                     (używaj tylko gdy referencja do failure.log nie jest potrzebna)
    """
    src = Path(file_path)
    if src.suffix == ".json":
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            {"line": m["line"], "content": m["content"]}
            for m in data.get("matches", [])
        ]
    else:
        if strict_refs:
            raise ValueError(
                f"Expected .json to preserve failure.log line references, got: {src.suffix}. "
                f"Pass strict_refs=False to load .log without line references."
            )
        with open(src, "r", encoding="utf-8", errors="replace") as f:
            raw = f.readlines()
        return [
            {"line": i + 1, "content": line.rstrip()}
            for i, line in enumerate(raw)
        ]

def _save_results(output_base: str, matches: list[dict]) -> dict:
    """
    Zapisuje dwa pliki z tego samego zestawu matches:
    - .log  → czyste linie (identyczne ze źródłem) — dla Compressora
    - .json → metadane (line, content, ...) — dla kolejnych filtrów
    Zwraca słownik z obiema ścieżkami.
    """
    base = Path(output_base).with_suffix("")
    log_path = base.with_suffix(".log")
    json_path = base.with_suffix(".json")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(m["content"] + "\n" for m in matches)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"matches": matches},
            f, ensure_ascii=False, indent=2
        )

    return {"result_log": str(log_path), "result_json": str(json_path)}


def severity_filter(
    file_path: str,
    output_file: str,
    levels: list[str] = ["WARN", "ERRO", "CRIT"],
    max_lines: int = -1
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
                "line": i + 1,
                "content": line.rstrip(),
            })
        if max_lines > 0 and len(matches) >= max_lines:
            break

    paths = _save_results(output_file, matches)   # Compressor needs .log  and .json for next filters

    result = {
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

    candidate_lines = _load_lines(file_path, strict_refs=False)  # ← ZMIANA: Wyłączamy restrykcję
    
    matches = [
        {
            **line,   # line + content bez zmian
            "matched_keywords": [kw for kw, p in zip(keywords, compiled) if p.search(line["content"])],
        }
        for line in candidate_lines
        if line_matches(line["content"])
    ]
    
    # Krok 2: OTO MAGIA - Filtrujemy i usuwamy spam od razu!
    clean_matches = smart_log_filter(matches)

    # Krok 3: Zapisujemy tylko to, co jest czyste i potrzebne
    paths = _save_results(output_base, clean_matches)


    return {
        **paths,
    }
    

def smart_log_filter(
    lines: list[dict], 
    critical_lvl: tuple[str, ...] = (), 
    optional_lvl: tuple[str, ...] = ('[ERRO]', '[CRIT]', '[INFO]', '[WARN]')
) -> list[dict]:
    """
    Filtruje listę logów:
    - critical_lvl: (puste) - brak wyjątków dla deduplikacji
    - optional_lvl: deduplikuje błędy, ostrzeżenia i info
    """
    seen_messages = set()
    filtered_lines = []
    
    for item in lines:
        content = item.get("content", "")
        
        # 1. Sprawdzamy, czy to poziom wymagający deduplikacji
        if any(lvl in content for lvl in optional_lvl):
            # Wycinamy timestamp do porównania (format [YYYY-MM-DD HH:MM:SS])
            core_message = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*', '', content).strip()
            
            if core_message not in seen_messages:
                seen_messages.add(core_message)
                filtered_lines.append(item)
            continue
            
        # 2. Jeśli coś wpadnie do critical_lvl (aktualnie puste), przepuszczamy wszystko
        if any(lvl in content for lvl in critical_lvl):
            filtered_lines.append(item)
            continue
            
    return filtered_lines

def chunk_by_time_window(
    file_path: str,
    output_dir: str,
    window_minutes: int,
    time_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
) -> dict:
    """Dzieli plik logów na chunki o stałym oknie czasowym (relatywnym od pierwszego wpisu).

    Każdy chunk trafia do osobnego pliku chunk_NNN.log w output_dir.
    Linie bez znacznika czasu są dołączane do ostatniego aktywnego chunka.

    Args:
        file_path:       Ścieżka do pliku .log lub .json (wynik severity_filter).
        output_dir:      Katalog docelowy dla plików chunk_NNN.log.
        window_minutes:  Rozmiar okna w minutach.
        time_pattern:    Regex do wyciągania znacznika czasu z linii.

    Returns:
        dict z listą chunks: [{chunk_index, file, line_count}, ...]
    """
  
    time_re = re.compile(time_pattern)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    

    raw_lines = _load_lines(file_path)
    if not raw_lines:
        raise ValueError(f"No lines found in file: {file_path}")


    window_secs = window_minutes * 60
    t0: datetime | None = None
    current_bucket: int = -1
    buckets: dict[int, list[dict]] = {}
    
    for entry in raw_lines:
        content = entry["content"]
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
        buckets.setdefault(current_bucket, []).append(entry)


    chunk_files = []
    for idx in sorted(buckets.keys()):
        output_base = str(out_dir / f"chunk_{idx + 1:03d}")
        paths = _save_results(output_base, buckets[idx])
        chunk_files.append({
            "chunk_index": idx + 1,
            **paths,
        })

    return {"chunks": chunk_files}

def validate_compression(original: list[dict], compressed: list[dict]) -> bool:
    if len(original) != len(compressed):
        return False
    for orig, comp in zip(original, compressed):
        if orig["line"] != comp["line"]:
            return False
    return True


def deduplicate_log_lines(lines: list[str]) -> list[str]:
    """
    Usuwa powtarzające się komunikaty błędów, zachowując tylko pierwsze wystąpienie.
    Ignoruje znacznik czasu przy porównywaniu linii.
    """
    seen_signatures = set()
    unique_lines = []
    
    # Zakładamy format: [YYYY-MM-DD HH:MM:SS] [LEVEL] Treść wiadomości...
    # Ten regex łapie wszystko po znaczniku poziomu, czyli samą treść
    pattern = re.compile(r"\[.*?\] \[[A-Z]+\] (.*)")
    
    for line in lines:
        match = pattern.search(line)
        if match:
            # Sygnaturą jest sama treść loga (bez daty i czasu)
            message_signature = match.group(1).strip()
            
            if message_signature not in seen_signatures:
                seen_signatures.add(message_signature)
                unique_lines.append(line.strip())
        else:
            # Jeśli linia nie pasuje do formatu, zostawiamy ją dla bezpieczeństwa
            unique_lines.append(line.strip())
            
    return unique_lines

