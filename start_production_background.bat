@echo off
echo Starting YouTube Downloader in PRODUCTION mode (Background)...
echo.

REM Set production environment variables
set SECRET_KEY=your_production_secret_key_here_change_this
set FLASK_ENV=production

REM Kill any existing Python processes
taskkill /f /im python.exe >nul 2>&1

REM Start Waitress in background
echo Starting Waitress server in background...
start /B waitress-serve --host=127.0.0.1 --port=5000 --threads=4 wsgi:app

echo.
echo Server started in background!
echo Access your application at: http://127.0.0.1:5000
echo.
echo To stop the server, run: taskkill /f /im python.exe
echo.

pause