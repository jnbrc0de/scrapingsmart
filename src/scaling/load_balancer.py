from typing import Dict, List, Optional
import asyncio
import logging
import psutil
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ResourceMetrics:
    cpu_percent: float
    memory_percent: float
    active_connections: int
    queue_size: int
    timestamp: datetime

@dataclass
class ScalingConfig:
    min_instances: int = 1
    max_instances: int = 5
    target_cpu_percent: float = 70.0
    target_memory_percent: float = 70.0
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 30.0
    cooldown_period: int = 300  # 5 minutes
    metrics_interval: int = 60  # 1 minute

class LoadBalancer:
    def __init__(self, config: ScalingConfig):
        self.config = config
        self._metrics_history: List[ResourceMetrics] = []
        self._last_scale_time: Optional[datetime] = None
        self._active_instances: int = config.min_instances
        self._lock = asyncio.Lock()
        self._running = False
        self._metrics_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the load balancer monitoring."""
        self._running = True
        self._metrics_task = asyncio.create_task(self._collect_metrics())
        logger.info("Load balancer started")

    async def stop(self):
        """Stop the load balancer monitoring."""
        self._running = False
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        logger.info("Load balancer stopped")

    async def _collect_metrics(self):
        """Collect system metrics periodically."""
        while self._running:
            try:
                metrics = ResourceMetrics(
                    cpu_percent=psutil.cpu_percent(),
                    memory_percent=psutil.virtual_memory().percent,
                    active_connections=self._get_active_connections(),
                    queue_size=self._get_queue_size(),
                    timestamp=datetime.utcnow()
                )
                
                async with self._lock:
                    self._metrics_history.append(metrics)
                    # Keep only last hour of metrics
                    cutoff = datetime.utcnow() - timedelta(hours=1)
                    self._metrics_history = [
                        m for m in self._metrics_history
                        if m.timestamp > cutoff
                    ]
                
                await self._check_scaling()
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            await asyncio.sleep(self.config.metrics_interval)

    def _get_active_connections(self) -> int:
        """Get number of active connections."""
        # TODO: Implement actual connection counting
        return len(psutil.Process().connections())

    def _get_queue_size(self) -> int:
        """Get current queue size."""
        # TODO: Implement actual queue size monitoring
        return 0

    async def _check_scaling(self):
        """Check if scaling is needed based on metrics."""
        if not self._metrics_history:
            return

        async with self._lock:
            # Check cooldown period
            if self._last_scale_time:
                if datetime.utcnow() - self._last_scale_time < timedelta(seconds=self.config.cooldown_period):
                    return

            # Calculate average metrics
            recent_metrics = [
                m for m in self._metrics_history
                if datetime.utcnow() - m.timestamp < timedelta(minutes=5)
            ]
            
            if not recent_metrics:
                return

            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            
            # Check if scaling is needed
            if (avg_cpu > self.config.scale_up_threshold or 
                avg_memory > self.config.scale_up_threshold):
                if self._active_instances < self.config.max_instances:
                    await self._scale_up()
            
            elif (avg_cpu < self.config.scale_down_threshold and 
                  avg_memory < self.config.scale_down_threshold):
                if self._active_instances > self.config.min_instances:
                    await self._scale_down()

    async def _scale_up(self):
        """Scale up the number of instances."""
        try:
            # TODO: Implement actual instance creation
            self._active_instances += 1
            self._last_scale_time = datetime.utcnow()
            logger.info(f"Scaling up to {self._active_instances} instances")
        except Exception as e:
            logger.error(f"Error scaling up: {e}")

    async def _scale_down(self):
        """Scale down the number of instances."""
        try:
            # TODO: Implement actual instance termination
            self._active_instances -= 1
            self._last_scale_time = datetime.utcnow()
            logger.info(f"Scaling down to {self._active_instances} instances")
        except Exception as e:
            logger.error(f"Error scaling down: {e}")

    async def get_metrics(self) -> Dict:
        """Get current metrics and scaling status."""
        async with self._lock:
            if not self._metrics_history:
                return {
                    "active_instances": self._active_instances,
                    "metrics": None
                }
            
            latest = self._metrics_history[-1]
            return {
                "active_instances": self._active_instances,
                "metrics": {
                    "cpu_percent": latest.cpu_percent,
                    "memory_percent": latest.memory_percent,
                    "active_connections": latest.active_connections,
                    "queue_size": latest.queue_size,
                    "timestamp": latest.timestamp.isoformat()
                }
            }

    async def cleanup(self):
        """Clean up resources."""
        await self.stop() 