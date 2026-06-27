@echo off
chcp 65001 >nul
title Snake Deluxe
cd /d "%~dp0"
python -m snake_deluxe
if errorlevel 1 (
    echo.
    echo [Error] Make sure Python 3.8+ is installed and on PATH.
    echo Press any key to exit...
    pause >nul
)
