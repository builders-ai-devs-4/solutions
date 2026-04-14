#!/usr/bin/env bash
set -e

echo "==> Aktualizacja listy pakietów..."
sudo apt update

echo "==> Instalacja Tesseract OCR + polski język..."
sudo apt install -y tesseract-ocr tesseract-ocr-pol

echo "==> Sprawdzanie wersji Tesseract..."
tesseract --version || {
  echo "Tesseract nie jest widoczny w PATH."
  exit 1
}

echo "==> Instalacja python3-pip (jeśli brak)..."
sudo apt install -y python3-pip

echo "==> Aktualizacja pip i instalacja paczek Python: pillow, pytesseract, opencv-python..."
python3 -m pip install --user --upgrade pip
python3 -m pip install --user --upgrade pillow pytesseract opencv-python

echo "==> Gotowe."
echo "Sprawdź w Pythonie:"
echo "  python3"
echo "  >>> import pytesseract, cv2"
echo "  >>> from PIL import Image"
echo "  >>> print(pytesseract.image_to_string(Image.open('electricity.jpg'), lang='pol'))"
