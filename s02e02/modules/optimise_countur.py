

import cv2
import numpy as np

def preprocess_cell(img_path: str) -> np.ndarray:
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    
    # 1. Resize do stałego rozmiaru (np. 128x128)
    img = cv2.resize(img, (128, 128), interpolation=cv2.INTER_CUBIC)
    
    # 2. Binaryzacja adaptacyjna (lepsza niż stały próg przy nierównym oświetleniu)
    img = cv2.adaptiveThreshold(
        img, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=15, C=5
    )
    
    # 3. Morphological cleanup — usuwa szum, wypełnia przerwy w liniach
    kernel = np.ones((2, 2), np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)  # scala przerwy
    img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)   # usuwa szum
    
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
    # h, w = img.shape
    # margin = int(min(h, w) * threshold)  # ~15% szerokości komórki
    
    # return {
    #     'TOP':    img[:margin, :].max() > 127,
    #     'BOTTOM': img[-margin:, :].max() > 127,
    #     'LEFT':   img[:, :margin].max() > 127,
    #     'RIGHT':  img[:, -margin:].max() > 127,
    # }
    
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
