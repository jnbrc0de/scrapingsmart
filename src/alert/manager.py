from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from src.config.settings import settings

class AlertManager:
    """Gerencia alertas e notificações do sistema."""
    
    def __init__(self, notifier=None):
        self.notifier = notifier
        self._setup_logging()
        self._alert_history: Dict[str, List[Dict]] = {}
        self._cooldown_period = timedelta(minutes=30)
        self._last_alert: Dict[str, datetime] = {}
    
    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(settings.LOG_DIR / "alerts_{time}.log"),
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    async def send_alert(self, level: str, message: str, domain: str = None, event: str = None):
        """Envia um alerta com cooldown e histórico."""
        try:
            # Verifica cooldown
            if self._is_in_cooldown(domain, event):
                return
            
            # Prepara o alerta
            alert = {
                "level": level,
                "message": message,
                "domain": domain,
                "event": event,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Envia notificação
            if self.notifier:
                await self.notifier.send_notification(alert)
            
            # Atualiza histórico
            self._update_alert_history(alert)
            
            # Atualiza último alerta
            self._last_alert[f"{domain}:{event}"] = datetime.utcnow()
            
            logger.info(f"Alert sent: {message}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
    
    def _is_in_cooldown(self, domain: str, event: str) -> bool:
        """Verifica se o alerta está em período de cooldown."""
        if not domain or not event:
            return False
            
        key = f"{domain}:{event}"
        last_alert = self._last_alert.get(key)
        
        if not last_alert:
            return False
            
        return datetime.utcnow() - last_alert < self._cooldown_period
    
    def _update_alert_history(self, alert: Dict):
        """Atualiza o histórico de alertas."""
        domain = alert.get("domain", "global")
        if domain not in self._alert_history:
            self._alert_history[domain] = []
            
        self._alert_history[domain].append(alert)
        
        # Mantém apenas os últimos 100 alertas por domínio
        if len(self._alert_history[domain]) > 100:
            self._alert_history[domain] = self._alert_history[domain][-100:]
    
    def get_alert_history(self, domain: str = None) -> List[Dict]:
        """Retorna o histórico de alertas."""
        if domain:
            return self._alert_history.get(domain, [])
        return [alert for alerts in self._alert_history.values() for alert in alerts]
    
    def clear_alert_history(self, domain: str = None):
        """Limpa o histórico de alertas."""
        if domain:
            self._alert_history.pop(domain, None)
        else:
            self._alert_history.clear()
    
    async def cleanup(self):
        """Limpa recursos do alert manager."""
        if self.notifier:
            self.notifier.cleanup() 