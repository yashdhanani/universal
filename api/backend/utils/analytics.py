"""
Performance Analytics and Monitoring System
Tracks usage patterns, performance metrics, and bottlenecks
"""

import sqlite3
import time
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from functools import wraps
import psutil
import threading

class PerformanceAnalytics:
    def __init__(self, db_path: str = "analytics/performance.db"):
        self.db_path = db_path
        
        # Ensure analytics directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        # Performance tracking
        self._request_times = []
        self._lock = threading.Lock()
    
    def _init_db(self):
        """Initialize analytics database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            # Request analytics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    status_code INTEGER,
                    platform TEXT,
                    url_hash TEXT,
                    format_requested TEXT,
                    user_agent TEXT,
                    ip_address TEXT
                )
            """)
            
            # Performance metrics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    cpu_percent REAL,
                    memory_mb REAL,
                    disk_io_read_mb REAL,
                    disk_io_write_mb REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    active_downloads INTEGER DEFAULT 0
                )
            """)
            
            # Popular formats
            conn.execute("""
                CREATE TABLE IF NOT EXISTS format_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    format_id TEXT NOT NULL,
                    quality TEXT,
                    file_type TEXT,
                    success BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Error tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT,
                    platform TEXT,
                    url_hash TEXT,
                    stack_trace TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_endpoint ON requests(endpoint)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_format_platform ON format_usage(platform, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp)")
            
            conn.commit()
    
    def log_request(self, endpoint: str, method: str, duration_ms: int, 
                   status_code: int = 200, platform: str = None, 
                   url_hash: str = None, format_requested: str = None,
                   user_agent: str = None, ip_address: str = None):
        """Log API request"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO requests 
                (timestamp, endpoint, method, duration_ms, status_code, platform, 
                 url_hash, format_requested, user_agent, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(time.time()), endpoint, method, duration_ms, status_code,
                platform, url_hash, format_requested, user_agent, ip_address
            ))
            conn.commit()
    
    def log_performance_metrics(self):
        """Log current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO performance_metrics 
                    (timestamp, cpu_percent, memory_mb, disk_io_read_mb, 
                     disk_io_write_mb, network_sent_mb, network_recv_mb)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(time.time()),
                    cpu_percent,
                    memory.used / 1024 / 1024,
                    disk_io.read_bytes / 1024 / 1024 if disk_io else 0,
                    disk_io.write_bytes / 1024 / 1024 if disk_io else 0,
                    network_io.bytes_sent / 1024 / 1024 if network_io else 0,
                    network_io.bytes_recv / 1024 / 1024 if network_io else 0
                ))
                conn.commit()
        except Exception:
            pass  # Don't let analytics break the app
    
    def log_format_usage(self, platform: str, format_id: str, 
                        quality: str = None, file_type: str = None, 
                        success: bool = True):
        """Log format usage statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO format_usage 
                (timestamp, platform, format_id, quality, file_type, success)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (int(time.time()), platform, format_id, quality, file_type, success))
            conn.commit()
    
    def log_error(self, endpoint: str, error_type: str, error_message: str,
                 platform: str = None, url_hash: str = None, stack_trace: str = None):
        """Log error for analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO errors 
                (timestamp, endpoint, error_type, error_message, platform, url_hash, stack_trace)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (int(time.time()), endpoint, error_type, error_message, 
                  platform, url_hash, stack_trace))
            conn.commit()
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        cutoff_time = int(time.time()) - (hours * 3600)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Request statistics
            requests = conn.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    AVG(duration_ms) as avg_duration_ms,
                    MIN(duration_ms) as min_duration_ms,
                    MAX(duration_ms) as max_duration_ms,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
                FROM requests 
                WHERE timestamp > ?
            """, (cutoff_time,)).fetchone()
            
            # Popular endpoints
            endpoints = conn.execute("""
                SELECT endpoint, COUNT(*) as count, AVG(duration_ms) as avg_duration
                FROM requests 
                WHERE timestamp > ?
                GROUP BY endpoint 
                ORDER BY count DESC 
                LIMIT 10
            """, (cutoff_time,)).fetchall()
            
            # Popular platforms
            platforms = conn.execute("""
                SELECT platform, COUNT(*) as count 
                FROM requests 
                WHERE timestamp > ? AND platform IS NOT NULL
                GROUP BY platform 
                ORDER BY count DESC
            """, (cutoff_time,)).fetchall()
            
            # Popular formats
            formats = conn.execute("""
                SELECT platform, format_id, quality, COUNT(*) as count
                FROM format_usage 
                WHERE timestamp > ?
                GROUP BY platform, format_id, quality 
                ORDER BY count DESC 
                LIMIT 10
            """, (cutoff_time,)).fetchall()
            
            # Recent errors
            errors = conn.execute("""
                SELECT endpoint, error_type, error_message, COUNT(*) as count
                FROM errors 
                WHERE timestamp > ?
                GROUP BY endpoint, error_type, error_message 
                ORDER BY count DESC 
                LIMIT 5
            """, (cutoff_time,)).fetchall()
            
            # Performance trends
            perf_avg = conn.execute("""
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    AVG(memory_mb) as avg_memory_mb,
                    MAX(memory_mb) as max_memory_mb
                FROM performance_metrics 
                WHERE timestamp > ?
            """, (cutoff_time,)).fetchone()
            
            return {
                'time_period_hours': hours,
                'requests': {
                    'total': requests['total_requests'],
                    'avg_duration_ms': round(requests['avg_duration_ms'] or 0, 2),
                    'min_duration_ms': requests['min_duration_ms'] or 0,
                    'max_duration_ms': requests['max_duration_ms'] or 0,
                    'error_rate': round((requests['error_count'] or 0) / max(requests['total_requests'], 1) * 100, 2)
                },
                'popular_endpoints': [dict(row) for row in endpoints],
                'popular_platforms': [dict(row) for row in platforms],
                'popular_formats': [dict(row) for row in formats],
                'recent_errors': [dict(row) for row in errors],
                'system_performance': {
                    'avg_cpu_percent': round(perf_avg['avg_cpu'] or 0, 2),
                    'avg_memory_mb': round(perf_avg['avg_memory_mb'] or 0, 2),
                    'max_memory_mb': round(perf_avg['max_memory_mb'] or 0, 2)
                }
            }
    
    def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Slow endpoints
            slow_endpoints = conn.execute("""
                SELECT endpoint, AVG(duration_ms) as avg_duration, COUNT(*) as count
                FROM requests 
                WHERE timestamp > ? AND duration_ms > 5000
                GROUP BY endpoint 
                HAVING count > 5
                ORDER BY avg_duration DESC
            """, (int(time.time()) - 3600,)).fetchall()
            
            for endpoint in slow_endpoints:
                bottlenecks.append({
                    'type': 'slow_endpoint',
                    'endpoint': endpoint['endpoint'],
                    'avg_duration_ms': round(endpoint['avg_duration'], 2),
                    'count': endpoint['count'],
                    'severity': 'high' if endpoint['avg_duration'] > 15000 else 'medium'
                })
            
            # High error rate endpoints
            error_endpoints = conn.execute("""
                SELECT 
                    endpoint, 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors
                FROM requests 
                WHERE timestamp > ?
                GROUP BY endpoint 
                HAVING total > 10 AND (errors * 100.0 / total) > 10
                ORDER BY (errors * 100.0 / total) DESC
            """, (int(time.time()) - 3600,)).fetchall()
            
            for endpoint in error_endpoints:
                error_rate = (endpoint['errors'] / endpoint['total']) * 100
                bottlenecks.append({
                    'type': 'high_error_rate',
                    'endpoint': endpoint['endpoint'],
                    'error_rate': round(error_rate, 2),
                    'total_requests': endpoint['total'],
                    'severity': 'high' if error_rate > 25 else 'medium'
                })
        
        return bottlenecks

# Global analytics instance
_analytics_instance = None

def get_analytics() -> PerformanceAnalytics:
    """Get global analytics instance"""
    global _analytics_instance
    if _analytics_instance is None:
        analytics_dir = os.path.join(os.getcwd(), "analytics")
        _analytics_instance = PerformanceAnalytics(os.path.join(analytics_dir, "performance.db"))
    return _analytics_instance

def track_performance(endpoint: str):
    """Decorator to track endpoint performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            analytics = get_analytics()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                analytics.log_request(endpoint, "POST", duration_ms, 200)
                return result
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                analytics.log_request(endpoint, "POST", duration_ms, 500)
                analytics.log_error(endpoint, type(e).__name__, str(e))
                raise
        return wrapper
    return decorator