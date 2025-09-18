@echo off
echo 🚀 Starting YouTube Downloader Server...
echo ========================================

cd /d "e:\project\downloader"

echo 📦 Checking dependencies...
python -c "import fastapi, yt_dlp, uvicorn" 2>nul
if errorlevel 1 (
    echo ❌ Missing dependencies! Installing...
    pip install -r requirements.txt
)

echo ✅ Dependencies OK!
echo 🌐 Starting server at http://127.0.0.1:8000
echo 📱 Access UI at: http://127.0.0.1:8000/universal_tailwind
echo.
echo Press Ctrl+C to stop the server
echo ========================================

uvicorn main_api:APP --host 127.0.0.1 --port 8000 --reload