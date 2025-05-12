import os
import random
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from loguru import logger
from datetime import timedelta
from playwright.sync_api import sync_playwright
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Redis configuration
REDIS_CONFIG = {
    'url': os.getenv('REDIS_URL', ''),
    'max_connections': 100,
    'timeout': 20,
    'retry_on_timeout': True
}

# Circuit Breaker settings
CIRCUIT_BREAKER_THRESHOLD = 5  # Number of failures before opening circuit
CIRCUIT_BREAKER_WINDOW = 300  # Time window for failure counting (seconds)
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT = 60  # Time before attempting recovery (seconds)
MAX_RETRIES = 3  # Maximum number of retries per request
BASE_RETRY_DELAY = 5  # Base delay for retries (seconds)

# Change Detection settings
LAYOUT_CHANGE_THRESHOLD = 0.7  # Minimum similarity threshold for layout changes
MIN_CONFIDENCE_THRESHOLD = 0.8  # Minimum confidence for extraction results
MAX_FALLBACK_STRATEGIES = 5  # Maximum number of fallback strategies per domain

# Monitoring settings
MONITORING_INTERVAL = 60  # Interval between metric checks (seconds)
ALERT_COOLDOWN = 30  # Minutes between alerts for the same issue

# Alert thresholds
ALERT_THRESHOLDS = {
    'success_rate': 0.8,  # Minimum acceptable success rate
    'response_time': 5.0,  # Maximum acceptable response time (seconds)
    'error_rate': 0.2,  # Maximum acceptable error rate
    'extraction_confidence': 0.8,  # Minimum acceptable extraction confidence
    'layout_changes': 3  # Maximum acceptable layout changes per hour
}

# Cache TTLs (in seconds)
CACHE_TTL = {
    'strategy': 86400,  # 24 hours
    'fingerprint': 3600,  # 1 hour
    'price': 300,  # 5 minutes
    'domain_stats': 1800,  # 30 minutes
}

# Cache size limits
CACHE_LIMITS = {
    'strategy': 1000,  # Max number of strategies per domain
    'fingerprint': 5000,  # Max number of fingerprints
    'price': 10000,  # Max number of price entries
}

# Cache patterns
CACHE_PATTERNS = {
    'strategy': 'strategy:{domain}:{type}',
    'fingerprint': 'fingerprint:{domain}:{hash}',
    'price': 'price:{url_id}:{timestamp}',
    'domain_stats': 'stats:{domain}:{period}'
}

# Cache configuration for different layers
CACHE_LAYERS = {
    'memory': {
        'enabled': True,
        'max_size': 1000,
        'ttl': 300
    },
    'redis': {
        'enabled': True,
        'max_size': '1GB',
        'ttl': 3600
    },
    'database': {
        'enabled': True,
        'ttl': 86400
    }
}

# Scheduler settings
MAX_CONCURRENT_DOMAINS = 5  # Maximum number of concurrent domain processing
BATCH_SIZE = 10  # Number of URLs to process in a batch
QUEUE_PROCESS_INTERVAL = 1  # Seconds between queue processing
PRIORITY_THRESHOLD = 86400  # 24 hours in seconds

# Logging settings
LOG_LEVEL = 'INFO'
LOG_ROTATION_SIZE = '100 MB'
LOG_RETENTION_DAYS = 7

# Proxy settings (opcional)
PROXY_ENABLED = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
PROXY_CONFIG = {
    'username': os.getenv('BRIGHTDATA_USERNAME', ''),
    'password': os.getenv('BRIGHTDATA_PASSWORD', ''),
    'host': os.getenv('BRIGHTDATA_HOST', 'brd.superproxy.io'),
    'port': os.getenv('BRIGHTDATA_PORT', '22225'),
    'region': os.getenv('PROXY_REGION', 'br')
}

# Browser settings
BROWSER_TIMEOUT = 30  # seconds
BROWSER_RETRY_ATTEMPTS = 3
BROWSER_HEADLESS = True

# Security settings
CAPTCHA_WINDOW_HOURS = 24
MAX_CAPTCHA_BLOCKS = 3
MAX_DOMAIN_ERRORS = 5

# Configurações de JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    username: str
    password: str
    host: str
    port: str
    region: str

    @property
    def url(self) -> str:
        """Get the complete proxy URL."""
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"

@dataclass
class ScrapingConfig:
    """Scraping operation settings."""
    interval_base: int
    interval_jitter: int
    max_concurrent: int
    request_timeout: int
    max_retries: int
    max_failed_attempts: int
    backoff_base: int

@dataclass
class LearningConfig:
    """Strategy learning configuration."""
    confidence_update: float
    confidence_discard_threshold: float
    evaluation_interval: int

@dataclass
class ResourceConfig:
    """Resource usage limits."""
    max_cpu_usage: float
    max_ram_mb: int

@dataclass
class MonitoringConfig:
    """Monitoring and alerting configuration."""
    apm_enabled: bool
    otlp_endpoint: str
    environment: str
    slack_webhook: Optional[str]
    email_host: str
    email_port: int
    email_username: str
    email_password: str
    email_recipients: List[str]

@dataclass
class SecurityConfig:
    """Security configuration settings."""
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_limit: int = 10
    rate_limit_block_duration: int = 300
    waf_enabled: bool = True
    audit_log_file: str = "audit.log"
    security_headers_enabled: bool = True
    content_security_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    x_xss_protection: str = "1; mode=block"
    strict_transport_security: str = "max-age=31536000; includeSubDomains"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"

@dataclass
class ScalingConfig:
    min_instances: int = int(os.getenv("MIN_INSTANCES", "1"))
    max_instances: int = int(os.getenv("MAX_INSTANCES", "5"))
    target_cpu_percent: float = float(os.getenv("TARGET_CPU_PERCENT", "70.0"))
    target_memory_percent: float = float(os.getenv("TARGET_MEMORY_PERCENT", "70.0"))
    scale_up_threshold: float = float(os.getenv("SCALE_UP_THRESHOLD", "80.0"))
    scale_down_threshold: float = float(os.getenv("SCALE_DOWN_THRESHOLD", "30.0"))
    cooldown_period: int = int(os.getenv("SCALING_COOLDOWN_PERIOD", "300"))
    metrics_interval: int = int(os.getenv("METRICS_INTERVAL", "60"))

@dataclass
class ResourceLimitsConfig:
    max_cpu_percent: float = float(os.getenv("MAX_CPU_PERCENT", "80.0"))
    max_memory_percent: float = float(os.getenv("MAX_MEMORY_PERCENT", "80.0"))
    max_memory_bytes: Optional[int] = int(os.getenv("MAX_MEMORY_BYTES", "0")) or None
    max_file_descriptors: int = int(os.getenv("MAX_FILE_DESCRIPTORS", "1024"))
    max_threads: int = int(os.getenv("MAX_THREADS", "100"))
    max_connections: int = int(os.getenv("MAX_CONNECTIONS", "1000"))

@dataclass
class CacheConfig:
    max_total_size: int = 1024 * 1024 * 1024  # 1GB
    max_entry_size: int = 10 * 1024 * 1024   # 10MB
    cleanup_interval: int = 300              # 5 minutes
    min_success_rate: float = 0.3
    max_pattern_age_days: int = 30

@dataclass
class NetworkConfig:
    request_batch_size: int = 10
    compression_level: int = 6
    connection_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    max_concurrent_connections: int = 10

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/scraper.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

class ScrapingSettings(BaseModel):
    max_concurrent: int = Field(default=10, description="Número máximo de domínios concorrentes")
    request_timeout: int = Field(default=30, description="Timeout das requisições de scraping em segundos")
    max_retries: int = Field(default=3, description="Número máximo de tentativas de scraping por URL")
    interval_base: int = Field(default=21600, description="Intervalo base entre scrapes em segundos (6h)")
    interval_jitter: int = Field(default=1800, description="Jitter do intervalo em segundos (30min)")
    batch_size: int = Field(default=10, description="Tamanho do lote de URLs processadas por domínio")
    loop_interval: int = Field(default=600, description="Intervalo do loop principal do scheduler em segundos (10min)")
    user_agent: str = Field(default="Mozilla/5.0", description="User-Agent padrão para scraping")

class ResourcesSettings(BaseModel):
    max_cpu_usage: float = Field(default=90.0, description="Uso máximo de CPU em porcentagem")
    max_ram_mb: int = Field(default=2048, description="Uso máximo de RAM em MB")

class Settings(BaseSettings):
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    PROXY_URL: Optional[str] = Field(None, env="PROXY_URL")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_rotation_size: str = Field(default="100 MB", env="LOG_ROTATION_SIZE")
    log_retention_days: int = Field(default=7, env="LOG_RETENTION_DAYS")
    scraping: ScrapingSettings = ScrapingSettings()
    resources: ResourcesSettings = ResourcesSettings()
    # Futuras seções: database, security, etc.

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Create a singleton instance
settings = Settings()

# Export commonly used settings for convenience
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
PROXY_URL = settings.PROXY_URL
MAX_CONCURRENT_SCRAPES = settings.scraping.max_concurrent
REQUEST_TIMEOUT = settings.scraping.request_timeout
MAX_RETRIES = settings.scraping.max_retries
MAX_CPU_USAGE = settings.resources.max_cpu_usage
MAX_RAM_MB = settings.resources.max_ram_mb


