@echo off
TITLE War Room System Controller
COLOR 0A

echo ===================================================
echo       WAR ROOM - SMART STARTUP
echo ===================================================
echo.

:: 1. Navigate to Project Root
cd /d "%~dp0"

echo [1/4] 🐳 Docker Services (Postgres & Chroma)...
:: Docker is smart: if already running, it just verifies state. Safe to run always.
docker-compose up -d postgres chromadb

echo [2/4] 🦙 Checking Ollama (Port 11434)...
netstat -ano | find "11434" >nul
if %errorlevel%==0 (
    echo    - Ollama is ALREADY RUNNING. Skipping start.
) else (
    echo    - Port 11434 free. Starting Ollama...
    start "WarRoom_AI_Engine" wsl ollama serve
)

echo [3/4] 🚀 Checking Backend (Port 8000)...
netstat -ano | find "8000" >nul
if %errorlevel%==0 (
    echo    - Backend is ALREADY RUNNING. Skipping start.
) else (
    echo    - Port 8000 free. Starting FastAPI...
    start "WarRoom_Backend" cmd /k "call venv\Scripts\activate && uvicorn backend.main:app --reload --port 8000 --host 127.0.0.1"
)

echo [4/4] 🎨 Checking Frontend (Port 5173)...
netstat -ano | find "5173" >nul
if %errorlevel%==0 (
    echo    - Frontend is ALREADY RUNNING. Skipping start.
) else (
    echo    - Port 5173 free. Starting Svelte...
    cd frontend
    start "WarRoom_Frontend" cmd /k "npm run dev"
)

echo.
echo ===================================================
echo       ✅ SYSTEM READY
echo ===================================================
echo.
timeout /t 5
