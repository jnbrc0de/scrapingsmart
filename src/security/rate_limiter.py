from typing import Dict, Optional
import time
import asyncio
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    burst_limit: int = 10
    block_duration: int = 300  # 5 minutes in seconds

class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._ip_requests: Dict[str, list] = {}
        self._ip_blocks: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, ip: str) -> bool:
        """Check if an IP is allowed to make a request."""
        async with self._lock:
            # Check if IP is blocked
            if ip in self._ip_blocks:
                if datetime.utcnow() < self._ip_blocks[ip]:
                    logger.warning(f"IP {ip} is blocked until {self._ip_blocks[ip]}")
                    return False
                else:
                    del self._ip_blocks[ip]

            # Initialize request history for new IPs
            if ip not in self._ip_requests:
                self._ip_requests[ip] = []

            # Clean old requests
            now = time.time()
            self._ip_requests[ip] = [
                req_time for req_time in self._ip_requests[ip]
                if now - req_time < 60
            ]

            # Check rate limit
            if len(self._ip_requests[ip]) >= self.config.requests_per_minute:
                logger.warning(f"Rate limit exceeded for IP {ip}")
                self._ip_blocks[ip] = datetime.utcnow() + timedelta(seconds=self.config.block_duration)
                return False

            # Check burst limit
            recent_requests = [
                req_time for req_time in self._ip_requests[ip]
                if now - req_time < 1
            ]
            if len(recent_requests) >= self.config.burst_limit:
                logger.warning(f"Burst limit exceeded for IP {ip}")
                return False

            # Add new request
            self._ip_requests[ip].append(now)
            return True

    async def get_ip_stats(self, ip: str) -> Dict:
        """Get statistics for an IP address."""
        async with self._lock:
            now = time.time()
            requests = self._ip_requests.get(ip, [])
            recent_requests = [req for req in requests if now - req < 60]
            
            return {
                "requests_last_minute": len(recent_requests),
                "is_blocked": ip in self._ip_blocks,
                "block_until": self._ip_blocks.get(ip),
                "total_requests": len(requests)
            }

    async def cleanup(self):
        """Clean up old request records."""
        async with self._lock:
            now = time.time()
            for ip in list(self._ip_requests.keys()):
                self._ip_requests[ip] = [
                    req_time for req_time in self._ip_requests[ip]
                    if now - req_time < 60
                ]
                if not self._ip_requests[ip]:
                    del self._ip_requests[ip]

            # Clean up expired blocks
            for ip in list(self._ip_blocks.keys()):
                if datetime.utcnow() >= self._ip_blocks[ip]:
                    del self._ip_blocks[ip] 