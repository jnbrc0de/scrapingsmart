from typing import Dict, Any
from dataclasses import dataclass
import os

@dataclass
class EnvironmentConfig:
    name: str
    database_url: str
    redis_url: str
    log_level: str
    debug: bool
    max_instances: int
    resource_limits: Dict[str, Any]
    monitoring: Dict[str, Any]

class EnvironmentManager:
    def __init__(self):
        self._environments: Dict[str, EnvironmentConfig] = {
            "development": EnvironmentConfig(
                name="development",
                database_url="postgresql://postgres:postgres@localhost:5432/scraper_dev",
                redis_url="redis://localhost:6379/0",
                log_level="DEBUG",
                debug=True,
                max_instances=2,
                resource_limits={
                    "max_cpu_percent": 50.0,
                    "max_memory_percent": 50.0,
                    "max_memory_bytes": 1024 * 1024 * 1024,  # 1GB
                    "max_file_descriptors": 1024,
                    "max_threads": 50,
                    "max_connections": 100
                },
                monitoring={
                    "metrics_interval": 30,
                    "alert_threshold": 80.0
                }
            ),
            "staging": EnvironmentConfig(
                name="staging",
                database_url=os.getenv("STAGING_DATABASE_URL"),
                redis_url=os.getenv("STAGING_REDIS_URL"),
                log_level="INFO",
                debug=False,
                max_instances=3,
                resource_limits={
                    "max_cpu_percent": 70.0,
                    "max_memory_percent": 70.0,
                    "max_memory_bytes": 2 * 1024 * 1024 * 1024,  # 2GB
                    "max_file_descriptors": 2048,
                    "max_threads": 100,
                    "max_connections": 500
                },
                monitoring={
                    "metrics_interval": 60,
                    "alert_threshold": 85.0
                }
            ),
            "production": EnvironmentConfig(
                name="production",
                database_url=os.getenv("PROD_DATABASE_URL"),
                redis_url=os.getenv("PROD_REDIS_URL"),
                log_level="WARNING",
                debug=False,
                max_instances=5,
                resource_limits={
                    "max_cpu_percent": 80.0,
                    "max_memory_percent": 80.0,
                    "max_memory_bytes": 4 * 1024 * 1024 * 1024,  # 4GB
                    "max_file_descriptors": 4096,
                    "max_threads": 200,
                    "max_connections": 1000
                },
                monitoring={
                    "metrics_interval": 30,
                    "alert_threshold": 90.0
                }
            )
        }

    def get_environment(self, name: str) -> EnvironmentConfig:
        """Get configuration for a specific environment."""
        if name not in self._environments:
            raise ValueError(f"Unknown environment: {name}")
        return self._environments[name]

    def get_current_environment(self) -> EnvironmentConfig:
        """Get configuration for the current environment."""
        env_name = os.getenv("ENVIRONMENT", "development")
        return self.get_environment(env_name)

    def validate_environment(self, name: str) -> bool:
        """Validate if an environment configuration is complete."""
        try:
            config = self.get_environment(name)
            required_vars = [
                "database_url",
                "redis_url",
                "log_level",
                "max_instances"
            ]
            
            # Check required variables
            for var in required_vars:
                if not getattr(config, var):
                    return False
            
            # Check resource limits
            if not config.resource_limits:
                return False
            
            # Check monitoring config
            if not config.monitoring:
                return False
            
            return True
        except Exception:
            return False

    def get_environment_variables(self, name: str) -> Dict[str, str]:
        """Get environment variables for a specific environment."""
        config = self.get_environment(name)
        return {
            "ENVIRONMENT": config.name,
            "DATABASE_URL": config.database_url,
            "REDIS_URL": config.redis_url,
            "LOG_LEVEL": config.log_level,
            "DEBUG": str(config.debug).lower(),
            "MAX_INSTANCES": str(config.max_instances),
            "MAX_CPU_PERCENT": str(config.resource_limits["max_cpu_percent"]),
            "MAX_MEMORY_PERCENT": str(config.resource_limits["max_memory_percent"]),
            "MAX_MEMORY_BYTES": str(config.resource_limits["max_memory_bytes"]),
            "MAX_FILE_DESCRIPTORS": str(config.resource_limits["max_file_descriptors"]),
            "MAX_THREADS": str(config.resource_limits["max_threads"]),
            "MAX_CONNECTIONS": str(config.resource_limits["max_connections"]),
            "METRICS_INTERVAL": str(config.monitoring["metrics_interval"]),
            "ALERT_THRESHOLD": str(config.monitoring["alert_threshold"])
        } 