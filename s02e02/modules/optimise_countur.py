

from pathlib import Path

import cv2
import numpy as np

def preprocess_cell(img_path: str) -> np.ndarray:
    
# Wczytujemy obraz
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Nie udało się wczytać: {img_path}")
        
    img = cv2.resize(img, (128, 128), interpolation=cv2.INTER_CUBIC)
    
    # 1. Klasyczna binaryzacja (zamiast adaptacyjnej)
    # Czarne krawędzie rury (wartości ok. 0-50) stają się BIAŁE (255)
    # Szare/białe tło staje się CZARNE (0)
    _, img = cv2.threshold(img, 80, 255, cv2.THRESH_BINARY_INV)
    
    # 2. EKSTREMALNE ZAMKNIĘCIE (Wypełnienie)
    # Zwiększamy kernel do 35x35. To potężny "pędzel", który na 100% stopi
    # ze sobą nawet bardzo odległe równoległe krawędzie rury.
    kernel_fill = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel_fill)
    
    # 3. DEBUGOWANIE - zapiszmy to, co widzi komputer!
    # Zapisze obrazek obok oryginału, dodając do nazwy "_debug.png"
    debug_dir = Path(img_path).parent / 'debug'
    debug_dir.mkdir(exist_ok=True)
    debug_path = debug_dir / (Path(img_path).stem + "_debug.png")
    cv2.imwrite(str(debug_path), img)
    
    return img

def enhance_lines(img: np.ndarray) -> np.ndarray:
    # Wykryj linie poziome i pionowe osobno
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
    
    horizontal = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel_h)
    vertical   = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel_v)
    
    # Połącz — tylko czyste linie H i V, bez szumu
    combined = cv2.add(horizontal, vertical)
    return combined

def check_edge_connectivity(img: np.ndarray, threshold=0.15) -> dict:
    
    # Powyższy kod zakłada, że do tej funkcji trafia obraz po binaryzacji, gdzie linie są białe, a tło czarne. Upewnij się, że tak jest na tym etapie w Twoim potoku!
    h, w = img.shape
    
    # Patrzymy tylko na wąski pasek na samym ŚRODKU krawędzi
    center_x, center_y = w // 2, h // 2
    span = 10  # 10 pikseli w lewo i prawo od środka
    edge_depth = 5 # Sprawdzamy 5 pikseli w głąb od krawędzi
    
    # Wycinamy środkowe punkty styku dla każdej krawędzi
    top_edge = img[0:edge_depth, center_x-span : center_x+span]
    bottom_edge = img[h-edge_depth:h, center_x-span : center_x+span]
    left_edge = img[center_y-span : center_y+span, 0:edge_depth]
    right_edge = img[center_y-span : center_y+span, w-edge_depth:w]
    
    # Jeśli w okienku jest mocno biały piksel (>127), linia wychodzi tą krawędzią
    return {
        'TOP':    int(top_edge.max()) > 127,
        'BOTTOM': int(bottom_edge.max()) > 127,
        'LEFT':   int(left_edge.max()) > 127,
        'RIGHT':  int(right_edge.max()) > 127,
    }

def prepare_for_llm(img: np.ndarray) -> np.ndarray:
    # Powiększ do 256x256 z antyaliasingiem
    img = cv2.resize(img, (256, 256), interpolation=cv2.INTER_LANCZOS4)
    
    # Zwiększ kontrast — linie mają być idealnie czarne, tło białe
    img = cv2.convertScaleAbs(img, alpha=2.0, beta=-50)
           
    # --- NOWE: ODWRÓCENIE KOLORÓW (NEGATYW) ---
    # Algorytmy morfologiczne wyżej działają na białych liniach na czarnym tle.
    # Tutaj odwracamy to dla LLM: czarne linie, białe tło.
    img = cv2.bitwise_not(img)
    
    # --- UWAGA NA RAMKĘ ---
    # Zakomentowałem tę linię. Jeśli narysujesz tu czarną ramkę, LLM
    # pomyśli, że linie dotykają wszystkich krawędzi obrazu.
    # Jeśli narysujesz białą, możesz "odciąć" przewód od krawędzi.
    # Najlepiej pozostawić krawędzie naturalne po odwróceniu kolorów.
    # cv2.rectangle(img, (0, 0), (255, 255), 255, 3)  
    
    return img
    
# Mapowanie: frozenset krawędzi → znak Unicode
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
    
    # Każda krawędź musi być jednoznaczna:
    # albo wyraźnie biała (>threshold) albo wyraźnie czarna (<50)
    for score in scores.values():
        if 50 <= score <= threshold:  # strefa szarości = niepewność
            return False
    return True
