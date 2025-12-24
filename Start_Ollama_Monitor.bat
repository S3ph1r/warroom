@echo off
TITLE Ollama Live Monitor
COLOR 0E
MODE con:cols=100 lines=20

:LOOP
cls
echo ===================================================
echo           OLLAMA LIVE MONITOR (WSL)
echo ===================================================
echo.
echo Current Time: %TIME%
echo.
wsl ollama ps
echo.
echo ===================================================
echo Press Ctrl+C to stop...
timeout /t 2 >nul
goto LOOP
