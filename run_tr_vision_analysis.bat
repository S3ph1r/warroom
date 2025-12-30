@echo off
echo ==================================================
echo      TRADE REPUBLIC: VISION-BASED ANALYSIS
echo      Model: Llama 3.2 Vision (11B)
echo ==================================================
echo.
set FILE="d:\Download\Trade Repubblic\Estratto conto.pdf"

echo [1/3] Vision Analysis (Analyzing PDF pages)...
echo This will take 2-5 minutes...
echo.
python "scripts/analyze_tr_vision.py" %FILE%
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo [2/3] Copying vision rules to main rules file...
copy /Y "d:\Download\Trade Repubblic\Estratto conto.vision.rules.json" "d:\Download\Trade Repubblic\Estratto conto.pdf.rules.json" >nul
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Vision rules file not found, parser will use existing rules
)

echo.
echo [3/3] Testing Parser with Vision Rules...
python "scripts/parse_tr_dynamic.py" %FILE%
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo ==================================================
echo      ANALYSIS COMPLETE
echo ==================================================
echo.
echo OUTPUT FILES:
echo   - Vision Rules: d:\Download\Trade Repubblic\Estratto conto.vision.rules.json
echo   - Extracted Data: d:\Download\Trade Repubblic\Estratto conto.extracted.json
echo.
echo NEXT STEPS:
echo   - Check if "type" field is no longer "UNKNOWN"
echo   - If results are bad, run: .\switch_to_llama32_vision.bat
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] Process failed. Check logs above.
echo.
echo TROUBLESHOOTING:
echo   - If "poppler not found": Install Poppler (see docs\VISION_SETUP.md)
echo   - If Vision Model timeout: Model may still be loading, wait 30s and retry
echo   - If JSON parse error: LLaVA may not be suitable, try Llama 3.2 Vision
echo.
pause
exit /b 1
