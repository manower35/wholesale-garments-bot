@echo off
title AT SELECTION - Garments Catalog Bot
echo ====================================================
echo      Starting AT SELECTION Garments Catalog Bot     
echo ====================================================

:: Check if .env file exists
if not exist .env (
    echo [!] Warning: .env file not found. Creating a template .env file.
    copy .env.example .env
    echo Please open the .env file in Notepad and replace the placeholder with your actual Telegram Bot Token.
    notepad .env
    pause
    exit /b
)

:: Check if venv exists
if not exist venv (
    echo [!] Error: Virtual environment folder 'venv' not found.
    echo Please run the following command to set it up:
    echo python -m venv venv
    echo .\venv\Scripts\pip install -r requirements.txt
    pause
    exit /b
)

echo [*] Starting the bot application...
echo Press Ctrl+C to close the bot window.
echo ----------------------------------------------------
.\venv\Scripts\python main.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Bot crashed or stopped with error code %errorlevel%.
    pause
)
