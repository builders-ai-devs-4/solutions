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
from loggers import agent_logger



def save_debug(name: str, image: np.ndarray):
    """Zapisuje obraz pośredni do folderu debug/."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / name
    cv2.imwrite(str(path), image)
    agent_logger.info(f"[debug] zapisano: {path.relative_to(task_data_folder)}")

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
    - działa bezpośrednio na surowym obrazie szarym.

    Zapisuje obrazy pośrednie do debug/:
      01_binary.png         - binaryzacja wejścia
      02_morph_horiz.png    - tylko poziome linie siatki
      03_morph_vert.png     - tylko pionowe linie siatki
      04_grid_lines.png     - suma: horiz + vert
      05_grid_detected.png  - oryginał z naniesionymi wykrytymi liniami
    """
    h, w = gray.shape

    # 1. Binaryzacja: linie siatki są bardzo ciemne (~0-80 na jasnym tle)
    _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    save_debug("01_binary.png", binary)

    # 2. Morfologia: kernel w//3 i h//3 jest dłuższy niż 1 komórka (~95px),
    #    ale krótszy niż cała siatka (~286px) - filtruje ścieżki labiryntu,
    #    zachowuje tylko linie separatorów i obramowania.
    horiz_len = w // 3
    vert_len  = h // 3

    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_len, 1))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vert_len))

    horiz = cv2.dilate(cv2.erode(binary, k_h), k_h)
    vert  = cv2.dilate(cv2.erode(binary, k_v), k_v)
    save_debug("02_morph_horiz.png", horiz)
    save_debug("03_morph_vert.png", vert)

    grid_lines_img = cv2.add(horiz, vert)
    save_debug("04_grid_lines.png", grid_lines_img)

    # 3. Profil → wykrycie linii siatki
    row_sum = horiz.sum(axis=1).astype(np.float32) / 255
    col_sum = vert.sum(axis=0).astype(np.float32) / 255

    row_lines = find_grid_lines(row_sum, h, min_gap=60)
    col_lines = find_grid_lines(col_sum, w, min_gap=60)

    n_rows = len(row_lines) - 1
    n_cols = len(col_lines) - 1
    print(f"Wykryta siatka: {n_rows} x {n_cols}")
    print(f"  row_lines: {row_lines}")
    print(f"  col_lines: {col_lines}")

    # 4. Wizualizacja wykrytych linii na oryginale
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for rl in row_lines:
        cv2.line(vis, (0, rl), (w, rl), (0, 0, 255), 2)   # czerwone = wiersze
    for cl in col_lines:
        cv2.line(vis, (cl, 0), (cl, h), (255, 0, 0), 2)   # niebieskie = kolumny
    # Ponumeruj komórki
    for r in range(n_rows):
        for c in range(n_cols):
            cx = (col_lines[c] + col_lines[c + 1]) // 2 - 10
            cy = (row_lines[r] + row_lines[r + 1]) // 2 + 5
            cv2.putText(vis, f"{r+1},{c+1}", (cx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 180, 0), 2)
    save_debug("05_grid_detected.png", vis)

    # 5. Wycinanie komórek
    cells = {}
    for r in range(n_rows):
        for c in range(n_cols):
            r0 = row_lines[r] + margin
            r1 = row_lines[r + 1] - margin
            c0 = col_lines[c] + margin
            c1 = col_lines[c + 1] - margin
            cells[(r, c)] = gray[r0:r1, c0:c1]

    return cells, row_lines, col_lines
