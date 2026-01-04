@echo off
TITLE War Room System Shutdown
COLOR 0C

echo ===================================================
echo       WAR ROOM - SYSTEM SHUTDOWN
echo ===================================================
echo.

:: 1. Navigate to Project Root (Quoted for safety with spaces)
cd /d "%~dp0"

echo [2/4] 🛑 Killing User Interfaces (Vite/Frontend)...
:: Kill processes by window title prefix using PowerShell
powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle -like 'WarRoom_Frontend*' } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"
taskkill /F /IM node.exe /T >nul 2>&1
echo    - Frontend cleanup attempted.

echo [3/4] 🛑 Killing Backend (FastAPI/Uvicorn)...
:: Kill processes by window title prefix using PowerShell
powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle -like 'WarRoom_Backend*' } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"
:: Robust Port 8201 Kill using PowerShell (kills the actual process listening)
powershell -Command "Get-NetTCPConnection -LocalPort 8201 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
echo    - Backend cleanup attempted.

echo [4/4] 🦙 Stopping Ollama...
:: Kill Native Windows Ollama (Process and Tray App)
taskkill /F /IM "ollama app.exe" /T >nul 2>&1
taskkill /F /IM "ollama.exe" /T >nul 2>&1
if %errorlevel%==0 ( echo    - Native Ollama Stopped. )

:: Force kill any lingering ollama processes in WSL (Backup)
wsl -e bash -c "pkill -9 ollama || killall -9 ollama" >nul 2>&1
if %errorlevel%==0 ( echo    - WSL Ollama Stopped. ) else ( echo    - Ollama clean. )

echo.
echo ===================================================
echo       ✅ SYSTEM OFFLINE
echo ===================================================
echo.
timeout /t 3
