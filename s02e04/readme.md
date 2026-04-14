# Info

## Dependencies

### Venv

```bash
python -m venv venv
python -m pip install --upgrade pip
```

### Interpreter


### Użyj palety poleceń:

1. Ctrl+Shift+P → wpisz "Python: Select Interpreter"
2. Kliknij "Enter interpreter path..." → "Find..."
3. Nawiguj do: \venv\Scripts\python.exe i wybierz go
4. Otwórz nowy terminal — powinien automatycznie aktywować właściwy venv

### .vscode/settings.json

VS Code zapisuje wybór w .vscode/settings.json na poziomie workspace.
​### Libs

```bash
pip install python-dotenv
pip install opencv-python pillow pytesseract
pip install matplotlib
pip install scipy
pip install tiktoken
pip install -U langchain-openrouter
```

or

```bash
pip install -r requirements.txt
```

### Create requirments file

```bash
pip freeze > requirements.txt
```

### Scripts

- setup_tesseract_linux.sh
- setup_tesseract_windows.ps1

### Uruchom PowerShell jako Administrator

```powershell
Invoke-WebRequest `
  -Uri "https://github.com/tesseract-ocr/tessdata_best/raw/main/pol.traineddata" `
  -OutFile "C:\Program Files\Tesseract-OCR\tessdata\pol.traineddata"
```

```powershell
Invoke-WebRequest `
  -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/pol.traineddata" `
  -OutFile "C:\Program Files\Tesseract-OCR\tessdata\pol.traineddata"
```

```powershell
# Sprawdź czy plik jest na miejscu
dir "C:\Program Files\Tesseract-OCR\tessdata\pol*"

# Tesseract powinien wylistować język
tesseract --list-langs
```
