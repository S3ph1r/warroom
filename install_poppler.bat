@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   POPPLER INSTALLATION FOR WINDOWS
echo ============================================
echo.

set "INSTALL_DIR=%USERPROFILE%\poppler"
set "POPPLER_URL=https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
set "TEMP_ZIP=%TEMP%\poppler.zip"

echo [1/4] Downloading Poppler (~30MB)...
echo Install directory: %INSTALL_DIR%
echo.
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%POPPLER_URL%' -OutFile '%TEMP_ZIP%' -UseBasicParsing}"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Download failed
    pause
    exit /b 1
)

echo.
echo [2/4] Extracting to %INSTALL_DIR%...
if exist "%INSTALL_DIR%" (
    echo Removing old installation...
    rmdir /s /q "%INSTALL_DIR%" 2>nul
)
mkdir "%INSTALL_DIR%" 2>nul
powershell -Command "& {Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%INSTALL_DIR%' -Force}"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Extraction failed
    pause
    exit /b 1
)

echo.
echo [3/4] Locating poppler binaries...
set "BIN_DIR="
for /d %%i in ("%INSTALL_DIR%\poppler-*") do (
    if exist "%%i\Library\bin" (
        set "BIN_DIR=%%i\Library\bin"
    )
)

if "!BIN_DIR!"=="" (
    echo ERROR: Could not find Library\bin directory
    pause
    exit /b 1
)

echo Found binaries at: !BIN_DIR!

echo.
echo [4/4] Configuring pdf2image to use Poppler...
rem Create a config file for pdf2image in the project
set "CONFIG_FILE=%~dp0scripts\poppler_config.py"
echo # Auto-generated Poppler configuration > "!CONFIG_FILE!"
echo POPPLER_PATH = r"!BIN_DIR!" >> "!CONFIG_FILE!"
echo. >> "!CONFIG_FILE!"

rem Update analyze_tr_vision.py to use the config
powershell -Command "(Get-Content '%~dp0scripts\analyze_tr_vision.py') -replace 'from pdf2image import convert_from_path', 'from pdf2image import convert_from_path`nimport sys`nfrom pathlib import Path`nsys.path.insert(0, str(Path(__file__).parent))`nfrom poppler_config import POPPLER_PATH' -replace 'convert_from_path\(pdf_path, dpi=150\)', 'convert_from_path(pdf_path, dpi=150, poppler_path=POPPLER_PATH)' | Set-Content '%~dp0scripts\analyze_tr_vision.py.tmp'"
move /y "%~dp0scripts\analyze_tr_vision.py.tmp" "%~dp0scripts\analyze_tr_vision.py" >nul

echo.
echo ============================================
echo   POPPLER INSTALLATION COMPLETE
echo ============================================
echo.
echo Installed to: !BIN_DIR!
echo Configuration: scripts\poppler_config.py
echo.
echo You can now run: .\run_tr_vision_analysis.bat
echo.

rem Cleanup
del "%TEMP_ZIP%" 2>nul

pause
