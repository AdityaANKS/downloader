"""Quick script to verify and create correct directories"""

import os
import sys


def _get_downloads_dir():
    """Get the default OS Downloads directory."""
    home = os.path.expanduser("~")
    
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            CSIDL_PROFILE = 0x0028
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PROFILE, None, 0, buf)
            profile = buf.value or home
            downloads = os.path.join(profile, "Downloads")
        except Exception:
            downloads = os.path.join(home, "Downloads")
    elif sys.platform == "darwin":
        downloads = os.path.join(home, "Downloads")
    else:
        xdg = os.environ.get("XDG_DOWNLOAD_DIR")
        downloads = xdg if xdg else os.path.join(home, "Downloads")
    
    return downloads


BASE = os.path.join(_get_downloads_dir(), "downloader")

PATHS = {
    "Base": BASE,
    "Videos": os.path.join(BASE, "videos"),
    "Audios": os.path.join(BASE, "audios"),
    "Thumbnails": os.path.join(BASE, "thumbnails"),
    "Subtitles": os.path.join(BASE, "subtitles"),
    "Text": os.path.join(BASE, "text"),
    "Temp": os.path.join(BASE, "temp"),
    "Cookies": os.path.join(BASE, "cookies"),
    "Images": os.path.join(BASE, "images"),
}

print("=" * 50)
print("  DIRECTORY SETUP")
print("=" * 50)

for name, path in PATHS.items():
    try:
        os.makedirs(path, exist_ok=True)
        exists = os.path.exists(path)
        writable = os.access(path, os.W_OK)
        
        if exists and writable:
            print(f"  [OK] {name}: {path}")
        else:
            print(f"  [FAIL] {name}: {path} (NOT WRITABLE)")
    except Exception as e:
        print(f"  [FAIL] {name}: Error - {e}")

print("=" * 50)
print("  Done! All directories should now exist.")
print("=" * 50)