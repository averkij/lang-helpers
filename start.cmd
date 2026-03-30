@echo off
chcp 65001 >nul
echo.
echo  ======================================
echo   Fieldwork Linguistics Tools
echo  ======================================
echo.
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo  [!] Python not found. Install Python 3.11+
    echo      https://www.python.org/downloads/
    pause
    exit /b 1
)
cd /d "%~dp0"
echo  Checking dependencies...
pip install -q -r requirements.txt 2>nul
if %errorlevel% neq 0 (
    echo  [!] Could not install dependencies.
    echo      Try manually: pip install -r requirements.txt
    pause
    exit /b 1
)
echo.
echo  Starting server...
echo  Open in browser: http://localhost:8000
echo.
echo  Press Ctrl+C to stop
echo.
python -X utf8 -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
pause
