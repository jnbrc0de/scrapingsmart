import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from loguru import logger
from src.config.settings import settings

class Notifier:
    """Gerencia notificações por email e outros canais."""
    
    def __init__(self):
        self._setup_logging()
        self._setup_email()
    
    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(settings.LOG_DIR / "notifier_{time}.log"),
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def _setup_email(self):
        """Configura o cliente de email."""
        if not all([
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
            settings.EMAIL_USERNAME,
            settings.EMAIL_PASSWORD
        ]):
            logger.warning("Email configuration incomplete. Email notifications will be disabled.")
            return
            
        try:
            self.smtp_client = smtplib.SMTP(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT
            )
            self.smtp_client.starttls()
            self.smtp_client.login(
                settings.EMAIL_USERNAME,
                settings.EMAIL_PASSWORD
            )
            logger.info("Email client configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure email client: {str(e)}")
            self.smtp_client = None
    
    async def send_notification(self, alert: Dict):
        """Envia notificação por email."""
        if not self.smtp_client or not settings.email_recipients_list:
            logger.warning("Email notifications disabled or no recipients configured")
            return
            
        try:
            message = MIMEMultipart()
            message["From"] = settings.EMAIL_USERNAME
            message["To"] = ", ".join(settings.email_recipients_list)
            message["Subject"] = f"Scraping Alert: {alert['level'].upper()} - {alert['event']}"
            
            body = f"""
            Level: {alert['level']}
            Event: {alert['event']}
            Domain: {alert.get('domain', 'N/A')}
            Message: {alert['message']}
            Timestamp: {alert['timestamp']}
            """
            
            message.attach(MIMEText(body, "plain"))
            
            self.smtp_client.send_message(message)
            logger.info(f"Email notification sent for alert: {alert['event']}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
    
    def cleanup(self):
        """Limpa recursos do notifier."""
        if self.smtp_client:
            try:
                self.smtp_client.quit()
            except:
                pass 