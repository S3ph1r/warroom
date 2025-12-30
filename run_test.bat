@echo off
title War Room Auto-Ingestion Test
echo ==========================================
echo      WAR ROOM AUTOMATED INGESTION TEST
echo ==========================================
echo.
echo 1. Cleaning old artifacts...
if exist "data\extracted\*.json" del /Q "data\extracted\*.json"
REM if exist "data\extracted\bgsaxo\*.json" del /Q "data\extracted\bgsaxo\*.json"
echo    Cleaned.
echo.
echo 2. Launching Python Orchestration Script...
echo    (This will use Qwen LLM for CSV and PDF)
echo    (Please wait, this may take several minutes)
echo.
python scripts/clean_and_test_bgsaxo.py
echo.
echo ==========================================
echo           TEST COMPLETED (or FAILED)
echo ==========================================
pause
