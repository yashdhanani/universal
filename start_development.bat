@echo off
echo Starting YouTube Downloader - Enhanced Development Mode
echo ========================================================
echo This will automatically:
echo - Check and install dependencies
echo - Update yt-dlp to latest version
echo - Test YouTube functionality
echo - Start the development server
echo ========================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Set environment variables for development
set FLASK_ENV=development
set SECRET_KEY=dev_secret_key_not_for_production
set PYTHONUNBUFFERED=1

REM Optional: Set ffmpeg path if you have it installed
REM set FFMPEG_LOCATION=C:\path\to\ffmpeg\bin

REM Start the enhanced application
python start_fixed.py

pause