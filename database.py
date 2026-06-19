"""
Database Manager for Personal Media Downloader
With automatic schema migration support.
"""

import os
import sqlite3
import json
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict

# Try importing Config for default paths
try:
    from config import Config as _Cfg
    _DEFAULT_DB_PATH = _Cfg.DATABASE_PATH
except ImportError:
    _DEFAULT_DB_PATH = os.path.join(
        os.path.expanduser("~"), "Downloads", "downloader", "downloader.db"
    )

# Try importing utils
try:
    from utils import format_size, format_duration, get_logger, ensure_directory
except ImportError:
    def format_size(b): 
        if not b: return "0 B"
        for u in ['B','KB','MB','GB','TB']:
            if b < 1024: return f"{b:.2f} {u}"
            b /= 1024
        return f"{b:.2f} PB"
    def format_duration(s): 
        if not s: return "00:00"
        h, m, s = int(s//3600), int((s%3600)//60), int(s%60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    def get_logger(): 
        import logging
        return logging.getLogger("database")
    def ensure_directory(p): 
        os.makedirs(p, exist_ok=True)
        return True

logger = get_logger()


@dataclass
class DownloadRecord:
    """Download record"""
    id: Optional[int] = None
    url: str = ""
    platform: str = ""
    title: str = ""
    uploader: str = ""
    duration: float = 0
    quality: str = ""
    format: str = ""
    filesize: int = 0
    filepath: str = ""
    thumbnail_path: str = ""
    description: str = ""
    view_count: int = 0
    like_count: int = 0
    video_id: str = ""
    media_type: str = "video"
    status: str = "complete"
    error_message: str = ""
    download_date: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict):
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid}
        return cls(**filtered)
    
    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls.from_dict(dict(row))


@dataclass
class QueueItem:
    """Queue item"""
    id: Optional[int] = None
    url: str = ""
    priority: int = 0
    status: str = "pending"
    added_date: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


class DownloadStatus:
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DatabaseManager:
    """SQLite database manager with migration support"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _DEFAULT_DB_PATH
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # Ensure directory
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            ensure_directory(db_dir)
        
        # Initialize
        self._init_database()
        self._run_migrations()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA foreign_keys = ON")
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        cursor = self._conn.cursor()
        try:
            yield cursor
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def _init_database(self):
        """Create tables if not exist"""
        with self._lock:
            with self._cursor() as c:
                # Downloads table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        platform TEXT,
                        title TEXT,
                        uploader TEXT,
                        duration REAL DEFAULT 0,
                        quality TEXT,
                        format TEXT,
                        filesize INTEGER DEFAULT 0,
                        filepath TEXT,
                        thumbnail_path TEXT,
                        description TEXT,
                        view_count INTEGER DEFAULT 0,
                        like_count INTEGER DEFAULT 0,
                        video_id TEXT,
                        media_type TEXT DEFAULT 'video',
                        status TEXT DEFAULT 'pending',
                        error_message TEXT,
                        download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Playlists table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        title TEXT,
                        uploader TEXT,
                        platform TEXT,
                        video_count INTEGER DEFAULT 0,
                        downloaded_count INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # History table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        download_id INTEGER,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE
                    )
                ''')
                
                # Queue table - SIMPLE version
                c.execute('''
                    CREATE TABLE IF NOT EXISTS queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        priority INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Settings table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Indexes
                c.execute('CREATE INDEX IF NOT EXISTS idx_downloads_url ON downloads(url)')
                c.execute('CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)')
                c.execute('CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status)')
    
    def _run_migrations(self):
        """Run database migrations for schema updates"""
        with self._lock:
            with self._cursor() as c:
                # Get existing columns in downloads table
                c.execute("PRAGMA table_info(downloads)")
                download_cols = {row['name'] for row in c.fetchall()}
                
                # Add missing columns to downloads
                new_cols = [
                    ("media_type", "TEXT DEFAULT 'video'"),
                    ("error_message", "TEXT"),
                    ("video_id", "TEXT"),
                    ("thumbnail_path", "TEXT"),
                    ("description", "TEXT"),
                    ("view_count", "INTEGER DEFAULT 0"),
                    ("like_count", "INTEGER DEFAULT 0"),
                ]
                
                for col_name, col_def in new_cols:
                    if col_name not in download_cols:
                        try:
                            c.execute(f"ALTER TABLE downloads ADD COLUMN {col_name} {col_def}")
                        except:
                            pass
                
                # Get existing columns in queue table
                c.execute("PRAGMA table_info(queue)")
                queue_cols = {row['name'] for row in c.fetchall()}
                
                # Check if queue table needs to be recreated
                # If it has old columns, just work with what we have
                # The simple queue only needs: id, url, priority, status, added_date
    
    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    # ==================== DOWNLOADS ====================
    
    def add_download(self, record: DownloadRecord = None, **kwargs) -> int:
        """Add download record"""
        if record:
            data = record.to_dict()
            data.pop('id', None)
        else:
            data = kwargs
        
        url = data.get('url')
        if not url:
            raise ValueError("URL required")
        
        data.setdefault('status', 'complete')
        data.setdefault('media_type', 'video')
        data.setdefault('download_date', datetime.now().isoformat())
        
        # Truncate description
        if data.get('description') and len(str(data['description'])) > 1000:
            data['description'] = str(data['description'])[:1000]
        
        with self._lock:
            with self._cursor() as c:
                # Check exists
                c.execute("SELECT id FROM downloads WHERE url = ?", (url,))
                existing = c.fetchone()
                
                if existing:
                    # Update
                    cols = [k for k in data.keys() if k not in ('url', 'id')]
                    if cols:
                        set_clause = ", ".join([f"{k} = ?" for k in cols])
                        values = [data[k] for k in cols] + [url]
                        c.execute(f"UPDATE downloads SET {set_clause}, download_date = CURRENT_TIMESTAMP WHERE url = ?", values)
                    return existing['id']
                else:
                    # Insert
                    cols = [k for k in data.keys() if k != 'id']
                    placeholders = ", ".join(["?" for _ in cols])
                    c.execute(f"INSERT INTO downloads ({', '.join(cols)}) VALUES ({placeholders})", [data[k] for k in cols])
                    return c.lastrowid
    
    def get_download(self, download_id: int = None, url: str = None) -> Optional[DownloadRecord]:
        """Get download by ID or URL"""
        with self._cursor() as c:
            if download_id:
                c.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
            elif url:
                c.execute("SELECT * FROM downloads WHERE url = ?", (url,))
            else:
                return None
            return DownloadRecord.from_row(c.fetchone())
    
    def get_downloads(self, limit=100, offset=0, status=None, platform=None, order_desc=True) -> List[DownloadRecord]:
        """Get downloads with filtering"""
        query = "SELECT * FROM downloads WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        
        query += f" ORDER BY download_date {'DESC' if order_desc else 'ASC'} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._cursor() as c:
            c.execute(query, params)
            return [DownloadRecord.from_row(row) for row in c.fetchall()]
    
    def is_downloaded(self, url: str) -> bool:
        """Check if URL downloaded"""
        with self._cursor() as c:
            c.execute("SELECT status FROM downloads WHERE url = ?", (url,))
            row = c.fetchone()
            return row is not None and row['status'] == 'complete'
    
    def update_download_status(self, url: str = None, download_id: int = None, status: str = None, 
                                filepath: str = None, filesize: int = None, error: str = None) -> bool:
        """Update download status"""
        if not url and not download_id:
            return False
        
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        if filepath:
            updates.append("filepath = ?")
            params.append(filepath)
        if filesize is not None:
            updates.append("filesize = ?")
            params.append(filesize)
        if error is not None:
            updates.append("error_message = ?")
            params.append(error)
        
        if not updates:
            return False
        
        updates.append("download_date = CURRENT_TIMESTAMP")
        
        where = "id = ?" if download_id else "url = ?"
        params.append(download_id if download_id else url)
        
        with self._lock:
            with self._cursor() as c:
                c.execute(f"UPDATE downloads SET {', '.join(updates)} WHERE {where}", params)
                return c.rowcount > 0
    
    def delete_download(self, download_id: int = None, url: str = None) -> bool:
        """Delete download"""
        with self._lock:
            with self._cursor() as c:
                if download_id:
                    c.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
                elif url:
                    c.execute("DELETE FROM downloads WHERE url = ?", (url,))
                else:
                    return False
                return c.rowcount > 0
    
    def search_downloads(self, query: str, limit=50) -> List[DownloadRecord]:
        """Search downloads"""
        term = f"%{query}%"
        with self._cursor() as c:
            c.execute("""
                SELECT * FROM downloads 
                WHERE title LIKE ? OR uploader LIKE ? OR description LIKE ?
                ORDER BY download_date DESC LIMIT ?
            """, (term, term, term, limit))
            return [DownloadRecord.from_row(row) for row in c.fetchall()]
    
    def get_failed_downloads(self) -> List[DownloadRecord]:
        """Get failed downloads"""
        return self.get_downloads(status='failed', limit=1000)
    
    def clear_failed_downloads(self) -> int:
        """Delete failed downloads"""
        with self._lock:
            with self._cursor() as c:
                c.execute("DELETE FROM downloads WHERE status = 'failed'")
                return c.rowcount
    
    # ==================== STATISTICS ====================
    
    def get_statistics(self) -> Dict:
        """Get statistics"""
        with self._cursor() as c:
            stats = {}
            
            c.execute("SELECT COUNT(*) as n FROM downloads WHERE status = 'complete'")
            stats['total_downloads'] = c.fetchone()['n']
            
            c.execute("SELECT COALESCE(SUM(filesize), 0) as s FROM downloads WHERE status = 'complete'")
            size = c.fetchone()['s']
            stats['total_size_bytes'] = size
            stats['total_size_human'] = format_size(size)
            
            c.execute("SELECT COALESCE(SUM(duration), 0) as d FROM downloads WHERE status = 'complete'")
            dur = c.fetchone()['d']
            stats['total_duration'] = format_duration(dur)
            
            c.execute("""
                SELECT platform, COUNT(*) as n FROM downloads 
                WHERE status = 'complete' AND platform IS NOT NULL
                GROUP BY platform ORDER BY n DESC
            """)
            stats['by_platform'] = {r['platform']: r['n'] for r in c.fetchall()}
            
            c.execute("SELECT COUNT(*) as n FROM downloads WHERE status = 'failed'")
            stats['failed_downloads'] = c.fetchone()['n']
            
            return stats
    
    # ==================== QUEUE (Simplified) ====================
    
    def add_to_queue(self, url: str, priority: int = 0) -> int:
        """Add to queue"""
        with self._lock:
            with self._cursor() as c:
                c.execute("INSERT INTO queue (url, priority, status) VALUES (?, ?, 'pending')", (url, priority))
                return c.lastrowid
    
    def get_queue(self, status: str = "pending") -> List[QueueItem]:
        """Get queue items"""
        with self._cursor() as c:
            c.execute("SELECT * FROM queue WHERE status = ? ORDER BY priority DESC, added_date ASC", (status,))
            return [QueueItem(
                id=r['id'],
                url=r['url'],
                priority=r['priority'],
                status=r['status'],
                added_date=r['added_date']
            ) for r in c.fetchall()]
    
    def get_next_queue_item(self) -> Optional[QueueItem]:
        """Get next pending item"""
        items = self.get_queue("pending")
        return items[0] if items else None
    
    def update_queue_status(self, queue_id: int, status: str) -> bool:
        """Update queue status"""
        with self._lock:
            with self._cursor() as c:
                c.execute("UPDATE queue SET status = ? WHERE id = ?", (status, queue_id))
                return c.rowcount > 0
    
    def remove_from_queue(self, queue_id: int) -> bool:
        """Remove from queue"""
        with self._lock:
            with self._cursor() as c:
                c.execute("DELETE FROM queue WHERE id = ?", (queue_id,))
                return c.rowcount > 0
    
    def clear_queue(self, status: str = None) -> int:
        """Clear queue"""
        with self._lock:
            with self._cursor() as c:
                if status:
                    c.execute("DELETE FROM queue WHERE status = ?", (status,))
                else:
                    c.execute("DELETE FROM queue")
                return c.rowcount
    
    def get_queue_count(self, status: str = "pending") -> int:
        """Count queue items"""
        with self._cursor() as c:
            c.execute("SELECT COUNT(*) as n FROM queue WHERE status = ?", (status,))
            return c.fetchone()['n']
    
    # ==================== PLAYLISTS ====================
    
    def add_playlist(self, url: str, title: str, uploader: str = None, 
                     platform: str = None, video_count: int = 0) -> int:
        """Add/update playlist"""
        with self._lock:
            with self._cursor() as c:
                c.execute("""
                    INSERT INTO playlists (url, title, uploader, platform, video_count, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(url) DO UPDATE SET
                        title = excluded.title,
                        uploader = excluded.uploader,
                        platform = excluded.platform,
                        video_count = excluded.video_count,
                        last_updated = CURRENT_TIMESTAMP
                """, (url, title, uploader, platform, video_count))
                return c.lastrowid
    
    def update_playlist_progress(self, url: str, downloaded: int) -> bool:
        """Update playlist progress"""
        with self._lock:
            with self._cursor() as c:
                c.execute("UPDATE playlists SET downloaded_count = ?, last_updated = CURRENT_TIMESTAMP WHERE url = ?", (downloaded, url))
                return c.rowcount > 0
    
    # ==================== HISTORY ====================
    
    def add_history(self, download_id: int, action: str, details: str = None) -> int:
        """Add history entry"""
        with self._lock:
            with self._cursor() as c:
                c.execute("INSERT INTO history (download_id, action, details) VALUES (?, ?, ?)", (download_id, action, details))
                return c.lastrowid
    
    def get_history(self, download_id: int = None, limit: int = 100) -> List[Dict]:
        """Get history"""
        with self._cursor() as c:
            if download_id:
                c.execute("""
                    SELECT h.*, d.title, d.url FROM history h
                    LEFT JOIN downloads d ON h.download_id = d.id
                    WHERE h.download_id = ? ORDER BY h.timestamp DESC LIMIT ?
                """, (download_id, limit))
            else:
                c.execute("""
                    SELECT h.*, d.title, d.url FROM history h
                    LEFT JOIN downloads d ON h.download_id = d.id
                    ORDER BY h.timestamp DESC LIMIT ?
                """, (limit,))
            return [dict(r) for r in c.fetchall()]
    
    # ==================== SETTINGS ====================
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set setting"""
        with self._lock:
            with self._cursor() as c:
                c.execute("""
                    INSERT INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """, (key, json.dumps(value)))
                return True
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting"""
        with self._cursor() as c:
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = c.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except:
                    return row['value']
            return default
    
    # ==================== MAINTENANCE ====================
    
    def vacuum(self):
        """Optimize database"""
        with self._lock:
            self._conn.execute("VACUUM")
    
    def get_db_size(self) -> int:
        """Get database size"""
        try:
            return os.path.getsize(self.db_path)
        except:
            return 0
    
    def backup(self, backup_path: str) -> bool:
        """Backup database"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            return True
        except:
            return False
    
    def export_json(self, filepath: str) -> bool:
        """Export to JSON"""
        try:
            downloads = self.get_downloads(limit=100000)
            data = [d.to_dict() for d in downloads]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            return True
        except:
            return False


# Global instance
_db: Optional[DatabaseManager] = None

def get_database(db_path: str = None) -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager(db_path)
    return _db

def close_database():
    global _db
    if _db:
        _db.close()
        _db = None


if __name__ == "__main__":
    print("Database Module Test")
    print("=" * 50)
    
    db = DatabaseManager()
    
    # Test add
    print("\nAdding test download...")
    rec = DownloadRecord(
        url="https://test.com/video123",
        platform="YouTube",
        title="Test Video",
        uploader="Test User",
        duration=180,
        quality="1080p",
        filesize=50*1024*1024,
        status="complete"
    )
    did = db.add_download(rec)
    print(f"  ID: {did}")
    
    # Test queue
    print("\nAdding to queue...")
    qid = db.add_to_queue("https://test.com/queue_test")
    print(f"  Queue ID: {qid}")
    
    # Stats
    print("\nStatistics:")
    stats = db.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    db.close()
    print("\nDone!")