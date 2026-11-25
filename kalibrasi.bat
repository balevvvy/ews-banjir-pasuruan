@echo off
rem Kalibrasi: ambil referensi botol kosong, pilih ROI, klik batas Waspada dan Siaga.
cd /d "%~dp0"
rem NumPy cukup 1 thread; mencegah gagal start saat memori laptop sedang penuh
set OPENBLAS_NUM_THREADS=1
venv\Scripts\python.exe -c "import cv2" >nul 2>&1 || (
    echo Lingkungan Python belum siap di laptop ini. Jalankan setup.bat dulu.
    pause
    exit /b 1
)
venv\Scripts\python.exe scripts\kalibrasi.py
pause
