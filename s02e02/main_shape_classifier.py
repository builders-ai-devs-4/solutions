from enum import Enum
import cv2

import os
import sys
from dotenv import load_dotenv
from string import Template

import numpy as np

from s02e02.shape_classify import classify_by_edges, classify_by_skeleton, classify_by_vision

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import api_logger, get_logger
from pathlib import Path

class Strategy(Enum):
    EDGES    = "edges"      # szybka, działa na czystych obrazach
    SKELETON = "skeleton"   # dokładna, wolniejsza
    VISION   = "vision"     # najlepsza, kosztuje tokeny

STRATEGY = Strategy.EDGES   # ← zmień tutaj

def classify_cell(cell_inv: np.ndarray, strategy: Strategy) -> str:
    if strategy == Strategy.EDGES:
        return classify_by_edges(cell_inv)
    elif strategy == Strategy.SKELETON:
        return classify_by_skeleton(cell_inv)
    elif strategy == Strategy.VISION:
        return classify_by_vision(cell_inv)

# W pętli głównej:
grid_result = {}
for (row, col), cell in cells.items():
    cell_inv            = cv2.bitwise_not(cell)
    shape               = classify_cell(cell_inv, STRATEGY)
    grid_result[(row, col)] = shape
    api_logger.info(f"Komórka ({row},{col}): '{shape}'")

# Wyświetl tekstową siatkę
n_rows = max(r for r, _ in grid_result) + 1
n_cols = max(c for _, c in grid_result) + 1

print("┌" + "───┬" * (n_cols - 1) + "───┐")
for r in range(n_rows):
    row_str = "│ " + " │ ".join(grid_result[(r, c)] for c in range(n_cols)) + " │"
    print(row_str)
    if r < n_rows - 1:
        print("├" + "───┼" * (n_cols - 1) + "───┤")
print("└" + "───┴" * (n_cols - 1) + "───┘")
