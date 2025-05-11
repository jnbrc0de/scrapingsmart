from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import asyncio
from config.settings import (
    ALERT_THRESHOLDS,
    MONITORING_INTERVAL,
    ALERT_COOLDOWN
)

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    domain: str
    type: str
    message: str
    severity: str
    timestamp: datetime
    context: Dict
    resolved: bool = False

@dataclass
class DomainMetrics:
    success_rate: float
    avg_response_time: float
    error_rate: float
    extraction_confidence: float
    layout_changes: int
    last_update: datetime

class MonitoringSystem:
    def __init__(self):
        self.metrics: Dict[str, DomainMetrics] = {}
        self.alerts: List[Alert] = []
        self.alert_cooldowns: Dict[str, datetime] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for monitoring system."""
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    async def update_metrics(self, domain: str, metrics: Dict) -> None:
        """Update metrics for a domain."""
        if domain not in self.metrics:
            self.metrics[domain] = DomainMetrics(
                success_rate=1.0,
                avg_response_time=0.0,
                error_rate=0.0,
                extraction_confidence=1.0,
                layout_changes=0,
                last_update=datetime.now()
            )

        current = self.metrics[domain]
        
        # Update metrics with exponential moving average
        alpha = 0.3  # Smoothing factor
        current.success_rate = (alpha * metrics.get('success_rate', current.success_rate) +
                              (1 - alpha) * current.success_rate)
        current.avg_response_time = (alpha * metrics.get('avg_response_time', current.avg_response_time) +
                                   (1 - alpha) * current.avg_response_time)
        current.error_rate = (alpha * metrics.get('error_rate', current.error_rate) +
                            (1 - alpha) * current.error_rate)
        current.extraction_confidence = (alpha * metrics.get('extraction_confidence', current.extraction_confidence) +
                                       (1 - alpha) * current.extraction_confidence)
        current.layout_changes = metrics.get('layout_changes', current.layout_changes)
        current.last_update = datetime.now()

        # Check for potential issues
        await self._check_metrics(domain, current)

    async def _check_metrics(self, domain: str, metrics: DomainMetrics) -> None:
        """Check metrics for potential issues and generate alerts."""
        # Check if domain is in cooldown
        if domain in self.alert_cooldowns:
            if datetime.now() < self.alert_cooldowns[domain]:
                return

        alerts = []

        # Check success rate
        if metrics.success_rate < ALERT_THRESHOLDS['success_rate']:
            alerts.append(Alert(
                domain=domain,
                type='low_success_rate',
                message=f"Low success rate: {metrics.success_rate:.2%}",
                severity='high',
                timestamp=datetime.now(),
                context={'current_rate': metrics.success_rate}
            ))

        # Check response time
        if metrics.avg_response_time > ALERT_THRESHOLDS['response_time']:
            alerts.append(Alert(
                domain=domain,
                type='high_response_time',
                message=f"High response time: {metrics.avg_response_time:.2f}s",
                severity='medium',
                timestamp=datetime.now(),
                context={'current_time': metrics.avg_response_time}
            ))

        # Check error rate
        if metrics.error_rate > ALERT_THRESHOLDS['error_rate']:
            alerts.append(Alert(
                domain=domain,
                type='high_error_rate',
                message=f"High error rate: {metrics.error_rate:.2%}",
                severity='high',
                timestamp=datetime.now(),
                context={'current_rate': metrics.error_rate}
            ))

        # Check extraction confidence
        if metrics.extraction_confidence < ALERT_THRESHOLDS['extraction_confidence']:
            alerts.append(Alert(
                domain=domain,
                type='low_extraction_confidence',
                message=f"Low extraction confidence: {metrics.extraction_confidence:.2%}",
                severity='medium',
                timestamp=datetime.now(),
                context={'current_confidence': metrics.extraction_confidence}
            ))

        # Check layout changes
        if metrics.layout_changes > ALERT_THRESHOLDS['layout_changes']:
            alerts.append(Alert(
                domain=domain,
                type='frequent_layout_changes',
                message=f"Frequent layout changes: {metrics.layout_changes}",
                severity='medium',
                timestamp=datetime.now(),
                context={'changes_count': metrics.layout_changes}
            ))

        # Process alerts
        for alert in alerts:
            await self._process_alert(alert)

        # Set cooldown if alerts were generated
        if alerts:
            self.alert_cooldowns[domain] = datetime.now() + timedelta(minutes=ALERT_COOLDOWN)

    async def _process_alert(self, alert: Alert) -> None:
        """Process an alert and take appropriate action."""
        # Add to alert history
        self.alerts.append(alert)

        # Log alert
        logger.warning(
            f"Alert: {alert.type} for {alert.domain} - {alert.message} "
            f"(Severity: {alert.severity})"
        )

        # Take action based on severity
        if alert.severity == 'high':
            await self._handle_high_severity_alert(alert)
        elif alert.severity == 'medium':
            await self._handle_medium_severity_alert(alert)

    async def _handle_high_severity_alert(self, alert: Alert) -> None:
        """Handle high severity alerts."""
        # Implement immediate actions for high severity alerts
        logger.error(f"High severity alert requires immediate attention: {alert.message}")
        # TODO: Implement specific actions (e.g., notify team, pause scraping)

    async def _handle_medium_severity_alert(self, alert: Alert) -> None:
        """Handle medium severity alerts."""
        # Implement actions for medium severity alerts
        logger.warning(f"Medium severity alert requires monitoring: {alert.message}")
        # TODO: Implement specific actions (e.g., increase monitoring frequency)

    def get_domain_metrics(self, domain: str) -> Optional[DomainMetrics]:
        """Get current metrics for a domain."""
        return self.metrics.get(domain)

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts if not alert.resolved]

    def resolve_alert(self, alert_id: int) -> None:
        """Mark an alert as resolved."""
        if 0 <= alert_id < len(self.alerts):
            self.alerts[alert_id].resolved = True

    async def run(self):
        """Main monitoring loop."""
        while True:
            try:
                # Update metrics for all domains
                for domain, metrics in self.metrics.items():
                    # Check if metrics are stale
                    if datetime.now() - metrics.last_update > timedelta(minutes=5):
                        logger.warning(f"Stale metrics for domain {domain}")
                        await self._check_metrics(domain, metrics)

                await asyncio.sleep(MONITORING_INTERVAL)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(MONITORING_INTERVAL) 