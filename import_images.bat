@echo off
title AT SELECTION - Bulk 2000+ Image Importer
cls
echo ====================================================
echo    AT SELECTION - Bulk 2000+ Image Importer
echo ====================================================
echo.

set "PYTHON_EXE=python"
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
)

echo [*] Starting Bulk Image Import...
%PYTHON_EXE% import_all_images.py

echo.
echo [!] Import complete! Press any key to exit.
pause
