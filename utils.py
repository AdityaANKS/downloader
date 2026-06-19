
import os
import sys
import re
import shutil
import hashlib
import subprocess
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any, Union
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import json

# ============================================================================
# CONSTANTS
# ============================================================================

INVALID_FILENAME_CHARS = '<>:"/\\|?*'
INVALID_FILENAME_CHARS_REGEX = re.compile(r'[<>:"/\\|?*]')
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

# File size units
SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

# Time units
TIME_UNITS = [
    (86400, 'd'),
    (3600, 'h'),
    (60, 'm'),
    (1, 's')
]


# ============================================================================
# LOGGING UTILITIES
# ============================================================================

class LoggerSetup:
    """Setup and manage logging"""
    
    _instance = None
    _logger = None
    
    @classmethod
    def get_logger(cls, name: str = "downloader", 
                   log_file: str = None,
                   level: str = "INFO",
                   log_to_file: bool = True,
                   log_to_console: bool = False) -> logging.Logger:
        """Get or create logger instance"""
        
        if cls._logger is not None:
            return cls._logger
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.handlers = []
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        if log_to_file and log_file:
            try:
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not create log file: {e}")
        
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            logger.addHandler(console_handler)
        
        cls._logger = logger
        return logger


def get_logger() -> logging.Logger:
    """Get the default logger"""
    return LoggerSetup.get_logger()


# ============================================================================
# STRING UTILITIES
# ============================================================================

def sanitize_filename(filename: str, 
                      max_length: int = 200,
                      replace_char: str = '_',
                      remove_emojis: bool = True,
                      ascii_only: bool = True) -> str:
    """
    Sanitize a string for use as a filename.
    
    Args:
        filename: The filename to sanitize
        max_length: Maximum length of the filename
        replace_char: Character to replace invalid chars with
        remove_emojis: Whether to remove emoji characters
        ascii_only: Whether to keep only ASCII characters
    
    Returns:
        Sanitized filename string
    """
    if not filename:
        return 'untitled'
    
    # Remove/replace invalid characters
    result = INVALID_FILENAME_CHARS_REGEX.sub(replace_char, filename)
    
    # Remove control characters (0-31)
    result = ''.join(char for char in result if ord(char) >= 32)
    
    # Remove emojis if requested
    if remove_emojis:
        result = EMOJI_PATTERN.sub('', result)
    
    # Convert to ASCII if requested
    if ascii_only:
        result = result.encode('ascii', 'ignore').decode('ascii')
    
    # Clean up multiple spaces/underscores
    result = re.sub(r'[_\s]+', ' ', result)
    
    # Remove leading/trailing whitespace and dots
    result = result.strip(' .')
    
    # Handle reserved Windows names
    reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 
                      'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                      'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
    name_upper = result.upper().split('.')[0]
    if name_upper in reserved_names:
        result = f"_{result}"
    
    # Limit length (preserve extension if present)
    if len(result) > max_length:
        name, ext = os.path.splitext(result)
        max_name_len = max_length - len(ext)
        result = name[:max_name_len].rstrip() + ext
    
    # Ensure not empty
    if not result or result == '.':
        result = 'untitled'
    
    return result


def truncate_string(text: str, max_length: int, suffix: str = '...') -> str:
    """Truncate string to max length with suffix"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_title(title: str) -> str:
    """Clean a video/audio title"""
    if not title:
        return 'Untitled'
    
    # Remove common suffixes
    patterns_to_remove = [
        r'\s*\[Official\s*(Video|Audio|Music\s*Video)?\]',
        r'\s*\(Official\s*(Video|Audio|Music\s*Video)?\)',
        r'\s*\|\s*Official\s*(Video|Audio)',
        r'\s*-\s*Official\s*(Video|Audio)',
        r'\s*\[HD\]',
        r'\s*\[4K\]',
        r'\s*\[Lyrics?\]',
        r'\s*\(Lyrics?\)',
    ]
    
    result = title
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    return result.strip()


def extract_video_id(url: str, platform: str = None) -> Optional[str]:
    """Extract video ID from URL"""
    parsed = urlparse(url)
    
    # YouTube
    if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
        if 'youtu.be' in parsed.netloc:
            return parsed.path.strip('/')
        if 'v' in parse_qs(parsed.query):
            return parse_qs(parsed.query)['v'][0]
        if '/shorts/' in parsed.path:
            return parsed.path.split('/shorts/')[-1].split('/')[0]
        if '/embed/' in parsed.path:
            return parsed.path.split('/embed/')[-1].split('/')[0]
    
    # Instagram
    if 'instagram.com' in parsed.netloc:
        parts = parsed.path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] in ['p', 'reel', 'reels', 'tv']:
            return parts[1]
    
    # Twitter/X
    if 'twitter.com' in parsed.netloc or 'x.com' in parsed.netloc:
        match = re.search(r'/status/(\d+)', parsed.path)
        if match:
            return match.group(1)
    
    # TikTok
    if 'tiktok.com' in parsed.netloc:
        match = re.search(r'/video/(\d+)', parsed.path)
        if match:
            return match.group(1)
    
    # Vimeo
    if 'vimeo.com' in parsed.netloc:
        match = re.search(r'/(\d+)', parsed.path)
        if match:
            return match.group(1)
    
    return None


# ============================================================================
# SIZE & TIME FORMATTING
# ============================================================================

def format_size(size_bytes: Union[int, float], precision: int = 2) -> str:
    """
    Format bytes to human-readable size.
    
    Args:
        size_bytes: Size in bytes
        precision: Decimal precision
    
    Returns:
        Formatted size string (e.g., "1.50 GB")
    """
    if size_bytes is None or size_bytes < 0:
        return "Unknown"
    
    if size_bytes == 0:
        return "0 B"
    
    size = float(size_bytes)
    for unit in SIZE_UNITS:
        if size < 1024:
            return f"{size:.{precision}f} {unit}"
        size /= 1024
    
    return f"{size:.{precision}f} PB"


def parse_size(size_str: str) -> Optional[int]:
    """
    Parse human-readable size to bytes.
    
    Args:
        size_str: Size string (e.g., "1.5 GB", "500MB")
    
    Returns:
        Size in bytes or None if parsing fails
    """
    if not size_str:
        return None
    
    size_str = size_str.strip().upper()
    
    # Extract number and unit
    match = re.match(r'^([\d.]+)\s*([KMGTP]?B?)$', size_str)
    if not match:
        return None
    
    try:
        number = float(match.group(1))
        unit = match.group(2) or 'B'
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
            'PB': 1024 ** 5,
            'K': 1024,
            'M': 1024 ** 2,
            'G': 1024 ** 3,
            'T': 1024 ** 4,
        }
        
        return int(number * multipliers.get(unit, 1))
    except (ValueError, KeyError):
        return None


def format_duration(seconds: Union[int, float], 
                    compact: bool = False,
                    include_ms: bool = False) -> str:
    """
    Format seconds to duration string.
    
    Args:
        seconds: Duration in seconds
        compact: Use compact format (1h 30m vs 01:30:00)
        include_ms: Include milliseconds
    
    Returns:
        Formatted duration string
    """
    if seconds is None or seconds < 0:
        return "00:00" if not compact else "0s"
    
    total_seconds = int(seconds)
    ms = int((seconds - total_seconds) * 1000) if include_ms else 0
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if compact:
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        if include_ms and ms > 0:
            parts.append(f"{ms}ms")
        return ' '.join(parts)
    else:
        if hours > 0:
            result = f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            result = f"{minutes:02d}:{secs:02d}"
        
        if include_ms:
            result += f".{ms:03d}"
        
        return result


def parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse duration string to seconds.
    
    Args:
        duration_str: Duration string (e.g., "01:30:00", "1h 30m", "90")
    
    Returns:
        Duration in seconds or None if parsing fails
    """
    if not duration_str:
        return None
    
    duration_str = duration_str.strip()
    
    # Try HH:MM:SS or MM:SS format
    time_pattern = re.match(r'^(\d+):(\d{2})(?::(\d{2}))?$', duration_str)
    if time_pattern:
        groups = time_pattern.groups()
        if groups[2] is not None:
            # HH:MM:SS
            return int(groups[0]) * 3600 + int(groups[1]) * 60 + int(groups[2])
        else:
            # MM:SS
            return int(groups[0]) * 60 + int(groups[1])
    
    # Try compact format (1h 30m 45s)
    total = 0
    patterns = [
        (r'(\d+)\s*h', 3600),
        (r'(\d+)\s*m', 60),
        (r'(\d+)\s*s', 1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, duration_str, re.IGNORECASE)
        if match:
            total += int(match.group(1)) * multiplier
    
    if total > 0:
        return total
    
    # Try plain number
    try:
        return int(float(duration_str))
    except ValueError:
        return None


def format_timestamp(dt: datetime = None, format_str: str = None) -> str:
    """Format datetime to string"""
    dt = dt or datetime.now()
    format_str = format_str or "%Y-%m-%d %H:%M:%S"
    return dt.strftime(format_str)


def format_relative_time(seconds: int) -> str:
    """Format seconds to relative time (e.g., '2 hours ago')"""
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} minute{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days > 1 else ''} ago"


# ============================================================================
# FILE SYSTEM UTILITIES
# ============================================================================

def get_unique_filepath(filepath: str) -> str:
    """
    Get a unique filepath if the file already exists.
    Appends (1), (2), etc. to the filename.
    """
    if not os.path.exists(filepath):
        return filepath
    
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    
    counter = 1
    while True:
        new_filename = f"{name} ({counter}){ext}"
        new_filepath = os.path.join(directory, new_filename)
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1
        if counter > 1000:  # Safety limit
            raise RuntimeError("Could not find unique filename")


def ensure_directory(path: str) -> bool:
    """Ensure a directory exists, create if necessary"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


def get_file_hash(filepath: str, algorithm: str = 'md5', 
                  chunk_size: int = 8192) -> Optional[str]:
    """Calculate file hash"""
    try:
        hasher = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def get_free_space(path: str) -> Tuple[int, int, int]:
    """
    Get disk space info for a path.
    
    Returns:
        Tuple of (total, used, free) in bytes
    """
    try:
        total, used, free = shutil.disk_usage(path)
        return total, used, free
    except Exception:
        return 0, 0, 0


def get_free_space_mb(path: str) -> int:
    """Get free disk space in MB"""
    _, _, free = get_free_space(path)
    return free // (1024 * 1024)


def check_disk_space(path: str, required_mb: int) -> bool:
    """Check if there's enough disk space"""
    return get_free_space_mb(path) >= required_mb


def find_file(directory: str, 
              name_contains: str = None,
              extensions: List[str] = None,
              newest_first: bool = True) -> Optional[str]:
    """
    Find a file in a directory.
    
    Args:
        directory: Directory to search
        name_contains: Substring the filename should contain
        extensions: List of valid extensions (e.g., ['.mp4', '.mkv'])
        newest_first: Sort by modification time, newest first
    
    Returns:
        Full path to the found file, or None
    """
    if not os.path.exists(directory):
        return None
    
    files = []
    for f in os.listdir(directory):
        filepath = os.path.join(directory, f)
        if not os.path.isfile(filepath):
            continue
        
        # Check extension
        if extensions:
            _, ext = os.path.splitext(f)
            if ext.lower() not in [e.lower() for e in extensions]:
                continue
        
        # Check name
        if name_contains:
            if name_contains.lower() not in f.lower():
                continue
        
        files.append((filepath, os.path.getmtime(filepath)))
    
    if not files:
        return None
    
    # Sort by modification time
    files.sort(key=lambda x: x[1], reverse=newest_first)
    
    return files[0][0]


def delete_file_safe(filepath: str) -> bool:
    """Safely delete a file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except Exception:
        return False


def move_file_safe(src: str, dst: str) -> bool:
    """Safely move a file"""
    try:
        # Ensure destination directory exists
        dst_dir = os.path.dirname(dst)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)
        
        shutil.move(src, dst)
        return True
    except Exception:
        return False


def get_file_info(filepath: str) -> Optional[Dict]:
    """Get file information"""
    try:
        stat = os.stat(filepath)
        return {
            'path': filepath,
            'name': os.path.basename(filepath),
            'size': stat.st_size,
            'size_human': format_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'extension': os.path.splitext(filepath)[1].lower(),
        }
    except Exception:
        return None


# ============================================================================
# SYSTEM UTILITIES
# ============================================================================

def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH"""
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            [command, '--version'] if command != 'ffmpeg' else [command, '-version'],
            capture_output=True,
            startupinfo=startupinfo
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available"""
    return check_command_exists('ffmpeg')


def check_ffprobe() -> bool:
    """Check if FFprobe is available"""
    return check_command_exists('ffprobe')


def run_command(command: List[str], 
                timeout: int = None,
                capture_output: bool = True) -> Tuple[int, str, str]:
    """
    Run a system command.
    
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            startupinfo=startupinfo
        )
        return result.returncode, result.stdout or '', result.stderr or ''
    except subprocess.TimeoutExpired:
        return -1, '', 'Command timed out'
    except Exception as e:
        return -1, '', str(e)


def get_ffmpeg_version() -> Optional[str]:
    """Get FFmpeg version"""
    code, stdout, _ = run_command(['ffmpeg', '-version'])
    if code == 0 and stdout:
        match = re.search(r'ffmpeg version (\S+)', stdout)
        if match:
            return match.group(1)
    return None


def get_python_version() -> str:
    """Get Python version"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def is_windows() -> bool:
    """Check if running on Windows"""
    return os.name == 'nt'


def is_linux() -> bool:
    """Check if running on Linux"""
    return sys.platform.startswith('linux')


def is_macos() -> bool:
    """Check if running on macOS"""
    return sys.platform == 'darwin'


# ============================================================================
# URL UTILITIES
# ============================================================================

def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize a URL"""
    url = url.strip()
    
    # Add https:// if no scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    return url


def get_domain(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def clean_url(url: str) -> str:
    """Clean URL by removing tracking parameters"""
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        
        # Parameters to remove (common tracking params)
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'ref', 'source', 'feature', 'si', 'pp'
        }
        
        # Filter query parameters
        cleaned_query = {k: v for k, v in query.items() if k.lower() not in tracking_params}
        
        # Rebuild URL
        from urllib.parse import urlencode
        new_query = urlencode(cleaned_query, doseq=True)
        
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (f"?{new_query}" if new_query else "")
    except Exception:
        return url


# ============================================================================
# PROGRESS UTILITIES
# ============================================================================

class ProgressTracker:
    """Track download/operation progress"""
    
    def __init__(self, total: int = 0, description: str = ""):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 0.5  # seconds
    
    def update(self, amount: int = 1) -> None:
        """Update progress"""
        self.current += amount
    
    def set_progress(self, current: int) -> None:
        """Set current progress"""
        self.current = current
    
    @property
    def percentage(self) -> float:
        """Get percentage complete"""
        if self.total <= 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    @property
    def speed(self) -> float:
        """Get speed (units per second)"""
        elapsed = self.elapsed
        if elapsed <= 0:
            return 0.0
        return self.current / elapsed
    
    @property
    def eta(self) -> float:
        """Get estimated time remaining in seconds"""
        if self.speed <= 0 or self.current >= self.total:
            return 0.0
        remaining = self.total - self.current
        return remaining / self.speed
    
    def get_progress_bar(self, width: int = 40) -> str:
        """Generate a text progress bar"""
        filled = int(width * self.percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {self.percentage:.1f}%"
    
    def should_update_display(self) -> bool:
        """Check if display should be updated (rate limiting)"""
        now = time.time()
        if now - self.last_update >= self.update_interval:
            self.last_update = now
            return True
        return False
    
    def get_status_line(self) -> str:
        """Get a complete status line"""
        bar = self.get_progress_bar()
        speed_str = format_size(self.speed) + "/s" if self.speed > 0 else "---"
        eta_str = format_duration(self.eta, compact=True) if self.eta > 0 else "--"
        return f"{bar} | {speed_str} | ETA: {eta_str}"


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_path(path: str) -> Tuple[bool, str]:
    """
    Validate a file path.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Path is empty"
    
    try:
        # Check for invalid characters
        if os.name == 'nt':
            # Windows-specific checks
            invalid_chars = '<>"|?*'
            for char in invalid_chars:
                if char in path:
                    return False, f"Path contains invalid character: {char}"
        
        # Check if path is too long
        if len(path) > 260 and os.name == 'nt':
            return False, "Path is too long (max 260 characters on Windows)"
        
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_url_for_platform(url: str, expected_platform: str = None) -> Tuple[bool, str]:
    """
    Validate URL for a specific platform.
    
    Returns:
        Tuple of (is_valid, error_message_or_platform)
    """
    if not url:
        return False, "URL is empty"
    
    if not is_valid_url(url):
        return False, "Invalid URL format"
    
    domain = get_domain(url)
    if not domain:
        return False, "Could not extract domain"
    
    # Platform detection
    platform_map = {
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'instagram.com': 'Instagram',
        'twitter.com': 'Twitter',
        'x.com': 'Twitter',
        'facebook.com': 'Facebook',
        'fb.watch': 'Facebook',
        'reddit.com': 'Reddit',
        'v.redd.it': 'Reddit',
        'tiktok.com': 'TikTok',
        'vm.tiktok.com': 'TikTok',
        'vimeo.com': 'Vimeo',
        'twitch.tv': 'Twitch',
        'clips.twitch.tv': 'Twitch',
        'soundcloud.com': 'SoundCloud',
        'dailymotion.com': 'Dailymotion',
    }
    
    detected_platform = None
    for domain_pattern, platform in platform_map.items():
        if domain_pattern in domain:
            detected_platform = platform
            break
    
    if expected_platform and detected_platform != expected_platform:
        return False, f"Expected {expected_platform} URL, got {detected_platform or 'unknown'}"
    
    return True, detected_platform or "Unknown"


# ============================================================================
# JSON UTILITIES
# ============================================================================

def load_json(filepath: str, default: Any = None) -> Any:
    """Load JSON from file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filepath: str, data: Any, indent: int = 4) -> bool:
    """Save data to JSON file"""
    try:
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
        return True
    except Exception:
        return False


# ============================================================================
# RETRY UTILITIES
# ============================================================================

def retry_on_exception(func, max_retries: int = 3, 
                       delay: float = 1.0,
                       backoff: float = 2.0,
                       exceptions: tuple = (Exception,)):
    """
    Retry a function on exception.
    
    Args:
        func: Function to call
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
    
    Returns:
        Result of the function
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                time.sleep(current_delay)
                current_delay *= backoff
    
    raise last_exception


# ============================================================================
# MAIN (Testing)
# ============================================================================

if __name__ == "__main__":
    print("Utils Module - Testing")
    print("=" * 50)
    
    # Test sanitize_filename
    print("\nTesting sanitize_filename:")
    test_names = [
        "Hello: World?",
        "Video | Test <file>",
        "🎵 Music Video 🎶",
        "a" * 300,
        "",
        "CON",
    ]
    for name in test_names:
        clean = sanitize_filename(name)
        print(f"  '{name[:30]}...' -> '{clean}'")
    
    # Test format_size
    print("\nTesting format_size:")
    sizes = [0, 512, 1024, 1024*1024, 1024*1024*1024, 1024*1024*1024*1024]
    for size in sizes:
        print(f"  {size} bytes -> {format_size(size)}")
    
    # Test format_duration
    print("\nTesting format_duration:")
    durations = [0, 45, 90, 3600, 3661, 86400]
    for dur in durations:
        print(f"  {dur}s -> {format_duration(dur)} | compact: {format_duration(dur, compact=True)}")
    
    # Test URL utilities
    print("\nTesting URL utilities:")
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "instagram.com/p/ABC123",
    ]
    for url in urls:
        normalized = normalize_url(url)
        vid_id = extract_video_id(normalized)
        print(f"  {url[:40]}... -> ID: {vid_id}")
    
    print("\n" + "=" * 50)
    print("Tests complete!")