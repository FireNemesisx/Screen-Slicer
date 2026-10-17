@echo off
title Screen Slicer
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo [HATA] Uygulama baslatilamadi veya beklenmedik sekilde sonlandi.
    echo Gerekli paketleri kontrol etmek icin su komutu calistirabilirsiniz:
    echo pip install -r requirements.txt
    echo.
    pause
)
