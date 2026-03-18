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

# 0. Ustawienia
# INPUT_PATH = "electricity.jpg"
INPUT_PATH =  str(task_data_folder / "solved_electricity.png")
# OUTPUT_STAGE_DIR = "."  # katalog na pośrednie pliki
OUTPUT_STAGE_DIR = str(task_data_folder)
LANG = "pol"            # polski

# 1. Wczytanie i konwersja do gray
img = cv2.imread(INPUT_PATH)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 2. Usunięcie tła (top-hat / difference of blur)
bg_blur = cv2.GaussianBlur(gray, (31, 31), 0)
no_bg = cv2.absdiff(gray, bg_blur)
no_bg_norm = cv2.normalize(no_bg, None, 0, 255, cv2.NORM_MINMAX)

cv2.imwrite(f"{OUTPUT_STAGE_DIR}/step1_no_bg_norm.jpg", no_bg_norm)

# 3. Odszumianie (minimalne, żeby nie zamydlić krawędzi)
bilat = cv2.bilateralFilter(no_bg_norm, d=9, sigmaColor=75, sigmaSpace=75)
median = cv2.medianBlur(bilat, 3)  # 3 zamiast 5, żeby mniej rozmywać

cv2.imwrite(f"{OUTPUT_STAGE_DIR}/step2_denoised.jpg", median)

# 4. Wyostrzanie (unsharp + kernel)
blur_small = cv2.GaussianBlur(median, (5, 5), 0)
sharp = cv2.addWeighted(median, 1.7, blur_small, -0.7, 0)

kernel = np.array([[0, -1, 0],
                   [-1, 5, -1],
                   [0, -1, 0]], dtype=np.float32)
sharp2 = cv2.filter2D(sharp, -1, kernel)

cv2.imwrite(f"{OUTPUT_STAGE_DIR}/step3_sharp2.jpg", sharp2)

# 5. (Opcjonalnie) lekka binarizacja z ręcznie dobranym progiem
#    Jeśli chcesz zostać w szarościach – pomiń ten blok.
THRESH_VAL = 140  # możesz ręcznie potestować np. 120..170
_, binary = cv2.threshold(sharp2, THRESH_VAL, 255, cv2.THRESH_BINARY)

cv2.imwrite(f"{OUTPUT_STAGE_DIR}/step4_binary.jpg", binary)

# Wybierz obraz do OCR:
# - do_gray_ocr: w odcieniach szarości (często lepsze)
# - do_bin_ocr: po lekkim threshold
do_gray_ocr = sharp2
do_bin_ocr = binary

# 6. Odwrócenie kolorów (jeśli chcesz czarny tekst na białym tle)
#    Jeśli już masz taki układ – możesz pominąć.
invert_for_gray = cv2.bitwise_not(do_gray_ocr)
invert_for_bin = cv2.bitwise_not(do_bin_ocr)

cv2.imwrite(f"{OUTPUT_STAGE_DIR}/step5_gray_inv.jpg", invert_for_gray)
cv2.imwrite(f"{OUTPUT_STAGE_DIR}/step5_bin_inv.jpg", invert_for_bin)

# 7. OCR – wybierz wariant, który lepiej czyta (gray / gray_inv / bin / bin_inv)
#    Na start proponuję 'invert_for_gray' (czarny tekst na białym tle).
image_for_ocr = invert_for_gray

pil_img = Image.fromarray(image_for_ocr)
text = pytesseract.image_to_string(pil_img, lang=LANG)

print("=== OCR RESULT ===")
print(text)
