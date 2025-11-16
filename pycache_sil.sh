#!/bin/bash

echo "[+] '__pycache__' klasörleri aranıyor..."
find . -type d -name "__pycache__" -print

echo
read -p "[?] Yukarıdaki klasörler silinsin mi? (y/n): " confirm

if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    find . -type d -name "__pycache__" -exec rm -rf {} +
    echo "[✓] Tüm '__pycache__' klasörleri silindi."
else
    echo "[!] İşlem iptal edildi."
fi

