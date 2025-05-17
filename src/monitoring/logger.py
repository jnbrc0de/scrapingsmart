from loguru import logger
import sys
import json
from datetime import datetime
from typing import Dict, Any
from elasticsearch import Elasticsearch
from src.config.settings import settings

class CentralizedLogger:
    def __init__(self):
        self.es = None
        self.elasticsearch_enabled = False
        if hasattr(settings, 'ELASTICSEARCH_URL') and getattr(settings, 'ELASTICSEARCH_URL'):
            try:
                self.es = Elasticsearch(getattr(settings, 'ELASTICSEARCH_URL'))
                self.elasticsearch_enabled = True
            except Exception as e:
                logger.warning(f"Elasticsearch not initialized: {e}")
        self._setup_logger()

    def _setup_logger(self):
        """Configura o logger com diferentes handlers."""
        # Remove handler padrão
        logger.remove()

        # Adiciona handler para console
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"  # Em produção, use INFO ou WARNING. Não registre dados sensíveis!
        )

        # Adiciona handler para arquivo
        logger.add(
            "logs/app.log",
            rotation="500 MB",
            retention="10 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG"
        )

        # Adiciona handler para Elasticsearch se habilitado
        if self.elasticsearch_enabled:
            logger.add(
                self._log_to_elasticsearch,
                format="{message}",
                level="INFO"
            )

    def _log_to_elasticsearch(self, message: Dict[str, Any]):
        """Envia logs para o Elasticsearch."""
        if not self.elasticsearch_enabled or not self.es:
            return
        try:
            log_entry = {
                "timestamp": datetime.utcnow(),
                "level": message["level"].name,
                "message": message["message"],
                "module": message["name"],
                "function": message["function"],
                "line": message["line"],
                "environment": getattr(settings, 'ENVIRONMENT', 'unknown')
            }
            self.es.index(index=f"logs-{datetime.utcnow().strftime('%Y.%m.%d')}", body=log_entry)
        except Exception as e:
            logger.error(f"Erro ao enviar log para Elasticsearch: {str(e)}")

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Registra um erro com contexto."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        logger.error(json.dumps(error_data))

    def log_performance(self, operation: str, duration: float, metadata: Dict[str, Any] = None):
        """Registra métricas de performance."""
        perf_data = {
            "operation": operation,
            "duration": duration,
            "metadata": metadata or {}
        }
        logger.info(f"PERFORMANCE: {json.dumps(perf_data)}")

    def log_security(self, event: str, severity: str, details: Dict[str, Any] = None):
        """Registra eventos de segurança."""
        security_data = {
            "event": event,
            "severity": severity,
            "details": details or {}
        }
        logger.warning(f"SECURITY: {json.dumps(security_data)}")

# Instância global do logger
centralized_logger = CentralizedLogger() 