from prometheus_client import Counter, Histogram, Gauge, start_http_server
import psutil
import time
from typing import Dict, Any
from functools import wraps
from .logger import centralized_logger
from .alerts import alert_manager

# Métricas Prometheus
REQUEST_COUNT = Counter(
    'app_request_count',
    'Total de requisições',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'app_request_latency_seconds',
    'Latência das requisições',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'app_error_count',
    'Total de erros',
    ['type', 'endpoint']
)

CPU_USAGE = Gauge(
    'app_cpu_usage_percent',
    'Uso de CPU em percentual'
)

MEMORY_USAGE = Gauge(
    'app_memory_usage_bytes',
    'Uso de memória em bytes'
)

DISK_USAGE = Gauge(
    'app_disk_usage_bytes',
    'Uso de disco em bytes'
)

class PerformanceMonitor:
    def __init__(self, port: int = 8000):
        self.port = port
        self.start_prometheus_server()
        self.start_resource_monitoring()

    def start_prometheus_server(self):
        """Inicia o servidor Prometheus."""
        try:
            start_http_server(self.port)
            centralized_logger.log_info("Servidor Prometheus iniciado", {"port": self.port})
        except Exception as e:
            centralized_logger.log_error(e, {"context": "start_prometheus_server"})

    def start_resource_monitoring(self):
        """Inicia o monitoramento de recursos do sistema."""
        try:
            while True:
                self.update_resource_metrics()
                time.sleep(60)  # Atualiza a cada minuto
        except Exception as e:
            centralized_logger.log_error(e, {"context": "resource_monitoring"})

    def update_resource_metrics(self):
        """Atualiza as métricas de recursos do sistema."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent()
            CPU_USAGE.set(cpu_percent)

            # Memória
            memory = psutil.virtual_memory()
            MEMORY_USAGE.set(memory.used)

            # Disco
            disk = psutil.disk_usage('/')
            DISK_USAGE.set(disk.used)

            # Verifica limites
            self._check_resource_limits(cpu_percent, memory.percent, disk.percent)

        except Exception as e:
            centralized_logger.log_error(e, {"context": "update_resource_metrics"})

    def _check_resource_limits(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Verifica se os recursos estão dentro dos limites."""
        if cpu_percent > 80:
            alert_manager.send_alert(
                title="Alto uso de CPU",
                message=f"CPU está em {cpu_percent}%",
                severity="warning",
                context={"cpu_percent": cpu_percent}
            )

        if memory_percent > 80:
            alert_manager.send_alert(
                title="Alto uso de memória",
                message=f"Memória está em {memory_percent}%",
                severity="warning",
                context={"memory_percent": memory_percent}
            )

        if disk_percent > 80:
            alert_manager.send_alert(
                title="Alto uso de disco",
                message=f"Disco está em {disk_percent}%",
                severity="warning",
                context={"disk_percent": disk_percent}
            )

def monitor_performance(func):
    """Decorator para monitorar performance de funções."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            status = "success"
            return result
        except Exception as e:
            status = "error"
            ERROR_COUNT.labels(type=type(e).__name__, endpoint=func.__name__).inc()
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=kwargs.get('method', 'unknown'),
                endpoint=func.__name__,
                status=status
            ).inc()
            REQUEST_LATENCY.labels(
                method=kwargs.get('method', 'unknown'),
                endpoint=func.__name__
            ).observe(duration)

            # Log de performance
            centralized_logger.log_performance(
                operation=func.__name__,
                duration=duration,
                metadata={
                    "method": kwargs.get('method', 'unknown'),
                    "status": status
                }
            )
    return wrapper

# Instância global do monitor de performance
performance_monitor = PerformanceMonitor() 