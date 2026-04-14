# map_utils.py
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple


Grid = List[List[str]]
Point = Tuple[int, int]


def parse_map_response(raw_map: Any) -> Dict[str, Any]:
    """
    Normalize raw getMap payload into a dict with keys:
    - tiles: dict[str, dict]
    - grid: list[list[str]]

    Accepted inputs:
    - JSON string of full API response: {"code": ..., "map": {...}}
    - JSON string of map only: {"name": ..., "tiles": ..., "grid": ...}
    - dict full response
    - dict map only
    """
    if isinstance(raw_map, str):
        raw_map = json.loads(raw_map)

    if not isinstance(raw_map, dict):
        raise ValueError("raw_map must be a dict or JSON string")

    if "map" in raw_map and isinstance(raw_map["map"], dict):
        raw_map = raw_map["map"]

    tiles = raw_map.get("tiles")
    grid = raw_map.get("grid")

    if not isinstance(tiles, dict):
        raise ValueError("Map payload missing valid 'tiles' dict")
    if not isinstance(grid, list) or not all(isinstance(row, list) for row in grid):
        raise ValueError("Map payload missing valid 'grid' list[list]")

    return {"tiles": tiles, "grid": grid}


def collect_used_tile_types(grid: Grid) -> List[str]:
    used = set()
    for row in grid:
        for cell in row:
            used.add(cell)
    return sorted(used)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def extract_numeric_family(token: str) -> Tuple[str, int] | None:
    """
    Detect tokens like:
    - block1
    - block_2
    - block-3
    - blok 4
    Returns (base, number) or None.
    """
    token = normalize_text(token)
    match = re.match(r"^(.*?)[\s_-]?(\d+)$", token)
    if not match:
        return None

    base = normalize_text(match.group(1))
    number = int(match.group(2))

    if not base:
        return None

    return base, number


def build_type_metadata(tiles: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    For each tile key, derive normalized metadata only from task data.
    """
    result: Dict[str, Dict[str, Any]] = {}

    for tile_key, tile_meta in tiles.items():
        label = str(tile_meta.get("label", ""))
        symbol = str(tile_meta.get("symbol", ""))

        key_norm = normalize_text(tile_key)
        label_norm = normalize_text(label)
        symbol_norm = normalize_text(symbol)

        key_family = extract_numeric_family(key_norm)
        label_family = extract_numeric_family(label_norm)
        symbol_family = extract_numeric_family(symbol_norm)

        result[tile_key] = {
            "key": tile_key,
            "key_norm": key_norm,
            "label": label,
            "label_norm": label_norm,
            "symbol": symbol,
            "symbol_norm": symbol_norm,
            "key_family": key_family,
            "label_family": label_family,
            "symbol_family": symbol_family,
        }

    return result


def find_numbered_families(
    tiles: Dict[str, Dict[str, Any]],
    grid: Grid,
) -> Dict[str, Any]:
    """
    Find numbered families based strictly on tile metadata present in task data.

    Preference order:
    1. key family, because grid uses tile keys
    2. label family
    3. symbol family

    Returns structure:
    {
      "block": {
        "source": "key",
        "members": [
          {"tile_key": "block1", "number": 1, "count": 4},
          ...
        ]
      }
    }
    """
    metadata = build_type_metadata(tiles)
    used_counts = count_tile_occurrences(grid)

    families: Dict[str, Dict[str, Any]] = {}

    by_source: Dict[str, Dict[str, List[Tuple[str, int]]]] = {
        "key": defaultdict(list),
        "label": defaultdict(list),
        "symbol": defaultdict(list),
    }

    for tile_key, meta in metadata.items():
        for source_name, family_key in [
            ("key", meta["key_family"]),
            ("label", meta["label_family"]),
            ("symbol", meta["symbol_family"]),
        ]:
            if family_key is None:
                continue
            base, number = family_key
            by_source[source_name][base].append((tile_key, number))

    for source_name in ["key", "label", "symbol"]:
        for base, members in by_source[source_name].items():
            if len(members) < 2:
                continue

            deduped = {}
            for tile_key, number in members:
                deduped[tile_key] = number

            materialized = [
                {
                    "tile_key": tile_key,
                    "number": number,
                    "count": used_counts.get(tile_key, 0),
                }
                for tile_key, number in deduped.items()
            ]
            materialized.sort(key=lambda x: (x["number"], x["tile_key"]))

            score = family_confidence_score(materialized)

            existing = families.get(base)
            current = {
                "source": source_name,
                "members": materialized,
                "confidence": score,
            }

            if existing is None or current["confidence"] > existing["confidence"]:
                families[base] = current

    return families


def family_confidence_score(members: List[Dict[str, Any]]) -> float:
    """
    Prefer families that:
    - have more members,
    - have contiguous numbering,
    - are actually used in the grid.
    """
    numbers = sorted(m["number"] for m in members)
    used_member_count = sum(1 for m in members if m["count"] > 0)
    contiguous_pairs = sum(
        1 for a, b in zip(numbers, numbers[1:]) if b == a + 1
    )

    return (
        len(members) * 10
        + used_member_count * 5
        + contiguous_pairs * 3
        + max(numbers)
    )


def count_tile_occurrences(grid: Grid) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for row in grid:
        for cell in row:
            counts[cell] += 1
    return dict(counts)


def select_target_tile_types(
    tiles: Dict[str, Dict[str, Any]],
    grid: Grid,
) -> Dict[str, Any]:
    """
    Select target tile types strictly from detected numbered families.

    Strategy:
    - detect families from keys/labels/symbols
    - keep only families with at least one member used in grid
    - choose best family by confidence
    - select highest-numbered member(s) from that family that are used in grid

    Returns diagnostic structure instead of only a set.
    """
    families = find_numbered_families(tiles, grid)
    if not families:
        return {
            "selected_types": [],
            "selected_family": None,
            "families": {},
            "reason": "no_numbered_families_detected",
        }

    usable_families = {}
    for base, family in families.items():
        used_members = [m for m in family["members"] if m["count"] > 0]
        if used_members:
            usable_families[base] = {**family, "used_members": used_members}

    if not usable_families:
        return {
            "selected_types": [],
            "selected_family": None,
            "families": families,
            "reason": "families_detected_but_not_used_in_grid",
        }

    best_base, best_family = max(
        usable_families.items(),
        key=lambda item: (
            item[1]["confidence"],
            len(item[1]["used_members"]),
            max(m["number"] for m in item[1]["used_members"]),
        ),
    )

    max_number = max(m["number"] for m in best_family["used_members"])
    selected = [
        m["tile_key"]
        for m in best_family["used_members"]
        if m["number"] == max_number
    ]

    return {
        "selected_types": sorted(selected),
        "selected_family": best_base,
        "families": usable_families,
        "reason": "ok",
    }


def extract_target_points(grid: Grid, selected_types: List[str]) -> List[Point]:
    selected_set = set(selected_types)
    points: List[Point] = []

    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell in selected_set:
                points.append((r, c))

    return points


def to_field_name(row: int, col: int) -> str:
    """
    Convert zero-based row/col to spreadsheet-like coordinates:
    (0,0) -> A1, (0,5) -> F1, (10,10) -> K11
    """
    return f"{column_name(col)}{row + 1}"


def column_name(index: int) -> str:
    result = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def manhattan(a: Point, b: Point) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def cluster_points(points: List[Point], threshold: int = 2) -> List[List[Point]]:
    """
    Simple connected-components style clustering using Manhattan distance threshold.
    threshold=2 works well for nearby city blocks without over-merging distant groups.
    """
    if not points:
        return []

    unvisited = set(points)
    clusters: List[List[Point]] = []

    while unvisited:
        start = unvisited.pop()
        queue = [start]
        cluster = [start]

        while queue:
            current = queue.pop()
            neighbors = [
                p for p in list(unvisited)
                if manhattan(current, p) <= threshold
            ]
            for n in neighbors:
                unvisited.remove(n)
                queue.append(n)
                cluster.append(n)

        clusters.append(sorted(cluster))

    clusters.sort(key=lambda cl: (min(r for r, _ in cl), min(c for _, c in cl)))
    return clusters


def choose_drop_point(cluster: List[Point], grid: Grid) -> str:
    """
    Choose a practical drop point:
    - prefer a point inside the cluster if it is already on a road
    - otherwise choose the nearest road tile to the cluster centroid
    - fallback to the first cluster block coordinate

    This uses only grid contents, no semantic hardcoding beyond literal 'road'
    key present in task_data.
    """
    if not cluster:
        raise ValueError("Cannot choose drop point for empty cluster")

    cluster_set = set(cluster)

    for r, c in cluster:
        if grid[r][c] == "road":
            return to_field_name(r, c)

    centroid_r = sum(r for r, _ in cluster) / len(cluster)
    centroid_c = sum(c for _, c in cluster) / len(cluster)

    road_points = [
        (r, c)
        for r, row in enumerate(grid)
        for c, cell in enumerate(row)
        if cell == "road"
    ]

    if road_points:
        best = min(
            road_points,
            key=lambda p: abs(p[0] - centroid_r) + abs(p[1] - centroid_c)
        )
        return to_field_name(*best)

    return to_field_name(*cluster[0])


def build_cluster_report(points: List[Point], grid: Grid) -> List[Dict[str, Any]]:
    raw_clusters = cluster_points(points)
    report: List[Dict[str, Any]] = []

    for idx, cluster in enumerate(raw_clusters):
        blocks = [to_field_name(r, c) for r, c in cluster]
        drop_point = choose_drop_point(cluster, grid)

        report.append({
            "cluster_id": idx,
            "blocks": blocks,
            "drop_point": drop_point,
            "block_count": len(blocks),
        })

    return report


def analyze_map_payload(raw_map: Any) -> Dict[str, Any]:
    """
    Main pure function for map analysis.
    Returns diagnostics + target fields + clusters.
    """
    parsed = parse_map_response(raw_map)
    tiles = parsed["tiles"]
    grid = parsed["grid"]

    used_tile_types = collect_used_tile_types(grid)
    selection = select_target_tile_types(tiles, grid)
    selected_types = selection["selected_types"]

    target_points = extract_target_points(grid, selected_types)
    target_fields = [to_field_name(r, c) for r, c in target_points]
    clusters = build_cluster_report(target_points, grid)

    return {
        "used_tile_types": used_tile_types,
        "selected_family": selection["selected_family"],
        "selected_target_types": selected_types,
        "selection_reason": selection["reason"],
        "families": selection["families"],
        "target_fields": target_fields,
        "clusters": clusters,
    }
    
