"""
grid_utils.py
=============
Shared utility library for grid-based image processing.

Provides generic functions that operate on already-detected grid line
coordinates (row_lines, col_lines). Completely agnostic about how the
lines were found — works with any detection strategy (morphology,
HSV masking, Canny, etc.).

Typical usage
-------------
    from libs.grid_utils import find_grid_lines, cut_cells, save_visualization

    row_lines, col_lines = my_project_specific_detector(img)
    cells  = cut_cells(img, row_lines, col_lines)
    table  = save_cells(cells, Path("output"))
    save_visualization(img, row_lines, col_lines, Path("output/grid_vis.png"))
    save_csv(table, Path("output/cells.csv"))
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Grid line detection
# ---------------------------------------------------------------------------

def find_grid_lines(
    profile: np.ndarray,
    size: int,
    min_gap: int = 80,
    thresh_ratio: float = 0.3,
) -> list[int]:
    """Locate grid lines as peaks in a 1-D pixel-sum profile.

    Works on the output of any binarisation strategy — the caller is
    responsible for producing the profile (row_sum or col_sum).  This
    function only knows about numbers, not about the image they came from.

    Algorithm
    ---------
    1. Compute a threshold = profile.max() * thresh_ratio.
    2. Walk the profile and group consecutive above-threshold values
       into a single "peak", represented by its midpoint.
    3. Drop peaks that are closer than *min_gap* pixels to the previous
       accepted peak (keeps only one line per grid separator).

    Parameters
    ----------
    profile : np.ndarray
        1-D float array of pixel sums along one axis
        (e.g. ``red_mask.sum(axis=1) / 255``).
    size : int
        Length of that axis in pixels (``h`` for rows, ``w`` for cols).
        Used only when the last peak reaches the array boundary.
    min_gap : int
        Minimum distance in pixels between two accepted lines.
        Set this to slightly less than the smallest expected cell size.
    thresh_ratio : float
        Fraction of the profile maximum used as the peak threshold.
        Lower values detect fainter lines; higher values ignore noise.

    Returns
    -------
    list[int]
        Sorted pixel positions of detected grid lines (borders included).
    """
    threshold = profile.max() * thresh_ratio
    lines: list[int] = []
    in_peak, start = False, 0

    for i, v in enumerate(profile):
        if v > threshold and not in_peak:
            start = i
            in_peak = True
        elif v <= threshold and in_peak:
            lines.append((start + i) // 2)
            in_peak = False
    if in_peak:
        lines.append((start + size) // 2)

    if not lines:
        return []

    filtered = [lines[0]]
    for line in lines[1:]:
        if line - filtered[-1] >= min_gap:
            filtered.append(line)
    return filtered


# ---------------------------------------------------------------------------
# Cell extraction
# ---------------------------------------------------------------------------

def cut_cells(
    img: np.ndarray,
    row_lines: list[int],
    col_lines: list[int],
    margin: int = 3,
) -> dict[tuple[int, int], np.ndarray]:
    """Crop individual cells from an image using known grid line positions.

    Indices are **1-based**: the top-left cell is ``(1, 1)``, the one to
    its right is ``(1, 2)``, the one below is ``(2, 1)``, and so on —
    consistent with the ``RxC`` naming convention used throughout the
    project.

    Parameters
    ----------
    img : np.ndarray
        Source image (colour or grayscale).
    row_lines : list[int]
        Pixel Y-positions of horizontal grid separators, including the
        top and bottom borders.  Must contain at least 2 values.
    col_lines : list[int]
        Pixel X-positions of vertical grid separators, including the
        left and right borders.  Must contain at least 2 values.
    margin : int
        Pixels to strip from every edge of each cell to remove the grid
        line artefacts from the cropped content.

    Returns
    -------
    dict[tuple[int, int], np.ndarray]
        Mapping ``{(row, col): cell_image}``, where both indices start
        at 1.
    """
    cells: dict[tuple[int, int], np.ndarray] = {}
    for r in range(len(row_lines) - 1):
        for c in range(len(col_lines) - 1):
            r0, r1 = row_lines[r] + margin, row_lines[r + 1] - margin
            c0, c1 = col_lines[c] + margin, col_lines[c + 1] - margin
            cells[(r + 1, c + 1)] = img[r0:r1, c0:c1]
    return cells


def save_cells(
    cells: dict[tuple[int, int], np.ndarray],
    output_dir: Path,
    prefix: str = "cell",
) -> list[dict[str, Any]]:
    """Save cell images to *output_dir/cells/* and return a metadata table.

    Each file is named ``<prefix>_RxC.png``.  The returned list of dicts
    is ready to be written with :func:`save_csv`.

    Parameters
    ----------
    cells : dict
        Output of :func:`cut_cells`.
    output_dir : Path
        Root output directory.  A ``cells/`` sub-directory is created
        automatically.
    prefix : str
        Filename prefix, default ``"cell"``.

    Returns
    -------
    list[dict]
        One dict per cell with keys:
        ``index``, ``row``, ``col``, ``width_px``, ``height_px``, ``file``.
    """
    cells_dir = output_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    table: list[dict[str, Any]] = []
    for (row, col), cell in sorted(cells.items()):
        fname = f"{prefix}_{row}x{col}.png"
        cv2.imwrite(str(cells_dir / fname), cell)
        h, w = cell.shape[:2]
        table.append({
            "index":     f"{row}x{col}",
            "row":       row,
            "col":       col,
            "width_px":  w,
            "height_px": h,
            "file":      fname,
        })
    return table


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def save_visualization(
    img_bgr: np.ndarray,
    row_lines: list[int],
    col_lines: list[int],
    out_path: Path,
    line_color: tuple[int, int, int] = (0, 0, 255),
    label_color: tuple[int, int, int] = (0, 255, 0),
    line_thickness: int = 3,
    font_scale: float = 1.4,
) -> None:
    """Draw the detected grid and cell index labels on a copy of the image.

    Saves the annotated image to *out_path*.

    Parameters
    ----------
    img_bgr : np.ndarray
        Original colour image in BGR format.
    row_lines : list[int]
        Horizontal grid line positions (pixels).
    col_lines : list[int]
        Vertical grid line positions (pixels).
    out_path : Path
        Destination file path (PNG recommended).
    line_color : tuple[int, int, int]
        BGR colour of the grid lines.  Default: red ``(0, 0, 255)``.
    label_color : tuple[int, int, int]
        BGR colour of the ``RxC`` text labels.  Default: green ``(0, 255, 0)``.
    line_thickness : int
        Stroke width of grid lines in pixels.
    font_scale : float
        OpenCV font scale for cell labels.
    """
    vis = img_bgr.copy()
    h, w = vis.shape[:2]

    for rl in row_lines:
        cv2.line(vis, (0, rl), (w, rl), line_color, line_thickness)
    for cl in col_lines:
        cv2.line(vis, (cl, 0), (cl, h), line_color, line_thickness)

    for r in range(len(row_lines) - 1):
        for c in range(len(col_lines) - 1):
            cx = (col_lines[c] + col_lines[c + 1]) // 2 - 30
            cy = (row_lines[r] + row_lines[r + 1]) // 2 + 15
            cv2.putText(
                vis, f"{r+1}x{c+1}", (cx, cy),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, label_color,
                line_thickness,
            )

    save_img(out_path, vis)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_img(path: Path | str, image: np.ndarray) -> None:
    """Save an OpenCV image, creating parent directories if needed.

    Parameters
    ----------
    path : Path | str
        Destination file path.
    image : np.ndarray
        Image array as returned by ``cv2.imread`` or any OpenCV operation.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def save_csv(table: list[dict[str, Any]], out_path: Path) -> None:
    """Write a list of dicts to a CSV file (UTF-8, with header).

    Parameters
    ----------
    table : list[dict]
        Rows to write.  All dicts must share the same keys; column order
        follows the key order of the first row.
    out_path : Path
        Destination CSV file path.
    """
    if not table:
        return
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=table[0].keys())
        writer.writeheader()
        writer.writerows(table)
