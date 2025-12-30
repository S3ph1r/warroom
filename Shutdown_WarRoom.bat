@echo off
TITLE War Room System Shutdown
COLOR 0C

echo ===================================================
echo       WAR ROOM - SYSTEM SHUTDOWN
echo ===================================================
echo.

:: 1. Navigate to Project Root (Quoted for safety with spaces)
cd /d "%~dp0"

echo [1/4] 🛑 Stopping Docker Services...
docker-compose down

echo [2/4] 🔪 Killing User Interfaces (Node/Frontend)...
:: Kill via process name
taskkill /F /IM node.exe /T >nul 2>&1
:: Kill via Window Title
taskkill /F /FI "WINDOWTITLE eq WarRoom_Frontend*" /T >nul 2>&1
if %errorlevel%==0 ( echo    - Frontend Stopped. ) else ( echo    - Frontend already clean. )

echo [3/4] 🔪 Killing Backend (Python/Uvicorn)...
:: Kill via Window Title
taskkill /F /FI "WINDOWTITLE eq WarRoom_Backend*" /T >nul 2>&1

:: Robust Port 8201 Kill using PowerShell (kills the actual process listening)
powershell -Command "Get-NetTCPConnection -LocalPort 8201 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
echo    - Cleanup of port 8201 complete.

echo [4/4] 🦙 Stopping Ollama...
:: Ollama in WSL is tricky to kill from CMD, usually we leave it or kill via wsl
:: Force kill any lingering ollama processes in WSL
wsl -e bash -c "pkill -9 ollama || killall -9 ollama" >nul 2>&1
if %errorlevel%==0 ( echo    - Ollama Stopped. ) else ( echo    - Ollama clean. )

echo.
echo ===================================================
echo       ✅ SYSTEM OFFLINE
echo ===================================================
echo.
timeout /t 3
