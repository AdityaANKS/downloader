"""
Quality Manager Module for Personal Media Downloader
Handles all quality settings for video, audio, thumbnails, and subtitles.

FIXED: Proper format selection for 4K, 8K, and all resolutions.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Union
from enum import Enum, auto
import json
import os

# Try importing Config for default paths
try:
    from config import Config as _Cfg
    _DEFAULT_QUALITY_PATH = os.path.join(_Cfg.BASE_DIR, "quality_settings.json")
except ImportError:
    _DEFAULT_QUALITY_PATH = os.path.join(
        os.path.expanduser("~"), "Downloads", "downloader", "quality_settings.json"
    )


# ============================================================================
# VIDEO RESOLUTION - With proper height values
# ============================================================================

class VideoResolution(Enum):
    """Video resolution options with exact height values"""
    RES_8K = (7680, 4320, "8K", "4320p", 4320)
    RES_4K = (3840, 2160, "4K", "2160p", 2160)
    RES_2K = (2560, 1440, "2K/QHD", "1440p", 1440)
    RES_1080P = (1920, 1080, "Full HD", "1080p", 1080)
    RES_720P = (1280, 720, "HD", "720p", 720)
    RES_480P = (854, 480, "SD", "480p", 480)
    RES_360P = (640, 360, "Low", "360p", 360)
    RES_240P = (426, 240, "Very Low", "240p", 240)
    RES_144P = (256, 144, "Lowest", "144p", 144)
    
    def __init__(self, width: int, height: int, name: str, label: str, h: int):
        self._width = width
        self._height = height
        self.display_name = name
        self.label = label
        self.height_value = h
    
    @property
    def width(self) -> int:
        return self._width
    
    @property
    def height(self) -> int:
        return self._height
    
    @property
    def pixels(self) -> int:
        return self._width * self._height
    
    def __str__(self) -> str:
        return self.label


class VideoFPS(Enum):
    """Video frame rate options"""
    FPS_60 = (60, "60fps", True)
    FPS_50 = (50, "50fps", True)
    FPS_30 = (30, "30fps", False)
    FPS_25 = (25, "25fps", False)
    FPS_24 = (24, "24fps", False)
    FPS_ANY = (0, "Any", False)
    
    def __init__(self, fps: int, label: str, is_high: bool):
        self.fps = fps
        self.label = label
        self.is_high_fps = is_high
    
    def __str__(self) -> str:
        return self.label


class VideoCodec(Enum):
    """Video codec options"""
    H264 = ("avc", "h264", "H.264/AVC", True, 1)
    H265 = ("hevc", "h265", "H.265/HEVC", True, 2)
    VP9 = ("vp9", "vp9", "VP9", True, 3)
    VP8 = ("vp8", "vp8", "VP8", False, 0)
    AV1 = ("av01", "av1", "AV1", True, 4)
    
    def __init__(self, yt_id: str, ffmpeg_id: str, display_name: str, is_modern: bool, quality_rank: int):
        self.yt_id = yt_id
        self.ffmpeg_id = ffmpeg_id
        self.display_name = display_name
        self.is_modern = is_modern
        self.quality_rank = quality_rank


class VideoContainer(Enum):
    """Video container formats"""
    MP4 = ("mp4", "MPEG-4", True)
    MKV = ("mkv", "Matroska", True)
    WEBM = ("webm", "WebM", True)
    MOV = ("mov", "QuickTime", False)
    AVI = ("avi", "AVI", False)
    
    def __init__(self, ext: str, name: str, recommended: bool):
        self.extension = ext
        self.display_name = name
        self.is_recommended = recommended


class AudioCodec(Enum):
    """Audio codec options"""
    MP3 = ("mp3", "MP3", True, 320)
    AAC = ("aac", "AAC", True, 256)
    M4A = ("m4a", "M4A", True, 256)
    OPUS = ("opus", "Opus", True, 256)
    VORBIS = ("vorbis", "Vorbis", True, 256)
    FLAC = ("flac", "FLAC", False, None)
    WAV = ("wav", "WAV", False, None)
    
    def __init__(self, codec_id: str, name: str, is_lossy: bool, max_bitrate: Optional[int]):
        self.codec_id = codec_id
        self.display_name = name
        self.is_lossy = is_lossy
        self.max_bitrate = max_bitrate


class AudioBitrate(Enum):
    """Audio bitrate options"""
    KBPS_320 = (320, "320 kbps", "Maximum")
    KBPS_256 = (256, "256 kbps", "High")
    KBPS_192 = (192, "192 kbps", "Standard")
    KBPS_160 = (160, "160 kbps", "Medium")
    KBPS_128 = (128, "128 kbps", "Compressed")
    KBPS_96 = (96, "96 kbps", "Low")
    KBPS_64 = (64, "64 kbps", "Minimum")
    LOSSLESS = (0, "Lossless", "Original")
    
    def __init__(self, kbps: int, label: str, desc: str):
        self.kbps = kbps
        self.label = label
        self.description = desc


class ThumbnailFormat(Enum):
    """Thumbnail formats"""
    JPG = ("jpg", "JPEG", 85)
    PNG = ("png", "PNG", None)
    WEBP = ("webp", "WebP", 85)
    
    def __init__(self, ext: str, name: str, quality: Optional[int]):
        self.extension = ext
        self.display_name = name
        self.default_quality = quality


class ThumbnailResolution(Enum):
    """Thumbnail resolutions"""
    MAXRES = (1920, 1080, "Maximum")
    HIGH = (1280, 720, "High")
    MEDIUM = (640, 480, "Medium")
    STANDARD = (480, 360, "Standard")
    LOW = (320, 180, "Low")
    
    def __init__(self, w: int, h: int, name: str):
        self._width = w
        self._height = h
        self.display_name = name
    
    @property
    def width(self):
        return self._width
    
    @property
    def height(self):
        return self._height


class SubtitleFormat(Enum):
    """Subtitle formats"""
    SRT = ("srt", "SubRip")
    VTT = ("vtt", "WebVTT")
    ASS = ("ass", "Advanced SSA")
    
    def __init__(self, ext: str, name: str):
        self.extension = ext
        self.display_name = name


class QualityPreset(Enum):
    """Quality presets"""
    MAXIMUM = "maximum"
    HIGH = "high"
    STANDARD = "standard"
    MEDIUM = "medium"
    LOW = "low"
    MINIMUM = "minimum"
    CUSTOM = "custom"


# ============================================================================
# QUALITY PROFILES
# ============================================================================

@dataclass
class VideoQualityProfile:
    """Video quality profile"""
    resolution: VideoResolution = VideoResolution.RES_1080P
    min_resolution: VideoResolution = None  # Minimum acceptable resolution
    fps: VideoFPS = VideoFPS.FPS_60
    codec: VideoCodec = VideoCodec.H264
    container: VideoContainer = VideoContainer.MP4
    prefer_hdr: bool = False
    prefer_high_fps: bool = True
    allow_fallback: bool = True  # Allow lower quality if requested not available
    
    def to_dict(self) -> Dict:
        return {
            "resolution": self.resolution.label,
            "fps": self.fps.fps,
            "codec": self.codec.yt_id,
            "container": self.container.extension,
            "prefer_hdr": self.prefer_hdr,
            "prefer_high_fps": self.prefer_high_fps,
            "allow_fallback": self.allow_fallback,
        }


@dataclass
class AudioQualityProfile:
    """Audio quality profile"""
    codec: AudioCodec = AudioCodec.MP3
    bitrate: AudioBitrate = AudioBitrate.KBPS_192
    channels: int = 2
    
    def to_dict(self) -> Dict:
        return {
            "codec": self.codec.codec_id,
            "bitrate": self.bitrate.kbps,
            "channels": self.channels,
        }


@dataclass
class ThumbnailProfile:
    """Thumbnail quality profile"""
    format: ThumbnailFormat = ThumbnailFormat.JPG
    resolution: ThumbnailResolution = ThumbnailResolution.HIGH
    quality: int = 85
    embed: bool = True
    save_separately: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "format": self.format.extension,
            "quality": self.quality,
            "embed": self.embed,
            "save_separately": self.save_separately,
        }


@dataclass
class SubtitleProfile:
    """Subtitle quality profile"""
    format: SubtitleFormat = SubtitleFormat.SRT
    languages: List[str] = field(default_factory=lambda: ["en"])
    auto_generated: bool = True
    embed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "format": self.format.extension,
            "languages": self.languages,
            "auto_generated": self.auto_generated,
            "embed": self.embed,
        }


# ============================================================================
# FORMAT STRING BUILDER - THE KEY FIX
# ============================================================================

class FormatStringBuilder:
    """
    Builds yt-dlp format strings that ACTUALLY download the requested quality.
    
    The key insight is that yt-dlp format selection works like this:
    - bestvideo[height<=X] means "best video with height at most X"
    - But this can pick 1080p when 4K is requested if 4K uses a different codec
    
    Solution: Use explicit height requirements and proper fallback chains.
    """
    
    @staticmethod
    def build_video_format(profile: VideoQualityProfile) -> str:
        """
        Build format string that prioritizes exact resolution.
        
        For 4K (2160p), we want:
        1. First try to get exactly 2160p
        2. Then try to get anything >= 2160p
        3. Only then fall back to lower resolutions
        """
        
        height = profile.resolution.height_value
        fps_filter = ""
        
        # FPS filter
        if profile.prefer_high_fps and profile.fps.fps >= 50:
            fps_filter = "[fps>=48]"  # 48 to catch 50fps too
        elif profile.fps.fps > 0 and profile.fps.fps < 50:
            fps_filter = f"[fps<={profile.fps.fps}]"
        
        # HDR filter (optional)
        hdr_filter = "[hdr]" if profile.prefer_hdr else ""
        
        # Build format string with PRIORITY on exact resolution
        format_parts = []
        
        # ===== PRIORITY 1: Exact resolution with preferred settings =====
        # Try exact height first (most important!)
        format_parts.append(f"bestvideo[height={height}]{fps_filter}{hdr_filter}+bestaudio/bestvideo[height={height}]{fps_filter}+bestaudio/bestvideo[height={height}]+bestaudio")
        
        # ===== PRIORITY 2: Resolution >= requested (might get higher) =====
        format_parts.append(f"bestvideo[height>={height}]{fps_filter}+bestaudio/bestvideo[height>={height}]+bestaudio")
        
        # ===== PRIORITY 3: Fallback to best available if allowed =====
        if profile.allow_fallback:
            # Best available at or below requested
            format_parts.append(f"bestvideo[height<={height}]+bestaudio")
            # Absolute best
            format_parts.append("bestvideo+bestaudio/best")
        
        return "/".join(format_parts)
    
    @staticmethod
    def build_video_format_strict(resolution: VideoResolution, 
                                   prefer_60fps: bool = True,
                                   prefer_hdr: bool = False) -> str:
        """
        Build a STRICT format string for a specific resolution.
        This is more aggressive about getting the exact quality.
        """
        
        h = resolution.height_value
        
        # For high resolutions (4K+), we need to be very specific
        if h >= 2160:
            # 4K and above - very specific format selection
            formats = [
                # Exact height, any codec, prefer high fps
                f"bestvideo[height={h}][fps>=48]+bestaudio",
                f"bestvideo[height={h}][fps>=24]+bestaudio",
                f"bestvideo[height={h}]+bestaudio",
                
                # Allow slightly higher (e.g., some 4K is 2176p)
                f"bestvideo[height>={h}][height<={h+100}]+bestaudio",
                
                # VP9/AV1 often have higher quality streams
                f"bestvideo[height>={h}][vcodec^=vp9]+bestaudio",
                f"bestvideo[height>={h}][vcodec^=vp09]+bestaudio",
                f"bestvideo[height>={h}][vcodec^=av01]+bestaudio",
                
                # General high quality
                f"bestvideo[height>={h}]+bestaudio",
                
                # Fallback
                "bestvideo+bestaudio/best",
            ]
        elif h >= 1080:
            # 1080p-1440p
            formats = [
                f"bestvideo[height={h}][fps>=48]+bestaudio",
                f"bestvideo[height={h}]+bestaudio",
                f"bestvideo[height>={h}][height<={h+400}]+bestaudio",
                f"bestvideo[height>={h}]+bestaudio",
                f"bestvideo[height<={h}]+bestaudio",
                "bestvideo+bestaudio/best",
            ]
        else:
            # Lower resolutions
            formats = [
                f"bestvideo[height<={h}]+bestaudio",
                f"bestvideo[height<={h+100}]+bestaudio",
                "bestvideo+bestaudio/best",
            ]
        
        return "/".join(formats)
    
    @staticmethod
    def build_audio_format(profile: AudioQualityProfile) -> str:
        """Build audio-only format string"""
        
        if profile.bitrate == AudioBitrate.LOSSLESS:
            # Prefer lossless formats
            return "bestaudio[acodec=flac]/bestaudio[acodec=alac]/bestaudio/best"
        
        # For lossy, just get best audio
        return "bestaudio/best"
    
    @staticmethod
    def build_format_for_resolution(resolution_label: str, 
                                     prefer_60fps: bool = True) -> str:
        """
        Build format string from resolution label like "4k", "1080p", etc.
        This is a convenience method.
        """
        
        # Map labels to VideoResolution
        label_map = {
            "8k": VideoResolution.RES_8K,
            "4320p": VideoResolution.RES_8K,
            "4k": VideoResolution.RES_4K,
            "2160p": VideoResolution.RES_4K,
            "2k": VideoResolution.RES_2K,
            "1440p": VideoResolution.RES_2K,
            "1080p": VideoResolution.RES_1080P,
            "720p": VideoResolution.RES_720P,
            "480p": VideoResolution.RES_480P,
            "360p": VideoResolution.RES_360P,
            "240p": VideoResolution.RES_240P,
            "144p": VideoResolution.RES_144P,
            "best": VideoResolution.RES_8K,  # Best = highest available
        }
        
        resolution = label_map.get(resolution_label.lower(), VideoResolution.RES_1080P)
        return FormatStringBuilder.build_video_format_strict(resolution, prefer_60fps)


# ============================================================================
# QUALITY MANAGER
# ============================================================================

class QualityManager:
    """
    Central quality settings manager.
    Now with FIXED format string generation that actually downloads requested quality.
    """
    
    # Preset definitions
    PRESETS = {
        QualityPreset.MAXIMUM: {
            "video": VideoQualityProfile(
                resolution=VideoResolution.RES_8K,
                fps=VideoFPS.FPS_60,
                codec=VideoCodec.AV1,
                prefer_hdr=True,
                prefer_high_fps=True,
            ),
            "audio": AudioQualityProfile(
                codec=AudioCodec.FLAC,
                bitrate=AudioBitrate.LOSSLESS,
            ),
        },
        QualityPreset.HIGH: {
            "video": VideoQualityProfile(
                resolution=VideoResolution.RES_4K,
                fps=VideoFPS.FPS_60,
                codec=VideoCodec.H265,
                prefer_high_fps=True,
            ),
            "audio": AudioQualityProfile(
                codec=AudioCodec.MP3,
                bitrate=AudioBitrate.KBPS_320,
            ),
        },
        QualityPreset.STANDARD: {
            "video": VideoQualityProfile(
                resolution=VideoResolution.RES_1080P,
                fps=VideoFPS.FPS_60,
                codec=VideoCodec.H264,
            ),
            "audio": AudioQualityProfile(
                codec=AudioCodec.MP3,
                bitrate=AudioBitrate.KBPS_192,
            ),
        },
        QualityPreset.MEDIUM: {
            "video": VideoQualityProfile(
                resolution=VideoResolution.RES_720P,
                fps=VideoFPS.FPS_30,
            ),
            "audio": AudioQualityProfile(
                codec=AudioCodec.MP3,
                bitrate=AudioBitrate.KBPS_160,
            ),
        },
        QualityPreset.LOW: {
            "video": VideoQualityProfile(
                resolution=VideoResolution.RES_480P,
                fps=VideoFPS.FPS_30,
            ),
            "audio": AudioQualityProfile(
                codec=AudioCodec.MP3,
                bitrate=AudioBitrate.KBPS_128,
            ),
        },
        QualityPreset.MINIMUM: {
            "video": VideoQualityProfile(
                resolution=VideoResolution.RES_360P,
                fps=VideoFPS.FPS_30,
            ),
            "audio": AudioQualityProfile(
                codec=AudioCodec.MP3,
                bitrate=AudioBitrate.KBPS_96,
            ),
        },
    }
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or _DEFAULT_QUALITY_PATH
        
        # Current profiles
        self.video = VideoQualityProfile()
        self.audio = AudioQualityProfile()
        self.thumbnail = ThumbnailProfile()
        self.subtitle = SubtitleProfile()
        self.preset = QualityPreset.STANDARD
        
        # Load saved settings
        self.load_settings()
    
    def apply_preset(self, preset: QualityPreset):
        """Apply a quality preset"""
        if preset not in self.PRESETS:
            return
        
        config = self.PRESETS[preset]
        self.video = config.get("video", VideoQualityProfile())
        self.audio = config.get("audio", AudioQualityProfile())
        self.preset = preset
    
    def get_video_format_string(self, resolution: VideoResolution = None) -> str:
        """
        Get yt-dlp format string for video.
        This is the FIXED version that actually downloads the correct resolution.
        """
        res = resolution or self.video.resolution
        return FormatStringBuilder.build_video_format_strict(
            res,
            prefer_60fps=self.video.prefer_high_fps
        )
    
    def get_format_for_quality(self, quality: str) -> str:
        """
        Get format string for a quality label like "4k", "1080p", etc.
        
        Args:
            quality: Quality string like "4k", "1080p", "720p", "best"
        
        Returns:
            yt-dlp format string
        """
        return FormatStringBuilder.build_format_for_resolution(
            quality, 
            self.video.prefer_high_fps
        )
    
    def get_audio_format_string(self) -> str:
        """Get yt-dlp format string for audio only"""
        return FormatStringBuilder.build_audio_format(self.audio)
    
    def get_ytdlp_options(self,
                          video: bool = True,
                          audio_only: bool = False,
                          quality: str = None,
                          subtitles: bool = False,
                          thumbnail: bool = True) -> Dict:
        """
        Get complete yt-dlp options dictionary.
        
        Args:
            video: Download video
            audio_only: Audio only mode
            quality: Quality override (e.g., "4k", "1080p")
            subtitles: Include subtitles
            thumbnail: Include thumbnail
        
        Returns:
            yt-dlp options dictionary
        """
        
        opts = {}
        
        if audio_only:
            opts['format'] = self.get_audio_format_string()
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio.codec.codec_id,
                'preferredquality': str(self.audio.bitrate.kbps) if self.audio.bitrate.kbps > 0 else 'best',
            }]
        elif video:
            # Use quality override if provided, otherwise use profile
            if quality:
                opts['format'] = self.get_format_for_quality(quality)
            else:
                opts['format'] = self.get_video_format_string()
            
            opts['merge_output_format'] = self.video.container.extension
        
        # Thumbnail
        if thumbnail:
            if self.thumbnail.embed or self.thumbnail.save_separately:
                opts['writethumbnail'] = True
            if self.thumbnail.embed:
                opts.setdefault('postprocessors', []).append({'key': 'EmbedThumbnail'})
        
        # Subtitles
        if subtitles:
            opts['writesubtitles'] = True
            opts['writeautomaticsub'] = self.subtitle.auto_generated
            opts['subtitleslangs'] = self.subtitle.languages
            opts['subtitlesformat'] = self.subtitle.format.extension
            if self.subtitle.embed:
                opts.setdefault('postprocessors', []).append({'key': 'FFmpegEmbedSubtitle'})
        
        # Metadata
        opts.setdefault('postprocessors', []).append({
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        })
        
        return opts
    
    def set_resolution(self, resolution: VideoResolution):
        """Set video resolution"""
        self.video.resolution = resolution
        self.preset = QualityPreset.CUSTOM
    
    def set_audio_codec(self, codec: AudioCodec):
        """Set audio codec"""
        self.audio.codec = codec
        self.preset = QualityPreset.CUSTOM
    
    def set_audio_bitrate(self, bitrate: AudioBitrate):
        """Set audio bitrate"""
        self.audio.bitrate = bitrate
        self.preset = QualityPreset.CUSTOM
    
    def save_settings(self) -> bool:
        """Save settings to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            data = {
                "preset": self.preset.value,
                "video": self.video.to_dict(),
                "audio": self.audio.to_dict(),
                "thumbnail": self.thumbnail.to_dict(),
                "subtitle": self.subtitle.to_dict(),
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving: {e}")
            return False
    
    def load_settings(self) -> bool:
        """Load settings from file"""
        if not os.path.exists(self.config_path):
            return False
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load preset
            preset_name = data.get("preset", "standard")
            try:
                self.preset = QualityPreset(preset_name)
                if self.preset in self.PRESETS:
                    self.apply_preset(self.preset)
            except ValueError:
                pass
            
            # Override with saved values
            if data.get("video"):
                v = data["video"]
                if v.get("prefer_hdr") is not None:
                    self.video.prefer_hdr = v["prefer_hdr"]
                if v.get("prefer_high_fps") is not None:
                    self.video.prefer_high_fps = v["prefer_high_fps"]
            
            if data.get("audio"):
                a = data["audio"]
                codec_map = {c.codec_id: c for c in AudioCodec}
                bitrate_map = {b.kbps: b for b in AudioBitrate}
                if a.get("codec") in codec_map:
                    self.audio.codec = codec_map[a["codec"]]
                if a.get("bitrate") in bitrate_map:
                    self.audio.bitrate = bitrate_map[a["bitrate"]]
            
            if data.get("subtitle"):
                s = data["subtitle"]
                if s.get("languages"):
                    self.subtitle.languages = s["languages"]
                if s.get("auto_generated") is not None:
                    self.subtitle.auto_generated = s["auto_generated"]
            
            return True
        except Exception as e:
            print(f"Error loading: {e}")
            return False
    
    def print_settings(self):
        """Print current settings"""
        print(f"\n  {'═' * 55}")
        print("  QUALITY SETTINGS")
        print(f"  {'═' * 55}")
        print(f"  Preset: {self.preset.value.upper()}")
        print(f"  {'─' * 55}")
        print("  VIDEO:")
        print(f"    Resolution:  {self.video.resolution.label} ({self.video.resolution.display_name})")
        print(f"    Actual Size: {self.video.resolution.width}x{self.video.resolution.height}")
        print(f"    FPS:         {self.video.fps.label}")
        print(f"    Codec:       {self.video.codec.display_name}")
        print(f"    Container:   {self.video.container.extension.upper()}")
        print(f"    Prefer 60fps: {'Yes' if self.video.prefer_high_fps else 'No'}")
        print(f"    Prefer HDR:   {'Yes' if self.video.prefer_hdr else 'No'}")
        print(f"  {'─' * 55}")
        print("  AUDIO:")
        print(f"    Codec:   {self.audio.codec.display_name}")
        print(f"    Bitrate: {self.audio.bitrate.label}")
        print(f"  {'─' * 55}")
        print("  SUBTITLES:")
        print(f"    Languages: {', '.join(self.subtitle.languages)}")
        print(f"    Auto-gen:  {'Yes' if self.subtitle.auto_generated else 'No'}")
        print(f"  {'═' * 55}")
        
        # Show format string being used
        print(f"\n  Format String (Video):")
        print(f"  {self.get_video_format_string()[:100]}...")


# ============================================================================
# QUALITY SELECTOR (Interactive CLI)
# ============================================================================

class QualitySelector:
    """Interactive quality selector"""
    
    def __init__(self, manager: QualityManager = None):
        self.manager = manager or QualityManager()
    
    def select_video_quality(self) -> VideoQualityProfile:
        """Select video quality interactively"""
        
        print("\n  VIDEO QUALITY")
        print("  " + "─" * 45)
        
        resolutions = [
            ("1", VideoResolution.RES_8K, "8K (4320p) - 7680x4320"),
            ("2", VideoResolution.RES_4K, "4K (2160p) - 3840x2160"),
            ("3", VideoResolution.RES_2K, "2K (1440p) - 2560x1440"),
            ("4", VideoResolution.RES_1080P, "1080p Full HD - 1920x1080 [Recommended]"),
            ("5", VideoResolution.RES_720P, "720p HD - 1280x720"),
            ("6", VideoResolution.RES_480P, "480p SD - 854x480"),
            ("7", VideoResolution.RES_360P, "360p - 640x360"),
            ("8", VideoResolution.RES_240P, "240p - 426x240"),
        ]
        
        for num, res, desc in resolutions:
            print(f"    {num}. {desc}")
        
        choice = input("\n  Select [4]: ").strip() or "4"
        res_map = {num: res for num, res, _ in resolutions}
        self.manager.video.resolution = res_map.get(choice, VideoResolution.RES_1080P)
        
        # FPS preference
        print("\n  Frame Rate Preference:")
        print("    1. Prefer 60fps (smoother)")
        print("    2. Prefer 30fps (smaller files)")
        
        fps_choice = input("  Select [1]: ").strip() or "1"
        self.manager.video.prefer_high_fps = fps_choice == "1"
        self.manager.video.fps = VideoFPS.FPS_60 if fps_choice == "1" else VideoFPS.FPS_30
        
        self.manager.preset = QualityPreset.CUSTOM
        
        print(f"\n  ✓ Set to: {self.manager.video.resolution.label} @ {self.manager.video.fps.label}")
        
        return self.manager.video
    
    def select_audio_quality(self) -> AudioQualityProfile:
        """Select audio quality interactively"""
        
        print("\n  AUDIO QUALITY")
        print("  " + "─" * 45)
        
        formats = [
            ("1", AudioCodec.MP3, "MP3 - Universal [Recommended]"),
            ("2", AudioCodec.M4A, "M4A - Apple/High quality"),
            ("3", AudioCodec.FLAC, "FLAC - Lossless"),
            ("4", AudioCodec.WAV, "WAV - Uncompressed"),
            ("5", AudioCodec.OPUS, "OPUS - Best compression"),
        ]
        
        for num, codec, desc in formats:
            print(f"    {num}. {desc}")
        
        choice = input("\n  Select [1]: ").strip() or "1"
        codec_map = {num: codec for num, codec, _ in formats}
        self.manager.audio.codec = codec_map.get(choice, AudioCodec.MP3)
        
        # Bitrate for lossy
        if self.manager.audio.codec.is_lossy:
            print("\n  Bitrate:")
            print("    1. 320 kbps - Maximum")
            print("    2. 256 kbps - High")
            print("    3. 192 kbps - Standard [Recommended]")
            print("    4. 128 kbps - Compressed")
            
            br_choice = input("  Select [3]: ").strip() or "3"
            br_map = {
                "1": AudioBitrate.KBPS_320,
                "2": AudioBitrate.KBPS_256,
                "3": AudioBitrate.KBPS_192,
                "4": AudioBitrate.KBPS_128,
            }
            self.manager.audio.bitrate = br_map.get(br_choice, AudioBitrate.KBPS_192)
        else:
            self.manager.audio.bitrate = AudioBitrate.LOSSLESS
        
        self.manager.preset = QualityPreset.CUSTOM
        
        return self.manager.audio
    
    def select_preset(self) -> QualityPreset:
        """Select a preset interactively"""
        
        print("\n  QUALITY PRESETS")
        print("  " + "─" * 50)
        
        presets = [
            ("1", QualityPreset.MAXIMUM, "Maximum - 8K, Lossless audio"),
            ("2", QualityPreset.HIGH, "High - 4K, 320kbps audio"),
            ("3", QualityPreset.STANDARD, "Standard - 1080p, 192kbps [Recommended]"),
            ("4", QualityPreset.MEDIUM, "Medium - 720p, 160kbps"),
            ("5", QualityPreset.LOW, "Low - 480p, 128kbps"),
            ("6", QualityPreset.MINIMUM, "Minimum - 360p, 96kbps"),
        ]
        
        for num, preset, desc in presets:
            marker = " <-- Current" if preset == self.manager.preset else ""
            print(f"    {num}. {desc}{marker}")
        
        print("\n    7. Custom (set manually)")
        
        choice = input("\n  Select [3]: ").strip() or "3"
        
        if choice == "7":
            self.select_video_quality()
            self.select_audio_quality()
            return QualityPreset.CUSTOM
        
        preset_map = {num: preset for num, preset, _ in presets}
        selected = preset_map.get(choice, QualityPreset.STANDARD)
        
        self.manager.apply_preset(selected)
        
        print(f"\n  ✓ Applied: {selected.value.upper()}")
        self.manager.print_settings()
        
        return selected


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_format_string(quality: str, prefer_60fps: bool = True) -> str:
    """
    Quick helper to get format string for a quality.
    
    Args:
        quality: "8k", "4k", "1440p", "1080p", "720p", "480p", "360p", "best"
        prefer_60fps: Whether to prefer 60fps
    
    Returns:
        yt-dlp format string
    
    Example:
        format_str = get_format_string("4k")
    """
    return FormatStringBuilder.build_format_for_resolution(quality, prefer_60fps)


def get_resolution_height(quality: str) -> int:
    """Get height value for a quality string"""
    height_map = {
        "8k": 4320,
        "4320p": 4320,
        "4k": 2160,
        "2160p": 2160,
        "2k": 1440,
        "1440p": 1440,
        "1080p": 1080,
        "720p": 720,
        "480p": 480,
        "360p": 360,
        "240p": 240,
        "144p": 144,
    }
    return height_map.get(quality.lower(), 1080)


# ============================================================================
# MAIN (Testing)
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  QUALITY MANAGER - TEST")
    print("=" * 60)
    
    manager = QualityManager()
    
    # Test format strings for each resolution
    print("\n  FORMAT STRINGS BY RESOLUTION:")
    print("  " + "-" * 55)
    
    test_qualities = ["8k", "4k", "1440p", "1080p", "720p", "480p"]
    for q in test_qualities:
        fmt = get_format_string(q)
        print(f"\n  {q.upper()}:")
        print(f"    {fmt[:80]}...")
    
    # Show current settings
    print("\n")
    manager.print_settings()
    
    # Interactive test
    print("\n  Test interactive selection? (y/n)")
    if input("  > ").strip().lower() == 'y':
        selector = QualitySelector(manager)
        selector.select_preset()
        manager.save_settings()
    
    print("\n" + "=" * 60)
    print("  DONE")
    print("=" * 60 + "\n")