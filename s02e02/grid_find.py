import cv2
import os
import sys
from dotenv import load_dotenv
from string import Template
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import get_logger
from pathlib import Path
import requests

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
TASK = os.getenv('TASK')
SOLUTION_URL = os.getenv('SOLUTION_URL')
DATA_FOLDER = os.getenv('DATA_FOLDER')
TASK_NAME = os.getenv('TASK_NAME')
MAP = os.getenv('SOURCE_URL1')
MAP_RESET = os.getenv('SOURCE_URL2')

current_folder = Path(__file__)
parent_folder_path = current_folder.parent
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
os.environ["DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)

map_template = Template(MAP)
map_url = map_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_URL"] = str(map_url)

map_reset_template = Template(MAP_RESET)
map_reset_url = map_reset_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_RESET_URL"] = str(map_reset_url)

INPUT_PATH = task_data_folder / "solved_electricity.png"
# INPUT_PATH = task_data_folder / "step2_denoised.jpg"


def find_grid_lines(profile, size, min_gap=50, thresh_ratio=0.2):
    """
    Wykrywa linie siatki jako szczyty profilu sumy pikseli.
    Działa na wyjściu morfologii (horiz/vert linie wyizolowane),
    gdzie linie siatki tworzą wyraźne piki w profilu.
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


def split_grid(gray, margin=4):
    """
    Dzieli obraz na komórki siatki.

    Używa morfologii z długim kernelem (w//3, h//3) aby wyizolować
    wyłącznie linie siatki (przebiegające przez cały wymiar siatki),
    odrzucając ścieżki labiryntu wewnątrz komórek (krótsze niż 1 komórka).

    Nie wymaga wcześniejszego preprocessingu (adaptiveThreshold, blur itp.)
    – działa bezpośrednio na surowym obrazie szarym.
    """
    h, w = gray.shape

    # Binaryzacja: linie siatki są bardzo ciemne (~0-80 na jasnym tle)
    _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

    # Morfologia: kernel w//3 i h//3 jest dłuższy niż 1 komórka (~95px),
    # ale krótszy niż cała siatka (~286px) – filtruje ścieżki labiryntu,
    # zachowuje tylko linie separatorów i obramowania.
    horiz_len = w // 3
    vert_len  = h // 3

    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_len, 1))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vert_len))

    horiz = cv2.dilate(cv2.erode(binary, k_h), k_h)
    vert  = cv2.dilate(cv2.erode(binary, k_v), k_v)

    row_sum = horiz.sum(axis=1).astype(np.float32) / 255
    col_sum = vert.sum(axis=0).astype(np.float32) / 255

    row_lines = find_grid_lines(row_sum, h, min_gap=60)
    col_lines = find_grid_lines(col_sum, w, min_gap=60)

    n_rows = len(row_lines) - 1
    n_cols = len(col_lines) - 1
    print(f"Wykryta siatka: {n_rows} x {n_cols}")

    cells = {}
    for r in range(n_rows):
        for c in range(n_cols):
            r0 = row_lines[r] + margin
            r1 = row_lines[r + 1] - margin
            c0 = col_lines[c] + margin
            c1 = col_lines[c + 1] - margin
            cells[(r, c)] = gray[r0:r1, c0:c1]

    return cells, row_lines, col_lines


def find_grid_roi(gray, dark_thresh=120, min_area_ratio=0.1):
    h, w = gray.shape
    _, dark = cv2.threshold(gray, dark_thresh, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    big = [c for c in cnts if cv2.contourArea(c) > h * w * min_area_ratio]
    largest = max(big, key=cv2.contourArea)
    x, y, w_box, h_box = cv2.boundingRect(largest)
    return y, y + h_box, x, x + w_box  # r0, r1, c0, c1


def find_grid_roi_projection(gray, is_positive=True, margin=5):
    h, w = gray.shape
    mode = cv2.THRESH_BINARY_INV if is_positive else cv2.THRESH_BINARY
    _, mask = cv2.threshold(gray, 127, 255, mode)
    row_sum = mask.sum(axis=1)
    col_sum = mask.sum(axis=0)
    rows = np.where(row_sum > row_sum.max() * 0.05)[0]
    cols = np.where(col_sum > col_sum.max() * 0.05)[0]
    return (max(0, rows[0] - margin), min(h, rows[-1] + margin),
            max(0, cols[0] - margin), min(w, cols[-1] + margin))


# ── Wczytanie obrazu ─────────────────────────────────────────────────────────
img = cv2.imread(str(INPUT_PATH))
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ── ETAP 1: podział na komórki ───────────────────────────────────────────────
# split_grid działa bezpośrednio na surowym gray – nie potrzeba preprocessingu
cells, row_lines, col_lines = split_grid(gray)
# cells = { (0,0): array, (0,1): array, ... (2,2): array }

# ── ETAP 2: analiza kształtu ─────────────────────────────────────────────────
for (row, col), cell in cells.items():
    # Odwróć tylko do analizy – oryginał zostawiasz niezmieniony
    cell_inv = cv2.bitwise_not(cell)
    # Teraz: białe = ścieżka labiryntu, czarne = tło komórki
    # Skeletonizacja, findContours, klasyfikacja kształtu...
    contours, _ = cv2.findContours(
        cell_inv,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

# ── ETAP 3: zapis komórek na dysk ────────────────────────────────────────────
cells_dir_path = task_data_folder / "cells"
cells_dir_path.mkdir(parents=True, exist_ok=True)

cells, _, _ = split_grid(gray)

for (r, c), cell in cells.items():
    cells_path = cells_dir_path / f"cell_{r}_{c}.png"
    cv2.imwrite(str(cells_path), cell)
