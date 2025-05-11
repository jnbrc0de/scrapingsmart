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

# Database settings
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Redis configuration
REDIS_CONFIG = {
    'url': os.getenv('REDIS_URL', ''),
    'max_connections': 100,
    'timeout': 20,
    'retry_on_timeout': True
}

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

class Settings:
    """Centralized settings management."""
    
    def __init__(self):
        # Database credentials
        self.SUPABASE_URL = self._get_required_env("SUPABASE_URL")
        self.SUPABASE_KEY = self._get_required_env("SUPABASE_KEY")
        
        # Proxy configuration (opcional)
        self.proxy_enabled = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
        self.proxy = None
        
        if self.proxy_enabled:
            username = os.getenv("BRIGHTDATA_USERNAME")
            password = os.getenv("BRIGHTDATA_PASSWORD")
            
            if username and password:
                self.proxy = ProxyConfig(
                    username=username,
                    password=password,
                    host=os.getenv("BRIGHTDATA_HOST", "brd.superproxy.io"),
                    port=os.getenv("BRIGHTDATA_PORT", "22225"),
                    region=os.getenv("PROXY_REGION", "br")
                )
            else:
                logger.warning("Proxy enabled but credentials not set. Disabling proxy.")
                self.proxy_enabled = False
        
        # Scraping configuration
        self.scraping = ScrapingConfig(
            interval_base=self._validate_int("SCRAPE_INTERVAL_BASE", 6 * 3600),
            interval_jitter=self._validate_int("SCRAPE_INTERVAL_JITTER", 0.5 * 3600),
            max_concurrent=self._validate_int("MAX_CONCURRENT_SCRAPES", 10),
            request_timeout=self._validate_int("REQUEST_TIMEOUT", 30),
            max_retries=self._validate_int("MAX_RETRIES", 3),
            max_failed_attempts=self._validate_int("MAX_FAILED_ATTEMPTS", 3),
            backoff_base=self._validate_int("BACKOFF_BASE", 60)
        )
        
        # Learning configuration
        self.learning = LearningConfig(
            confidence_update=self._validate_float("STRATEGY_CONFIDENCE_UPDATE", 0.9),
            confidence_discard_threshold=self._validate_float("CONFIDENCE_DISCARD_THRESHOLD", 0.1),
            evaluation_interval=self._validate_int("STRATEGY_EVALUATION_INTERVAL", 50)
        )
        
        # Resource limits
        self.resources = ResourceConfig(
            max_cpu_usage=self._validate_float("MAX_CPU_USAGE", 0.80),
            max_ram_mb=self._validate_int("MAX_RAM_USAGE_MB", 2048)
        )
        
        # Circuit Breaker settings
        self.circuit_breaker_failure_threshold = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
        self.circuit_breaker_recovery_timeout = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
        self.circuit_breaker_half_open_timeout = int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT", "30"))
        self.circuit_breaker_success_threshold = int(os.getenv("CIRCUIT_BREAKER_SUCCESS_THRESHOLD", "2"))
        
        # Retry settings
        self.retry_delay = int(os.getenv("RETRY_DELAY", "2"))
        
        # Session settings
        self.session_timeout = int(os.getenv("SESSION_TIMEOUT", "3600"))
        self.session_file = os.getenv("SESSION_FILE", "browser_sessions.json")
        
        # Proxy settings
        self.proxy_url = os.getenv("PROXY_URL", "")
        
        # Logging settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "scraping.log")
        
        # Monitoring configuration
        self.monitoring = MonitoringConfig(
            apm_enabled=os.getenv("APM_ENABLED", "true").lower() == "true",
            otlp_endpoint=os.getenv("OTLP_ENDPOINT", "localhost:4317"),
            environment=os.getenv("ENVIRONMENT", "production"),
            slack_webhook=os.getenv("SLACK_WEBHOOK"),
            email_host=os.getenv("EMAIL_HOST", "smtp.gmail.com"),
            email_port=int(os.getenv("EMAIL_PORT", "587")),
            email_username=os.getenv("EMAIL_USERNAME", ""),
            email_password=os.getenv("EMAIL_PASSWORD", ""),
            email_recipients=os.getenv("EMAIL_RECIPIENTS", "").split(",")
        )
        
        # Security configuration
        self.security = SecurityConfig(
            rate_limit_requests_per_minute=int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60")),
            rate_limit_burst_limit=int(os.getenv("RATE_LIMIT_BURST_LIMIT", "10")),
            rate_limit_block_duration=int(os.getenv("RATE_LIMIT_BLOCK_DURATION", "300")),
            waf_enabled=os.getenv("WAF_ENABLED", "true").lower() == "true",
            audit_log_file=os.getenv("AUDIT_LOG_FILE", "audit.log"),
            security_headers_enabled=os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true",
            content_security_policy=os.getenv("CONTENT_SECURITY_POLICY", "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"),
            x_frame_options=os.getenv("X_FRAME_OPTIONS", "DENY"),
            x_content_type_options=os.getenv("X_CONTENT_TYPE_OPTIONS", "nosniff"),
            x_xss_protection=os.getenv("X_XSS_PROTECTION", "1; mode=block"),
            strict_transport_security=os.getenv("STRICT_TRANSPORT_SECURITY", "max-age=31536000; includeSubDomains"),
            referrer_policy=os.getenv("REFERRER_POLICY", "strict-origin-when-cross-origin"),
            permissions_policy=os.getenv("PERMISSIONS_POLICY", "geolocation=(), microphone=(), camera=()")
        )
        
        # Scaling configuration
        self.scaling = ScalingConfig()
        
        # Resource limits configuration
        self.resource_limits = ResourceLimitsConfig()
        
        # Cache configuration
        self.cache = CacheConfig()
        
        # Network configuration
        self.network = NetworkConfig()
        
        # Logging configuration
        self.logging = LoggingConfig()
        
        # Validate all settings
        self._validate_settings()
        
        # Setup logging
        self._setup_logging()

    def _get_required_env(self, key: str) -> str:
        """Get a required environment variable or raise an error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def _validate_int(self, key: str, default: int) -> int:
        """Validate and return an integer setting."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default

    def _validate_float(self, key: str, default: float) -> float:
        """Validate and return a float setting."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default

    def _validate_settings(self):
        """Validate all settings for consistency and reasonableness."""
        # Validate scraping intervals
        if self.scraping.interval_base < 3600:  # Less than 1 hour
            logger.warning("Scraping interval is very short (< 1 hour)")
        
        if self.scraping.interval_jitter > self.scraping.interval_base:
            logger.warning("Jitter is larger than base interval")
        
        # Validate resource limits
        if self.resources.max_cpu_usage > 0.95:
            logger.warning("CPU usage limit is very high (> 95%)")
        
        if self.resources.max_ram_mb < 512:
            logger.warning("RAM limit is very low (< 512MB)")
        
        # Validate learning parameters
        if self.learning.confidence_update > 1.0:
            logger.warning("Confidence update factor is > 1.0")
        
        if self.learning.confidence_discard_threshold > 0.5:
            logger.warning("Confidence discard threshold is very high (> 0.5)")

    def _setup_logging(self):
        """Configure logging settings."""
        logger.add(
            self.log_file,
            level=self.log_level
        )

    def get_randomized_interval(self) -> int:
        """Get a randomized interval for scraping with jitter."""
        jitter = random.uniform(-self.scraping.interval_jitter, self.scraping.interval_jitter)
        return max(3600, int(self.scraping.interval_base + jitter))  # Minimum 1 hour

    def get_proxy_url(self) -> str:
        """Get the complete proxy URL."""
        return self.proxy.url

    def get_backoff_time(self, attempt: int) -> int:
        """Calculate exponential backoff time."""
        return min(
            self.scraping.backoff_base * (2 ** attempt),
            3600  # Maximum 1 hour
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "database_url": self.SUPABASE_URL,
            "headless": self.proxy_enabled,
            "browser_timeout": self.session_timeout,
            "user_agent": self.proxy.username,
            "circuit_breaker_failure_threshold": self.circuit_breaker_failure_threshold,
            "circuit_breaker_recovery_timeout": self.circuit_breaker_recovery_timeout,
            "circuit_breaker_half_open_timeout": self.circuit_breaker_half_open_timeout,
            "circuit_breaker_success_threshold": self.circuit_breaker_success_threshold,
            "max_retries": self.scraping.max_retries,
            "retry_delay": self.retry_delay,
            "session_timeout": self.session_timeout,
            "session_file": self.session_file,
            "proxy_enabled": self.proxy_enabled,
            "proxy_url": self.proxy_url,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "monitoring": {
                "apm_enabled": self.monitoring.apm_enabled,
                "otlp_endpoint": self.monitoring.otlp_endpoint,
                "environment": self.monitoring.environment,
                "slack_webhook": self.monitoring.slack_webhook,
                "email_host": self.monitoring.email_host,
                "email_port": self.monitoring.email_port,
                "email_username": self.monitoring.email_username,
                "email_password": self.monitoring.email_password,
                "email_recipients": self.monitoring.email_recipients
            },
            "security": {
                "rate_limit_requests_per_minute": self.security.rate_limit_requests_per_minute,
                "rate_limit_burst_limit": self.security.rate_limit_burst_limit,
                "rate_limit_block_duration": self.security.rate_limit_block_duration,
                "waf_enabled": self.security.waf_enabled,
                "audit_log_file": self.security.audit_log_file,
                "security_headers_enabled": self.security.security_headers_enabled,
                "content_security_policy": self.security.content_security_policy,
                "x_frame_options": self.security.x_frame_options,
                "x_content_type_options": self.security.x_content_type_options,
                "x_xss_protection": self.security.x_xss_protection,
                "strict_transport_security": self.security.strict_transport_security,
                "referrer_policy": self.security.referrer_policy,
                "permissions_policy": self.security.permissions_policy
            },
            "scaling": {
                "min_instances": self.scaling.min_instances,
                "max_instances": self.scaling.max_instances,
                "target_cpu_percent": self.scaling.target_cpu_percent,
                "target_memory_percent": self.scaling.target_memory_percent,
                "scale_up_threshold": self.scaling.scale_up_threshold,
                "scale_down_threshold": self.scaling.scale_down_threshold,
                "cooldown_period": self.scaling.cooldown_period,
                "metrics_interval": self.scaling.metrics_interval
            },
            "resource_limits": {
                "max_cpu_percent": self.resource_limits.max_cpu_percent,
                "max_memory_percent": self.resource_limits.max_memory_percent,
                "max_memory_bytes": self.resource_limits.max_memory_bytes,
                "max_file_descriptors": self.resource_limits.max_file_descriptors,
                "max_threads": self.resource_limits.max_threads,
                "max_connections": self.resource_limits.max_connections
            },
            "cache": {
                "max_total_size": self.cache.max_total_size,
                "max_entry_size": self.cache.max_entry_size,
                "cleanup_interval": self.cache.cleanup_interval,
                "min_success_rate": self.cache.min_success_rate,
                "max_pattern_age_days": self.cache.max_pattern_age_days
            },
            "network": {
                "request_batch_size": self.network.request_batch_size,
                "compression_level": self.network.compression_level,
                "connection_timeout": self.network.connection_timeout,
                "max_retries": self.network.max_retries,
                "retry_delay": self.network.retry_delay,
                "max_concurrent_connections": self.network.max_concurrent_connections
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count
            }
        }

# Create a singleton instance
settings = Settings()

# Export commonly used settings for convenience
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
PROXY_URL = settings.get_proxy_url()
MAX_CONCURRENT_SCRAPES = settings.scraping.max_concurrent
REQUEST_TIMEOUT = settings.scraping.request_timeout
MAX_RETRIES = settings.scraping.max_retries
MAX_CPU_USAGE = settings.resources.max_cpu_usage
MAX_RAM_MB = settings.resources.max_ram_mb


