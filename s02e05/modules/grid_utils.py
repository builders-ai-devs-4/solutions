import csv

import cv2
import os
import sys
from dotenv import load_dotenv
from string import Template
import numpy as np
from pathlib import Path
import requests

def find_grid_lines(profile: np.ndarray, size: int,
                    min_gap: int = 80, thresh_ratio: float = 0.3) -> list[int]:
    """
    Detects grid lines as peaks in the pixel sum profile.
    Works on the output of morphology (horiz/vert lines isolated),
    where grid lines form distinct peaks in the profile.
    """
    threshold = profile.max() * thresh_ratio
    lines = []
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

    filtered = [lines[0]] if lines else []
    for l in lines[1:]:
        if l - filtered[-1] >= min_gap:
            filtered.append(l)
    return filtered

def cut_cells(img_bgr, row_lines, col_lines, margin=3):
    cells = {}
    for r in range(len(row_lines) - 1):
        for c in range(len(col_lines) - 1):
            r0, r1 = row_lines[r] + margin, row_lines[r+1] - margin
            c0, c1 = col_lines[c] + margin, col_lines[c+1] - margin
            cells[(r+1, c+1)] = img_bgr[r0:r1, c0:c1]
    return cells


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


def save_img(file_path: Path | str, image: np.ndarray):
    """Saves an image to the specified file path."""
    path = Path(file_path)
    cv2.imwrite(str(path), image)


def save_csv(table, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=table[0].keys())
        writer.writeheader()
        writer.writerows(table)

# save_visualization(img_bgr, row_lines, col_lines, out_path)
# # Rysowanie siatki + etykiet — identyczne w każdym projekcie

# save_img(path, image)
# # Wrapper cv2.imwrite z tworzeniem katalogu

# save_csv(table, out_path)
# # Zapis listy dict → CSV