from typing import Dict, Optional
import asyncio
import logging
import psutil
import resource
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ResourceLimits:
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 80.0
    max_memory_bytes: Optional[int] = None
    max_file_descriptors: int = 1024
    max_threads: int = 100
    max_connections: int = 1000

class ResourceManager:
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self._lock = asyncio.Lock()
        self._violations: Dict[str, datetime] = {}
        self._setup_limits()

    def _setup_limits(self):
        """Set up system resource limits."""
        try:
            # Set file descriptor limit
            resource.setrlimit(resource.RLIMIT_NOFILE, 
                             (self.limits.max_file_descriptors, 
                              self.limits.max_file_descriptors))
            
            # Set memory limit if specified
            if self.limits.max_memory_bytes:
                resource.setrlimit(resource.RLIMIT_AS,
                                 (self.limits.max_memory_bytes,
                                  self.limits.max_memory_bytes))
            
            logger.info("Resource limits set successfully")
        except Exception as e:
            logger.error(f"Error setting resource limits: {e}")

    async def check_limits(self) -> Dict[str, bool]:
        """Check if current resource usage is within limits."""
        async with self._lock:
            current_usage = self._get_current_usage()
            violations = {}
            
            # Check CPU usage
            if current_usage["cpu_percent"] > self.limits.max_cpu_percent:
                violations["cpu"] = True
                self._record_violation("cpu")
            
            # Check memory usage
            if current_usage["memory_percent"] > self.limits.max_memory_percent:
                violations["memory"] = True
                self._record_violation("memory")
            
            # Check file descriptors
            if current_usage["file_descriptors"] > self.limits.max_file_descriptors:
                violations["file_descriptors"] = True
                self._record_violation("file_descriptors")
            
            # Check threads
            if current_usage["threads"] > self.limits.max_threads:
                violations["threads"] = True
                self._record_violation("threads")
            
            # Check connections
            if current_usage["connections"] > self.limits.max_connections:
                violations["connections"] = True
                self._record_violation("connections")
            
            return violations

    def _get_current_usage(self) -> Dict[str, float]:
        """Get current resource usage."""
        process = psutil.Process()
        
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "file_descriptors": len(process.open_files()),
            "threads": process.num_threads(),
            "connections": len(process.connections())
        }

    def _record_violation(self, resource_type: str):
        """Record a resource limit violation."""
        self._violations[resource_type] = datetime.utcnow()
        logger.warning(f"Resource limit violation: {resource_type}")

    async def get_violations(self) -> Dict[str, str]:
        """Get recent resource limit violations."""
        async with self._lock:
            return {
                resource_type: timestamp.isoformat()
                for resource_type, timestamp in self._violations.items()
            }

    async def get_usage(self) -> Dict[str, float]:
        """Get current resource usage."""
        async with self._lock:
            return self._get_current_usage()

    async def cleanup(self):
        """Clean up resources."""
        # Reset resource limits to system defaults
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (-1, -1))
            resource.setrlimit(resource.RLIMIT_AS, (-1, -1))
            logger.info("Resource limits reset to system defaults")
        except Exception as e:
            logger.error(f"Error resetting resource limits: {e}") 