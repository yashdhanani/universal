# 🚀 **Universal Media Downloader - Production Ready**

## 🎯 **Quick Start Production**

### **1. Start Production Server**
```bash
# Auto-optimized production server
python start_production.py

# Custom configuration
python start_production.py --server gunicorn --workers 4 --host 0.0.0.0 --port 8000

# With SSL support
python start_production.py --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem
```

### **2. Test Production Deployment**
```bash
# Run comprehensive tests
python test_production.py

# Check server health
curl http://localhost:8000/health
```

---

## 🍪 **Cookies Management for Private Content**

### **✅ Supported Platforms**
- **Instagram:** Private profiles, stories, highlights, reels
- **Facebook:** Private posts, groups, pages, videos
- **Twitter/X:** Protected tweets, private accounts
- **TikTok:** Private videos, age-restricted content
- **Pinterest:** Private boards and pins
- **Snapchat:** Private stories and content
- **LinkedIn:** Private posts and videos
- **Reddit:** Private subreddits and posts

### **✅ Cookie Features**
- 🔐 **Multi-platform support** - Separate cookies for each platform
- 👥 **Multiple accounts** - Multiple sessions per platform
- ✅ **Cookie validation** - Test cookies before use
- 📤 **Export/Import** - Backup and restore sessions
- 🧹 **Auto-cleanup** - Remove old/expired sessions
- 🔒 **Secure storage** - Encrypted cookie management

### **✅ How to Use Cookies**

#### **Step 1: Get Cookies from Browser**
1. Install browser extension: "Get cookies.txt LOCALLY" or "cookies.txt"
2. Log into the platform (Instagram, Facebook, etc.)
3. Use extension to export cookies in Netscape format
4. Copy the cookies content

#### **Step 2: Upload Cookies**
1. Visit `/cookies` in your browser
2. Select the platform
3. Enter a session name (optional)
4. Paste cookies content
5. Click "Upload Cookies"

#### **Step 3: Download Private Content**
- Private content will now work automatically
- The system uses the appropriate cookies for each platform
- If cookies are needed, you'll get a helpful error message

---

## 🌐 **Production Deployment Options**

### **🔧 Multi-Worker Deployment**

#### **Uvicorn (Recommended)**
```bash
# Auto-optimized workers
python start_production.py --server uvicorn

# Custom worker count
python start_production.py --server uvicorn --workers 8

# With proxy headers for reverse proxy
python start_production.py --server uvicorn --host 0.0.0.0 --port 8000
```

#### **Gunicorn (Alternative)**
```bash
# Production-ready Gunicorn
python start_production.py --server gunicorn --workers 4

# With custom settings
gunicorn main_api:APP -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --proxy-protocol
```

### **🐳 Docker Deployment**
```bash
# Build and run
docker build -t universal-downloader .
docker run -p 8000:8000 -v ./downloads:/app/downloads universal-downloader

# With docker-compose
docker-compose up -d
```

### **🔧 Systemd Service**
```bash
# Create service file
python start_production.py --create-service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable universal-downloader
sudo systemctl start universal-downloader
```

### **🌐 Reverse Proxy Setup**
```bash
# Create nginx config
python start_production.py --create-nginx --domain yourdomain.com

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📊 **Production Features**

### **✅ Performance Optimizations**
- **Multi-worker support** with optimal CPU utilization
- **Proxy headers** for reverse proxy compatibility
- **Connection pooling** and keep-alive
- **Graceful shutdown** and restart handling
- **Resource limits** and memory management

### **✅ Security Features**
- **SSL/HTTPS support** with automatic certificate detection
- **Secure headers** (CSP, HSTS, X-Frame-Options)
- **Input validation** and sanitization
- **Rate limiting** and request throttling
- **Secure cookie storage** with encryption

### **✅ Monitoring & Logging**
- **Health check endpoints** (`/health`)
- **Structured logging** with rotation
- **Performance metrics** and monitoring
- **Error tracking** and alerting
- **Resource usage** monitoring

### **✅ High Availability**
- **Load balancing** across multiple workers
- **Automatic failover** and recovery
- **Zero-downtime deployments**
- **Database connection pooling**
- **Caching** for improved performance

---

## 🌍 Public HTTPS URL and Auto-CORS (ngrok)

- **Prerequisites**: Docker Desktop installed and an ngrok auth token.
- **Start with ngrok and auto-apply CORS**:

```powershell
# Start API + worker + ngrok (compose profile), auto-apply CORS with optional extra origins
.\start_with_ngrok.ps1 -NgrokToken "<YOUR_TOKEN>" -AutoCors -Origins "https://yourdomain.com"

# Alternative: generic compose helper
.\start_compose.ps1 -WithTunnel -NgrokToken "<YOUR_TOKEN>"
```

- **What it does**:
  - **Prints and copies** the public HTTPS URL to your clipboard.
  - If `-AutoCors` is used, **sets `CORS_ALLOW_ORIGINS`** to that URL and rebuilds the `api` service so it takes effect immediately.
  - Inspect requests at: `http://localhost:4040` (ngrok inspector).

- **Retrieve only the public URL** (without modifying services):

```powershell
.\print_ngrok_url.ps1
# Quiet mode and capture in a variable
$publicUrl = .\print_ngrok_url.ps1 -Quiet; $publicUrl
```

- **Manual CORS alternative**:
  - Set in `.env` or your environment: `CORS_ALLOW_ORIGINS=<your-ngrok-https-url>`
  - Apply changes: `docker compose up -d` or restart your service/process manager

### CORS for multiple origins
- **Comma-separated list** is supported. Examples:
  - Docker Compose (.env or compose env):
    ```env
    CORS_ALLOW_ORIGINS=https://app1.ngrok.app,https://app2.ngrok.app,https://yourdomain.com
    ```
  - Bare-metal (Linux):
    ```bash
    export CORS_ALLOW_ORIGINS="https://app1.ngrok.app,https://app2.ngrok.app,https://yourdomain.com"
    systemctl restart universal-downloader  # if using systemd
    ```
  - Bare-metal (Windows/PowerShell):
    ```powershell
    $env:CORS_ALLOW_ORIGINS = "https://app1.ngrok.app,https://app2.ngrok.app,https://yourdomain.com"
    python start_production.py --server uvicorn --host 0.0.0.0 --port 8000
    ```

### Reverse proxy (Nginx) tips for CORS/HTTPS
- Terminate TLS at Nginx and forward to app:
  ```nginx
  server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
      proxy_pass http://127.0.0.1:8000;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto https;
    }

    # Optional: add CORS at proxy (if not handled by app)
    add_header Access-Control-Allow-Origin "https://app1.ngrok.app https://app2.ngrok.app" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "*" always;

    if ($request_method = OPTIONS) {
      return 204;
    }
  }
  ```
- If using a reverse proxy, keep `--proxy-headers` enabled (already set in docker-compose) so FastAPI respects forwarded headers.

## 🔧 **Configuration Options**

### **Environment Variables**

#### API key usage (production)
- Set keys via environment or .env: `API_KEYS=key1,key2`
- Clients must send header: `X-API-Key: key1`
- Example with curl:
  ```bash
  curl -H "X-API-Key: key1" "https://yourdomain.com/api/v2/youtube/info?url=..."
  ```
- With Nginx, ensure you forward headers unchanged (default behavior).
```bash
# Production settings
export ENVIRONMENT=production
export DEBUG=false
export SECRET_KEY="your-strong-secret-key"

# Server configuration
export HOST=0.0.0.0
export PORT=8000
export WORKERS=4

# SSL configuration
export SSL_CERT_PATH="/path/to/certificate.crt"
export SSL_KEY_PATH="/path/to/private.key"

# Performance tuning
export MAX_CONCURRENT_DOWNLOADS=8
export SOCKET_TIMEOUT=30
export HTTP_CHUNK_SIZE=10485760

# External tools
export FFMPEG_LOCATION="/usr/bin/ffmpeg"
export ARIA2C_PATH="/usr/bin/aria2c"
```

### **Advanced Configuration**
```bash
# Database settings (if using)
export DATABASE_URL="postgresql://user:pass@localhost/db"
export DATABASE_POOL_SIZE=20

# Redis settings (if using)
export REDIS_URL="redis://localhost:6379/0"
export CACHE_TTL=3600

# Security settings
export ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
export SECURE_COOKIES=true
export HTTPS_ONLY=true
```

---

## 📈 **Performance Tuning**

### **Worker Configuration**
```bash
# CPU-intensive workloads
workers = (2 × CPU_cores) + 1

# I/O-intensive workloads (recommended for downloads)
workers = (4 × CPU_cores) + 1

# Memory considerations
max_workers = min(calculated_workers, available_memory / 512MB)
```

### **System Limits**
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Kernel parameters
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" >> /etc/sysctl.conf
```

---

## 🔍 **Monitoring & Troubleshooting**

### **Health Checks**
```bash
# Application health
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/api/status

# Cookies status
curl http://localhost:8000/api/auth/cookies/sessions
```

### **Log Analysis**
```bash
# View application logs
tail -f logs/production.log

# Monitor system resources
htop
iotop
nethogs

# Check disk space
df -h downloads/
```

### **Common Issues**

#### **Private Content Access**
```bash
# Issue: "Login required" or "403 Forbidden"
# Solution: Upload cookies for the platform
# Visit: http://localhost:8000/cookies
```

#### **Performance Issues**
```bash
# Issue: Slow downloads
# Solution: Install aria2c for faster downloads
sudo apt install aria2
export ARIA2C_PATH=/usr/bin/aria2c
```

#### **SSL Certificate Issues**
```bash
# Issue: SSL certificate errors
# Solution: Check certificate paths and permissions
openssl x509 -in /path/to/cert.pem -text -noout
```

---

## 🎉 **Production Checklist**

### **Pre-Deployment**
- [ ] Install Python 3.10+, FFmpeg, Aria2c
- [ ] Set up SSL certificates
- [ ] Configure environment variables
- [ ] Test with development server
- [ ] Run security audit (`python test_production.py`)

### **Deployment**
- [ ] Deploy with production server (`python start_production.py`)
- [ ] Set up reverse proxy (Nginx/Apache)
- [ ] Configure systemd service
- [ ] Set up log rotation
- [ ] Configure monitoring and alerting

### **Post-Deployment**
- [ ] Test all platform downloads
- [ ] Verify cookies management works
- [ ] Check SSL certificate validity
- [ ] Monitor performance metrics
- [ ] Set up automated backups

### **Security Hardening**
- [ ] Configure firewall rules
- [ ] Set proper file permissions
- [ ] Enable security headers
- [ ] Set up rate limiting
- [ ] Configure HTTPS redirects

---

## 🌟 **What's New in Production Mode**

### **🚀 Enterprise-Grade Features**
- ✅ **Multi-worker deployment** with automatic scaling
- ✅ **Proxy headers support** for load balancers
- ✅ **SSL/HTTPS support** with automatic detection
- ✅ **Cookies management UI** for private content
- ✅ **Universal download engine** with platform auto-detection
- ✅ **Production monitoring** and health checks
- ✅ **Security hardening** with proper headers and limits

### **🍪 Private Content Support**
- ✅ **Instagram private profiles** and stories
- ✅ **Facebook private posts** and groups
- ✅ **Twitter protected accounts**
- ✅ **TikTok age-restricted content**
- ✅ **Multi-account support** per platform
- ✅ **Cookie validation** and management

### **📊 Production Monitoring**
- ✅ **Real-time health checks**
- ✅ **Performance metrics**
- ✅ **Error tracking and alerting**
- ✅ **Resource usage monitoring**
- ✅ **Structured logging with rotation**

---

## 🎊 **Ready for Production!**

Your **Universal Media Downloader** is now enterprise-ready with:

- 🚀 **Multi-worker deployment** for high performance
- 🍪 **Cookies management** for private content access
- 🔒 **Security hardening** for production environments
- 📊 **Comprehensive monitoring** and logging
- 🌐 **Reverse proxy support** for scalability
- 🐳 **Docker deployment** options
- ⚡ **Performance optimizations** for heavy loads

**Deploy with confidence and let your users download from all major platforms seamlessly!** 🎉