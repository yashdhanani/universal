#!/usr/bin/env python3
"""
Production Deployment Script
Handles multi-worker deployment with proxy headers support
"""

import os
import sys
import argparse
import subprocess
import multiprocessing
import shutil
from pathlib import Path

def get_optimal_workers():
    """Calculate optimal number of workers based on CPU cores"""
    cpu_count = multiprocessing.cpu_count()
    # For I/O intensive workloads like downloading: (2 × CPU) + 1
    return min((2 * cpu_count) + 1, 16)  # Cap at 16 workers

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    # Check Python packages
    try:
        import uvicorn
    except ImportError:
        missing.append("uvicorn")
    
    try:
        import gunicorn
    except ImportError:
        missing.append("gunicorn (optional)")
    
    # Check system dependencies
    if not shutil.which('ffmpeg'):
        missing.append("ffmpeg")
    
    if missing:
        print("⚠️  Missing dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\nInstall with:")
        print("   pip install uvicorn gunicorn")
        print("   # Install ffmpeg from your system package manager")
        return False
    
    return True

def create_systemd_service(app_path, user="www-data", workers=None):
    """Create systemd service file"""
    workers = workers or get_optimal_workers()
    
    service_content = f"""[Unit]
Description=Universal Media Downloader
After=network.target

[Service]
Type=notify
User={user}
Group={user}
WorkingDirectory={app_path}
Environment=PATH={app_path}/venv/bin
ExecStart={sys.executable} start_production.py --server uvicorn --workers {workers} --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
MemoryMax=4G
CPUQuota=400%

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={app_path}/downloads {app_path}/logs {app_path}/cookies

[Install]
WantedBy=multi-user.target
"""
    
    service_file = "/etc/systemd/system/universal-downloader.service"
    print(f"📝 Creating systemd service: {service_file}")
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        print("✅ Systemd service created successfully!")
        print("\nTo enable and start:")
        print("   sudo systemctl daemon-reload")
        print("   sudo systemctl enable universal-downloader")
        print("   sudo systemctl start universal-downloader")
        print("   sudo systemctl status universal-downloader")
        
    except PermissionError:
        print("❌ Permission denied. Run with sudo to create systemd service.")
        return False
    
    return True

def create_nginx_config(domain="localhost", ssl_cert=None, ssl_key=None):
    """Create nginx configuration"""
    
    ssl_config = ""
    if ssl_cert and ssl_key:
        ssl_config = f"""
    listen 443 ssl http2;
    ssl_certificate {ssl_cert};
    ssl_certificate_key {ssl_key};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Redirect HTTP to HTTPS
    if ($scheme != "https") {{
        return 301 https://$host$request_uri;
    }}
"""
    else:
        ssl_config = "listen 80;"
    
    nginx_content = f"""server {{
{ssl_config}
    server_name {domain};
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' fonts.googleapis.com cdn.tailwindcss.com; font-src fonts.gstatic.com; img-src 'self' data:;";
    
    # File upload limits
    client_max_body_size 500M;
    client_body_timeout 300s;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Static files caching
    location /static/ {{
        alias /path/to/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }}
    
    # Downloads with proper headers
    location /download/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Large file support
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_max_temp_file_size 0;
        
        # Timeouts for large downloads
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }}
    
    # API endpoints
    location /api/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # API timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }}
    
    # Main application
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Standard timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
}}
"""
    
    config_file = f"/etc/nginx/sites-available/universal-downloader"
    print(f"📝 Creating nginx config: {config_file}")
    
    try:
        with open(config_file, 'w') as f:
            f.write(nginx_content)
        
        # Create symlink to sites-enabled
        enabled_link = "/etc/nginx/sites-enabled/universal-downloader"
        if not os.path.exists(enabled_link):
            os.symlink(config_file, enabled_link)
        
        print("✅ Nginx configuration created successfully!")
        print("\nTo enable:")
        print("   sudo nginx -t")
        print("   sudo systemctl reload nginx")
        
    except PermissionError:
        print("❌ Permission denied. Run with sudo to create nginx config.")
        return False
    
    return True

def start_uvicorn(host, port, workers, ssl_cert=None, ssl_key=None):
    """Start with Uvicorn (recommended)"""
    cmd = [
        sys.executable, "-m", "uvicorn", "main_api:APP",
        "--host", host,
        "--port", str(port),
        "--workers", str(workers),
        "--proxy-headers",
        "--forwarded-allow-ips", "*",
        "--access-log",
        "--log-level", "info"
    ]
    
    # Add SSL if certificates provided
    if ssl_cert and ssl_key:
        cmd.extend(["--ssl-certfile", ssl_cert, "--ssl-keyfile", ssl_key])
    
    print(f"🚀 Starting Uvicorn with {workers} workers...")
    print(f"   Command: {' '.join(cmd)}")
    
    return subprocess.run(cmd)

def start_gunicorn(host, port, workers, ssl_cert=None, ssl_key=None):
    """Start with Gunicorn (alternative)"""
    cmd = [
        "gunicorn", "main_api:APP",
        "-w", str(workers),
        "-k", "uvicorn.workers.UvicornWorker",
        "-b", f"{host}:{port}",
        "--proxy-protocol",
        "--forwarded-allow-ips", "*",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "--max-requests", "1000",
        "--max-requests-jitter", "100",
        "--timeout", "120",
        "--keep-alive", "5",
        "--graceful-timeout", "30"
    ]
    
    # Add SSL if certificates provided
    if ssl_cert and ssl_key:
        cmd.extend(["--certfile", ssl_cert, "--keyfile", ssl_key])
    
    print(f"🚀 Starting Gunicorn with {workers} workers...")
    print(f"   Command: {' '.join(cmd)}")
    
    return subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="Production deployment for Universal Media Downloader")
    parser.add_argument("--server", choices=["uvicorn", "gunicorn", "auto"], default="auto",
                       help="ASGI server to use (default: auto)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--workers", type=int, help="Number of workers (default: auto-detect)")
    parser.add_argument("--ssl-cert", help="SSL certificate file path")
    parser.add_argument("--ssl-key", help="SSL private key file path")
    
    # Service management
    parser.add_argument("--create-service", action="store_true", help="Create systemd service file")
    parser.add_argument("--create-nginx", action="store_true", help="Create nginx configuration")
    parser.add_argument("--domain", default="localhost", help="Domain name for nginx config")
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Get optimal workers
    workers = args.workers or get_optimal_workers()
    
    # Create service files if requested
    if args.create_service:
        create_systemd_service(os.getcwd(), workers=workers)
        return
    
    if args.create_nginx:
        create_nginx_config(args.domain, args.ssl_cert, args.ssl_key)
        return
    
    # Auto-detect server
    server = args.server
    if server == "auto":
        try:
            import gunicorn
            server = "gunicorn"
        except ImportError:
            server = "uvicorn"
    
    # Set production environment
    os.environ["ENVIRONMENT"] = "production"
    
    # Create necessary directories
    for directory in ["downloads", "logs", "cookies", "static"]:
        Path(directory).mkdir(exist_ok=True)
    
    print("🎯 Production Deployment Starting...")
    print(f"   Server: {server}")
    print(f"   Workers: {workers}")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   SSL: {'Yes' if args.ssl_cert else 'No'}")
    print()
    
    # Start the server
    try:
        if server == "uvicorn":
            result = start_uvicorn(args.host, args.port, workers, args.ssl_cert, args.ssl_key)
        else:
            result = start_gunicorn(args.host, args.port, workers, args.ssl_cert, args.ssl_key)
        
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()