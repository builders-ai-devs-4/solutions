import math
import json
from typing import Any

# Uzupełnij po wywołaniu get_help — symbole oznaczające wysokie budynki na mapie
TALL_BLOCK_SYMBOLS = {"B", "H", "W"}  # placeholder — zweryfikuj przez get_help/getMap

def euclidean(a: tuple[int, int], b: tuple[int, int]) -> float:
    """
    Calculates the Euclidean distance between two grid points.

    Args:
        a: First point as (row, col).
        b: Second point as (row, col).

    Returns:
        Euclidean distance as float.
    """
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def greedy_cluster(
    points: list[tuple[int, int]],
    threshold: float = 2.5,
) -> list[list[tuple[int, int]]]:
    """
    Groups spatial points into clusters based on Euclidean distance.

    Greedy algorithm: for each unassigned point, creates a new cluster and adds
    all other unassigned points within distance <= threshold to it.
    The order of input points affects the result — earlier points act as cluster seeds.

    Args:
        points: List of (row, column) coordinates to group,
                e.g. coordinates of high-rise blocks on an 11x11 map.
        threshold: Maximum Euclidean distance between a seed point and a candidate
                   for the candidate to be included in the same cluster.
                   Defaults to 2.5 — covers a 2-field neighborhood in each direction.

    Returns:
        List of clusters, where each cluster is a list of (row, column) points
        belonging to that group. Each input point appears in exactly one cluster.

    Example:
        >>> blocks = [(1,1), (1,2), (2,1), (8,8), (9,8)]
        >>> greedy_cluster(blocks, threshold=2.5)
        [[(1, 1), (1, 2), (2, 1)], [(8, 8), (9, 8)]]

    Note:
        The algorithm is not symmetric — changing the order of input points
        may produce different clusters. For deterministic results, sort `points`
        before calling, e.g. sorted(points).
    """
    clusters = []
    assigned = set()

    for i, p in enumerate(sorted(points)):
        if i in assigned:
            continue
        cluster = [p]
        assigned.add(i)
        for j, q in enumerate(sorted(points)):
            if j not in assigned and euclidean(p, q) <= threshold:
                cluster.append(q)
                assigned.add(j)
        clusters.append(cluster)

    return clusters


def centroid(cluster: list[tuple[int, int]]) -> tuple[int, int]:
    """
    Calculates the centroid (geometric center) of a cluster of grid points.

    The result is rounded to the nearest integer grid coordinates,
    making it directly usable as a transporter drop point.

    Args:
        cluster: List of (row, column) grid points belonging to one cluster.

    Returns:
        Centroid as (row, col) rounded to nearest integer.

    Example:
        >>> centroid([(1, 1), (1, 2), (2, 1)])
        (1, 1)
    """
    row = sum(p[0] for p in cluster) / len(cluster)
    col = sum(p[1] for p in cluster) / len(cluster)
    return (round(row), round(col))


def coords_to_grid(row: int, col: int) -> str:
    """
    Converts zero-based (row, col) indices to grid notation (e.g. 'F6').

    Columns are mapped to letters (0=A, 1=B, ..., 10=K).
    Rows are 1-indexed in grid notation.

    Args:
        row: Zero-based row index (0-10 for an 11x11 grid).
        col: Zero-based column index (0-10 for an 11x11 grid).

    Returns:
        Grid coordinate string, e.g. 'F6'.

    Example:
        >>> coords_to_grid(5, 5)
        'F6'
    """
    col_letter = chr(ord("A") + col)
    return f"{col_letter}{row + 1}"


def parse_map(raw_map: Any) -> list[list[str]]:
    """
    Parses the raw getMap API response into a 2D list of symbols.

    Handles both JSON dict/list responses and plain string grid formats.

    Args:
        raw_map: Raw response from getMap — JSON string, dict, or plain text grid.

    Returns:
        2D list where each element is a single symbol string, e.g. [['.',  'B', ...], ...].

    Raises:
        ValueError: If the response cannot be parsed into a recognizable grid format.
    """
    if isinstance(raw_map, str):
        try:
            raw_map = json.loads(raw_map)
        except json.JSONDecodeError:
            # Plain text grid — split by newlines and spaces
            rows = [line.split() for line in raw_map.strip().splitlines()]
            return rows

    # JSON list of lists
    if isinstance(raw_map, list):
        return raw_map

    # JSON dict — look for common keys
    for key in ("map", "grid", "data", "fields"):
        if key in raw_map:
            return raw_map[key]

    raise ValueError(f"Cannot parse map from response: {str(raw_map)[:200]}")


def extract_tall_blocks(grid: list[list[str]]) -> list[tuple[int, int]]:
    """
    Extracts coordinates of all tall building fields from a parsed map grid.

    Args:
        grid: 2D list of symbols as returned by parse_map.

    Returns:
        List of (row, col) coordinates where tall building symbols are present.
    """
    blocks = []
    for row_idx, row in enumerate(grid):
        for col_idx, symbol in enumerate(row):
            if symbol in TALL_BLOCK_SYMBOLS:
                blocks.append((row_idx, col_idx))
    return blocks