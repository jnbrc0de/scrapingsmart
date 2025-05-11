import asyncio
import aiohttp
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .logger import centralized_logger
from .alerts import alert_manager

class HealthCheck:
    def __init__(self, name: str, url: str, interval: int = 60):
        self.name = name
        self.url = url
        self.interval = interval
        self.last_check = None
        self.last_status = None
        self.consecutive_failures = 0
        self.total_checks = 0
        self.total_failures = 0

    async def check(self) -> bool:
        """Realiza o health check."""
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(self.url) as response:
                    duration = time.time() - start_time
                    self.last_check = datetime.utcnow()
                    self.last_status = response.status
                    self.total_checks += 1

                    if response.status == 200:
                        self.consecutive_failures = 0
                        return True
                    else:
                        self.consecutive_failures += 1
                        self.total_failures += 1
                        return False

        except Exception as e:
            self.consecutive_failures += 1
            self.total_failures += 1
            self.last_check = datetime.utcnow()
            self.last_status = None
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do health check."""
        return {
            "name": self.name,
            "url": self.url,
            "last_check": self.last_check,
            "last_status": self.last_status,
            "consecutive_failures": self.consecutive_failures,
            "total_checks": self.total_checks,
            "total_failures": self.total_failures,
            "success_rate": ((self.total_checks - self.total_failures) / self.total_checks * 100) if self.total_checks > 0 else 0
        }

class UptimeMonitor:
    def __init__(self):
        self.health_checks: List[HealthCheck] = []
        self.running = False
        self._setup_default_checks()

    def _setup_default_checks(self):
        """Configura health checks padrão."""
        self.add_health_check(
            name="API",
            url="http://localhost:8000/health",
            interval=30
        )
        self.add_health_check(
            name="Database",
            url="http://localhost:8000/health/db",
            interval=60
        )
        self.add_health_check(
            name="Redis",
            url="http://localhost:8000/health/redis",
            interval=60
        )

    def add_health_check(self, name: str, url: str, interval: int = 60):
        """Adiciona um novo health check."""
        self.health_checks.append(HealthCheck(name, url, interval))

    async def start_monitoring(self):
        """Inicia o monitoramento de uptime."""
        self.running = True
        while self.running:
            for check in self.health_checks:
                if not check.last_check or (datetime.utcnow() - check.last_check).total_seconds() >= check.interval:
                    await self._run_check(check)
            await asyncio.sleep(1)

    async def _run_check(self, check: HealthCheck):
        """Executa um health check específico."""
        is_healthy = await check.check()
        
        if not is_healthy:
            # Envia alerta após 3 falhas consecutivas
            if check.consecutive_failures >= 3:
                alert_manager.send_alert(
                    title=f"Falha no Health Check: {check.name}",
                    message=f"Serviço {check.name} está indisponível. {check.consecutive_failures} falhas consecutivas.",
                    severity="critical",
                    context=check.get_stats()
                )

            # Log do erro
            centralized_logger.log_error(
                Exception(f"Health check failed for {check.name}"),
                check.get_stats()
            )

    def stop_monitoring(self):
        """Para o monitoramento de uptime."""
        self.running = False

    def get_status(self) -> Dict[str, Any]:
        """Retorna o status atual de todos os health checks."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [check.get_stats() for check in self.health_checks]
        }

# Instância global do monitor de uptime
uptime_monitor = UptimeMonitor() 