import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import cv2
import numpy as np
from PIL import Image
import pytesseract

import os
import sys
from dotenv import load_dotenv
from string import Template

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



def opencv_maze_analysis(img_path):
    """OpenCV skeletonization + contour detection for maze grid"""
    
    # 1. Wczytaj obraz
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Preprocessing – binarizacja adaptacyjna (lepsza niż stała progowanie)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # 3. Znajdź siatkę (te same granice co wcześniej)
    r0, r1 = 99, 386
    c0, c1 = 237, 524
    grid = binary[r0:r1, c0:c1]
    
    # 4. Skeletonization (zostaw tylko 1px grube linie)
    size = np.size(grid)
    skel = np.zeros(grid.shape, np.uint8)
    
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
    done = False
    
    while(not done):
        eroded = cv2.erode(grid, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(grid, temp)
        skel = cv2.bitwise_or(skel, temp)
        grid = eroded.copy()
        zeros = size - cv2.countNonZero(grid)
        if zeros == size:
            done = True
    
    # 5. Detekcja konturów na skeletonie
    contours, _ = cv2.findContours(skel, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 6. Podziel na komórki i analizuj każdą osobno
    cell_h = (r1 - r0) // 3
    cell_w = (c1 - c0) // 3
    
    cell_patterns = {}
    
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    fig.patch.set_facecolor('black')
    
    for row in range(3):
        for col in range(3):
            rs = r0 + row * cell_h
            re = r0 + (row + 1) * cell_h
            cs = c0 + col * cell_w
            ce = c0 + (col + 1) * cell_w
            
            cell_skel = skel[rs:re, cs:ce]
            
            # Znajdź kontury tylko w tej komórce
            cell_contours, _ = cv2.findContours(cell_skel, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Klasyfikuj kształt na podstawie konturów
            pattern = classify_cell_pattern(cell_contours, cell_h, cell_w)
            cell_patterns[(row, col)] = pattern
            
            # Wizualizacja
            ax = axes[row][col]
            ax.imshow(cell_skel, cmap='gray')
            ax.set_title(f"({row},{col}): {pattern}", color='white', fontsize=12)
            ax.axis('off')
    
    plt.suptitle("Skeleton + Contour Analysis per Cell", color='white', fontsize=16)
    plt.tight_layout()
    plt.savefig("opencv_cells_analysis.png", dpi=120, bbox_inches='tight', facecolor='black')
    plt.close()
    
    # 7. Stwórz tekstową reprezentację
    grid_map = render_grid_map(cell_patterns)
    
    return cell_patterns, grid_map, skel

def classify_cell_pattern(contours, cell_h, cell_w):
    """Klasyfikuj kształt ścieżki w komórce"""
    if len(contours) == 0:
        return "EMPTY"
    
    # Oblicz momenty i punkty środkowe
    areas = [cv2.contourArea(c) for c in contours]
    largest = contours[np.argmax(areas)]
    
    M = cv2.moments(largest)
    if M["m00"] == 0:
        return "DOT"
    
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    
    # Sprawdź połączenia z krawędziami (odległość od środka do krawędzi)
    top_dist = cy
    bot_dist = cell_h - cy
    left_dist = cx
    right_dist = cell_w - cx
    
    connections = []
    if top_dist < 15:   connections.append('T')
    if bot_dist < 15:   connections.append('B')
    if left_dist < 15:  connections.append('L')
    if right_dist < 15: connections.append('R')
    
    # Unicode mapping
    if len(connections) == 2:
        if 'T' in connections and 'R' in connections: return '┘'
        if 'T' in connections and 'L' in connections: return '└'
        if 'B' in connections and 'R' in connections: return '┐'
        if 'B' in connections and 'L' in connections: return '┌'
        if 'T' in connections and 'B' in connections: return '│'
        if 'L' in connections and 'R' in connections: return '─'
    
    elif len(connections) == 3:
        if 'T' not in connections: return '┬'  # R+B+L
        if 'B' not in connections: return '┴'  # T+R+L
        if 'L' not in connections: return '┤'  # T+R+B
        if 'R' not in connections: return '├'  # T+B+L
    
    elif len(connections) == 4:
        return '┼'
    
    return f"{len(contours)}c"  # liczba konturów

def render_grid_map(cell_patterns):
    """Stwórz ładną siatkę tekstową"""
    chars = [['' for _ in range(3)] for _ in range(3)]
    
    for (row, col), pattern in cell_patterns.items():
        chars[row][col] = pattern if len(pattern) <= 2 else pattern[0]
    
    print("\n=== OPENCV GRID MAP ===")
    print("┌───┬───┬───┐")
    for i, row in enumerate(chars):
        print(f"│ {row[0]} │ {row[1]} │ {row[2]} │")
        if i < 2:
            print("├───┼───┼───┤")
    print("└───┴───┴───┘")
    
    return chars

# Uruchomienie
if __name__ == "__main__":
    INPUT_PATH =  str(task_data_folder / "step1_no_bg_norm.jpg")
    patterns, grid, skeleton = opencv_maze_analysis(INPUT_PATH)
