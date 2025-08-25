@echo off
title YouTube Downloader - Auto Restart
echo YouTube Downloader Auto-Restart Script
echo ========================================
echo This script will automatically restart the server if it crashes
echo Press Ctrl+C to stop
echo.

:start
echo [%date% %time%] Starting YouTube Downloader...
python start_fixed.py

echo.
echo [%date% %time%] Server stopped. Waiting 5 seconds before restart...
timeout /t 5 /nobreak > nul

echo [%date% %time%] Restarting...
goto start
