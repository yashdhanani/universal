"""
SQLite-based caching system for ultra-fast repeated requests
Provides persistent, lightweight caching for video analysis
"""

import sqlite3
import json
import hashlib
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class VideoCache:
    def __init__(self, db_path: str = "cache/video_cache.db", ttl_hours: int = 24):
        self.db_path = db_path
        self.ttl_seconds = ttl_hours * 3600
        
        # Ensure cache directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with optimized settings"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for performance
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            conn.execute("PRAGMA cache_size=10000")  # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            
            # Create tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_cache (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    accessed_at INTEGER NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform_created 
                ON video_cache(platform, created_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_accessed_at 
                ON video_cache(accessed_at)
            """)
            
            conn.commit()
    
    def _get_url_hash(self, url: str) -> str:
        """Generate consistent hash for URL"""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def get(self, url: str, platform: str = "youtube") -> Optional[Dict[str, Any]]:
        """Get cached video data if available and not expired"""
        url_hash = self._get_url_hash(url)
        current_time = int(time.time())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT data, created_at FROM video_cache 
                WHERE url_hash = ? AND platform = ?
            """, (url_hash, platform))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Check if expired
            if current_time - row['created_at'] > self.ttl_seconds:
                # Delete expired entry
                conn.execute("DELETE FROM video_cache WHERE url_hash = ?", (url_hash,))
                conn.commit()
                return None
            
            # Update access statistics
            conn.execute("""
                UPDATE video_cache 
                SET accessed_at = ?, access_count = access_count + 1
                WHERE url_hash = ?
            """, (current_time, url_hash))
            conn.commit()
            
            try:
                return json.loads(row['data'])
            except json.JSONDecodeError:
                # Corrupted data, remove it
                conn.execute("DELETE FROM video_cache WHERE url_hash = ?", (url_hash,))
                conn.commit()
                return None
    
    def set(self, url: str, data: Dict[str, Any], platform: str = "youtube"):
        """Cache video data"""
        url_hash = self._get_url_hash(url)
        current_time = int(time.time())
        data_json = json.dumps(data, separators=(',', ':'))  # Compact JSON
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO video_cache 
                (url_hash, url, platform, data, created_at, accessed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (url_hash, url, platform, data_json, current_time, current_time))
            conn.commit()
    
    def clear_expired(self):
        """Remove expired cache entries"""
        current_time = int(time.time())
        cutoff_time = current_time - self.ttl_seconds
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM video_cache WHERE created_at < ?", (cutoff_time,))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total entries
            total = conn.execute("SELECT COUNT(*) as count FROM video_cache").fetchone()['count']
            
            # By platform
            platforms = conn.execute("""
                SELECT platform, COUNT(*) as count 
                FROM video_cache 
                GROUP BY platform
            """).fetchall()
            
            # Most accessed
            popular = conn.execute("""
                SELECT url, access_count, platform
                FROM video_cache 
                ORDER BY access_count DESC 
                LIMIT 5
            """).fetchall()
            
            # Cache size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            return {
                'total_entries': total,
                'platforms': {row['platform']: row['count'] for row in platforms},
                'popular_videos': [dict(row) for row in popular],
                'db_size_mb': round(db_size / 1024 / 1024, 2),
                'ttl_hours': self.ttl_seconds / 3600
            }
    
    def clear_all(self):
        """Clear all cache entries"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM video_cache")
            conn.execute("VACUUM")  # Reclaim space
            conn.commit()

# Global cache instance
_cache_instance = None

def get_cache() -> VideoCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        cache_dir = os.path.join(os.getcwd(), "cache")
        _cache_instance = VideoCache(os.path.join(cache_dir, "video_cache.db"))
    return _cache_instance

def cache_video_analysis(platform: str):
    """Decorator to cache video analysis results"""
    def decorator(func):
        def wrapper(url: str, *args, **kwargs):
            cache = get_cache()
            
            # Try to get from cache first
            cached_result = cache.get(url, platform)
            if cached_result:
                return cached_result
            
            # Not in cache, call original function
            result = func(url, *args, **kwargs)
            
            # Cache the result
            cache.set(url, result, platform)
            
            return result
        return wrapper
    return decorator