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

TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DEBUG_DIR = Path(TASK_DATA_FOLDER_PATH) / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
CELLS_DIR = Path(TASK_DATA_FOLDER_PATH) / "cells"
CELLS_DIR.mkdir(parents=True, exist_ok=True)

from loggers import agent_logger


def save_img(file_path: Path | str, image: np.ndarray):
    """Saves an image to the specified file path."""
    path = Path(file_path)
    cv2.imwrite(str(path), image)

def find_grid_lines(profile, size, min_gap=50, thresh_ratio=0.2):
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

def _img_binarization(gray):
    
    h, w = gray.shape
  # 1. Binarization: grid lines are very dark (~0-80 on a light background)
    _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    return binary

def _img_morphology(gray, binary):
    h, w = gray.shape
    # 2. Morphology: kernels w//3 and h//3 are longer than 1 cell (~95px)
    #    but shorter than the full grid (~286px) — filters out maze paths,
    #    keeps only separator lines and borders.
    horiz_len = w // 3
    vert_len  = h // 3

    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_len, 1))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vert_len))

    horiz = cv2.dilate(cv2.erode(binary, k_h), k_h)
    vert  = cv2.dilate(cv2.erode(binary, k_v), k_v)
    return horiz, vert

def _img_grid_lines(horiz, vert):
    grid_lines_img = cv2.add(horiz, vert)
    return grid_lines_img

def _img_profile(gray, horiz, vert):
    h, w = gray.shape
    # 3. Profile → grid line detection
    row_sum = horiz.sum(axis=1).astype(np.float32) / 255
    col_sum = vert.sum(axis=0).astype(np.float32) / 255

    row_lines = find_grid_lines(row_sum, h, min_gap=60)
    col_lines = find_grid_lines(col_sum, w, min_gap=60)

    n_rows = len(row_lines) - 1
    n_cols = len(col_lines) - 1

    return row_lines, col_lines, n_rows, n_cols

def _img_visualization(gray, row_lines, col_lines):
    h, w = gray.shape
    # 4. Visualization of detected grid lines on the original image 
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for rl in row_lines:
        cv2.line(vis, (0, rl), (w, rl), (0, 0, 255), 2)   # red = rows
    for cl in col_lines:
        cv2.line(vis, (cl, 0), (cl, h), (255, 0, 0), 2)   # blue = columns
    # Number the cells for easier reference in debugging and classification
    for r in range(len(row_lines) - 1):
        for c in range(len(col_lines) - 1):
            cx = (col_lines[c] + col_lines[c + 1]) // 2 - 10
            cy = (row_lines[r] + row_lines[r + 1]) // 2 + 5
            cv2.putText(vis, f"{r+1},{c+1}", (cx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 180, 0), 2)
    return vis

def _img_cut_cells(gray, row_lines, col_lines, margin=4):
     # 5. Crop cells
    cells = {}
    for r in range(len(row_lines) - 1):
        for c in range(len(col_lines) - 1):
            r0 = row_lines[r] + margin
            r1 = row_lines[r + 1] - margin
            c0 = col_lines[c] + margin
            c1 = col_lines[c + 1] - margin
            cells[(r, c)] = gray[r0:r1, c0:c1]
    return cells

def split_grid(gray, margin=4):
    """
    Splits a grayscale image into grid cells without any prior preprocessing.

    Isolates grid lines using morphological operations (kernel w//3 x h//3) —
    longer than a single cell but shorter than the full grid — effectively
    discarding maze paths inside cells.
    """
    binary = _img_binarization(gray)
    img_file = DEBUG_DIR / "01_binary.png"
    save_img(img_file, binary)
    agent_logger.info(f"[grid_detector] saved binary image: {str(img_file)}")
    
    horiz, vert = _img_morphology(gray, binary)
    img_file = DEBUG_DIR / "02_morph_horiz.png"
    save_img(img_file, horiz)
    agent_logger.info(f"[grid_detector] saved horizontal morphology image: {str(img_file)}")
    img_file = DEBUG_DIR / "03_morph_vert.png"
    save_img(img_file, vert)
    agent_logger.info(f"[grid_detector] saved vertical morphology image: {str(img_file)}")
    
    grid_lines_img = _img_grid_lines(horiz, vert)
    img_file = DEBUG_DIR / "04_grid_lines.png"
    save_img(img_file, grid_lines_img)
    agent_logger.info(f"[grid_detector] saved grid lines image: {str(img_file)}")
    
    row_lines, col_lines, n_rows, n_cols = _img_profile(gray, horiz, vert)
        
    agent_logger.info(f"[grid_detector] detected grid: {n_rows} x {n_cols}")
    agent_logger.info(f"[grid_detector] row_lines: {row_lines}")
    agent_logger.info(f"[grid_detector] col_lines: {col_lines}")
    
    vis = _img_visualization(gray, row_lines, col_lines)
    img_file = Path(TASK_DATA_FOLDER_PATH) / "05_grid_detected.png"
    save_img(img_file, vis)
    agent_logger.info(f"[grid_detector] saved grid visualization image: {str(img_file)}")
    
    cells = _img_cut_cells(gray, row_lines, col_lines, margin)
    return cells, row_lines, col_lines
    

def change_img_to_gray(image_path: Path | str) -> np.ndarray:
    """Reads an image from the given path and converts it to grayscale."""
    img = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray

def shape_analysis(cell):
    # Invert only for analysis - keep original unchanged
    cell_inv = cv2.bitwise_not(cell)
    # Now: white = maze path, black = cell background
    # Skeletonization, findContours, shape classification...
    contours, _ = cv2.findContours(
        cell_inv,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    return contours


def get_grid_cells(image_path: str):
    """Main function to get grid cells as a dict {(row, col): cell_image_array}."""
    image_path = Path(image_path)
    gray = change_img_to_gray(image_path)
    
    img_file = DEBUG_DIR / "00_input_gray.png"
    save_img(img_file, gray)
    agent_logger.info(f"[grid_detector] saved gray image: {str(img_file)}")
    cells, row_lines, col_lines = split_grid(gray)

    for (r, c), cell in cells.items():
        cells_path = CELLS_DIR / f"cell_{r+1}_{c+1}.png"
        cv2.imwrite(str(cells_path), cell)
        agent_logger.info(f"[grid_detector] saved cell image: {str(cells_path)}")
    return str(CELLS_DIR)