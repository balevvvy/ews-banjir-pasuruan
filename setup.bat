@echo off
rem Buat virtual environment dan pasang dependensi. Jalankan sekali di setiap laptop baru.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
echo === Setup EWS Banjir ===
echo.

rem venv yang disalin dari laptop lain tidak bisa dipakai, jadi dibuat ulang
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Folder venv berasal dari laptop lain atau rusak, dibuat ulang...
        rmdir /s /q venv
    )
)
if exist venv\Scripts\python.exe goto install

rem Cari Python 3.12 atau lebih baru
set "PY="
for %%V in (3.14 3.13 3.12) do (
    if not defined PY (
        py -%%V -c "pass" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [GAGAL] Python 3.12 atau lebih baru tidak ditemukan.
    echo Unduh Python dari https://www.python.org/downloads/
    echo Saat instalasi, centang "Add python.exe to PATH". Lalu jalankan setup.bat lagi.
    pause
    exit /b 1
)

echo Membuat virtual environment dengan: !PY!
!PY! -m venv venv
if errorlevel 1 (
    echo [GAGAL] Tidak bisa membuat virtual environment.
    pause
    exit /b 1
)

:install
echo Memasang dependensi. Butuh internet, bisa beberapa menit...
venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [GAGAL] Instalasi dependensi gagal. Periksa koneksi internet lalu jalankan setup.bat lagi.
    pause
    exit /b 1
)
if not exist config\config.yaml copy config\config.example.yaml config\config.yaml >nul

echo.
venv\Scripts\python.exe -c "import sys, cv2, fastapi; print('Python', sys.version.split()[0], '- OpenCV', cv2.__version__, '- siap dipakai')"
echo.
echo Selesai. Langkah berikutnya: cek_kamera.bat, kalibrasi.bat, lalu run.bat
pause
