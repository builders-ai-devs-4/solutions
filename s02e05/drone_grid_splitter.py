#!/usr/bin/env python3
"""
drone_grid_splitter.py
Splits a drone aerial photo with a visible red grid overlay into individual
cell images. Cells are named cell_RxC.png (1-indexed, row first).

Usage:
    python drone_grid_splitter.py <image_path> [--output <dir>] [--margin <int>] [--min-gap <int>]

Output:
    <output>/cells/cell_RxC.png     - individual cell images
    <output>/grid_visualization.png - annotated grid overlay
    <output>/grid_cells.csv         - metadata table
"""

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np


def _detect_red_mask(img_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0,   120, 100]), np.array([10,  255, 255]))
    mask2 = cv2.inRange(hsv, np.array([170, 120, 100]), np.array([180, 255, 255]))
    return cv2.bitwise_or(mask1, mask2)


def find_grid_lines(profile: np.ndarray, size: int,
                    min_gap: int = 80, thresh_ratio: float = 0.3) -> list[int]:
    threshold = profile.max() * thresh_ratio
    lines, in_peak, start = [], False, 0
    for i, v in enumerate(profile):
        if v > threshold and not in_peak:
            start = i; in_peak = True
        elif v <= threshold and in_peak:
            lines.append((start + i) // 2); in_peak = False
    if in_peak:
        lines.append((start + size) // 2)
    if not lines:
        return []
    filtered = [lines[0]]
    for line in lines[1:]:
        if line - filtered[-1] >= min_gap:
            filtered.append(line)
    return filtered


def detect_grid(img_bgr: np.ndarray, min_gap: int = 80) -> tuple[list[int], list[int]]:
    red_mask = _detect_red_mask(img_bgr)
    h, w = red_mask.shape
    row_sum = red_mask.sum(axis=1).astype(np.float32) / 255
    col_sum = red_mask.sum(axis=0).astype(np.float32) / 255
    return find_grid_lines(row_sum, h, min_gap), find_grid_lines(col_sum, w, min_gap)


def cut_cells(img_bgr, row_lines, col_lines, margin=3):
    cells = {}
    for r in range(len(row_lines) - 1):
        for c in range(len(col_lines) - 1):
            r0, r1 = row_lines[r] + margin, row_lines[r+1] - margin
            c0, c1 = col_lines[c] + margin, col_lines[c+1] - margin
            cells[(r+1, c+1)] = img_bgr[r0:r1, c0:c1]
    return cells


def save_cells(cells, output_dir):
    cells_dir = output_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    table = []
    for (row, col), cell in sorted(cells.items()):
        fname = f"cell_{row}x{col}.png"
        cv2.imwrite(str(cells_dir / fname), cell)
        h, w = cell.shape[:2]
        table.append({"index": f"{row}x{col}", "row": row, "col": col,
                      "width_px": w, "height_px": h, "file": fname})
    return table


def save_visualization(img_bgr, row_lines, col_lines, out_path):
    vis = img_bgr.copy()
    h, w = vis.shape[:2]
    for rl in row_lines:
        cv2.line(vis, (0, rl), (w, rl), (0, 0, 255), 3)
    for cl in col_lines:
        cv2.line(vis, (cl, 0), (cl, h), (0, 0, 255), 3)
    for r in range(len(row_lines) - 1):
        for c in range(len(col_lines) - 1):
            cx = (col_lines[c] + col_lines[c+1]) // 2 - 30
            cy = (row_lines[r] + row_lines[r+1]) // 2 + 15
            # cv2.putText(vis, f"{r+1}x{c+1}", (cx, cy),
            #             cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 0), 3)
            cv2.putText(vis, f"{r+1}x{c+1}", (cx, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)
    cv2.imwrite(str(out_path), vis)


def save_csv(table, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=table[0].keys())
        writer.writeheader()
        writer.writerows(table)


def main():
    parser = argparse.ArgumentParser(description="Split drone photo by red grid into cells.")
    parser.add_argument("image", help="Input image path (e.g. drone.jpg)")
    parser.add_argument("--output",  default="output",  help="Output directory (default: output/)")
    parser.add_argument("--margin",  type=int, default=3,  help="Edge trim per cell in px (default: 3)")
    parser.add_argument("--min-gap", type=int, default=80, help="Min gap between grid lines in px (default: 80)")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"ERROR: File not found: {img_path}", file=sys.stderr); sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading: {img_path}")
    img_bgr = cv2.imread(str(img_path))
    if img_bgr is None:
        print(f"ERROR: Cannot read image: {img_path}", file=sys.stderr); sys.exit(1)

    print("Detecting grid lines...")
    row_lines, col_lines = detect_grid(img_bgr, min_gap=args.min_gap)
    n_rows, n_cols = len(row_lines)-1, len(col_lines)-1
    print(f"Grid: {n_rows} rows x {n_cols} cols")

    cells = cut_cells(img_bgr, row_lines, col_lines, margin=args.margin)
    table = save_cells(cells, output_dir)
    print(f"Cells saved → {output_dir}/cells/")

    save_visualization(img_bgr, row_lines, col_lines, output_dir / "grid_visualization.png")
    print(f"Visualization → {output_dir}/grid_visualization.png")

    save_csv(table, output_dir / "grid_cells.csv")
    print(f"CSV → {output_dir}/grid_cells.csv")

    print("\n=== Cell table ===")
    print(f"{'index':>6}  {'row':>4}  {'col':>4}  {'width_px':>9}  {'height_px':>10}  file")
    print("-" * 55)
    for row in table:
        print(f"{row['index']:>6}  {row['row']:>4}  {row['col']:>4}  {row['width_px']:>9}  {row['height_px']:>10}  {row['file']}")


if __name__ == "__main__":
    main()
