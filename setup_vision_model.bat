@echo off
echo ============================================
echo   VISION MODEL SETUP FOR TRADE REPUBLIC
echo ============================================
echo.
echo [1/3] Downloading LLaVA Vision Model...
echo This will take a few minutes (7GB model)
echo.
wsl ollama pull llava:13b
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to download LLaVA model
    pause
    exit /b 1
)

echo.
echo [2/3] Installing required Python packages...
pip install pdf2image pillow --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Python packages
    pause
    exit /b 1
)

echo.
echo [3/3] Testing Vision Model...
wsl ollama list | findstr llava
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: LLaVA model not found after installation
    pause
    exit /b 1
)

echo.
echo ============================================
echo   SETUP COMPLETE!
echo ============================================
echo LLaVA Vision Model is ready to use.
echo.
pause
