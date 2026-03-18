import cv2

import os
import sys
from dotenv import load_dotenv
from string import Template

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import get_logger
# os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
from pathlib import Path
import requests

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
TASK           = os.getenv('TASK')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')
MAP = os.getenv('SOURCE_URL1')
MAP_RESET = os.getenv('SOURCE_URL2')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
os.environ["DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)

map_template = Template(MAP)
map_url = map_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_URL"] = str(map_url)

map_reset_template = Template(MAP_RESET)
map_reset_url = map_reset_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_RESET_URL"] = str(map_reset_url)

INPUT_PATH =  task_data_folder / "solved_electricity.png"
# INPUT_PATH =  task_data_folder / "step2_denoised.jpg"

def find_grid_lines(profile, size, darkness_thresh=0.25, min_gap=30):
    max_val = profile.max()
    dark = profile < max_val * darkness_thresh

    lines = []
    in_line = False
    start = 0
    for i, d in enumerate(dark):
        if d and not in_line:
            start = i
            in_line = True
        elif not d and in_line:
            lines.append((start + i) // 2)
            in_line = False
    if in_line:
        lines.append((start + size) // 2)

    # Usuń linie zbyt blisko siebie (grube obramowania)
    filtered = [lines[0]]
    for l in lines[1:]:
        if l - filtered[-1] >= min_gap:
            filtered.append(l)

    return filtered

def _filter_small_segments(lines, min_ratio=0.4):
    if len(lines) < 3:
        return lines
    segments = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    avg = sum(segments) / len(segments)
    result = [lines[0]]
    for i, seg in enumerate(segments):
        if seg >= avg * min_ratio:
            result.append(lines[i + 1])
    return result


def split_grid(gray, darkness_thresh=0.25, min_gap=30, margin=4):
    h, w = gray.shape

    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

    row_sum = binary.sum(axis=1).astype(np.float32)
    col_sum = binary.sum(axis=0).astype(np.float32)
    row_lines = _filter_small_segments(find_grid_lines(row_sum, h, darkness_thresh, min_gap))
    col_lines = _filter_small_segments(find_grid_lines(col_sum, w, darkness_thresh, min_gap))
    # row_lines = find_grid_lines(row_sum, h, darkness_thresh, min_gap)
    # col_lines = find_grid_lines(col_sum, w, darkness_thresh, min_gap)

    n_rows = len(row_lines) - 1
    n_cols = len(col_lines) - 1
    print(f"Wykryta siatka: {n_rows} x {n_cols}")

    cells = {}
    for r in range(n_rows):
        for c in range(n_cols):
            r0 = row_lines[r]     + margin
            r1 = row_lines[r + 1] - margin
            c0 = col_lines[c]     + margin
            c1 = col_lines[c + 1] - margin
            cells[(r, c)] = gray[r0:r1, c0:c1]

    return cells, row_lines, col_lines

def find_grid_roi(gray, dark_thresh=120, min_area_ratio=0.1):
    h, w = gray.shape

    # Zbinaryzuj – wytnij ciemne piksele (linie siatki)
    _, dark = cv2.threshold(gray, dark_thresh, 255, cv2.THRESH_BINARY_INV)

    # Znajdź kontury zewnętrzne
    cnts, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Odrzuć małe (szumy) – zachowaj tylko te > 10% rozmiaru obrazu
    big = [c for c in cnts if cv2.contourArea(c) > h * w * min_area_ratio]
    largest = max(big, key=cv2.contourArea)

    x, y, w_box, h_box = cv2.boundingRect(largest)
    return y, y + h_box, x, x + w_box   # r0, r1, c0, c1

def find_grid_roi_projection(gray, is_positive=True, margin=5):
    h, w = gray.shape

    # Dla pozytywa ciemne = linie, dla negatywu jasne = linie
    mode = cv2.THRESH_BINARY_INV if is_positive else cv2.THRESH_BINARY
    _, mask = cv2.threshold(gray, 127, 255, mode)

    # Zsumuj każdy wiersz i każdą kolumnę osobno
    row_sum = mask.sum(axis=1)   # shape: (height,)
    col_sum = mask.sum(axis=0)   # shape: (width,)

    # Znajdź zakres gdzie jest zawartość (> 5% maksimum)
    rows = np.where(row_sum > row_sum.max() * 0.05)[0]
    cols = np.where(col_sum > col_sum.max() * 0.05)[0]

    return (max(0, rows[0] - margin), min(h, rows[-1] + margin),
            max(0, cols[0] - margin), min(w, cols[-1] + margin))

img  = cv2.imread(str(INPUT_PATH))

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 1. Wykryj ROI dynamicznie
r0, r1, c0, c1 = find_grid_roi(gray)   # Metoda 1
# 2. Wytnij
roi = gray[r0:r1, c0:c1]

# 3. Dalsze przetwarzanie
adapt = cv2.adaptiveThreshold(roi, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV, 51, 8)

result = cv2.bitwise_not(adapt)
cv2.imwrite(str(task_data_folder / f"{INPUT_PATH.stem}_binary.jpg"), result)

# 2. Usunięcie tła (top-hat / difference of blur)
bg_blur = cv2.GaussianBlur(gray, (31, 31), 0)
no_bg = cv2.absdiff(gray, bg_blur)
no_bg_norm = cv2.normalize(no_bg, None, 0, 255, cv2.NORM_MINMAX)

# 3. Odszumianie (minimalne, żeby nie zamydlić krawędzi)
bilat = cv2.bilateralFilter(no_bg_norm, d=9, sigmaColor=75, sigmaSpace=75)
median = cv2.medianBlur(bilat, 3)  # 3 zamiast 5, żeby mniej rozmywać

# 4. Wyostrzanie (unsharp + kernel)
blur_small = cv2.GaussianBlur(median, (5, 5), 0)
sharp = cv2.addWeighted(median, 1.7, blur_small, -0.7, 0)

kernel = np.array([[0, -1, 0],
                   [-1, 5, -1],
                   [0, -1, 0]], dtype=np.float32)
sharp2 = cv2.filter2D(sharp, -1, kernel)

cv2.imwrite(str(task_data_folder / f"{INPUT_PATH.stem}_binary_sharp2.jpg"), sharp2)


r0, r1, c0, c1 = find_grid_roi_projection(gray) 
roi = gray[r0:r1, c0:c1]

adapt = cv2.adaptiveThreshold(roi, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV, 51, 8)
result = cv2.bitwise_not(adapt)
cv2.imwrite(str(task_data_folder / f"{INPUT_PATH.stem}_binary_proj.jpg"), result)

img  = cv2.imread(str(task_data_folder / f"{INPUT_PATH.stem}_binary.jpg"))
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ── ETAP 1: podział ──────────────────────────────
# Oryginał: czarne linie siatki → szukamy minimów profilu
cells, row_lines, col_lines = split_grid(gray)
# cells = { (0,0): array, (0,1): array, ... (2,2): array }

# ── ETAP 2: analiza kształtu ─────────────────────
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


cells_dir_path =  task_data_folder / "cells"
cells_dir_path.mkdir(parents=True, exist_ok=True)

cells, _, _ = split_grid(gray)

for (r, c), cell in cells.items():
    cells_path = cells_dir_path / f"cell_{r}_{c}.png"
    cv2.imwrite(str(cells_path), cell) 

# Wynik na dysku:
# cells/cell_0_0.png
# cells/cell_0_1.png
# ...
# cells/cell_2_2.png
