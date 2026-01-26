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

# Log temizleme bölümü
echo
echo "[+] Log dosyaları (.log) aranıyor..."
find config/logs -type f -name "*.log" -print 2>/dev/null

echo
read -p "[?] Yukarıdaki log dosyaları silinsin mi? (y/n): " confirm_log

if [[ "$confirm_log" == "y" || "$confirm_log" == "Y" ]]; then
    find config/logs -type f -name "*.log" -exec rm -f {} +
    echo "[✓] Log dosyaları silindi."
else
    echo "[!] Log silme işlemi iptal edildi."
fi
