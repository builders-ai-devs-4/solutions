"""
drone_grid_splitter.py
======================
Splits a drone aerial photo with a **red** grid overlay into individual
cell images.

This module contains only the drone-specific detection logic (_detect_red_mask).
All generic grid operations are delegated to ``libs.grid_utils``.

Usage (CLI)
-----------
    python drone_grid_splitter.py drone.jpg --output output/

Usage (API)
-----------
    from drone_grid_splitter import detect_grid
    from libs.grid_utils import cut_cells, save_cells, save_visualization, save_csv

    img = cv2.imread("drone.jpg")
    row_lines, col_lines = detect_grid(img)
    cells = cut_cells(img, row_lines, col_lines)
    ...

Output layout
-------------
    <output>/
        cells/
            cell_1x1.png
            cell_1x2.png
            ...
        grid_visualization.png
        grid_cells.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# Adjust the import path if grid_utils lives in a different location
sys.path.append(str(Path(__file__).parent.parent / "libs"))
from grid_utils import (
    find_grid_lines,
    cut_cells,
    save_cells,
    save_visualization,
    save_img,
    save_csv,
)


# ---------------------------------------------------------------------------
# Drone-specific: red grid line detection via HSV masking
# ---------------------------------------------------------------------------

def _detect_red_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Isolate red-coloured pixels using the HSV colour space.

    Red hue wraps around 0°/180° in OpenCV's HSV wheel, so two ranges
    are combined with a bitwise OR.

    Parameters
    ----------
    img_bgr : np.ndarray
        Input image in BGR format (as loaded by ``cv2.imread``).

    Returns
    -------
    np.ndarray
        Binary mask (uint8, 0/255) where 255 = red pixel.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # Lower red range: hue 0–10°
    mask_lo = cv2.inRange(hsv, np.array([0,   120, 100]), np.array([10,  255, 255]))
    # Upper red range: hue 170–180°
    mask_hi = cv2.inRange(hsv, np.array([170, 120, 100]), np.array([180, 255, 255]))
    return cv2.bitwise_or(mask_lo, mask_hi)


def detect_grid(
    img_bgr: np.ndarray,
    min_gap: int = 80,
    thresh_ratio: float = 0.3,
) -> tuple[list[int], list[int]]:
    """Detect red grid lines and return their pixel positions.

    Produces a binary red mask, then computes row/column sum profiles
    and delegates peak detection to the generic :func:`find_grid_lines`.

    Parameters
    ----------
    img_bgr : np.ndarray
        Input image in BGR format.
    min_gap : int
        Minimum pixel distance between two accepted grid lines.
        Should be slightly smaller than the narrowest expected cell.
    thresh_ratio : float
        Passed through to :func:`find_grid_lines` — fraction of the
        profile maximum used as the detection threshold.

    Returns
    -------
    tuple[list[int], list[int]]
        ``(row_lines, col_lines)`` — pixel Y and X positions of all
        detected grid separators, borders included.
    """
    red_mask = _detect_red_mask(img_bgr)
    h, w = red_mask.shape

    row_sum = red_mask.sum(axis=1).astype(np.float32) / 255
    col_sum = red_mask.sum(axis=0).astype(np.float32) / 255

    row_lines = find_grid_lines(row_sum, h, min_gap=min_gap, thresh_ratio=thresh_ratio)
    col_lines = find_grid_lines(col_sum, w, min_gap=min_gap, thresh_ratio=thresh_ratio)
    return row_lines, col_lines


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split a drone photo with a red grid overlay into labelled cell images."
    )
    parser.add_argument("image",        help="Input image path (e.g. drone.jpg)")
    parser.add_argument("--output",     default="output",  help="Output directory  (default: output/)")
    parser.add_argument("--margin",     type=int, default=3,  help="Edge trim per cell in px  (default: 3)")
    parser.add_argument("--min-gap",    type=int, default=80, help="Min gap between grid lines in px  (default: 80)")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"ERROR: file not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading: {img_path}")
    img_bgr = cv2.imread(str(img_path))
    if img_bgr is None:
        print(f"ERROR: cannot read image: {img_path}", file=sys.stderr)
        sys.exit(1)

    print("Detecting red grid lines...")
    row_lines, col_lines = detect_grid(img_bgr, min_gap=args.min_gap)
    n_rows, n_cols = len(row_lines) - 1, len(col_lines) - 1
    print(f"Grid detected: {n_rows} rows x {n_cols} cols")
    print(f"  row_lines : {row_lines}")
    print(f"  col_lines : {col_lines}")

    cells = cut_cells(img_bgr, row_lines, col_lines, margin=args.margin)
    table = save_cells(cells, output_dir)
    print(f"Cells saved  → {output_dir}/cells/  ({len(table)} files)")

    vis_path = output_dir / "grid_visualization.png"
    save_visualization(img_bgr, row_lines, col_lines, vis_path)
    print(f"Vis saved    → {vis_path}")

    csv_path = output_dir / "grid_cells.csv"
    save_csv(table, csv_path)
    print(f"CSV saved    → {csv_path}")

    # Pretty-print the cell table to stdout
    print("\n=== Cell index table ===")
    hdr = f"  {'index':>6}  {'row':>4}  {'col':>4}  {'width_px':>9}  {'height_px':>10}  file"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for row in table:
        print(f"  {row['index']:>6}  {row['row']:>4}  {row['col']:>4}"
              f"  {row['width_px']:>9}  {row['height_px']:>10}  {row['file']}")


if __name__ == "__main__":
    main()
