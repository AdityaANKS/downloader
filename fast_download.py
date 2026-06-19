"""
FAST YouTube Downloader - Single attempt, no waiting
"""
import yt_dlp
import os
import sys

def download(url, quality="1080p", audio_only=False):
    """Fast download - single attempt"""
    
    out_dir = os.path.join(os.path.expanduser("~"), "Downloads", "downloader", "videos")
    os.makedirs(out_dir, exist_ok=True)
    
    # Height mapping
    h_map = {'8k': 4320, '4k': 2160, '1440p': 1440, '1080p': 1080, '720p': 720, '480p': 480}
    h = h_map.get(quality.lower(), 1080)
    
    opts = {
        'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
        'quiet': False,
        'socket_timeout': 10,
        'retries': 2,
        'geo_bypass': True,
        'windowsfilenames': True,
        # Use iOS client - usually fastest and least blocked
        'extractor_args': {'youtube': {'player_client': ['ios']}},
    }
    
    if audio_only:
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        opts['format'] = f'bestvideo[height<={h}]+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
    
    print(f"Downloading: {url}")
    print(f"Quality: {quality}")
    print()
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        print("\nDone!")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTry: pip install -U yt-dlp")

if __name__ == "__main__":
    url = input("URL: ").strip()
    if not url:
        print("No URL")
        sys.exit(1)
    
    mode = input("Audio only? (y/n) [n]: ").strip().lower()
    audio = mode == 'y'
    
    if not audio:
        q = input("Quality (1080p/720p/480p) [1080p]: ").strip() or "1080p"
    else:
        q = "best"
    
    download(url, q, audio)