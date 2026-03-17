# Install Tesseract OCR via winget and Python packages

# 1. Install Tesseract-OCR (UB Mannheim build) if not installed
winget install -e --id UB-Mannheim.TesseractOCR -h --accept-package-agreements --accept-source-agreements

# 2. Add Tesseract directory to user PATH
$dir = "C:\\Program Files\\Tesseract-OCR\\"

$current = [System.Environment]::GetEnvironmentVariable(
    "Path",
    [System.EnvironmentVariableTarget]::User
)

if ($current -notlike "*$dir*") {
    $new = "$current;$dir"
    [System.Environment]::SetEnvironmentVariable(
        "Path",
        $new,
        [System.EnvironmentVariableTarget]::User
    )
    Write-Host "Dodano Tesseract do PATH (user)." -ForegroundColor Green
} else {
    Write-Host "Tesseract już jest w PATH użytkownika." -ForegroundColor Yellow
}

# 3. Install Python packages in current environment
python -m pip install --upgrade pip
python -m pip install --upgrade pillow pytesseract opencv-python

Write-Host "Instalacja Tesseract + Pillow + pytesseract + OpenCV zakończona." -ForegroundColor Green
