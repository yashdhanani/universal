@echo off
echo Starting YouTube Downloader in PRODUCTION mode with Waitress...
echo.

REM Set production environment variables
set SECRET_KEY=your_production_secret_key_here_change_this
set FLASK_ENV=production

REM Kill any existing Python processes
taskkill /f /im python.exe >nul 2>&1

REM Start Waitress WSGI server
echo Starting Waitress server...
echo Server will be available at: http://127.0.0.1:5000
echo.
waitress-serve --host=127.0.0.1 --port=5000 --threads=4 wsgi:app

pause