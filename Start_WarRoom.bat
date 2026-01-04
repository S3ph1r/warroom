@echo off
TITLE War Room System Controller
COLOR 0A

echo ===================================================
echo       WAR ROOM - SMART STARTUP
echo ===================================================
echo.

:: 1. Navigate to Project Root
cd /d "%~dp0"

echo [1/4] Docker Services - Postgres and Chroma...
:: Docker is smart: if already running, it just verifies state. Safe to run always.
docker-compose up -d postgres chromadb

echo [2/4] Checking Ollama (Port 11434)...
:: Check if Port 11434 is busy
netstat -ano | find "11434" >nul
if %errorlevel% neq 0 goto :START_OLLAMA

:: Port is busy. Is it Ollama?
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find "ollama.exe" >nul
if %errorlevel% equ 0 (
    echo    - Ollama Engine is ALREADY RUNNING.
    goto :AI_CHECK
)
tasklist /FI "IMAGENAME eq ollama app.exe" 2>nul | find "ollama app.exe" >nul
if %errorlevel% equ 0 (
    echo    - Ollama Tray App is ALREADY RUNNING.
    goto :AI_CHECK
)

:: Port is busy by something else (e.g. WSL Relay zombie)
echo    - Port 11434 is busy but Ollama is NOT running.
echo    - Attempting to clear stale process (WSL Relay?)...
powershell -Command "$p = Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1; if ($p) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; echo '      Cleaned up process ID: ' $p }"
timeout /t 2 >nul

:START_OLLAMA
echo    - Starting Native Ollama...
if exist "C:\Users\Roberto\AppData\Local\Programs\Ollama\ollama app.exe" (
    echo    - Launching Tray App...
    start "" "C:\Users\Roberto\AppData\Local\Programs\Ollama\ollama app.exe"
    timeout /t 5 >nul
    goto :AI_CHECK
)

where ollama >nul 2>nul
if %errorlevel% equ 0 (
    echo    - Launching Engine...
    start "WarRoom_AI_Engine" ollama serve
    timeout /t 5 >nul
    goto :AI_CHECK
)

echo    - Native Ollama NOT FOUND. Falling back to WSL...
start "WarRoom_AI_Engine" wsl ollama serve
timeout /t 5 >nul
echo    - Configuring Network Bridge...
powershell -ExecutionPolicy Bypass -File scripts\bridge_wsl.ps1

:AI_CHECK
echo.
echo [2.5/4] Verifying AI Connectivity...
python scripts\check_ollama_status.py
if %errorlevel% neq 0 (
    echo.
    echo WARNING: AI Engine check failed.
    echo.
    pause
)

echo [3/4] Checking Backend (Port 8201)...
netstat -ano | findstr /C:":8201 " >nul
if %errorlevel%==0 (
    echo    - Backend is ALREADY RUNNING.
) else (
    echo    - Starting FastAPI Backend...
    start "WarRoom_Backend" /D "%~dp0" cmd /k venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8201 --host 127.0.0.1
)

echo [4/4] Starting Frontend (Port 5173)...
start "WarRoom_Frontend" /D "%~dp0frontend" cmd /k npm.cmd run dev

echo.
echo ===================================================
echo       SYSTEM READY
echo ===================================================
echo.
timeout /t 5
