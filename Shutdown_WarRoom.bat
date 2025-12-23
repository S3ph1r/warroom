@echo off
TITLE War Room System Shutdown
COLOR 0C

echo ===================================================
echo       WAR ROOM - SYSTEM SHUTDOWN
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/4] 🛑 Stopping Docker Services...
docker-compose down

echo [2/4] 🔪 Killing User Interfaces (Node/Frontend)...
taskkill /F /IM node.exe /T 2>nul
if %errorlevel%==0 ( echo    - Frontend Stopped. ) else ( echo    - No Frontend found. )

echo [3/4] 🔪 Killing Backend (Python/Uvicorn)...
taskkill /F /IM uvicorn.exe /T 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq WarRoom_Backend*" /T 2>nul
:: Hard cleanup of port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a 2>nul

echo [4/4] 🦙 Stopping Ollama...
:: Ollama in WSL is tricky to kill from CMD, usually we leave it or kill via wsl
wsl pkill ollama 2>nul
if %errorlevel%==0 ( echo    - Ollama Stopped. ) else ( echo    - Ollama clean. )

echo.
echo ===================================================
echo       ✅ SYSTEM OFFLINE
echo ===================================================
echo.
timeout /t 3
