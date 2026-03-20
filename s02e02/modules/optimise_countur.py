

from pathlib import Path

import cv2
import numpy as np

def preprocess_cell(img_path: str) -> np.ndarray:
    
# Load image
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Failed to load: {img_path}")
        
    img = cv2.resize(img, (128, 128), interpolation=cv2.INTER_CUBIC)
    
    # 1. Classic binarization (instead of adaptive)
    # Dark pipe edges (values ~0-50) become WHITE (255)
    # Gray/white background becomes BLACK (0)
    _, img = cv2.threshold(img, 80, 255, cv2.THRESH_BINARY_INV)
    
    # 2. EXTREME CLOSING (Fill)
    # Increase kernel to 35x35. This is a very large "brush" that will
    # merge even distant parallel pipe edges.
    kernel_fill = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel_fill)
    
    # 3. DEBUG - save what the algorithm sees
    # Save the debug image next to the original, adding "_debug.png" to the name
    debug_dir = Path(img_path).parent / 'debug'
    debug_dir.mkdir(exist_ok=True)
    debug_path = debug_dir / (Path(img_path).stem + "_debug.png")
    cv2.imwrite(str(debug_path), img)
    
    return img

def enhance_lines(img: np.ndarray) -> np.ndarray:
    # Detect horizontal and vertical lines separately
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
    
    horizontal = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel_h)
    vertical   = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel_v)
    
    # Combine — only clean H and V lines, without noise
    combined = cv2.add(horizontal, vertical)
    return combined

def check_edge_connectivity(img: np.ndarray, threshold=0.15) -> dict:
    
    # This function expects a binarized image where lines are white and background is black.
    # Make sure the pipeline provides that to this stage.
    h, w = img.shape
    
    # Inspect only a narrow strip at the CENTER of each edge
    center_x, center_y = w // 2, h // 2
    span = 10  # 10 pixels left/right from center
    edge_depth = 5  # check 5 pixels inward from the edge
    
    # Crop the central contact regions for each edge
    top_edge = img[0:edge_depth, center_x-span : center_x+span]
    bottom_edge = img[h-edge_depth:h, center_x-span : center_x+span]
    left_edge = img[center_y-span : center_y+span, 0:edge_depth]
    right_edge = img[center_y-span : center_y+span, w-edge_depth:w]
    
    # If the window contains a strongly white pixel (>127), the line exits through that edge
    return {
        'TOP':    int(top_edge.max()) > 127,
        'BOTTOM': int(bottom_edge.max()) > 127,
        'LEFT':   int(left_edge.max()) > 127,
        'RIGHT':  int(right_edge.max()) > 127,
    }

def prepare_for_llm(img: np.ndarray) -> np.ndarray:
    # Resize to 256x256 with anti-aliasing
    img = cv2.resize(img, (256, 256), interpolation=cv2.INTER_LANCZOS4)

    # Increase contrast — lines should be pure black, background white
    img = cv2.convertScaleAbs(img, alpha=2.0, beta=-50)
           
    # --- NEW: INVERT COLORS (NEGATIVE) ---
    # Morphological steps above operate on white lines on black background.
    # For the LLM we invert: black lines on white background.
    img = cv2.bitwise_not(img)

    # --- NOTE ABOUT FRAME ---
    # This line is commented out. Drawing a black frame here would make
    # the LLM think lines touch all image edges. Drawing a white frame
    # could detach a wire from the edge. Best to leave edges natural
    # after color inversion.
    # cv2.rectangle(img, (0, 0), (255, 255), 255, 3)  
    
    return img
    
# Mapping: frozenset of edges → Unicode character
EDGES_TO_CHAR = {
    frozenset():                                ' ',
    frozenset(['LEFT', 'RIGHT']):               '─',
    frozenset(['TOP', 'BOTTOM']):               '│',
    frozenset(['RIGHT', 'TOP']):                '└',
    frozenset(['RIGHT', 'BOTTOM']):             '┌',
    frozenset(['LEFT', 'BOTTOM']):              '┐',
    frozenset(['LEFT', 'TOP']):                 '┘',
    frozenset(['RIGHT', 'TOP', 'BOTTOM']):      '├',
    frozenset(['LEFT', 'TOP', 'BOTTOM']):       '┤',
    frozenset(['LEFT', 'RIGHT', 'BOTTOM']):     '┬',
    frozenset(['LEFT', 'RIGHT', 'TOP']):        '┴',
    frozenset(['LEFT', 'RIGHT', 'TOP', 'BOTTOM']): '┼',
}

def edges_to_char(edges: dict[str, bool]) -> str:
    active = frozenset(k for k, v in edges.items() if v)
    return EDGES_TO_CHAR.get(active, '?')


def is_detection_confident(img: np.ndarray, threshold=200) -> bool:
    h, w = img.shape
    margin = int(min(h, w) * 0.15)
    
    scores = {
        'TOP':    int(img[:margin, :].max()),
        'BOTTOM': int(img[-margin:, :].max()),
        'LEFT':   int(img[:, :margin].max()),
        'RIGHT':  int(img[:, -margin:].max()),
    }


    # Each edge must be unambiguous:
    # either clearly white (>threshold) or clearly black (<50)
    for score in scores.values():
        if 50 <= score <= threshold:  # gray zone = uncertainty
          return False
    return True
