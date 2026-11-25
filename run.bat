@echo off
rem Jalankan dashboard EWS di http://localhost:8000 (Ctrl+C untuk berhenti).
cd /d "%~dp0"
rem NumPy cukup 1 thread; mencegah gagal start saat memori laptop sedang penuh
set OPENBLAS_NUM_THREADS=1
venv\Scripts\python.exe -c "import cv2, fastapi" >nul 2>&1 || (
    echo Lingkungan Python belum siap di laptop ini. Jalankan setup.bat dulu.
    pause
    exit /b 1
)
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000/operator"
venv\Scripts\python.exe -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 2
pause
