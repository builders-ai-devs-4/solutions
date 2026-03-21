# tools/severity_filter.py
import re
import json
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Literal


def severity_filter(
    file_path: str,
    output_file: str,
    levels: list[str] = ["WARN", "ERRO", "CRIT"],
) -> dict:
    """
    First pass: filters logs by severity level using regex.
    Saves results to a JSON file and returns them directly.
    If the output JSON already exists, returns cached result immediately.
    """
    output_path = Path(output_file)
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)

    log_path = Path(file_path)
    if not log_path.exists():
        return {"error": f"File does not exist: {file_path}"}

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(lvl) for lvl in levels) + r")\b",
        re.IGNORECASE
    )

    matches = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if m := pattern.search(line):
            matches.append({
                "line_number": i + 1,
                "content": line.rstrip(),
                "matched_level": m.group(1).upper(),
            })

    result = {
        "total_lines_scanned": len(lines),
        "total_matches": len(matches),
        "matches": matches,
        "output_file": output_file,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result

def keyword_search(
    file_path: str,
    keywords: list[str],
    mode: Literal["any", "all"] = "any",
    use_regex: bool = False,
    case_sensitive: bool = False,
) -> dict:
    """
    Searches for keywords in a log file or in a JSON file from severity_filter.
    Detects file type automatically by extension.
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = [
        re.compile(kw if use_regex else re.escape(kw), flags)
        for kw in keywords
    ]

    def line_matches(line: str) -> bool:
        hits = [bool(p.search(line)) for p in compiled]
        return all(hits) if mode == "all" else any(hits)

    if Path(file_path).suffix == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            severity_data = json.load(f)
        candidate_lines = [
            (m["line_number"], m["content"])
            for m in severity_data.get("matches", [])
        ]
    else:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_lines = f.readlines()
        candidate_lines = [(i + 1, line.rstrip()) for i, line in enumerate(raw_lines)]

    matches = [
        {
            "line_number": line_no,
            "content": content,
            "matched_keywords": [
                kw for kw, p in zip(keywords, compiled) if p.search(content)
            ],
        }
        for line_no, content in candidate_lines
        if line_matches(content)
    ]

    result = {
        "total_candidates_scanned": len(candidate_lines),
        "total_matches": len(matches),
        "matches": matches,
    }
    
    return result

def time_window_search(
    file_path: str,
    time_from: str,
    time_to: str,
    time_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
) -> dict:
    """
    Pobiera wszystkie linie z przedziału czasowego.
    Zamiast zgadywać słowa kluczowe, Supervisor podaje okno: '08:26' - '08:29'.
    """
    from datetime import datetime

    time_re = re.compile(time_pattern)
    candidates = []

    src = Path(file_path)
    if src.suffix == ".json":
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        lines = [(m["line_number"], m["content"]) for m in data.get("matches", [])]
    else:
        with open(src, "r", encoding="utf-8", errors="replace") as f:
            raw = f.readlines()
        lines = [(i + 1, l.rstrip()) for i, l in enumerate(raw)]

    for line_no, content in lines:
        m = time_re.search(content)
        if not m:
            continue
        try:
            ts = datetime.fromisoformat(m.group(0))
            t_from = datetime.fromisoformat(time_from)
            t_to = datetime.fromisoformat(time_to)
            if t_from <= ts <= t_to:
                candidates.append({"line_number": line_no, "content": content})
        except ValueError:
            continue

    return {
        "total_candidates_scanned": len(lines),
        "total_matches": len(candidates),
        "matches": candidates,
    }
