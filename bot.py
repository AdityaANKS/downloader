"""
Bot Module - Anti-detection and Browser Automation
Optional module providing stealth capabilities for the downloader
"""

import asyncio
import json
import os
import random
import re
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Union
from urllib.parse import urlparse
import hashlib
import base64

# Configure logging
logger = logging.getLogger(__name__)

# Try to import optional dependencies
PLAYWRIGHT_AVAILABLE = False
SELENIUM_AVAILABLE = False
CURL_CFFI_AVAILABLE = False
UNDETECTED_CHROME_AVAILABLE = False

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    pass

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    pass

try:
    import undetected_chromedriver as uc
    UNDETECTED_CHROME_AVAILABLE = True
except ImportError:
    pass

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================================
# USER AGENT DATABASE
# ============================================================================

USER_AGENTS = {
    'chrome_windows': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ],
    'chrome_mac': [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    ],
    'chrome_linux': [
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    ],
    'firefox_windows': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
    ],
    'firefox_mac': [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
    ],
    'safari_mac': [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ],
    'edge_windows': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    ],
    'mobile_ios': [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    ],
    'mobile_android': [
        'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    ],
}


# ============================================================================
# FINGERPRINT GENERATOR
# ============================================================================

@dataclass
class BrowserFingerprint:
    """Browser fingerprint configuration"""
    user_agent: str
    platform: str  # Win32, MacIntel, Linux x86_64
    language: str  # en-US
    languages: List[str]  # ['en-US', 'en']
    timezone: str  # America/New_York
    timezone_offset: int  # -300 for EST
    screen_width: int
    screen_height: int
    avail_width: int
    avail_height: int
    color_depth: int
    pixel_ratio: float
    hardware_concurrency: int
    device_memory: int
    max_touch_points: int
    webgl_vendor: str
    webgl_renderer: str
    plugins: List[Dict[str, str]]
    do_not_track: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_agent': self.user_agent,
            'platform': self.platform,
            'language': self.language,
            'languages': self.languages,
            'timezone': self.timezone,
            'timezone_offset': self.timezone_offset,
            'screen': {
                'width': self.screen_width,
                'height': self.screen_height,
                'availWidth': self.avail_width,
                'availHeight': self.avail_height,
                'colorDepth': self.color_depth,
                'pixelRatio': self.pixel_ratio,
            },
            'hardware_concurrency': self.hardware_concurrency,
            'device_memory': self.device_memory,
            'max_touch_points': self.max_touch_points,
            'webgl': {
                'vendor': self.webgl_vendor,
                'renderer': self.webgl_renderer,
            },
            'plugins': self.plugins,
            'do_not_track': self.do_not_track,
        }


class FingerprintGenerator:
    """Generate consistent browser fingerprints"""
    
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (2560, 1440), (1366, 768), (1536, 864),
        (1440, 900), (1680, 1050), (2560, 1080), (3840, 2160),
    ]
    
    WEBGL_VENDORS = [
        "Google Inc. (NVIDIA)",
        "Google Inc. (Intel)",
        "Google Inc. (AMD)",
        "Intel Inc.",
        "NVIDIA Corporation",
    ]
    
    WEBGL_RENDERERS = [
        "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    ]
    
    CHROME_PLUGINS = [
        {"name": "PDF Viewer", "filename": "internal-pdf-viewer"},
        {"name": "Chrome PDF Viewer", "filename": "internal-pdf-viewer"},
        {"name": "Chromium PDF Viewer", "filename": "internal-pdf-viewer"},
        {"name": "Microsoft Edge PDF Viewer", "filename": "internal-pdf-viewer"},
        {"name": "WebKit built-in PDF", "filename": "internal-pdf-viewer"},
    ]
    
    TIMEZONES = [
        ("America/New_York", -300),
        ("America/Chicago", -360),
        ("America/Denver", -420),
        ("America/Los_Angeles", -480),
        ("Europe/London", 0),
        ("Europe/Paris", 60),
        ("Europe/Berlin", 60),
        ("Asia/Tokyo", 540),
    ]
    
    @classmethod
    def generate(cls, browser_type: str = 'chrome', os_type: str = 'windows') -> BrowserFingerprint:
        """Generate a consistent fingerprint"""
        
        # Select user agent
        ua_key = f"{browser_type}_{os_type}"
        if ua_key not in USER_AGENTS:
            ua_key = 'chrome_windows'
        user_agent = random.choice(USER_AGENTS[ua_key])
        
        # Platform based on OS
        platform_map = {
            'windows': 'Win32',
            'mac': 'MacIntel',
            'linux': 'Linux x86_64',
            'ios': 'iPhone',
            'android': 'Linux armv8l',
        }
        platform = platform_map.get(os_type, 'Win32')
        
        # Screen resolution
        screen = random.choice(cls.SCREEN_RESOLUTIONS)
        
        # Timezone
        tz = random.choice(cls.TIMEZONES)
        
        # Hardware
        cores = random.choice([4, 8, 12, 16])
        memory = random.choice([4, 8, 16, 32])
        
        return BrowserFingerprint(
            user_agent=user_agent,
            platform=platform,
            language='en-US',
            languages=['en-US', 'en'],
            timezone=tz[0],
            timezone_offset=tz[1],
            screen_width=screen[0],
            screen_height=screen[1],
            avail_width=screen[0],
            avail_height=screen[1] - 40,  # Taskbar
            color_depth=24,
            pixel_ratio=random.choice([1.0, 1.25, 1.5, 2.0]),
            hardware_concurrency=cores,
            device_memory=memory,
            max_touch_points=0 if os_type not in ['ios', 'android'] else 5,
            webgl_vendor=random.choice(cls.WEBGL_VENDORS),
            webgl_renderer=random.choice(cls.WEBGL_RENDERERS),
            plugins=cls.CHROME_PLUGINS if browser_type == 'chrome' else [],
            do_not_track='1' if random.random() > 0.7 else None,
        )


# ============================================================================
# USER AGENT MANAGER
# ============================================================================

class UserAgentManager:
    """Manage and rotate user agents"""
    
    def __init__(self, rotation_strategy: str = 'random'):
        self.rotation_strategy = rotation_strategy
        self.current_index = 0
        self.domain_agents: Dict[str, str] = {}
        self._all_agents = self._flatten_agents()
    
    def _flatten_agents(self) -> List[str]:
        """Flatten all user agents into a single list"""
        agents = []
        for agent_list in USER_AGENTS.values():
            agents.extend(agent_list)
        return agents
    
    def get_random(self) -> str:
        """Get a random user agent"""
        return random.choice(self._all_agents)
    
    def get_sequential(self) -> str:
        """Get user agent sequentially"""
        agent = self._all_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self._all_agents)
        return agent
    
    def get_for_domain(self, domain: str) -> str:
        """Get consistent user agent for a domain"""
        if domain not in self.domain_agents:
            self.domain_agents[domain] = self.get_random()
        return self.domain_agents[domain]
    
    def get(self, domain: Optional[str] = None) -> str:
        """Get user agent based on strategy"""
        if domain:
            return self.get_for_domain(domain)
        
        if self.rotation_strategy == 'random':
            return self.get_random()
        elif self.rotation_strategy == 'sequential':
            return self.get_sequential()
        else:
            return self.get_random()
    
    def get_mobile(self) -> str:
        """Get a mobile user agent"""
        mobile_agents = USER_AGENTS.get('mobile_ios', []) + USER_AGENTS.get('mobile_android', [])
        return random.choice(mobile_agents) if mobile_agents else self.get_random()


# ============================================================================
# HEADERS MANAGER
# ============================================================================

class HeadersManager:
    """Generate realistic HTTP headers"""
    
    ACCEPT_HEADERS = {
        'html': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'json': 'application/json, text/plain, */*',
        'image': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'video': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
        'any': '*/*',
    }
    
    def __init__(self, fingerprint: Optional[BrowserFingerprint] = None):
        self.fingerprint = fingerprint or FingerprintGenerator.generate()
        self.ua_manager = UserAgentManager()
    
    def get_headers(self, 
                    accept_type: str = 'html',
                    referer: Optional[str] = None,
                    origin: Optional[str] = None,
                    extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate realistic headers"""
        
        headers = {
            'User-Agent': self.fingerprint.user_agent,
            'Accept': self.ACCEPT_HEADERS.get(accept_type, self.ACCEPT_HEADERS['any']),
            'Accept-Language': f"{self.fingerprint.language},{self.fingerprint.languages[1]};q=0.9",
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        # Chrome-specific headers
        if 'Chrome' in self.fingerprint.user_agent:
            headers.update({
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': f'"{self.fingerprint.platform}"',
            })
        
        if referer:
            headers['Referer'] = referer
            headers['Sec-Fetch-Site'] = 'same-origin' if urlparse(referer).netloc == origin else 'cross-site'
        
        if origin:
            headers['Origin'] = origin
        
        if self.fingerprint.do_not_track:
            headers['DNT'] = self.fingerprint.do_not_track
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def get_api_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests"""
        return self.get_headers(
            accept_type='json',
            referer=referer,
            extra_headers={
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
            }
        )


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Rate limiting with per-domain support"""
    
    DEFAULT_LIMITS = {
        'youtube.com': 30,
        'instagram.com': 20,
        'twitter.com': 30,
        'x.com': 30,
        'facebook.com': 20,
        'reddit.com': 60,
        'tiktok.com': 20,
        'default': 30,
    }
    
    def __init__(self, limits: Optional[Dict[str, int]] = None):
        self.limits = limits or self.DEFAULT_LIMITS
        self.requests: Dict[str, List[float]] = {}
        try:
            asyncio.get_running_loop()
            self._lock = asyncio.Lock()
        except RuntimeError:
            # No running event loop in this thread (likely sync usage)
            self._lock = None
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    
    def _get_limit(self, domain: str) -> int:
        """Get rate limit for domain"""
        for key, limit in self.limits.items():
            if key in domain:
                return limit
        return self.limits.get('default', 30)
    
    def _clean_old_requests(self, domain: str) -> None:
        """Remove requests older than 1 minute"""
        now = time.time()
        if domain in self.requests:
            self.requests[domain] = [t for t in self.requests[domain] if now - t < 60]
    
    def can_request(self, url: str) -> bool:
        """Check if we can make a request"""
        domain = self._get_domain(url)
        self._clean_old_requests(domain)
        
        limit = self._get_limit(domain)
        current_count = len(self.requests.get(domain, []))
        
        return current_count < limit
    
    def wait_time(self, url: str) -> float:
        """Get time to wait before next request"""
        domain = self._get_domain(url)
        self._clean_old_requests(domain)
        
        limit = self._get_limit(domain)
        requests_list = self.requests.get(domain, [])
        
        if len(requests_list) < limit:
            return 0
        
        oldest = min(requests_list)
        wait = 60 - (time.time() - oldest)
        return max(0, wait)
    
    def record_request(self, url: str) -> None:
        """Record a request"""
        domain = self._get_domain(url)
        if domain not in self.requests:
            self.requests[domain] = []
        self.requests[domain].append(time.time())
    
    async def wait_and_record(self, url: str) -> None:
        """Wait if needed and record request"""
        wait = self.wait_time(url)
        if wait > 0:
            logger.debug(f"Rate limiting: waiting {wait:.2f}s for {url}")
            await asyncio.sleep(wait + random.uniform(0.1, 0.5))
        self.record_request(url)
    
    def wait_and_record_sync(self, url: str) -> None:
        """Synchronous wait and record"""
        wait = self.wait_time(url)
        if wait > 0:
            logger.debug(f"Rate limiting: waiting {wait:.2f}s for {url}")
            time.sleep(wait + random.uniform(0.1, 0.5))
        self.record_request(url)


# ============================================================================
# COOKIE MANAGER
# ============================================================================

class CookieManager:
    """Manage cookies across sessions"""
    
    def __init__(self, cookie_dir: str):
        self.cookie_dir = cookie_dir
        os.makedirs(cookie_dir, exist_ok=True)
    
    def _get_cookie_path(self, domain: str) -> str:
        """Get cookie file path for domain"""
        safe_domain = re.sub(r'[^\w\-.]', '_', domain)
        return os.path.join(self.cookie_dir, f"{safe_domain}.json")
    
    def save_cookies(self, domain: str, cookies: List[Dict]) -> None:
        """Save cookies to file"""
        path = self._get_cookie_path(domain)
        with open(path, 'w') as f:
            json.dump(cookies, f, indent=2)
        logger.debug(f"Saved {len(cookies)} cookies for {domain}")
    
    def load_cookies(self, domain: str) -> List[Dict]:
        """Load cookies from file"""
        path = self._get_cookie_path(domain)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    cookies = json.load(f)
                logger.debug(f"Loaded {len(cookies)} cookies for {domain}")
                return cookies
            except Exception as e:
                logger.warning(f"Failed to load cookies for {domain}: {e}")
        return []
    
    def export_netscape(self, domain: str, output_path: str) -> None:
        """Export cookies in Netscape format"""
        cookies = self.load_cookies(domain)
        lines = ["# Netscape HTTP Cookie File"]
        
        for cookie in cookies:
            secure = "TRUE" if cookie.get('secure') else "FALSE"
            http_only = "TRUE" if cookie.get('httpOnly') else "FALSE"
            expires = str(int(cookie.get('expires', 0)))
            
            line = "\t".join([
                cookie.get('domain', ''),
                "TRUE",
                cookie.get('path', '/'),
                secure,
                expires,
                cookie.get('name', ''),
                cookie.get('value', ''),
            ])
            lines.append(line)
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
    
    def import_from_browser(self, browser: str = 'chrome') -> Dict[str, List[Dict]]:
        """Import cookies from browser (requires browser_cookie3)"""
        try:
            import browser_cookie3
            
            if browser == 'chrome':
                cj = browser_cookie3.chrome()
            elif browser == 'firefox':
                cj = browser_cookie3.firefox()
            else:
                logger.warning(f"Unsupported browser: {browser}")
                return {}
            
            cookies_by_domain: Dict[str, List[Dict]] = {}
            for cookie in cj:
                domain = cookie.domain.lstrip('.')
                if domain not in cookies_by_domain:
                    cookies_by_domain[domain] = []
                
                cookies_by_domain[domain].append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'secure': cookie.secure,
                    'expires': cookie.expires,
                })
            
            # Save all cookies
            for domain, domain_cookies in cookies_by_domain.items():
                self.save_cookies(domain, domain_cookies)
            
            return cookies_by_domain
            
        except ImportError:
            logger.warning("browser_cookie3 not installed, cannot import browser cookies")
            return {}


# ============================================================================
# PROXY MANAGER
# ============================================================================

@dataclass
class Proxy:
    """Proxy configuration"""
    host: str
    port: int
    protocol: str = 'http'  # http, https, socks4, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    
    @property
    def url(self) -> str:
        """Get proxy URL"""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, str]:
        """Get proxy dict for requests"""
        return {
            'http': self.url,
            'https': self.url,
        }


class ProxyManager:
    """Manage proxy configuration and rotation"""
    
    def __init__(self, proxies: Optional[List[Proxy]] = None):
        self.proxies = proxies or []
        self.current_index = 0
        self.failed_proxies: Dict[str, int] = {}
        self.max_failures = 3
    
    def add_proxy(self, proxy: Proxy) -> None:
        """Add a proxy to the pool"""
        self.proxies.append(proxy)
    
    def add_from_string(self, proxy_string: str) -> None:
        """Add proxy from string (protocol://user:pass@host:port)"""
        match = re.match(
            r'(?P<protocol>\w+)://(?:(?P<user>[^:]+):(?P<pass>[^@]+)@)?(?P<host>[^:]+):(?P<port>\d+)',
            proxy_string
        )
        if match:
            self.add_proxy(Proxy(
                host=match.group('host'),
                port=int(match.group('port')),
                protocol=match.group('protocol'),
                username=match.group('user'),
                password=match.group('pass'),
            ))
    
    def get_next(self) -> Optional[Proxy]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None
        
        # Skip failed proxies
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            if self.failed_proxies.get(proxy.url, 0) < self.max_failures:
                return proxy
            
            attempts += 1
        
        # All proxies have failed, reset and try again
        self.failed_proxies.clear()
        return self.proxies[0] if self.proxies else None
    
    def get_random(self) -> Optional[Proxy]:
        """Get random proxy"""
        available = [p for p in self.proxies if self.failed_proxies.get(p.url, 0) < self.max_failures]
        return random.choice(available) if available else None
    
    def report_failure(self, proxy: Proxy) -> None:
        """Report proxy failure"""
        self.failed_proxies[proxy.url] = self.failed_proxies.get(proxy.url, 0) + 1
        logger.warning(f"Proxy {proxy.host} failed ({self.failed_proxies[proxy.url]}/{self.max_failures})")
    
    def report_success(self, proxy: Proxy) -> None:
        """Report proxy success"""
        if proxy.url in self.failed_proxies:
            del self.failed_proxies[proxy.url]
    
    async def check_proxy(self, proxy: Proxy, timeout: int = 10) -> bool:
        """Check if proxy is working"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://httpbin.org/ip',
                    proxy=proxy.url,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    return response.status == 200
        except:
            return False


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """Manage HTTP sessions with persistence"""
    
    def __init__(self, 
                 fingerprint: Optional[BrowserFingerprint] = None,
                 rate_limiter: Optional[RateLimiter] = None,
                 proxy_manager: Optional[ProxyManager] = None,
                 cookie_manager: Optional[CookieManager] = None):
        
        self.fingerprint = fingerprint or FingerprintGenerator.generate()
        self.headers_manager = HeadersManager(self.fingerprint)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.proxy_manager = proxy_manager
        self.cookie_manager = cookie_manager
        
        self._session: Optional[requests.Session] = None
    
    def get_session(self) -> requests.Session:
        """Get or create requests session"""
        if self._session is None:
            self._session = requests.Session()
            
            # Configure retries
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
            # Set default headers
            self._session.headers.update(self.headers_manager.get_headers())
        
        return self._session
    
    def request(self, 
                method: str,
                url: str,
                **kwargs) -> requests.Response:
        """Make a request with all protections"""
        
        # Rate limiting
        self.rate_limiter.wait_and_record_sync(url)
        
        # Get session
        session = self.get_session()
        
        # Add proxy if available
        if self.proxy_manager:
            proxy = self.proxy_manager.get_next()
            if proxy:
                kwargs['proxies'] = proxy.to_dict()
        
        # Load cookies
        if self.cookie_manager:
            domain = urlparse(url).netloc.replace('www.', '')
            cookies = self.cookie_manager.load_cookies(domain)
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
        
        # Make request
        response = session.request(method, url, **kwargs)
        
        # Save cookies
        if self.cookie_manager:
            domain = urlparse(url).netloc.replace('www.', '')
            cookies_list = [
                {
                    'name': c.name,
                    'value': c.value,
                    'domain': c.domain,
                    'path': c.path,
                    'secure': c.secure,
                    'expires': c.expires,
                }
                for c in session.cookies
            ]
            self.cookie_manager.save_cookies(domain, cookies_list)
        
        return response
    
    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request('POST', url, **kwargs)
    
    def close(self):
        """Close session"""
        if self._session:
            self._session.close()
            self._session = None


# ============================================================================
# CLOUDFLARE BYPASS
# ============================================================================

class CloudflareBypass:
    """Handle Cloudflare protection"""
    
    CHALLENGE_MARKERS = [
        'cf-browser-verification',
        'cf_chl_opt',
        'cf-challenge',
        'Just a moment...',
        'Checking your browser',
        'cf-spinner',
        'Cloudflare',
        '_cf_chl',
    ]
    
    def __init__(self, cookie_manager: Optional[CookieManager] = None):
        self.cookie_manager = cookie_manager
    
    def is_challenge_page(self, html: str) -> bool:
        """Check if page is a Cloudflare challenge"""
        for marker in self.CHALLENGE_MARKERS:
            if marker in html:
                return True
        return False
    
    def has_clearance(self, domain: str) -> bool:
        """Check if we have cf_clearance cookie"""
        if not self.cookie_manager:
            return False
        
        cookies = self.cookie_manager.load_cookies(domain)
        return any(c['name'] == 'cf_clearance' for c in cookies)
    
    def get_with_bypass(self, url: str, timeout: int = 30) -> Optional[str]:
        """Get URL with Cloudflare bypass using curl_cffi"""
        if not CURL_CFFI_AVAILABLE:
            logger.warning("curl_cffi not available for Cloudflare bypass")
            return None
        
        try:
            response = curl_requests.get(
                url,
                impersonate="chrome110",
                timeout=timeout,
            )
            
            if response.status_code == 200:
                return response.text
            
            logger.warning(f"Cloudflare bypass failed: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Cloudflare bypass error: {e}")
            return None
    
    async def solve_with_browser(self, url: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """Solve Cloudflare challenge using browser"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available for Cloudflare solving")
            return None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()
                
                await page.goto(url)
                
                # Wait for challenge to complete
                start_time = time.time()
                while time.time() - start_time < timeout:
                    html = await page.content()
                    if not self.is_challenge_page(html):
                        # Challenge solved
                        cookies = await context.cookies()
                        
                        if self.cookie_manager:
                            domain = urlparse(url).netloc.replace('www.', '')
                            self.cookie_manager.save_cookies(domain, cookies)
                        
                        await browser.close()
                        return {
                            'cookies': cookies,
                            'html': html,
                        }
                    
                    await asyncio.sleep(1)
                
                await browser.close()
                logger.warning("Cloudflare challenge timeout")
                return None
                
        except Exception as e:
            logger.error(f"Browser Cloudflare bypass error: {e}")
            return None


# ============================================================================
# STEALTH BROWSER
# ============================================================================

class StealthBrowser:
    """Browser automation with anti-detection"""
    
    # JavaScript to inject for stealth
    STEALTH_JS = """
    // Remove webdriver property
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });
    
    // Mock plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                { name: 'Native Client', filename: 'internal-nacl-plugin' },
            ];
            plugins.item = (index) => plugins[index];
            plugins.namedItem = (name) => plugins.find(p => p.name === name);
            plugins.refresh = () => {};
            return plugins;
        },
    });
    
    // Mock languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });
    
    // Mock permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    
    // Remove automation indicators
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    
    // Override toString
    const originalFunction = Function.prototype.toString;
    Function.prototype.toString = function() {
        if (this === window.navigator.permissions.query) {
            return 'function query() { [native code] }';
        }
        return originalFunction.call(this);
    };
    """
    
    def __init__(self,
                 headless: bool = True,
                 fingerprint: Optional[BrowserFingerprint] = None,
                 proxy: Optional[Proxy] = None,
                 cookie_manager: Optional[CookieManager] = None):
        
        self.headless = headless
        self.fingerprint = fingerprint or FingerprintGenerator.generate()
        self.proxy = proxy
        self.cookie_manager = cookie_manager
        
        self._browser = None
        self._context = None
        self._page = None
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """Start browser"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")
        
        self._playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
                f'--user-agent={self.fingerprint.user_agent}',
            ],
        }
        
        if self.proxy:
            launch_options['proxy'] = {
                'server': f'{self.proxy.protocol}://{self.proxy.host}:{self.proxy.port}',
            }
            if self.proxy.username:
                launch_options['proxy']['username'] = self.proxy.username
                launch_options['proxy']['password'] = self.proxy.password
        
        self._browser = await self._playwright.chromium.launch(**launch_options)
        
        # Context options
        context_options = {
            'viewport': {
                'width': self.fingerprint.screen_width,
                'height': self.fingerprint.screen_height,
            },
            'user_agent': self.fingerprint.user_agent,
            'locale': self.fingerprint.language,
            'timezone_id': self.fingerprint.timezone,
            'device_scale_factor': self.fingerprint.pixel_ratio,
        }
        
        self._context = await self._browser.new_context(**context_options)
        
        # Inject stealth script on all pages
        await self._context.add_init_script(self.STEALTH_JS)
        
        # Load cookies if available
        if self.cookie_manager:
            # Will be loaded per-domain during navigation
            pass
        
        self._page = await self._context.new_page()
    
    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def goto(self, url: str, wait_until: str = 'networkidle') -> None:
        """Navigate to URL"""
        # Load cookies for domain
        if self.cookie_manager:
            domain = urlparse(url).netloc.replace('www.', '')
            cookies = self.cookie_manager.load_cookies(domain)
            if cookies:
                await self._context.add_cookies(cookies)
        
        await self._page.goto(url, wait_until=wait_until)
        
        # Random delay
        await asyncio.sleep(random.uniform(0.5, 1.5))
    
    async def get_content(self) -> str:
        """Get page content"""
        return await self._page.content()
    
    async def get_cookies(self) -> List[Dict]:
        """Get all cookies"""
        return await self._context.cookies()
    
    async def save_cookies(self, domain: str) -> None:
        """Save cookies for domain"""
        if self.cookie_manager:
            cookies = await self.get_cookies()
            self.cookie_manager.save_cookies(domain, cookies)
    
    async def screenshot(self, path: str) -> None:
        """Take screenshot"""
        await self._page.screenshot(path=path, full_page=True)
    
    async def click(self, selector: str, delay: float = None) -> None:
        """Click element with human-like delay"""
        if delay is None:
            delay = random.uniform(50, 150)
        await self._page.click(selector, delay=delay)
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def type(self, selector: str, text: str, delay: float = None) -> None:
        """Type text with human-like speed"""
        if delay is None:
            delay = random.uniform(50, 150)
        await self._page.type(selector, text, delay=delay)
    
    async def scroll(self, direction: str = 'down', amount: int = 500) -> None:
        """Scroll page"""
        if direction == 'down':
            await self._page.mouse.wheel(0, amount)
        else:
            await self._page.mouse.wheel(0, -amount)
        await asyncio.sleep(random.uniform(0.2, 0.5))
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        """Wait for element"""
        await self._page.wait_for_selector(selector, timeout=timeout)
    
    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript"""
        return await self._page.evaluate(script)
    
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get element attribute"""
        element = await self._page.query_selector(selector)
        if element:
            return await element.get_attribute(attribute)
        return None
    
    async def extract_video_urls(self) -> List[str]:
        """Extract video URLs from page"""
        urls = await self.evaluate("""
            () => {
                const urls = [];
                
                // Video elements
                document.querySelectorAll('video source').forEach(s => {
                    if (s.src) urls.push(s.src);
                });
                
                document.querySelectorAll('video').forEach(v => {
                    if (v.src) urls.push(v.src);
                    if (v.currentSrc) urls.push(v.currentSrc);
                });
                
                // Look for video in data attributes
                document.querySelectorAll('[data-video-url]').forEach(el => {
                    urls.push(el.dataset.videoUrl);
                });
                
                return [...new Set(urls)];
            }
        """)
        return urls


# ============================================================================
# CAPTCHA HANDLER
# ============================================================================

class CaptchaHandler:
    """Handle CAPTCHA challenges"""
    
    CAPTCHA_MARKERS = {
        'recaptcha': ['g-recaptcha', 'recaptcha', 'grecaptcha'],
        'hcaptcha': ['h-captcha', 'hcaptcha'],
        'turnstile': ['cf-turnstile', 'turnstile'],
    }
    
    def __init__(self, cookie_manager: Optional[CookieManager] = None):
        self.cookie_manager = cookie_manager
    
    def detect_captcha(self, html: str) -> Optional[str]:
        """Detect CAPTCHA type"""
        for captcha_type, markers in self.CAPTCHA_MARKERS.items():
            for marker in markers:
                if marker in html.lower():
                    return captcha_type
        return None
    
    async def notify_user(self, captcha_type: str, url: str) -> None:
        """Notify user about CAPTCHA"""
        logger.warning(f"CAPTCHA detected: {captcha_type}")
        logger.warning(f"URL: {url}")
        logger.warning("Please solve the CAPTCHA manually in the browser window.")
    
    async def wait_for_solve(self, 
                            browser: StealthBrowser,
                            timeout: int = 300) -> bool:
        """Wait for user to solve CAPTCHA"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            html = await browser.get_content()
            if not self.detect_captcha(html):
                logger.info("CAPTCHA solved!")
                
                # Save cookies
                current_url = browser._page.url if browser._page else ""
                domain = urlparse(current_url).netloc.replace('www.', '')
                await browser.save_cookies(domain)
                
                return True
            
            await asyncio.sleep(2)
        
        logger.warning("CAPTCHA solve timeout")
        return False


# ============================================================================
# JS RENDERER
# ============================================================================

class JSRenderer:
    """Render JavaScript-heavy pages"""
    
    def __init__(self,
                 fingerprint: Optional[BrowserFingerprint] = None,
                 proxy: Optional[Proxy] = None,
                 cookie_manager: Optional[CookieManager] = None):
        
        self.fingerprint = fingerprint or FingerprintGenerator.generate()
        self.proxy = proxy
        self.cookie_manager = cookie_manager
    
    async def render(self, 
                    url: str,
                    wait_for: str = 'networkidle',
                    wait_for_selector: Optional[str] = None,
                    timeout: int = 30000) -> str:
        """Render page and return HTML"""
        
        async with StealthBrowser(
            headless=True,
            fingerprint=self.fingerprint,
            proxy=self.proxy,
            cookie_manager=self.cookie_manager
        ) as browser:
            
            await browser.goto(url, wait_until=wait_for)
            
            if wait_for_selector:
                await browser.wait_for_selector(wait_for_selector, timeout=timeout)
            
            html = await browser.get_content()
            
            # Save cookies
            domain = urlparse(url).netloc.replace('www.', '')
            await browser.save_cookies(domain)
            
            return html
    
    async def render_with_scroll(self, 
                                 url: str,
                                 scroll_count: int = 5,
                                 scroll_delay: float = 1.0) -> str:
        """Render page with infinite scroll"""
        
        async with StealthBrowser(
            headless=True,
            fingerprint=self.fingerprint,
            proxy=self.proxy,
            cookie_manager=self.cookie_manager
        ) as browser:
            
            await browser.goto(url)
            
            for i in range(scroll_count):
                await browser.scroll('down', 800)
                await asyncio.sleep(scroll_delay + random.uniform(0, 0.5))
            
            html = await browser.get_content()
            return html


# ============================================================================
# BOT SESSION (Main Interface)
# ============================================================================

class BotSession:
    """Main interface for bot functionality"""
    
    def __init__(self, 
                 cookie_dir: str = "cookies",
                 use_proxy: bool = False,
                 proxy_url: Optional[str] = None):
        
        self.fingerprint = FingerprintGenerator.generate()
        self.cookie_manager = CookieManager(cookie_dir)
        self.rate_limiter = RateLimiter()
        self.headers_manager = HeadersManager(self.fingerprint)
        self.cloudflare_bypass = CloudflareBypass(self.cookie_manager)
        self.captcha_handler = CaptchaHandler(self.cookie_manager)
        
        # Proxy setup
        self.proxy_manager = None
        if use_proxy and proxy_url:
            self.proxy_manager = ProxyManager()
            self.proxy_manager.add_from_string(proxy_url)
        
        # Session manager
        self.session_manager = SessionManager(
            fingerprint=self.fingerprint,
            rate_limiter=self.rate_limiter,
            proxy_manager=self.proxy_manager,
            cookie_manager=self.cookie_manager,
        )
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request with protections"""
        return self.session_manager.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make POST request with protections"""
        return self.session_manager.post(url, **kwargs)
    
    def get_headers(self) -> Dict[str, str]:
        """Get current headers"""
        return self.headers_manager.get_headers()
    
    async def get_with_browser(self, url: str, headless: bool = True) -> str:
        """Get page content using browser"""
        proxy = self.proxy_manager.get_next() if self.proxy_manager else None
        
        async with StealthBrowser(
            headless=headless,
            fingerprint=self.fingerprint,
            proxy=proxy,
            cookie_manager=self.cookie_manager,
        ) as browser:
            
            await browser.goto(url)
            html = await browser.get_content()
            
            # Check for challenges
            if self.cloudflare_bypass.is_challenge_page(html):
                logger.info("Cloudflare challenge detected, waiting...")
                await asyncio.sleep(10)
                html = await browser.get_content()
            
            captcha_type = self.captcha_handler.detect_captcha(html)
            if captcha_type:
                await self.captcha_handler.notify_user(captcha_type, url)
                await self.captcha_handler.wait_for_solve(browser)
                html = await browser.get_content()
            
            # Save cookies
            domain = urlparse(url).netloc.replace('www.', '')
            await browser.save_cookies(domain)
            
            return html
    
    async def render_js(self, url: str, **kwargs) -> str:
        """Render JavaScript page"""
        renderer = JSRenderer(
            fingerprint=self.fingerprint,
            proxy=self.proxy_manager.get_next() if self.proxy_manager else None,
            cookie_manager=self.cookie_manager,
        )
        return await renderer.render(url, **kwargs)
    
    def get_cookie_path(self, domain: str) -> str:
        """Get cookie file path for domain"""
        return self.cookie_manager._get_cookie_path(domain)
    
    def close(self):
        """Close all sessions"""
        self.session_manager.close()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'BotSession',
    'StealthBrowser',
    'CloudflareBypass',
    'CaptchaHandler',
    'SessionManager',
    'RateLimiter',
    'ProxyManager',
    'Proxy',
    'CookieManager',
    'UserAgentManager',
    'HeadersManager',
    'FingerprintGenerator',
    'BrowserFingerprint',
    'JSRenderer',
    'PLAYWRIGHT_AVAILABLE',
    'SELENIUM_AVAILABLE',
    'CURL_CFFI_AVAILABLE',
]
