import os
import json
import asyncio
import smtplib
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from loguru import logger
from playwright.async_api import Page
from src.config.settings import settings

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AlertContext:
    http_code: Optional[int] = None
    retry_count: int = 0
    extracted_html: Optional[str] = None
    screenshot_path: Optional[str] = None
    stacktrace: Optional[str] = None
    proxy_used: Optional[str] = None
    fingerprint: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    resource_usage: Optional[Dict[str, float]] = None
    last_valid_price: Optional[float] = None
    price_variation: Optional[float] = None

@dataclass
class Alert:
    timestamp: datetime
    url: str
    domain: str
    event: str
    level: AlertLevel
    context: AlertContext
    resolution: Optional[str] = None

class AlertNotifier:
    def __init__(self, db):
        """Initialize the alert notifier with dependencies."""
        self.db = db
        self.alert_history: Dict[str, List[Alert]] = {}
        self.domain_alerts: Dict[str, List[Alert]] = {}
        self.cool_off_urls: Set[str] = set()
        self._setup_logging()
        self._setup_directories()

    def _setup_logging(self):
        """Configure logging with loguru."""
        # Configure different log files for each level
        for level in AlertLevel:
            logger.add(
                f"logs/{level.value}.log",
                rotation=settings.LOG_ROTATION_SIZE,
                retention=f"{settings.LOG_RETENTION_DAYS} days",
                level=level.value.upper(),
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
            )

    def _setup_directories(self):
        """Create necessary directories for logs and screenshots."""
        os.makedirs("logs/html", exist_ok=True)
        os.makedirs("logs/screenshots", exist_ok=True)

    async def send_alert(
        self,
        level: AlertLevel,
        message: str,
        url: str,
        domain: str,
        event: str,
        context: Optional[Dict[str, Any]] = None,
        resolution: Optional[str] = None
    ):
        """Send an alert through appropriate channels based on level."""
        try:
            # Create alert context
            alert_context = AlertContext(**(context or {}))
            
            # Create alert object
            alert = Alert(
                timestamp=datetime.utcnow(),
                url=url,
                domain=domain,
                event=event,
                level=level,
                context=alert_context,
                resolution=resolution
            )
            
            # Check if we should debounce this alert
            if await self._should_debounce_alert(alert):
                return
            
            # Log the alert
            await self._log_alert(alert)
            
            # Store in history
            self._store_alert(alert)
            
            # Send notifications based on level
            if level == AlertLevel.CRITICAL:
                await self._send_critical_alert(alert)
            elif level == AlertLevel.ERROR:
                await self._send_error_alert(alert)
            elif level == AlertLevel.WARNING:
                await self._send_warning_alert(alert)
            
            # Store in database
            await self._store_alert_in_db(alert)
            
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")

    async def _should_debounce_alert(self, alert: Alert) -> bool:
        """Check if alert should be debounced based on various rules."""
        # Check cool-off period for critical alerts
        if alert.level == AlertLevel.CRITICAL and alert.url in self.cool_off_urls:
            return True
        
        # Check domain aggregation
        if alert.domain in self.domain_alerts:
            recent_alerts = [
                a for a in self.domain_alerts[alert.domain]
                if (alert.timestamp - a.timestamp) < timedelta(minutes=5)
            ]
            if len(recent_alerts) >= settings.MAX_DOMAIN_ALERTS_PER_WINDOW:
                return True
        
        # Add to cool-off if critical
        if alert.level == AlertLevel.CRITICAL:
            self.cool_off_urls.add(alert.url)
            asyncio.create_task(self._remove_from_cool_off(alert.url))
        
        return False

    async def _remove_from_cool_off(self, url: str):
        """Remove URL from cool-off set after timeout."""
        await asyncio.sleep(settings.ALERT_COOL_OFF_MINUTES * 60)
        self.cool_off_urls.discard(url)

    def _store_alert(self, alert: Alert):
        """Store alert in memory for history tracking."""
        # Store in URL history
        if alert.url not in self.alert_history:
            self.alert_history[alert.url] = []
        self.alert_history[alert.url].append(alert)
        
        # Store in domain history
        if alert.domain not in self.domain_alerts:
            self.domain_alerts[alert.domain] = []
        self.domain_alerts[alert.domain].append(alert)
        
        # Clean old alerts
        self._clean_old_alerts()

    def _clean_old_alerts(self):
        """Clean alerts older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=settings.ALERT_RETENTION_DAYS)
        
        for url in list(self.alert_history.keys()):
            self.alert_history[url] = [
                alert for alert in self.alert_history[url]
                if alert.timestamp > cutoff
            ]
            if not self.alert_history[url]:
                del self.alert_history[url]
        
        for domain in list(self.domain_alerts.keys()):
            self.domain_alerts[domain] = [
                alert for alert in self.domain_alerts[domain]
                if alert.timestamp > cutoff
            ]
            if not self.domain_alerts[domain]:
                del self.domain_alerts[domain]

    async def _log_alert(self, alert: Alert):
        """Log alert to appropriate log file."""
        log_data = {
            "timestamp": alert.timestamp.isoformat(),
            "url": alert.url,
            "domain": alert.domain,
            "event": alert.event,
            "level": alert.level.value,
            "context": {
                "http_code": alert.context.http_code,
                "retry_count": alert.context.retry_count,
                "screenshot_path": alert.context.screenshot_path,
                "last_valid_price": alert.context.last_valid_price,
                "price_variation": alert.context.price_variation
            }
        }
        
        logger.log(alert.level.value.upper(), json.dumps(log_data))

    async def _store_alert_in_db(self, alert: Alert):
        """Store alert in database."""
        try:
            await self.db.insert_scrape_log(
                url=alert.url,
                domain=alert.domain,
                status=alert.event,
                error=alert.context.stacktrace,
                http_code=alert.context.http_code,
                retry_count=alert.context.retry_count,
                last_valid_price=alert.context.last_valid_price,
                price_variation=alert.context.price_variation,
                screenshot_path=alert.context.screenshot_path,
                resolution=alert.resolution
            )
        except Exception as e:
            logger.error(f"Error storing alert in database: {str(e)}")

    async def _send_critical_alert(self, alert: Alert):
        """Send critical alert via email and other channels."""
        try:
            # Prepare email
            msg = MIMEMultipart()
            msg['Subject'] = f"CRITICAL ALERT: {alert.event} on {alert.domain}"
            msg['From'] = settings.SMTP_FROM
            msg['To'] = ", ".join(settings.CRITICAL_ALERT_EMAILS)
            
            # Create HTML body
            body = f"""
            <h2>Critical Alert Details</h2>
            <p><strong>Time:</strong> {alert.timestamp}</p>
            <p><strong>URL:</strong> {alert.url}</p>
            <p><strong>Domain:</strong> {alert.domain}</p>
            <p><strong>Event:</strong> {alert.event}</p>
            <p><strong>Context:</strong></p>
            <ul>
                <li>HTTP Code: {alert.context.http_code}</li>
                <li>Retry Count: {alert.context.retry_count}</li>
                <li>Last Valid Price: {alert.context.last_valid_price}</li>
                <li>Price Variation: {alert.context.price_variation}</li>
            </ul>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Attach screenshot if available
            if alert.context.screenshot_path and os.path.exists(alert.context.screenshot_path):
                with open(alert.context.screenshot_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-Disposition', 'attachment', filename='error_screenshot.png')
                    msg.attach(img)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
            
        except Exception as e:
            logger.error(f"Error sending critical alert: {str(e)}")

    async def _send_error_alert(self, alert: Alert):
        """Send error alert via appropriate channels."""
        # For now, just log to error.log
        logger.error(f"Error alert for {alert.url}: {alert.event}")

    async def _send_warning_alert(self, alert: Alert):
        """Send warning alert via appropriate channels."""
        # For now, just log to warning.log
        logger.warning(f"Warning alert for {alert.url}: {alert.event}")

    async def detect_captcha(self, page: Page) -> bool:
        """Detect presence of CAPTCHA on page."""
        try:
            # Check for common CAPTCHA indicators
            captcha_indicators = [
                "iframe[src*='captcha']",
                "iframe[src*='recaptcha']",
                ".g-recaptcha",
                "[class*='captcha']",
                "text='captcha'",
                "text='verificação'"
            ]
            
            for indicator in captcha_indicators:
                if await page.query_selector(indicator):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA: {str(e)}")
            return False

    async def detect_broken_page(self, page: Page) -> bool:
        """Detect if page is broken or product doesn't exist."""
        try:
            # Check HTTP status
            response = await page.goto(page.url, wait_until="domcontentloaded")
            if response and response.status in [404, 410]:
                return True
            
            # Check for common error indicators
            error_indicators = [
                "text='produto não encontrado'",
                "text='página não encontrada'",
                "text='error 404'",
                "text='página indisponível'"
            ]
            
            for indicator in error_indicators:
                if await page.query_selector(indicator):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting broken page: {str(e)}")
            return False

    async def detect_anti_bot(self, page: Page) -> bool:
        """Detect anti-bot measures on page."""
        try:
            # Check for common anti-bot indicators
            anti_bot_indicators = [
                "iframe[src*='challenge']",
                "[class*='challenge']",
                "[class*='security']",
                "text='verificação de segurança'",
                "text='security check'"
            ]
            
            for indicator in anti_bot_indicators:
                if await page.query_selector(indicator):
                    return True
            
            # Check for suspicious redirects
            if page.url != page.main_frame.url:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting anti-bot: {str(e)}")
            return False

    async def detect_price_anomaly(self, current_price: float, last_price: float) -> bool:
        """Detect significant price variations."""
        try:
            if not last_price:
                return False
            
            variation = abs(current_price - last_price) / last_price
            return variation > settings.PRICE_VARIATION_THRESHOLD
            
        except Exception as e:
            logger.error(f"Error detecting price anomaly: {str(e)}")
            return False

    async def save_page_context(self, page: Page, alert: Alert):
        """Save page context for debugging."""
        try:
            # Save HTML
            html_path = f"logs/html/{alert.timestamp.strftime('%Y%m%d_%H%M%S')}_{alert.domain}.html"
            html_content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save screenshot
            screenshot_path = f"logs/screenshots/{alert.timestamp.strftime('%Y%m%d_%H%M%S')}_{alert.domain}.png"
            await page.screenshot(path=screenshot_path)
            
            # Update alert context
            alert.context.extracted_html = html_path
            alert.context.screenshot_path = screenshot_path
            
        except Exception as e:
            logger.error(f"Error saving page context: {str(e)}")

class Notifier:
    """Classe simples para notificações durante testes."""
    
    async def send_alert(self, level: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Envia um alerta para o log."""
        logger.log(level.upper(), f"{message} - Detalhes: {details}")
        
    async def send_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Registra uma métrica no log."""
        logger.info(f"Métrica: {name} = {value} - Tags: {tags}")
        
    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Registra um evento no log."""
        logger.info(f"Evento: {event_type} - Dados: {data}")

if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize dependencies (replace with actual implementations)
        db = None
        
        notifier = AlertNotifier(db)
        
        # Example alert
        await notifier.send_alert(
            level=AlertLevel.CRITICAL,
            message="CAPTCHA detected",
            url="https://example.com/product",
            domain="example.com",
            event="captcha_blocked",
            context={
                "http_code": 403,
                "retry_count": 3,
                "last_valid_price": 199.99
            }
        )
    
    import asyncio
    asyncio.run(main())
