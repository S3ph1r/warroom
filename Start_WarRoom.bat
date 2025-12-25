@echo off
TITLE War Room System Controller
COLOR 0A

echo ===================================================
echo       WAR ROOM - SMART STARTUP
echo ===================================================
echo.

:: 1. Navigate to Project Root
cd /d "%~dp0"

echo [1/4] 🐳 Docker Services - Postgres and Chroma...
:: Docker is smart: if already running, it just verifies state. Safe to run always.
docker-compose up -d postgres chromadb

echo [2/4] 🦙 Checking Ollama (Port 11434)...
netstat -ano | find "11434" >nul
if %errorlevel%==0 (
    echo    - Ollama is ALREADY RUNNING. Skipping start.
) else (
    echo    - Port 11434 free. Starting Ollama...
    start "WarRoom_AI_Engine" wsl ollama serve
    :: Give it a moment to bind
    timeout /t 5 >nul
    
    echo    - Configuring Network Bridge...
    powershell -ExecutionPolicy Bypass -File scripts\bridge_wsl.ps1
)

echo.
echo [2.5/4] 🔌 Verifying AI Connectivity...
python scripts\check_ollama_status.py
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  WARNING: AI Engine check failed.
    echo     The Council might not be able to speak.
    echo     Follow the instructions above [WSL export config].
    echo.
    pause
)

echo [3/4] 🚀 Checking Backend (Port 8000)...
netstat -ano | find "8000" >nul
if %errorlevel%==0 (
    echo    - Backend is ALREADY RUNNING. Skipping start.
) else (
    echo    - Port 8000 free. Starting FastAPI...
    start "WarRoom_Backend" /D "%~dp0" cmd /k venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000 --host 127.0.0.1
)

echo [4/4] 🎨 Checking Frontend (Port 5173)...
netstat -ano | find "5173" >nul
if %errorlevel%==0 (
    echo    - Frontend is ALREADY RUNNING. Skipping start.
) else (
    echo    - Port 5173 free. Starting Svelte...
    start "WarRoom_Frontend" /D "%~dp0frontend" cmd /k npm.cmd run dev
)

echo.
echo ===================================================
echo       ✅ SYSTEM READY
echo ===================================================
echo.
timeout /t 5
