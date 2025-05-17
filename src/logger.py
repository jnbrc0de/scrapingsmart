import os
import json
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import wraps
from loguru import logger
import asyncio
from datetime import datetime, timedelta
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Load logging configuration
CONFIG_PATH = Path(__file__).parent.parent / "config" / "logging.conf"
with open(CONFIG_PATH) as f:
    LOG_CONFIG = json.load(f)

class AlertManager:
    def __init__(self):
        self.alert_history: Dict[str, List[Dict[str, Any]]] = {}
        self.cooldown_until: Dict[str, datetime] = {}
    
    def _generate_alert_id(self) -> str:
        """Generate a unique alert ID."""
        return str(uuid.uuid4())
    
    def _is_in_cooldown(self, domain: str, level: str) -> bool:
        """Check if domain is in cooldown for the given alert level."""
        key = f"{domain}:{level}"
        if key not in self.cooldown_until:
            return False
        return datetime.now() < self.cooldown_until[key]
    
    def _update_cooldown(self, domain: str, level: str):
        """Update cooldown period for domain and alert level."""
        key = f"{domain}:{level}"
        cooldown_minutes = LOG_CONFIG["alerts"]["levels"][level]["cooldown"]
        self.cooldown_until[key] = datetime.now() + timedelta(minutes=cooldown_minutes)
    
    def _should_aggregate(self, domain: str, level: str) -> bool:
        """Check if alert should be aggregated based on recent history."""
        if not LOG_CONFIG["alerts"]["levels"][level]["aggregate"]:
            return False
        
        window = timedelta(minutes=LOG_CONFIG["alerts"]["aggregation"]["window_minutes"])
        max_alerts = LOG_CONFIG["alerts"]["aggregation"]["max_alerts_per_window"]
        
        recent_alerts = [
            alert for alert in self.alert_history.get(domain, [])
            if alert["level"] == level and
            datetime.now() - alert["timestamp"] < window
        ]
        
        return len(recent_alerts) >= max_alerts
    
    async def handle_alert(self, level: str, message: str, domain: str, url: str):
        """Handle an alert with aggregation and notification."""
        if not LOG_CONFIG["alerts"]["enabled"]:
            return
        
        if self._is_in_cooldown(domain, level):
            return
        
        alert_id = self._generate_alert_id()
        timestamp = datetime.now()
        
        # Record alert
        if domain not in self.alert_history:
            self.alert_history[domain] = []
        self.alert_history[domain].append({
            "id": alert_id,
            "level": level,
            "message": message,
            "timestamp": timestamp,
            "url": url
        })
        
        # Check aggregation
        if self._should_aggregate(domain, level):
            return
        
        # Format message
        alert_config = LOG_CONFIG["alerts"]["levels"][level]
        formatted_message = alert_config["format"].format(message=message)
        
        # Log alert
        logger.bind(
            alert_id=alert_id,
            domain=domain,
            url=url
        ).log(level, formatted_message)
        
        # Send notifications
        if alert_config["notify"]:
            await self._send_notifications(level, formatted_message, domain, url)
        
        # Update cooldown
        self._update_cooldown(domain, level)
    
    async def _send_notifications(self, level: str, message: str, domain: str, url: str):
        """Send notifications through configured channels."""
        if LOG_CONFIG["alerts"]["notification"]["email"]["enabled"]:
            await self._send_email(level, message, domain, url)
        
        if LOG_CONFIG["alerts"]["notification"]["webhook"]["enabled"]:
            await self._send_webhook(level, message, domain, url)
    
    async def _send_email(self, level: str, message: str, domain: str, url: str):
        """Send email notification."""
        try:
            email_config = LOG_CONFIG["alerts"]["notification"]["email"]
            subject = email_config["subject_template"].format(
                level=level,
                domain=domain,
                message=message
            )
            
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = os.getenv("ALERT_EMAIL_FROM", "alerts@example.com")
            msg["To"] = ", ".join(email_config["recipients"])
            
            body = f"""
            Alert Details:
            Level: {level}
            Domain: {domain}
            URL: {url}
            Message: {message}
            Time: {datetime.now()}
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email (implement your SMTP logic here)
            # This is a placeholder - implement actual email sending
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_webhook(self, level: str, message: str, domain: str, url: str):
        """Send webhook notification."""
        webhook_config = LOG_CONFIG["alerts"]["notification"]["webhook"]
        
        payload = {
            "level": level,
            "message": message,
            "domain": domain,
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
        
        for attempt in range(webhook_config["retry_attempts"]):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_config["url"],
                        json=payload,
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            return
                        logger.warning(f"Webhook returned status {response.status}")
            except Exception as e:
                logger.error(f"Webhook attempt {attempt + 1} failed: {e}")
                if attempt < webhook_config["retry_attempts"] - 1:
                    await asyncio.sleep(webhook_config["retry_delay"])

# Initialize alert manager
alert_manager = AlertManager()

# Configure logger
def setup_logger():
    """Configure the logger with all sinks and filters."""
    # Remove default handler
    logger.remove()
    
    # Add console handler (development only)
    if os.getenv("ENVIRONMENT") == "development":
        logger.add(
            LOG_CONFIG["handlers"]["console"]["sink"],
            format=LOG_CONFIG["handlers"]["console"]["format"],
            level=LOG_CONFIG["handlers"]["console"]["level"],
            colorize=True,
            enqueue=True
        )
    
    # Add file handler
    logger.add(
        LOG_CONFIG["handlers"]["file"]["sink"],
        format=LOG_CONFIG["handlers"]["file"]["format"],
        level=LOG_CONFIG["handlers"]["file"]["level"],
        rotation=LOG_CONFIG["handlers"]["file"]["rotation"],
        retention=LOG_CONFIG["handlers"]["file"]["retention"],
        compression=LOG_CONFIG["handlers"]["file"]["compression"],
        enqueue=True
    )
    
    # Add alerts handler
    logger.add(
        LOG_CONFIG["handlers"]["alerts"]["sink"],
        format=LOG_CONFIG["handlers"]["alerts"]["format"],
        level=LOG_CONFIG["handlers"]["alerts"]["level"],
        rotation=LOG_CONFIG["handlers"]["alerts"]["rotation"],
        retention=LOG_CONFIG["handlers"]["alerts"]["retention"],
        compression=LOG_CONFIG["handlers"]["alerts"]["compression"],
        enqueue=True
    )
    
    # Add webhook handler
    logger.add(
        LOG_CONFIG["handlers"]["webhook"]["sink"],
        format=LOG_CONFIG["handlers"]["webhook"]["format"],
        level=LOG_CONFIG["handlers"]["webhook"]["level"],
        rotation=LOG_CONFIG["handlers"]["webhook"]["rotation"],
        retention=LOG_CONFIG["handlers"]["webhook"]["retention"],
        compression=LOG_CONFIG["handlers"]["webhook"]["compression"],
        enqueue=True
    )

# Metrics collection
class MetricsCollector:
    def __init__(self):
        self.failures_by_domain: Dict[str, int] = {}
        self.scraping_time: Dict[str, float] = {}
    
    def record_failure(self, domain: str):
        """Record a failure for a domain."""
        self.failures_by_domain[domain] = self.failures_by_domain.get(domain, 0) + 1
    
    def record_scraping_time(self, url: str, duration: float):
        """Record scraping time for a URL."""
        self.scraping_time[url] = duration
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "failures_by_domain": self.failures_by_domain,
            "scraping_time": self.scraping_time
        }

metrics = MetricsCollector()

# Context manager for logging
class LogContext:
    def __init__(self, domain: str, url: str, status: str = "unknown"):
        self.domain = domain
        self.url = url
        self.status = status
        self.start_time = time.time()
    
    def __enter__(self):
        logger.configure(extra={
            "domain": self.domain,
            "url": self.url,
            "status": self.status
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if LOG_CONFIG["metrics"]["enabled"]:
            metrics.record_scraping_time(self.url, duration)
        
        if exc_type is not None:
            error_msg = f"Error during scraping: {exc_val}"
            logger.error(error_msg)
            if LOG_CONFIG["metrics"]["enabled"]:
                metrics.record_failure(self.domain)
            # Send alert for errors
            asyncio.create_task(alert_manager.handle_alert(
                "ERROR",
                error_msg,
                self.domain,
                self.url
            ))

# Decorator for logging function calls
def log_function(level: str = "INFO"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            domain = kwargs.get("domain", "unknown")
            url = kwargs.get("url", "unknown")
            
            with LogContext(domain, url):
                logger.log(level, f"Starting {func.__name__}")
                try:
                    result = await func(*args, **kwargs)
                    logger.log(level, f"Completed {func.__name__}")
                    return result
                except Exception as e:
                    error_msg = f"Error in {func.__name__}: {str(e)}"
                    logger.error(error_msg)
                    # Send alert for errors
                    await alert_manager.handle_alert(
                        "ERROR",
                        error_msg,
                        domain,
                        url
                    )
                    raise
        return wrapper
    return decorator

# Initialize logger
setup_logger()

# Example usage:
if __name__ == "__main__":
    # Example of using the logger with context
    with LogContext("example.com", "https://example.com/product"):
        logger.info("Starting scraping")
        logger.warning("Rate limit approaching")
        logger.error("Failed to extract price")
    
    # Example of using the decorator
    @log_function(level="INFO")
    async def scrape_url(url: str, domain: str):
        # Simulate scraping
        await asyncio.sleep(1)
        return {"price": 99.99}
    
    # Run example
    asyncio.run(scrape_url("https://example.com/product", "example.com")) 