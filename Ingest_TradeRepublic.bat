@echo off
setlocal enabledelayedexpansion

:: ==================================================
::    TRADE REPUBLIC: END-TO-END INGESTION
:: ==================================================

:: CONFIG
set "PDF_FILE=d:\Download\Trade Repubblic\Estratto conto.pdf"
set "SCRIPTS_DIR=scripts"

echo ==================================================
echo      TRADE REPUBLIC END-TO-END INGESTION
echo ==================================================
echo Target: "%PDF_FILE%"

:: MASTER ORCHESTRATOR
python "%SCRIPTS_DIR%\ingest_tr_full.py" "%PDF_FILE%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ PIPELINE FAILED with error code %ERRORLEVEL%
) else (
    echo.
    echo ==================================================
    echo      PIPELINE COMPLETED SUCCESSFULLY
    echo ==================================================
)
pause
