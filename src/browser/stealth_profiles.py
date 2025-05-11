import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

@dataclass
class BrowserProfile:
    """Represents a complete browser profile configuration."""
    # Basic browser info
    user_agent: str
    browser_name: str
    browser_version: str
    os_name: str
    os_version: str
    
    # Display and hardware
    viewport: Dict[str, int]
    device_pixel_ratio: float
    color_depth: int
    hardware_concurrency: int
    device_memory: int
    touch_points: int
    
    # Localization
    language: str
    languages: List[str]
    timezone: str
    geolocation: Dict[str, float]
    
    # Browser features
    plugins: List[Dict[str, str]]
    mime_types: List[Dict[str, str]]
    webgl_vendor: str
    webgl_renderer: str
    webgl_version: str
    
    # Anti-detection
    canvas_noise: float
    audio_noise: float
    webgl_noise: float
    
    # Marketplace specific
    navigation_pattern: Dict[str, Any]
    interaction_delays: Dict[str, float]
    scroll_behavior: Dict[str, Any]
    mouse_behavior: Dict[str, Any]

# Common plugins and MIME types for modern browsers
COMMON_PLUGINS = [
    {
        "name": "Chrome PDF Plugin",
        "description": "Portable Document Format",
        "filename": "internal-pdf-viewer",
        "mime_types": [
            {"type": "application/pdf", "suffixes": "pdf", "description": "Portable Document Format"}
        ]
    },
    {
        "name": "Chrome PDF Viewer",
        "description": "Portable Document Format",
        "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai",
        "mime_types": [
            {"type": "application/pdf", "suffixes": "pdf", "description": "Portable Document Format"}
        ]
    },
    {
        "name": "Native Client",
        "description": "Native Client Executable",
        "filename": "internal-nacl-plugin",
        "mime_types": [
            {"type": "application/x-nacl", "suffixes": "", "description": "Native Client Executable"},
            {"type": "application/x-pnacl", "suffixes": "", "description": "Portable Native Client Executable"}
        ]
    }
]

# Desktop profiles with enhanced realism
DESKTOP_PROFILES = [
    # Windows 10 - Chrome (High-end)
    BrowserProfile(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        browser_name="Chrome",
        browser_version="112.0.0.0",
        os_name="Windows",
        os_version="10",
        viewport={"width": 1920, "height": 1080},
        device_pixel_ratio=1.0,
        color_depth=24,
        hardware_concurrency=8,
        device_memory=8,
        touch_points=0,
        language="pt-BR",
        languages=["pt-BR", "pt", "en-US", "en"],
        timezone="America/Sao_Paulo",
        geolocation={"latitude": -23.5505, "longitude": -46.6333},
        plugins=COMMON_PLUGINS,
        mime_types=[mime for plugin in COMMON_PLUGINS for mime in plugin["mime_types"]],
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
        webgl_version="WebGL 1.0",
        canvas_noise=0.1,
        audio_noise=0.05,
        webgl_noise=0.1,
        navigation_pattern={
            "type": "desktop",
            "scroll_speed": [100, 500],
            "scroll_pause": [500, 2000],
            "click_delay": [100, 300]
        },
        interaction_delays={
            "page_load": [2000, 5000],
            "click": [100, 300],
            "scroll": [500, 2000],
            "type": [50, 150]
        },
        scroll_behavior={
            "style": "smooth",
            "speed_variance": 0.3,
            "pause_probability": 0.2
        },
        mouse_behavior={
            "movement_style": "natural",
            "speed_variance": 0.2,
            "acceleration": True,
            "overshoot_probability": 0.1
        }
    ),
    
    # Windows 10 - Firefox (Mid-range)
    BrowserProfile(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
        browser_name="Firefox",
        browser_version="112.0",
        os_name="Windows",
        os_version="10",
        viewport={"width": 1366, "height": 768},
        device_pixel_ratio=1.0,
        color_depth=24,
        hardware_concurrency=4,
        device_memory=4,
        touch_points=0,
        language="pt-BR",
        languages=["pt-BR", "pt", "en-US", "en"],
        timezone="America/Sao_Paulo",
        geolocation={"latitude": -23.5505, "longitude": -46.6333},
        plugins=COMMON_PLUGINS,
        mime_types=[mime for plugin in COMMON_PLUGINS for mime in plugin["mime_types"]],
        webgl_vendor="Mozilla",
        webgl_renderer="Mozilla",
        webgl_version="WebGL 1.0",
        canvas_noise=0.1,
        audio_noise=0.05,
        webgl_noise=0.1,
        navigation_pattern={
            "type": "desktop",
            "scroll_speed": [80, 400],
            "scroll_pause": [400, 1800],
            "click_delay": [150, 400]
        },
        interaction_delays={
            "page_load": [2500, 6000],
            "click": [150, 400],
            "scroll": [600, 2500],
            "type": [60, 180]
        },
        scroll_behavior={
            "style": "smooth",
            "speed_variance": 0.25,
            "pause_probability": 0.25
        },
        mouse_behavior={
            "movement_style": "natural",
            "speed_variance": 0.25,
            "acceleration": True,
            "overshoot_probability": 0.15
        }
    ),
    
    # macOS - Safari (High-end)
    BrowserProfile(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        browser_name="Safari",
        browser_version="16.0",
        os_name="macOS",
        os_version="10.15.7",
        viewport={"width": 1440, "height": 900},
        device_pixel_ratio=2.0,
        color_depth=30,
        hardware_concurrency=8,
        device_memory=8,
        touch_points=0,
        language="pt-BR",
        languages=["pt-BR", "pt", "en-US", "en"],
        timezone="America/Sao_Paulo",
        geolocation={"latitude": -23.5505, "longitude": -46.6333},
        plugins=COMMON_PLUGINS,
        mime_types=[mime for plugin in COMMON_PLUGINS for mime in plugin["mime_types"]],
        webgl_vendor="Apple GPU",
        webgl_renderer="Apple M1 Pro",
        webgl_version="WebGL 1.0",
        canvas_noise=0.1,
        audio_noise=0.05,
        webgl_noise=0.1,
        navigation_pattern={
            "type": "desktop",
            "scroll_speed": [120, 600],
            "scroll_pause": [400, 1600],
            "click_delay": [80, 250]
        },
        interaction_delays={
            "page_load": [1800, 4500],
            "click": [80, 250],
            "scroll": [400, 1600],
            "type": [40, 120]
        },
        scroll_behavior={
            "style": "smooth",
            "speed_variance": 0.2,
            "pause_probability": 0.15
        },
        mouse_behavior={
            "movement_style": "natural",
            "speed_variance": 0.15,
            "acceleration": True,
            "overshoot_probability": 0.05
        }
    )
]

# Mobile profiles with enhanced realism
MOBILE_PROFILES = [
    # iPhone 13 Pro
    BrowserProfile(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1",
        browser_name="Safari",
        browser_version="15.4",
        os_name="iOS",
        os_version="15.4",
        viewport={"width": 390, "height": 844},
        device_pixel_ratio=3.0,
        color_depth=24,
        hardware_concurrency=6,
        device_memory=4,
        touch_points=5,
        language="pt-BR",
        languages=["pt-BR", "pt", "en-US", "en"],
        timezone="America/Sao_Paulo",
        geolocation={"latitude": -23.5505, "longitude": -46.6333},
        plugins=[],
        mime_types=[],
        webgl_vendor="Apple GPU",
        webgl_renderer="Apple A15 GPU",
        webgl_version="WebGL 1.0",
        canvas_noise=0.1,
        audio_noise=0.05,
        webgl_noise=0.1,
        navigation_pattern={
            "type": "mobile",
            "scroll_speed": [50, 200],
            "scroll_pause": [300, 1200],
            "click_delay": [50, 150]
        },
        interaction_delays={
            "page_load": [1500, 4000],
            "click": [50, 150],
            "scroll": [300, 1200],
            "type": [30, 100]
        },
        scroll_behavior={
            "style": "momentum",
            "speed_variance": 0.4,
            "pause_probability": 0.3
        },
        mouse_behavior={
            "movement_style": "touch",
            "speed_variance": 0.3,
            "acceleration": True,
            "overshoot_probability": 0.2
        }
    ),
    
    # Samsung Galaxy S21
    BrowserProfile(
        user_agent="Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        browser_name="Chrome",
        browser_version="112.0.0.0",
        os_name="Android",
        os_version="12",
        viewport={"width": 360, "height": 800},
        device_pixel_ratio=3.0,
        color_depth=24,
        hardware_concurrency=8,
        device_memory=8,
        touch_points=5,
        language="pt-BR",
        languages=["pt-BR", "pt", "en-US", "en"],
        timezone="America/Sao_Paulo",
        geolocation={"latitude": -23.5505, "longitude": -46.6333},
        plugins=[],
        mime_types=[],
        webgl_vendor="Google Inc. (Qualcomm)",
        webgl_renderer="ANGLE (Qualcomm, Adreno (TM) 650, OpenGL ES 3.2 V@050.0 (GIT@050.0))",
        webgl_version="WebGL 1.0",
        canvas_noise=0.1,
        audio_noise=0.05,
        webgl_noise=0.1,
        navigation_pattern={
            "type": "mobile",
            "scroll_speed": [60, 250],
            "scroll_pause": [350, 1300],
            "click_delay": [60, 180]
        },
        interaction_delays={
            "page_load": [1800, 4500],
            "click": [60, 180],
            "scroll": [350, 1300],
            "type": [40, 120]
        },
        scroll_behavior={
            "style": "momentum",
            "speed_variance": 0.35,
            "pause_probability": 0.25
        },
        mouse_behavior={
            "movement_style": "touch",
            "speed_variance": 0.25,
            "acceleration": True,
            "overshoot_probability": 0.15
        }
    )
]

# Marketplace-specific profiles
MARKETPLACE_PROFILES = {
    "mercadolivre.com.br": {
        "preferred_profiles": [0, 2],  # Windows Chrome and macOS Safari
        "navigation_pattern": {
            "category_browse": True,
            "search_history": True,
            "product_comparison": True
        },
        "interaction_delays": {
            "category_browse": [2000, 5000],
            "product_view": [3000, 8000],
            "search": [1000, 3000]
        }
    },
    "magazineluiza.com.br": {
        "preferred_profiles": [1, 2],  # Windows Firefox and macOS Safari
        "navigation_pattern": {
            "category_browse": True,
            "search_history": False,
            "product_comparison": True
        },
        "interaction_delays": {
            "category_browse": [2500, 6000],
            "product_view": [3500, 9000],
            "search": [1200, 3500]
        }
    },
    "americanas.com.br": {
        "preferred_profiles": [0, 1],  # Windows Chrome and Firefox
        "navigation_pattern": {
            "category_browse": True,
            "search_history": True,
            "product_comparison": False
        },
        "interaction_delays": {
            "category_browse": [2200, 5500],
            "product_view": [3200, 8500],
            "search": [1100, 3200]
        }
    }
}

def get_profile_for_domain(domain: str, url: str) -> BrowserProfile:
    """Get a consistent profile for a domain and URL."""
    # Create a deterministic hash from domain and URL
    hash_input = f"{domain}{url}".encode()
    hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
    
    # Get marketplace-specific configuration
    marketplace_config = MARKETPLACE_PROFILES.get(domain, {})
    preferred_profiles = marketplace_config.get("preferred_profiles", [])
    
    # Select from preferred profiles if available
    if preferred_profiles:
        profile_index = preferred_profiles[hash_value % len(preferred_profiles)]
        return DESKTOP_PROFILES[profile_index]
    
    # Fallback to all profiles
    all_profiles = DESKTOP_PROFILES + MOBILE_PROFILES
    return all_profiles[hash_value % len(all_profiles)]

# Combine all profiles
PROFILES = DESKTOP_PROFILES + MOBILE_PROFILES
