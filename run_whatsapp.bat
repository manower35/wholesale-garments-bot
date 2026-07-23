@echo off
title AT SELECTION - WhatsApp AI Catalog Bot Launcher
cls
echo ====================================================
echo    AT SELECTION - WhatsApp AI Catalog Bot Launcher
echo ====================================================
echo.

:: 1. Detect Python Executable (prefer virtualenv if present)
set "PYTHON_EXE=python"
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo [*] Using project virtual environment (venv).
) else (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] ERROR: Python is not installed or not added to PATH.
        echo Please install Python 3.10+ and add it to PATH.
        pause
        exit /b 1
    )
)

:: 2. Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\nodejs\node.exe" (
        set "PATH=C:\Program Files\nodejs;%PATH%"
    ) else (
        echo [!] ERROR: Node.js is not found in PATH.
        echo Please close and reopen your Command Prompt window to refresh PATH.
        pause
        exit /b 1
    )
)

:: 3. Create .env if missing
if not exist .env (
    echo [*] Creating .env file from .env.example...
    copy .env.example .env >nul
)

:: 4. Install Bridge Dependencies if node_modules is missing
if not exist whatsapp_bridge\node_modules (
    echo [*] Installing WhatsApp Bridge Node.js dependencies...
    cd whatsapp_bridge
    call npm install
    cd ..
    echo [+] Node.js dependencies installed successfully.
)

:: 5. Launch Python API Server in a background window
echo [*] Launching Python AI Server (Port 5000)...
start "AT SELECTION - Python WhatsApp API" cmd /k "%PYTHON_EXE% whatsapp_api.py"

:: 6. Launch WhatsApp Web Bridge in current window for QR Code scanning
echo [*] Starting WhatsApp Web Bridge...
echo.
cd whatsapp_bridge
node index.js

pause
