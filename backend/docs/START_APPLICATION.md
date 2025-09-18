# 🚀 HOW TO RUN YOUR FULL YOUTUBE DOWNLOADER APPLICATION

## 📋 Quick Start Options

### 🎯 **OPTION 1: Complete Full-Stack Application (RECOMMENDED)**
```powershell
.\run_all.ps1
```
**What this does:**
- ✅ Starts FastAPI backend server
- ✅ Starts Celery worker for background downloads
- ✅ Opens browser automatically
- ✅ Provides full functionality with Redis caching
- ✅ Real-time progress tracking
- ✅ Multi-platform support (YouTube, Instagram, TikTok, etc.)

### 🎯 **OPTION 2: Development Mode (Single Process)**
```powershell
.\run_dev.ps1
```
**What this does:**
- ✅ Starts FastAPI backend only
- ✅ Auto-reload on code changes
- ✅ Good for development and testing
- ⚠️ No Celery worker (uses background tasks)

### 🎯 **OPTION 3: Enhanced Startup with Auto-Fix**
```powershell
python start_fixed.py
```
**What this does:**
- ✅ Automatically checks and installs dependencies
- ✅ Updates yt-dlp to latest version
- ✅ Tests functionality before starting
- ✅ Cleans up old files
- ✅ Starts the application

---

## 🔧 Prerequisites Setup

### 1. **Install Redis (for full functionality)**
```powershell
# Using Chocolatey (recommended)
choco install redis-64

# Or download from: https://github.com/microsoftarchive/redis/releases
```

### 2. **Install FFmpeg (for video processing)**
```powershell
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

### 3. **Verify Environment**
```powershell
# Check if Redis is running
redis-cli ping

# Check if FFmpeg is available
ffmpeg -version
```

---

## 🚀 **RECOMMENDED: Full Application Startup**

### Step 1: Start Redis (if not running)
```powershell
# Start Redis server
redis-server
```

### Step 2: Run Full Application
```powershell
# Navigate to project directory
Set-Location "e:\project\downloader"

# Start complete application
.\run_all.ps1
```

### Step 3: Access Your Application
- **Main Interface**: http://127.0.0.1:8000/universal_tailwind
- **API Documentation**: http://127.0.0.1:8000/docs
- **Alternative Interface**: http://127.0.0.1:8000/universal

---

## 🎛️ **Advanced Options**

### Custom Port
```powershell
.\run_all.ps1 -ApiPort 5000
```

### Skip Celery (Single Process Mode)
```powershell
.\run_all.ps1 -NoCelery
```

### Install Dependencies First
```powershell
.\run_all.ps1 -Install
```

### Development Mode with Hot Reload
```powershell
.\run_dev.ps1 -ApiPort 5000
```

---

## 📊 **Monitor Your Application**

### Real-Time Activity Monitoring
```powershell
# Live log monitoring
.\live_monitor.ps1

# Quick status check
.\check_activity.ps1
```

### View Logs
```powershell
# Application logs
Get-Content logs\app.log -Tail 20 -Wait

# Server logs
Get-Content logs\uvicorn.err -Tail 10
```

---

## 🌟 **Application Features**

### **Multi-Platform Support**
- 📺 **YouTube**: Videos, playlists, shorts
- 📸 **Instagram**: Posts, reels, stories
- 🎵 **TikTok**: Videos and audio
- 📘 **Facebook**: Videos and reels
- 🐦 **Twitter/X**: Video tweets
- 📌 **Pinterest**: Video pins

### **Download Options**
- 🎬 **Video Formats**: MP4, WebM, MKV
- 🎵 **Audio Formats**: MP3 (128k, 192k, 320k)
- 📱 **Quality Options**: 360p to 4K
- ⚡ **Fast Downloads**: Aria2c integration
- 🔄 **Progress Tracking**: Real-time updates

### **Advanced Features**
- 🧠 **Smart Caching**: Redis-based caching
- 🔄 **Background Processing**: Celery workers
- 📊 **Progress API**: Real-time download status
- 🔒 **Secure Downloads**: Signed URLs
- 📱 **Mobile Responsive**: Works on all devices

---

## 🛠️ **Troubleshooting**

### Application Won't Start
```powershell
# Check dependencies
python -m pip install -r requirements.txt

# Update yt-dlp
python -m pip install --upgrade yt-dlp

# Check Python version (requires 3.8+)
python --version
```

### Redis Connection Issues
```powershell
# Start Redis manually
redis-server

# Or run without Celery
.\run_all.ps1 -NoCelery
```

### Port Already in Use
```powershell
# Use different port
.\run_all.ps1 -ApiPort 9000

# Or kill existing processes
Get-Process -Name "python" | Stop-Process -Force
```

### Download Failures
```powershell
# Update yt-dlp
python -m pip install --upgrade yt-dlp

# Check cookies file
ls cookies.txt

# Verify FFmpeg
ffmpeg -version
```

---

## 📁 **File Structure**

```
e:\project\downloader\
├── main_api.py           # Main FastAPI application
├── run_all.ps1          # Full application startup
├── run_dev.ps1          # Development mode startup
├── start_fixed.py       # Enhanced startup with auto-fix
├── backend/             # Backend modules
│   ├── platforms/       # Platform-specific handlers
│   ├── tasks/          # Celery tasks
│   └── utils/          # Utility functions
├── templates/          # HTML templates
├── static/            # CSS, JS, assets
├── downloads/         # Downloaded files
├── logs/             # Application logs
└── venv/             # Python virtual environment
```

---

## 🎯 **Quick Commands Reference**

| Command | Purpose |
|---------|---------|
| `.\run_all.ps1` | Start full application |
| `.\run_dev.ps1` | Development mode |
| `python start_fixed.py` | Auto-fix startup |
| `.\live_monitor.ps1` | Monitor activity |
| `.\check_activity.ps1` | Quick status |
| `redis-server` | Start Redis |
| `Get-Content logs\app.log -Wait` | View logs |

---

## 🌐 **Access URLs**

- **Main App**: http://127.0.0.1:8000/universal_tailwind
- **API Docs**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/api/health
- **Download Files**: http://127.0.0.1:8000/download/filename

---

**🎉 Your YouTube Downloader is ready to use! Choose your preferred startup method and enjoy downloading from multiple platforms!**