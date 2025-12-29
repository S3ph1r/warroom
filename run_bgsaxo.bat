@echo off
echo ==================================================
echo      AVVIO INGESTION BG SAXO (AUTO-DETECT)
echo ==================================================
echo.
echo Searching for latest files in d:\Download\BGSAXO...
python "scripts/run_bgsaxo_pipeline.py"
echo.
echo ==================================================
echo      PROCESSO TERMINATO
echo ==================================================
pause
