@echo off
set OLLAMA_EXE="C:\Users\Roberto\AppData\Local\Programs\Ollama\ollama.exe"

echo ===================================================
echo   SETUP NATIVE OLLAMA - MODEL DOWNLOADER
echo ===================================================
echo.
echo 1. Verifying Ollama installation at %OLLAMA_EXE%...
%OLLAMA_EXE% --version
if %errorlevel% neq 0 (
    echo [ERROR] Ollama is not found at expected path!
    echo.
    echo Please install it manually first:
    echo visit: https://ollama.com/download
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Ollama found. Proceeding to download models...
echo This might take a while depending on your internet connection.

echo.
echo 2. Pulling Llama 3.2 Vision (11b)...
%OLLAMA_EXE% pull llama3.2-vision:11b

echo.
echo 3. Pulling Qwen 2.5 (14b)...
%OLLAMA_EXE% pull qwen2.5:14b

echo.
echo 4. Pulling Qwen 2.5 (14b) High Quality [Q6_K]...
%OLLAMA_EXE% pull qwen2.5:14b-instruct-q6_K

echo.
echo 5. Pulling Qwen 3 (14b) Experimental...
%OLLAMA_EXE% pull qwen3:14b

echo.
echo 6. Pulling Mistral Nemo (as requested)...
%OLLAMA_EXE% pull mistral-nemo

echo.
echo ===================================================
echo   SETUP COMPLETE!
echo   You can now run: python scripts/smart_orchestrator.py ...
echo ===================================================
pause
