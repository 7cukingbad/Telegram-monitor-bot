@echo off
title Telegram Monitor Bot - Running
color 0A
echo.
echo  =========================================
echo   Telegram Monitor Bot - Starting...
echo  =========================================
echo.

if not exist config.py (
    echo  [ERROR] config.py not found!
    echo  Please run 2_setup.bat first.
    echo.
    pause
    exit /b 1
)

if not exist main.py (
    echo  [ERROR] main.py not found!
    echo  Make sure all bot files are in the same folder.
    echo.
    pause
    exit /b 1
)

echo  Bot is starting...
echo  On first run, enter the OTP sent to your Telegram.
echo.
echo  Press Ctrl+C to stop the bot.
echo  =========================================
echo.

python main.py

echo.
echo  Bot has stopped.
pause
