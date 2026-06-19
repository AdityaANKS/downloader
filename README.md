# Media Downloader

A command-line media downloader for personal use. Downloads videos and audio from YouTube, Instagram, Twitter/X, TikTok, Reddit, Facebook, Vimeo, Twitch, SoundCloud, and more.

Built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- Download video (up to 8K) or audio only (up to 320kbps / FLAC)
- Playlist downloads
- Batch download from multiple URLs
- Download thumbnails and subtitles separately
- Quality picker — shows what's actually available before downloading
- Clipboard auto-paste — copies URL from clipboard automatically
- Organizes files by platform (YouTube/, Instagram/, etc.)
- Download history and search (SQLite)
- Resume failed downloads
- Background pre-downloading
- Optional stealth/bot module for anti-detection

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) (must be on PATH)

## Setup

```bash
git clone https://github.com/AdityaANKS/downloader.git
cd downloader
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Usage

```bash
python downloader.py
```

This opens an interactive menu. Pick what you want to do — download video, audio, playlist, etc.

### Quick download (no menu)

```bash
python fast_download.py
```

Asks for a URL and quality, downloads immediately.

## Where do files go?

By default, everything saves to:

| OS | Path |
|----|------|
| Windows | `C:\Users\<you>\Downloads\downloader\` |
| macOS | `~/Downloads/downloader/` |
| Linux | `~/Downloads/downloader/` |

Files are organized into subfolders: `videos/`, `audios/`, `thumbnails/`, `subtitles/`.

### Change the save location

Create a file called `.downloader_settings.json` in your home directory:

```json
{
    "base_dir": "D:\\MyMedia\\downloader"
}
```

Or just change it through the settings menu in the app.

## Project Structure

```
downloader.py      — main CLI app
config.py          — settings and paths
database.py        — download history (SQLite)
quality_manager.py — video/audio quality profiles
platforms.py       — platform detection (YouTube, TikTok, etc.)
utils.py           — helpers (filename cleanup, progress bars, etc.)
bot.py             — optional anti-detection module
fast_download.py   — quick single-video downloader
fix_paths.py       — directory setup script
```

## License

Personal use.
