from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os
from src.config.settings import settings
from .logger import centralized_logger

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AlertRule:
    name: str
    condition: str
    severity: AlertSeverity
    threshold: float
    window: int  # seconds
    cooldown: int  # seconds
    description: str
    action: str

@dataclass
class Alert:
    rule: AlertRule
    value: float
    timestamp: datetime
    context: Dict[str, Any]
    status: str = "active"

class AlertManager:
    def __init__(self):
        self.email_config = {
            "host": os.getenv("EMAIL_HOST", ""),
            "port": int(os.getenv("EMAIL_PORT", "0")),
            "username": os.getenv("EMAIL_USERNAME", ""),
            "password": os.getenv("EMAIL_PASSWORD", ""),
            "recipients": os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else []
        }
        self.slack_webhook = os.getenv("SLACK_WEBHOOK", None)
        self.alert_cooldown = {}  # Para evitar spam de alertas
        self.rules: List[AlertRule] = []
        self.alerts: List[Alert] = []
        self._setup_default_rules()
        self._alert_lock = asyncio.Lock()

    def _setup_default_rules(self):
        """Setup default alerting rules."""
        self.rules = [
            AlertRule(
                name="high_error_rate",
                condition="error_rate > threshold",
                severity=AlertSeverity.ERROR,
                threshold=0.2,  # 20% error rate
                window=300,  # 5 minutes
                cooldown=1800,  # 30 minutes
                description="Error rate exceeds threshold",
                action="notify_team"
            ),
            AlertRule(
                name="high_latency",
                condition="latency > threshold",
                severity=AlertSeverity.WARNING,
                threshold=5.0,  # 5 seconds
                window=60,  # 1 minute
                cooldown=300,  # 5 minutes
                description="Response latency exceeds threshold",
                action="notify_team"
            ),
            AlertRule(
                name="circuit_breaker_trips",
                condition="circuit_trips > threshold",
                severity=AlertSeverity.CRITICAL,
                threshold=3,  # 3 trips
                window=600,  # 10 minutes
                cooldown=3600,  # 1 hour
                description="Multiple circuit breaker trips",
                action="notify_team"
            ),
            AlertRule(
                name="high_cpu_usage",
                condition="cpu_usage > threshold",
                severity=AlertSeverity.WARNING,
                threshold=0.8,  # 80%
                window=300,  # 5 minutes
                cooldown=600,  # 10 minutes
                description="CPU usage exceeds threshold",
                action="notify_team"
            ),
            AlertRule(
                name="high_memory_usage",
                condition="memory_usage > threshold",
                severity=AlertSeverity.WARNING,
                threshold=0.9,  # 90%
                window=300,  # 5 minutes
                cooldown=600,  # 10 minutes
                description="Memory usage exceeds threshold",
                action="notify_team"
            )
        ]

    async def check_metrics(self, metrics: Dict[str, Any]):
        """Check metrics against alert rules."""
        async with self._alert_lock:
            for rule in self.rules:
                if await self._evaluate_rule(rule, metrics):
                    await self._create_alert(rule, metrics)

    async def _evaluate_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Evaluate if a rule condition is met."""
        try:
            # Get metric value for the rule
            value = metrics.get(rule.name, 0.0)
            
            # Check if value exceeds threshold
            if value > rule.threshold:
                # Check cooldown
                last_alert = self._get_last_alert(rule.name)
                if last_alert:
                    time_since_last = (datetime.utcnow() - last_alert.timestamp).total_seconds()
                    if time_since_last < rule.cooldown:
                        return False
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.name}: {e}")
            return False

    def _get_last_alert(self, rule_name: str) -> Optional[Alert]:
        """Get the last alert for a rule."""
        for alert in reversed(self.alerts):
            if alert.rule.name == rule_name:
                return alert
        return None

    async def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Create a new alert."""
        alert = Alert(
            rule=rule,
            value=metrics.get(rule.name, 0.0),
            timestamp=datetime.utcnow(),
            context=metrics
        )
        
        self.alerts.append(alert)
        
        # Send notification
        await self._send_notification(alert)
        
        logger.warning(
            f"Alert triggered: {rule.name} - {rule.description} "
            f"(value: {alert.value}, threshold: {rule.threshold})"
        )

    async def _send_notification(self, alert: Alert):
        """Send alert notification."""
        try:
            # Format message
            message = (
                f"🚨 Alert: {alert.rule.name}\n"
                f"Severity: {alert.rule.severity.value}\n"
                f"Description: {alert.rule.description}\n"
                f"Value: {alert.value}\n"
                f"Threshold: {alert.rule.threshold}\n"
                f"Time: {alert.timestamp.isoformat()}\n"
                f"Context: {alert.context}"
            )
            
            # Send to configured channels
            if self.slack_webhook:
                await self._send_slack(message)
                
            if self.email_config.get("recipients"):
                await self._send_email(message)
                
            # Log alert
            logger.warning(f"Alert notification sent: {message}")
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")

    async def _send_slack(self, message: str):
        """Send alert to Slack."""
        try:
            if not self.slack_webhook:
                return

            # Formata a mensagem do Slack
            message_blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {alert.rule.name}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{alert.rule.severity.value}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{alert.timestamp.isoformat()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{alert.rule.description}"
                    }
                }
            ]

            # Adiciona contexto se houver
            if alert.context:
                message_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Context:*\n```{alert.context}```"
                    }
                })

            # Envia para o Slack
            response = requests.post(
                self.slack_webhook,
                json={"blocks": message_blocks},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    async def _send_email(self, message: str):
        """Send alert via email."""
        try:
            msg = MIMEMultipart()
            msg["Subject"] = f"[{alert.rule.severity.value.upper()}] {alert.rule.name}"
            msg["From"] = self.email_config["username"]
            msg["To"] = ", ".join(self.email_config["recipients"])

            # Formata o corpo do email
            body = f"""
            Alerta: {alert.rule.name}
            Severidade: {alert.rule.severity.value}
            Data/Hora: {alert.timestamp.isoformat()}
            
            Mensagem:
            {message}
            
            Contexto:
            {alert.context}
            """
            msg.attach(MIMEText(body, "plain"))

            # Envia o email
            with smtplib.SMTP(self.email_config["host"], self.email_config["port"]) as server:
                server.starttls()
                server.login(self.email_config["username"], self.email_config["password"])
                server.send_message(msg)

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get list of active alerts."""
        return [a for a in self.alerts if a.status == "active"]

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [a for a in self.alerts if a.timestamp > cutoff]

    async def cleanup(self):
        """Cleanup alert manager resources."""
        # Archive old alerts
        cutoff = datetime.utcnow() - timedelta(days=7)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]

    def send_alert(self, 
                  title: str, 
                  message: str, 
                  severity: str = "info",
                  channels: List[str] = ["email", "slack"],
                  context: Dict[str, Any] = None):
        """Envia alerta através dos canais configurados."""
        try:
            # Verifica cooldown
            if self._is_in_cooldown(title):
                return

            # Prepara o alerta
            alert_data = {
                "title": title,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
                "context": context or {}
            }

            # Envia para cada canal configurado
            if "email" in channels:
                self._send_email_alert(alert_data)
            if "slack" in channels:
                self._send_slack_alert(alert_data)

            # Registra o alerta
            centralized_logger.log_security(
                event="alert_sent",
                severity=severity,
                details=alert_data
            )

            # Atualiza cooldown
            self._update_cooldown(title)

        except Exception as e:
            centralized_logger.log_error(e, {"alert_data": alert_data})

    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Envia alerta por email."""
        try:
            msg = MIMEMultipart()
            msg["Subject"] = f"[{alert_data['severity'].upper()}] {alert_data['title']}"
            msg["From"] = self.email_config["username"]
            msg["To"] = ", ".join(self.email_config["recipients"])

            # Formata o corpo do email
            body = f"""
            Alerta: {alert_data['title']}
            Severidade: {alert_data['severity']}
            Data/Hora: {alert_data['timestamp']}
            
            Mensagem:
            {alert_data['message']}
            
            Contexto:
            {alert_data['context']}
            """
            msg.attach(MIMEText(body, "plain"))

            # Envia o email
            with smtplib.SMTP(self.email_config["host"], self.email_config["port"]) as server:
                server.starttls()
                server.login(self.email_config["username"], self.email_config["password"])
                server.send_message(msg)

        except Exception as e:
            centralized_logger.log_error(e, {"alert_data": alert_data})

    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Envia alerta para o Slack."""
        try:
            if not self.slack_webhook:
                return

            # Formata a mensagem do Slack
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🚨 {alert_data['title']}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Severidade:*\n{alert_data['severity']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Data/Hora:*\n{alert_data['timestamp']}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Mensagem:*\n{alert_data['message']}"
                        }
                    }
                ]
            }

            # Adiciona contexto se houver
            if alert_data["context"]:
                message["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Contexto:*\n```{alert_data['context']}```"
                    }
                })

            # Envia para o Slack
            response = requests.post(
                self.slack_webhook,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

        except Exception as e:
            centralized_logger.log_error(e, {"alert_data": alert_data})

    def _is_in_cooldown(self, alert_title: str) -> bool:
        """Verifica se o alerta está em cooldown."""
        if alert_title not in self.alert_cooldown:
            return False
        
        cooldown_time = self.alert_cooldown[alert_title]
        return (datetime.utcnow() - cooldown_time).total_seconds() < settings.ALERT_COOLDOWN

    def _update_cooldown(self, alert_title: str):
        """Atualiza o cooldown do alerta."""
        self.alert_cooldown[alert_title] = datetime.utcnow()

# Instância global do gerenciador de alertas
alert_manager = AlertManager() 