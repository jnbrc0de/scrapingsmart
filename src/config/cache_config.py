from typing import Dict, Any
import os

# Redis configuration
REDIS_CONFIG = {
    'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'max_connections': 100,
    'timeout': 20,
    'retry_on_timeout': True
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