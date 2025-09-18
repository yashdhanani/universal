#!/usr/bin/env python3
"""
Production Deployment Script
Switches from CDN to local Tailwind CSS and optimizes for production
"""

import os
import re
import subprocess
import sys

def switch_to_local_tailwind():
    """Switch from Tailwind CDN to local build"""
    print("🎨 Switching to local Tailwind CSS build...")
    
    template_path = "templates/universal_tailwind.html"
    
    # Read the template
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace CDN with local build
    content = re.sub(
        r'<!-- Tailwind CSS - Using CDN for development, switch to local build for production -->\s*<script src="https://cdn\.tailwindcss\.com"></script>\s*<!-- <link href="/static/tailwind\.min\.css" rel="stylesheet"> -->',
        '<!-- Tailwind CSS - Production Build -->\n  <link href="/static/tailwind.min.css" rel="stylesheet">',
        content,
        flags=re.MULTILINE
    )
    
    # Write back
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("   ✅ Switched to local Tailwind CSS")

def build_tailwind():
    """Build Tailwind CSS for production"""
    print("🔨 Building Tailwind CSS...")
    
    try:
        # Ensure directories exist
        os.makedirs("src", exist_ok=True)
        os.makedirs("static", exist_ok=True)
        
        # Build Tailwind
        result = subprocess.run([
            "./node_modules/.bin/tailwindcss",
            "-i", "./src/input.css",
            "-o", "./static/tailwind.min.css",
            "--minify"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ Tailwind CSS built successfully")
            
            # Check file size
            if os.path.exists("static/tailwind.min.css"):
                size = os.path.getsize("static/tailwind.min.css")
                print(f"   📦 Build size: {size:,} bytes")
        else:
            print(f"   ❌ Build failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("   ❌ Tailwind CLI not found. Run: npm install -D @tailwindcss/cli")
        return False
    
    return True

def create_favicon():
    """Create a proper favicon"""
    print("🎯 Creating favicon...")
    
    # Create a simple SVG favicon
    favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="#ef4444" rx="20"/>
  <text x="50" y="70" font-size="60" text-anchor="middle" fill="white">📱</text>
</svg>'''
    
    with open("static/favicon.svg", 'w', encoding='utf-8') as f:
        f.write(favicon_svg)
    
    print("   ✅ Created SVG favicon")

def optimize_static_files():
    """Optimize static files for production"""
    print("⚡ Optimizing static files...")
    
    # Create .htaccess for caching (if using Apache)
    htaccess_content = '''# Cache static assets
<IfModule mod_expires.c>
    ExpiresActive on
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType image/svg+xml "access plus 1 year"
    ExpiresByType image/x-icon "access plus 1 year"
</IfModule>

# Gzip compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE image/svg+xml
</IfModule>'''
    
    with open("static/.htaccess", 'w') as f:
        f.write(htaccess_content)
    
    print("   ✅ Created .htaccess for caching")

def update_template_for_production():
    """Update template with production optimizations"""
    print("🔧 Applying production optimizations...")
    
    template_path = "templates/universal_tailwind.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update favicon reference
    content = re.sub(
        r'<link rel="icon" type="image/x-icon" href="data:image/svg\+xml[^"]*">',
        '<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">',
        content
    )
    
    # Add preload for critical CSS
    content = re.sub(
        r'(<link href="/static/tailwind\.min\.css" rel="stylesheet">)',
        r'<link rel="preload" href="/static/tailwind.min.css" as="style" onload="this.onload=null;this.rel=\'stylesheet\'">\n  \1',
        content
    )
    
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("   ✅ Applied production optimizations")

def create_production_config():
    """Create production configuration"""
    print("⚙️ Creating production configuration...")
    
    prod_config = '''# Production Configuration
# Set these environment variables for production deployment

# Required: FFmpeg path for video processing
FFMPEG_LOCATION=C:\\ffmpeg\\bin\\ffmpeg.exe

# Optional: Cookies for private content access
COOKIES_FILE=cookies.txt

# Optional: Aria2c for faster downloads
ARIA2C_PATH=C:\\aria2\\aria2c.exe

# Production settings
ENVIRONMENT=production
DEBUG=false

# Server settings
HOST=0.0.0.0
PORT=8000

# Security (set strong values in production)
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (if using)
DATABASE_URL=sqlite:///production.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/production.log
'''
    
    with open(".env.production", 'w') as f:
        f.write(prod_config)
    
    print("   ✅ Created .env.production template")

def main():
    print("🚀 Production Deployment Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("templates/universal_tailwind.html"):
        print("❌ Error: Run this script from the project root directory")
        sys.exit(1)
    
    # Step 1: Build Tailwind CSS
    if not build_tailwind():
        print("❌ Failed to build Tailwind CSS")
        sys.exit(1)
    
    # Step 2: Switch to local Tailwind
    switch_to_local_tailwind()
    
    # Step 3: Create favicon
    create_favicon()
    
    # Step 4: Optimize static files
    optimize_static_files()
    
    # Step 5: Update template
    update_template_for_production()
    
    # Step 6: Create production config
    create_production_config()
    
    print("\n" + "=" * 50)
    print("🎉 Production Setup Complete!")
    print("=" * 50)
    print("✅ Tailwind CSS: Local build (no CDN)")
    print("✅ Favicon: SVG favicon created")
    print("✅ Static files: Optimized with caching")
    print("✅ Template: Production-ready")
    print("✅ Config: .env.production template created")
    
    print("\n📋 Next Steps:")
    print("1. Review and customize .env.production")
    print("2. Set up your web server (nginx/Apache)")
    print("3. Configure SSL certificates")
    print("4. Set up monitoring and logging")
    print("5. Test with real social media URLs")
    
    print("\n🌐 Start production server:")
    print("   python -m uvicorn main_api:APP --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()