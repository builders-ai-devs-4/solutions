import cv2
import numpy as np

# Podejście 1 – Detekcja krawędzi (T/R/B/L)  najszybsze
# Sprawdza czy ścieżka "wychodzi" przez każdą z 4 krawędzi komórki:
CHAR_MAP = {
    (0,0,0,0): ' ', (1,0,1,0): '│', (0,1,0,1): '─',
    (0,1,1,0): '┐', (1,0,0,1): '└', (1,1,0,0): '┘',
    (0,0,1,1): '┌', (1,1,1,0): '├', (1,0,1,1): '┤',
    (1,1,0,1): '┴', (0,1,1,1): '┬', (1,1,1,1): '┼',
}

def classify_by_edges(cell_inv: np.ndarray, margin: int = 8,
                       strip: int = 10, thresh: float = 0.06) -> str:
    """
    Sprawdza obecność białych pikseli przy każdej krawędzi komórki.
    cell_inv: białe linie na czarnym tle
    """
    h, w   = cell_inv.shape
    bright = (cell_inv > 127).astype(np.float32)

    rmid = h // 2
    cmid = w // 2
    m    = margin

    # Próbkuj ćwiartki bliskie krawędziom (nie sam brzeg – to linia siatki)
    T = bright[m : m + h//4,          cmid-strip//2 : cmid+strip//2].mean()
    B = bright[h - m - h//4 : h - m,  cmid-strip//2 : cmid+strip//2].mean()
    L = bright[rmid-strip//2 : rmid+strip//2, m : m + w//4         ].mean()
    R = bright[rmid-strip//2 : rmid+strip//2, w - m - w//4 : w - m ].mean()

    key = (int(T > thresh), int(R > thresh),
           int(B > thresh), int(L > thresh))
    return CHAR_MAP.get(key, '?')


def skeletonize(binary: np.ndarray) -> np.ndarray:
    skel = np.zeros_like(binary)
    el   = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    img  = binary.copy()
    while True:
        eroded = cv2.erode(img, el)
        temp   = cv2.subtract(img, cv2.dilate(eroded, el))
        skel   = cv2.bitwise_or(skel, temp)
        img    = eroded
        if cv2.countNonZero(img) == 0:
            break
    return skel

# Podejście 2 – Szkielet + analiza węzłów najdokładniejsze
# Skeletonizuje ścieżkę i zlicza połączenia w centrum komórki.
def classify_by_skeleton(cell_inv: np.ndarray) -> str:
    """
    Szkieletyzuje ścieżkę i sprawdza w jakich kierunkach
    wychodzi ze środka komórki.
    """
    h, w  = cell_inv.shape
    skel  = skeletonize(cell_inv)

    # Podziel szkielet na 9 stref (3x3)
    h3, w3 = h // 3, w // 3
    zones = {
        'T': skel[0:h3,      w3:2*w3  ],   # górny środek
        'B': skel[2*h3:h,    w3:2*w3  ],   # dolny środek
        'L': skel[h3:2*h3,   0:w3     ],   # lewy środek
        'R': skel[h3:2*h3,   2*w3:w   ],   # prawy środek
    }

    key = tuple(int(zones[d].any()) for d in ['T', 'R', 'B', 'L'])
    return CHAR_MAP.get(key, '?')

# Podejście 3 – Vision API (GPT-4o) najbardziej elastyczne
# Idealne gdy kształty są nieregularne lub obraz zaszumiony:

import base64
from openai import OpenAI
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

PROMPT = """Patrzysz na pojedynczą komórkę schematu połączeń elektrycznych.
Wewnątrz komórki jest ścieżka/linia która łączy krawędzie.
Odpowiedz TYLKO jednym znakiem Unicode opisującym kształt ścieżki:
│ ─ └ ┘ ┌ ┐ ├ ┤ ┬ ┴ ┼ lub spacja jeśli puste.
Żadnych innych słów."""

def classify_by_vision(cell: np.ndarray) -> str:
    """Wysyła komórkę do GPT-4o Vision i zwraca znak Unicode."""
    _, buf = cv2.imencode('.png', cell)
    b64    = base64.b64encode(buf).decode('utf-8')

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text",  "text": PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}",
                               "detail": "low"}},
            ]
        }],
        max_tokens=5,
        temperature=0,
    )
    return response.choices[0].message.content.strip()
