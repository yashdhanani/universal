"""
Authentication Manager
Handles cookies, login sessions, and private content access
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import tempfile
import shutil

class AuthManager:
    """Manages authentication cookies and sessions for different platforms"""
    
    def __init__(self, cookies_dir: str = "cookies"):
        self.cookies_dir = Path(cookies_dir)
        self.cookies_dir.mkdir(exist_ok=True)
        self.active_sessions = {}
        
    def save_cookies(self, platform: str, cookies_content: str, 
                    session_name: str = "default") -> Dict[str, Any]:
        """Save cookies for a platform"""
        try:
            # Create platform directory
            platform_dir = self.cookies_dir / platform
            platform_dir.mkdir(exist_ok=True)
            
            # Generate session info
            session_id = hashlib.md5(f"{platform}_{session_name}_{time.time()}".encode()).hexdigest()[:12]
            timestamp = datetime.now().isoformat()
            
            # Save cookies file
            cookies_file = platform_dir / f"{session_name}_{session_id}.txt"
            with open(cookies_file, 'w', encoding='utf-8') as f:
                f.write(cookies_content)
            
            # Save session metadata
            metadata = {
                "session_id": session_id,
                "session_name": session_name,
                "platform": platform,
                "created_at": timestamp,
                "cookies_file": str(cookies_file),
                "status": "active",
                "last_used": timestamp,
                "usage_count": 0
            }
            
            metadata_file = platform_dir / f"{session_name}_{session_id}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            # Update active sessions
            if platform not in self.active_sessions:
                self.active_sessions[platform] = {}
            self.active_sessions[platform][session_name] = metadata
            
            return {
                "success": True,
                "session_id": session_id,
                "session_name": session_name,
                "platform": platform,
                "message": f"Cookies saved successfully for {platform}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save cookies for {platform}"
            }
    
    def get_cookies_file(self, platform: str, session_name: str = "default") -> Optional[str]:
        """Get the cookies file path for a platform session"""
        try:
            platform_dir = self.cookies_dir / platform
            if not platform_dir.exists():
                return None
            
            # Find the most recent session if session_name is not specific
            sessions = []
            for metadata_file in platform_dir.glob(f"{session_name}_*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    if metadata.get("status") == "active":
                        sessions.append(metadata)
                except:
                    continue
            
            if not sessions:
                return None
            
            # Sort by last_used and return the most recent
            sessions.sort(key=lambda x: x.get("last_used", ""), reverse=True)
            cookies_file = sessions[0]["cookies_file"]
            
            # Update usage
            self._update_session_usage(platform, sessions[0]["session_id"])
            
            return cookies_file if Path(cookies_file).exists() else None
            
        except Exception:
            return None
    
    def list_sessions(self, platform: str = None) -> List[Dict[str, Any]]:
        """List all available sessions"""
        sessions = []
        
        platforms = [platform] if platform else [d.name for d in self.cookies_dir.iterdir() if d.is_dir()]
        
        for plat in platforms:
            platform_dir = self.cookies_dir / plat
            if not platform_dir.exists():
                continue
                
            for metadata_file in platform_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Add file size info
                    cookies_file = Path(metadata["cookies_file"])
                    if cookies_file.exists():
                        metadata["file_size"] = cookies_file.stat().st_size
                        metadata["file_exists"] = True
                    else:
                        metadata["file_exists"] = False
                    
                    sessions.append(metadata)
                except:
                    continue
        
        # Sort by platform, then by last_used
        sessions.sort(key=lambda x: (x.get("platform", ""), x.get("last_used", "")), reverse=True)
        return sessions
    
    def delete_session(self, platform: str, session_id: str) -> Dict[str, Any]:
        """Delete a session and its files"""
        try:
            platform_dir = self.cookies_dir / platform
            
            # Find and delete session files
            deleted_files = []
            for file_path in platform_dir.glob(f"*_{session_id}.*"):
                file_path.unlink()
                deleted_files.append(str(file_path))
            
            # Remove from active sessions
            if platform in self.active_sessions:
                self.active_sessions[platform] = {
                    k: v for k, v in self.active_sessions[platform].items()
                    if v.get("session_id") != session_id
                }
            
            return {
                "success": True,
                "deleted_files": deleted_files,
                "message": f"Session {session_id} deleted successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to delete session {session_id}"
            }
    
    def validate_cookies(self, platform: str, session_name: str = "default") -> Dict[str, Any]:
        """Validate cookies by testing with yt-dlp"""
        cookies_file = self.get_cookies_file(platform, session_name)
        if not cookies_file:
            return {
                "valid": False,
                "error": "No cookies file found",
                "message": f"No cookies available for {platform}"
            }
        
        try:
            import yt_dlp
            
            # Test URLs for different platforms
            test_urls = {
                "instagram": "https://www.instagram.com/",
                "facebook": "https://www.facebook.com/",
                "twitter": "https://twitter.com/home",
                "tiktok": "https://www.tiktok.com/",
                "youtube": "https://www.youtube.com/"
            }
            
            test_url = test_urls.get(platform, f"https://www.{platform}.com/")
            
            # Create yt-dlp options with cookies
            ydl_opts = {
                'cookiefile': cookies_file,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Try to extract basic info (this will test cookie validity)
                info = ydl.extract_info(test_url, download=False)
                
            return {
                "valid": True,
                "message": f"Cookies are valid for {platform}",
                "test_url": test_url
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": f"Cookies validation failed for {platform}"
            }
    
    def _update_session_usage(self, platform: str, session_id: str):
        """Update session usage statistics"""
        try:
            platform_dir = self.cookies_dir / platform
            for metadata_file in platform_dir.glob(f"*_{session_id}.json"):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                metadata["last_used"] = datetime.now().isoformat()
                metadata["usage_count"] = metadata.get("usage_count", 0) + 1
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                break
        except:
            pass
    
    def export_session(self, platform: str, session_id: str) -> Optional[str]:
        """Export session as a downloadable file"""
        try:
            platform_dir = self.cookies_dir / platform
            
            # Find session files
            session_files = list(platform_dir.glob(f"*_{session_id}.*"))
            if not session_files:
                return None
            
            # Create temporary zip file
            import zipfile
            temp_dir = Path(tempfile.mkdtemp())
            zip_path = temp_dir / f"{platform}_{session_id}_cookies.zip"
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in session_files:
                    zipf.write(file_path, file_path.name)
            
            return str(zip_path)
            
        except Exception:
            return None
    
    def import_session(self, platform: str, zip_file_path: str) -> Dict[str, Any]:
        """Import session from uploaded zip file"""
        try:
            import zipfile
            
            platform_dir = self.cookies_dir / platform
            platform_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_file_path, 'r') as zipf:
                zipf.extractall(platform_dir)
            
            return {
                "success": True,
                "message": f"Session imported successfully for {platform}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import session for {platform}"
            }
    
    def cleanup_old_sessions(self, days: int = 30):
        """Clean up sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned = []
        
        for platform_dir in self.cookies_dir.iterdir():
            if not platform_dir.is_dir():
                continue
                
            for metadata_file in platform_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    last_used = datetime.fromisoformat(metadata.get("last_used", ""))
                    if last_used < cutoff_date:
                        session_id = metadata["session_id"]
                        result = self.delete_session(platform_dir.name, session_id)
                        if result["success"]:
                            cleaned.append(f"{platform_dir.name}:{session_id}")
                except:
                    continue
        
        return cleaned

# Global auth manager instance
auth_manager = AuthManager()