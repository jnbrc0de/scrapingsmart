import os
import json
import time
import asyncio
import psutil
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from loguru import logger
from src.config.settings import settings

@dataclass
class ScrapeMetrics:
    domain: str
    strategy: str
    load_time_ms: float
    extraction_time_ms: float
    outcome: str
    cpu_pct: float
    ram_mb: float
    connections: int
    network_bytes_tx: int
    network_bytes_rx: int
    timestamp: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_total: float
    cpu_per_core: List[float]
    ram_total: float
    ram_used: float
    ram_per_process: Dict[str, float]
    network_connections: int
    network_bytes_tx: int
    network_bytes_rx: int
    process_count: int

class MetricsCollector:
    def __init__(self, db, notifier):
        """Initialize the metrics collector with dependencies."""
        self.db = db
        self.notifier = notifier
        self.timers: Dict[str, float] = {}
        self.metrics_buffer: List[ScrapeMetrics] = []
        self.system_metrics_buffer: List[SystemMetrics] = []
        self._setup_logging()
        self._setup_directories()
        self.monitoring_task = None

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            "logs/metrics_{time}.log",
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    def _setup_directories(self):
        """Create necessary directories for metrics storage."""
        os.makedirs("logs/metrics", exist_ok=True)

    async def start_timer(self, step: str):
        """Start timing a specific step."""
        self.timers[step] = time.time()

    async def stop_timer(self, step: str) -> float:
        """Stop timing a step and return elapsed time in milliseconds."""
        if step not in self.timers:
            return 0.0
        elapsed = (time.time() - self.timers[step]) * 1000
        del self.timers[step]
        return elapsed

    async def register_scrape_metrics(
        self,
        domain: str,
        strategy: str,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register metrics for a scraping operation."""
        try:
            # Get timing metrics
            load_time = await self.stop_timer("load")
            extraction_time = await self.stop_timer("extract")
            
            # Get system metrics
            system_metrics = await self._get_current_system_metrics()
            
            # Create metrics object
            metrics = ScrapeMetrics(
                domain=domain,
                strategy=strategy,
                load_time_ms=load_time,
                extraction_time_ms=extraction_time,
                outcome=outcome,
                cpu_pct=system_metrics.cpu_total,
                ram_mb=system_metrics.ram_used,
                connections=system_metrics.network_connections,
                network_bytes_tx=system_metrics.network_bytes_tx,
                network_bytes_rx=system_metrics.network_bytes_rx,
                timestamp=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Add to buffer
            self.metrics_buffer.append(metrics)
            
            # Export if buffer is full
            if len(self.metrics_buffer) >= settings.METRICS_BUFFER_SIZE:
                await self._export_metrics()
            
            # Check for anomalies
            await self._check_metrics_anomalies(metrics)
            
        except Exception as e:
            logger.error(f"Error registering scrape metrics: {str(e)}")

    async def _get_current_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
            cpu_total = sum(cpu_percent) / len(cpu_percent)
            
            # RAM metrics
            ram = psutil.virtual_memory()
            ram_per_process = {}
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    if proc.info['name'] in ['python', 'chromium']:
                        ram_per_process[proc.info['name']] = proc.info['memory_percent']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Network metrics
            net_io = psutil.net_io_counters()
            connections = len(psutil.net_connections())
            
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_total=cpu_total,
                cpu_per_core=cpu_percent,
                ram_total=ram.total / (1024 * 1024),  # Convert to MB
                ram_used=ram.used / (1024 * 1024),
                ram_per_process=ram_per_process,
                network_connections=connections,
                network_bytes_tx=net_io.bytes_sent,
                network_bytes_rx=net_io.bytes_recv,
                process_count=len(psutil.pids())
            )
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_total=0.0,
                cpu_per_core=[],
                ram_total=0.0,
                ram_used=0.0,
                ram_per_process={},
                network_connections=0,
                network_bytes_tx=0,
                network_bytes_rx=0,
                process_count=0
            )

    async def start_monitoring(self):
        """Start periodic system monitoring."""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitor_system())

    async def stop_monitoring(self):
        """Stop system monitoring."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None

    async def _monitor_system(self):
        """Monitor system metrics periodically."""
        try:
            while True:
                metrics = await self._get_current_system_metrics()
                self.system_metrics_buffer.append(metrics)
                
                # Check for system anomalies
                await self._check_system_anomalies(metrics)
                
                # Export if buffer is full
                if len(self.system_metrics_buffer) >= settings.SYSTEM_METRICS_BUFFER_SIZE:
                    await self._export_system_metrics()
                
                await asyncio.sleep(settings.SYSTEM_METRICS_INTERVAL)
                
        except asyncio.CancelledError:
            # Export any remaining metrics
            await self._export_system_metrics()
        except Exception as e:
            logger.error(f"Error in system monitoring: {str(e)}")

    async def _check_system_anomalies(self, metrics: SystemMetrics):
        """Check for system anomalies and send alerts."""
        try:
            # Check CPU usage
            if metrics.cpu_total > settings.CPU_ALERT_THRESHOLD:
                await self.notifier.send_alert(
                    level="warning",
                    message=f"High CPU usage: {metrics.cpu_total}%",
                    url="system",
                    domain="system",
                    event="high_cpu",
                    context={
                        "cpu_total": metrics.cpu_total,
                        "cpu_per_core": metrics.cpu_per_core
                    }
                )
            
            # Check RAM usage
            if metrics.ram_used / metrics.ram_total > settings.RAM_ALERT_THRESHOLD:
                await self.notifier.send_alert(
                    level="warning",
                    message=f"High RAM usage: {metrics.ram_used / metrics.ram_total * 100}%",
                    url="system",
                    domain="system",
                    event="high_ram",
                    context={
                        "ram_used": metrics.ram_used,
                        "ram_total": metrics.ram_total,
                        "ram_per_process": metrics.ram_per_process
                    }
                )
            
            # Check connection count
            if metrics.network_connections > settings.MAX_CONNECTIONS:
                await self.notifier.send_alert(
                    level="warning",
                    message=f"High connection count: {metrics.network_connections}",
                    url="system",
                    domain="system",
                    event="high_connections",
                    context={
                        "connections": metrics.network_connections
                    }
                )
            
        except Exception as e:
            logger.error(f"Error checking system anomalies: {str(e)}")

    async def _check_metrics_anomalies(self, metrics: ScrapeMetrics):
        """Check for scraping metrics anomalies and send alerts."""
        try:
            # Check load time
            if metrics.load_time_ms > settings.MAX_LOAD_TIME:
                await self.notifier.send_alert(
                    level="warning",
                    message=f"Slow page load: {metrics.load_time_ms}ms",
                    url=metrics.domain,
                    domain=metrics.domain,
                    event="slow_load",
                    context={
                        "load_time": metrics.load_time_ms,
                        "strategy": metrics.strategy
                    }
                )
            
            # Check extraction time
            if metrics.extraction_time_ms > settings.MAX_EXTRACTION_TIME:
                await self.notifier.send_alert(
                    level="warning",
                    message=f"Slow extraction: {metrics.extraction_time_ms}ms",
                    url=metrics.domain,
                    domain=metrics.domain,
                    event="slow_extraction",
                    context={
                        "extraction_time": metrics.extraction_time_ms,
                        "strategy": metrics.strategy
                    }
                )
            
            # Check for failed scrapes
            if metrics.outcome != "success":
                await self.notifier.send_alert(
                    level="error",
                    message=f"Scrape failed: {metrics.outcome}",
                    url=metrics.domain,
                    domain=metrics.domain,
                    event="scrape_failed",
                    context={
                        "outcome": metrics.outcome,
                        "strategy": metrics.strategy,
                        "load_time": metrics.load_time_ms,
                        "extraction_time": metrics.extraction_time_ms
                    }
                )
            
        except Exception as e:
            logger.error(f"Error checking metrics anomalies: {str(e)}")

    async def _export_metrics(self):
        """Export metrics to database and local storage."""
        try:
            if not self.metrics_buffer:
                return
            
            # Export to database
            for metrics in self.metrics_buffer:
                await self.db.insert_scrape_metrics(
                    domain=metrics.domain,
                    strategy=metrics.strategy,
                    load_time_ms=metrics.load_time_ms,
                    extraction_time_ms=metrics.extraction_time_ms,
                    outcome=metrics.outcome,
                    cpu_pct=metrics.cpu_pct,
                    ram_mb=metrics.ram_mb,
                    connections=metrics.connections,
                    network_bytes_tx=metrics.network_bytes_tx,
                    network_bytes_rx=metrics.network_bytes_rx,
                    timestamp=metrics.timestamp,
                    metadata=metrics.metadata
                )
            
            # Export to local file
            async with aiofiles.open(
                f"logs/metrics/scrape_metrics_{datetime.utcnow().strftime('%Y%m%d')}.jsonl",
                mode='a'
            ) as f:
                for metrics in self.metrics_buffer:
                    await f.write(json.dumps(metrics.__dict__) + '\n')
            
            # Clear buffer
            self.metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {str(e)}")

    async def _export_system_metrics(self):
        """Export system metrics to database and local storage."""
        try:
            if not self.system_metrics_buffer:
                return
            
            # Export to database
            for metrics in self.system_metrics_buffer:
                await self.db.insert_system_metrics(
                    timestamp=metrics.timestamp,
                    cpu_total=metrics.cpu_total,
                    cpu_per_core=metrics.cpu_per_core,
                    ram_total=metrics.ram_total,
                    ram_used=metrics.ram_used,
                    ram_per_process=metrics.ram_per_process,
                    network_connections=metrics.network_connections,
                    network_bytes_tx=metrics.network_bytes_tx,
                    network_bytes_rx=metrics.network_bytes_rx,
                    process_count=metrics.process_count
                )
            
            # Export to local file
            async with aiofiles.open(
                f"logs/metrics/system_metrics_{datetime.utcnow().strftime('%Y%m%d')}.jsonl",
                mode='a'
            ) as f:
                for metrics in self.system_metrics_buffer:
                    await f.write(json.dumps(metrics.__dict__) + '\n')
            
            # Clear buffer
            self.system_metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error exporting system metrics: {str(e)}")

    async def get_domain_stats(self, domain: str, days: int = 7) -> Dict[str, Any]:
        """Get statistics for a specific domain."""
        try:
            # Get metrics from database
            metrics = await self.db.get_domain_metrics(domain, days)
            
            # Calculate statistics
            stats = {
                "total_scrapes": len(metrics),
                "success_rate": sum(1 for m in metrics if m["outcome"] == "success") / len(metrics) if metrics else 0,
                "avg_load_time": sum(m["load_time_ms"] for m in metrics) / len(metrics) if metrics else 0,
                "avg_extraction_time": sum(m["extraction_time_ms"] for m in metrics) / len(metrics) if metrics else 0,
                "strategy_success": {},
                "hourly_success": {},
                "errors": {}
            }
            
            # Calculate strategy success rates
            for metric in metrics:
                strategy = metric["strategy"]
                if strategy not in stats["strategy_success"]:
                    stats["strategy_success"][strategy] = {"success": 0, "total": 0}
                stats["strategy_success"][strategy]["total"] += 1
                if metric["outcome"] == "success":
                    stats["strategy_success"][strategy]["success"] += 1
            
            # Calculate hourly success rates
            for metric in metrics:
                hour = metric["timestamp"].hour
                if hour not in stats["hourly_success"]:
                    stats["hourly_success"][hour] = {"success": 0, "total": 0}
                stats["hourly_success"][hour]["total"] += 1
                if metric["outcome"] == "success":
                    stats["hourly_success"][hour]["success"] += 1
            
            # Count errors
            for metric in metrics:
                if metric["outcome"] != "success":
                    if metric["outcome"] not in stats["errors"]:
                        stats["errors"][metric["outcome"]] = 0
                    stats["errors"][metric["outcome"]] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting domain stats: {str(e)}")
            return {}

if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize dependencies (replace with actual implementations)
        db = None
        notifier = None
        
        collector = MetricsCollector(db, notifier)
        
        # Start monitoring
        await collector.start_monitoring()
        
        # Example metrics collection
        await collector.start_timer("load")
        # Simulate page load
        await asyncio.sleep(1)
        await collector.start_timer("extract")
        # Simulate extraction
        await asyncio.sleep(0.5)
        
        await collector.register_scrape_metrics(
            domain="example.com",
            strategy="css",
            outcome="success"
        )
        
        # Get domain stats
        stats = await collector.get_domain_stats("example.com")
        
        # Stop monitoring
        await collector.stop_monitoring()
    
    import asyncio
    asyncio.run(main())
