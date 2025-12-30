@echo off
echo ==================================================
echo   SWITCHING TO LLAMA 3.2 VISION (11B)
echo   More intelligent vision model for documents
echo ==================================================
echo.

echo [INFO] Llama 3.2 Vision is superior for:
echo   - Document structure understanding
echo   - Table parsing
echo   - Precise regex generation
echo.
echo [WARNING] This will download ~7GB
echo.
pause

echo [1/2] Downloading Llama 3.2 Vision (11B)...
wsl ollama pull llama3.2-vision:11b
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to download model
    pause
    exit /b 1
)

echo.
echo [2/2] Updating analyzer script to use Llama 3.2 Vision...
powershell -Command "(Get-Content 'scripts\analyze_tr_vision.py') -replace 'llava:13b', 'llama3.2-vision:11b' | Set-Content 'scripts\analyze_tr_vision.py'"

echo.
echo ==================================================
echo   SETUP COMPLETE
echo ==================================================
echo Now run: .\run_tr_vision_analysis.bat
echo.
pause
