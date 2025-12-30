@echo off
echo ==================================================
echo      DEBUG TRADEREPUBLIC: ANALYSIS & EXTRACTION
echo ==================================================
echo.
set FILE="d:\Download\Trade Repubblic\Estratto conto.pdf"

echo [1/2] Running Structural Analysis (LLM)...
python "scripts/analyze_tr_structure.py" %FILE%
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo [2/2] Running Dynamic Parser (Rule-Based Engine)...
python "scripts/parse_tr_dynamic.py" %FILE%
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo ==================================================
echo      EXTRACTION COMPLETE
echo Check the logs above and the output file:
echo d:\Download\Trade Repubblic\Estratto conto.extracted.json
echo ==================================================
pause
exit /b 0

:error
echo.
echo [ERROR] Process failed. Check logs above.
pause
exit /b 1
