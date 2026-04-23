@echo off
title Telegram Monitor Bot - Install
color 0A
echo.
echo  =========================================
echo   Telegram Monitor Bot - Installation
echo  =========================================
echo.
echo  Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Please install Python from https://python.org
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo  Python found!
echo.
echo  Installing required packages...
echo.
pip install telethon==1.36.0 httpx==0.27.0

if errorlevel 1 (
    echo.
    echo  [ERROR] Failed to install packages. Check your internet connection.
    echo.
    pause
    exit /b 1
)

echo.
echo  =========================================
echo   Installation complete!
echo   Next step: Run 2_setup.bat
echo  =========================================
echo.
pause
