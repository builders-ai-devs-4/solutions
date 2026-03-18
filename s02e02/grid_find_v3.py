import cv2
import os
import sys
from dotenv import load_dotenv
from string import Template
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import get_logger

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
TASK           = os.getenv('TASK')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')
MAP            = os.getenv('SOURCE_URL1')
MAP_RESET      = os.getenv('SOURCE_URL2')

current_folder     = Path(__file__)
parent_folder_path = current_folder.parent
task_data_folder   = parent_folder_path / DATA_FOLDER / TASK_NAME

os.environ["DATA_FOLDER_PATH"]   = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)

map_url       = Template(MAP).substitute(ai_devs_secret=AI_DEVS_SECRET)
map_reset_url = Template(MAP_RESET).substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_URL"]       = str(map_url)
os.environ["MAP_RESET_URL"] = str(map_reset_url)

INPUT_PATH = task_data_folder / "solved_electricity.png"
logger = get_logger(__name__)


# ── WYKRYWANIE ROI SIATKI ──────────────────────────────────────────────────────

def find_grid_roi(gray: np.ndarray, dark_thresh: int = 120,
                  min_area_ratio: float = 0.1) -> tuple[int, int, int, int]:
    """
    Wykrywa bounding box głównej siatki przez największy kontur.
    Zwraca (r0, r1, c0, c1).
    """
    h, w = gray.shape
    _, dark = cv2.threshold(gray, dark_thresh, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    big = [c for c in cnts if cv2.contourArea(c) > h * w * min_area_ratio]
    if not big:
        raise ValueError("Nie znaleziono konturu siatki – sprawdź dark_thresh.")

    x, y, w_box, h_box = cv2.boundingRect(max(big, key=cv2.contourArea))
    return y, y + h_box, x, x + w_box


# ── WYKRYWANIE LINII SIATKI ────────────────────────────────────────────────────

def find_grid_lines_robust(gray: np.ndarray) -> tuple[list[int], list[int]]:
    """
    Wykrywa linie siatki na SUROWYM binarnym obrazie (cv2.THRESH_BINARY).
    NIE używa adaptiveThreshold – ten krok jest celowo pominięty, bo
    adaptiveThreshold wykrywa lokalne krawędzie wewnątrz komórek, co
    generuje fałszywe linie siatki (np. 4x3 zamiast 3x3).

    Pipeline:
    1. THRESH_BINARY (globalny próg 127) → czysty podział ciemne/jasne
    2. Morfologia OPEN z kernelem >= 40% rozmiaru → eliminuje artefakty i szum
    3. find_peaks na profilu jasności → środki linii siatki
    4. Klastrowanie bliskich peaków → jedna linia = jeden środek
    """
    h, w = gray.shape
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    inv = cv2.bitwise_not(binary)

    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.4), 1))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * 0.4)))
    h_lines_mask = cv2.morphologyEx(inv, cv2.MORPH_OPEN, k_h)
    v_lines_mask = cv2.morphologyEx(inv, cv2.MORPH_OPEN, k_v)

    row_profile = h_lines_mask.sum(axis=1).astype(np.float32)
    col_profile = v_lines_mask.sum(axis=0).astype(np.float32)

    def _peaks(profile: np.ndarray) -> list[int]:
        if profile.max() == 0:
            return []
        peaks, _ = find_peaks(profile,
                               height=profile.max() * 0.3,
                               distance=15)
        if len(peaks) == 0:
            return []
        groups = [[peaks[0]]]
        for p in peaks[1:]:
            if p - groups[-1][-1] <= 8:
                groups[-1].append(p)
            else:
                groups.append([p])
        return [int(np.mean(g)) for g in groups]

    return _peaks(row_profile), _peaks(col_profile)


# ── PREPROCESSING KOMÓRKI ──────────────────────────────────────────────────────

def preprocess_cell(cell_gray: np.ndarray) -> np.ndarray:
    """
    Binaryzuje pojedynczą komórkę przez adaptiveThreshold.
    Zwraca obraz z białymi ścieżkami na czarnym tle (gotowy do findContours).

    Stosujemy adaptiveThreshold PER KOMÓRKA (nie na całym ROI), dzięki czemu:
    - każda komórka ma własny lokalny kontrast referencyjny
    - artefakty z sąsiednich komórek nie wpływają na próg
    - nie generuje fałszywych linii siatki podczas split_grid
    """
    mean_val  = cell_gray.mean()
    is_positive = mean_val > 127
    thresh_type = cv2.THRESH_BINARY_INV if is_positive else cv2.THRESH_BINARY

    cell_binary = cv2.adaptiveThreshold(
        cell_gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresh_type,
        blockSize=31,
        C=8
    )

    # Lekkie odszumianie – nie niszczy krawędzi linii
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT,    (3, 3))
    k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    cell_binary = cv2.morphologyEx(cell_binary, cv2.MORPH_CLOSE, k_close, iterations=1)
    cell_binary = cv2.morphologyEx(cell_binary, cv2.MORPH_OPEN,  k_open,  iterations=1)

    return cell_binary  # białe linie na czarnym tle


# ── PODZIAŁ NA KOMÓRKI ─────────────────────────────────────────────────────────

def split_grid(gray: np.ndarray,
               margin: int = 4) -> tuple[dict, list[int], list[int]]:
    """
    Dzieli surowy obraz na komórki siatki.
    WAŻNE: gray powinien być surowym obrazem w skali szarości (bez preprocessingu).
    Zwraca:
      cells     – słownik {(row, col): np.ndarray} (surowe komórki w skali szarości)
      row_lines – lista Y-współrzędnych linii poziomych
      col_lines – lista X-współrzędnych linii pionowych
    """
    row_lines, col_lines = find_grid_lines_robust(gray)
    n_rows = len(row_lines) - 1
    n_cols = len(col_lines) - 1
    logger.info(f"Wykryta siatka: {n_rows} x {n_cols}")

    cells = {}
    for r in range(n_rows):
        for c in range(n_cols):
            r0 = row_lines[r]     + margin
            r1 = row_lines[r + 1] - margin
            c0 = col_lines[c]     + margin
            c1 = col_lines[c + 1] - margin
            cells[(r, c)] = gray[r0:r1, c0:c1]

    return cells, row_lines, col_lines


# ── ZAPIS KOMÓREK ──────────────────────────────────────────────────────────────

def save_cells(cells: dict, output_dir: Path) -> None:
    """Zapisuje każdą komórkę jako osobny plik PNG."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for (r, c), cell in cells.items():
        path = output_dir / f"cell_{r}_{c}.png"
        cv2.imwrite(str(path), cell)
    logger.info(f"Zapisano {len(cells)} komórek → {output_dir}")


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main() -> None:
    img = cv2.imread(str(INPUT_PATH))
    if img is None:
        raise FileNotFoundError(f"Nie znaleziono pliku: {INPUT_PATH}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Wykryj ROI siatki (wytnij z całego obrazu)
    r0, r1, c0, c1 = find_grid_roi(gray)
    roi = gray[r0:r1, c0:c1]
    logger.info(f"ROI: y={r0}:{r1}, x={c0}:{c1}  ({c1-c0}x{r1-r0}px)")

    # 2. Podziel siatkę na komórki (na SUROWYM roi – bez adaptiveThreshold)
    cells, row_lines, col_lines = split_grid(roi)

    # 3. Zapisz surowe komórki (diagnostyka / Vision API)
    cells_dir = task_data_folder / "cells"
    save_cells(cells, cells_dir)

    # 4. Analiza każdej komórki
    grid_result = {}
    for (row, col), cell_gray in cells.items():

        # Preprocessing per komórka – adaptiveThreshold dopiero tutaj
        cell_binary = preprocess_cell(cell_gray)
        # cell_binary: białe linie na czarnym tle → gotowe do findContours

        contours, _ = cv2.findContours(
            cell_binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        logger.debug(f"Komórka ({row},{col}): {len(contours)} konturów")

        # TODO: klasyfikacja kształtu (└ ┐ ─ │ ┼ itd.)
        # shape = classify_cell(cell_binary, Strategy.EDGES)
        # grid_result[(row, col)] = shape


if __name__ == "__main__":
    main()
