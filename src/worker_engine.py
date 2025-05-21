import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from loguru import logger

from src.engine import ScrapingEngine
from src.browser.manager import BrowserManager
from src.circuit_breaker import DomainCircuitBreaker
from src.metrics import MetricsCollector
from src.resource_optimizer import ResourceOptimizer
from src.strategy_manager import StrategyManager

class WorkerEngine:
    """
    Integração entre Worker e Engine, fornecendo gerenciamento de recursos,
    retry inteligente e coleta de métricas.
    """
    def __init__(self, config=None):
        self.config = config
        self.engine = ScrapingEngine(config=config)
        self.metrics = MetricsCollector()
        self.resource_optimizer = ResourceOptimizer()
        self.strategy_manager = StrategyManager()
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(self.config.LOG_DIR / "worker_engine_{time}.log"),
            rotation=self.config.LOG_ROTATION_SIZE,
            retention=f"{self.config.LOG_RETENTION_DAYS} days",
            level=self.config.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    async def initialize(self):
        """Initialize all components."""
        await self.engine.initialize()
        await self.metrics.initialize()
        await self.resource_optimizer.initialize()
        await self.strategy_manager.initialize()
        logger.info("WorkerEngine initialized successfully")

    async def process_url(self, url: str, priority: int = 0) -> Dict[str, Any]:
        """
        Processa uma URL com gerenciamento inteligente de recursos e retry.
        """
        start_time = datetime.utcnow()
        domain = url.split('/')[2]  # Extrai o domínio da URL

        try:
            # Verifica recursos disponíveis
            if not await self.resource_optimizer.check_resources():
                logger.warning("Insufficient resources, waiting...")
                await asyncio.sleep(30)
                return {"status": "retry", "reason": "insufficient_resources"}

            # Seleciona estratégia baseada no domínio
            strategy = await self.strategy_manager.get_strategy(domain)
            
            # Obtém browser com perfil otimizado
            browser = await self.engine.browser_manager.get_browser(domain)
            
            # Executa scraping com retry inteligente
            result = await self._execute_with_retry(
                url=url,
                browser=browser,
                strategy=strategy,
                priority=priority
            )

            # Coleta métricas
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self.metrics.record_processing(
                domain=domain,
                processing_time=processing_time,
                success=result.get("status") == "success"
            )

            return result

        except Exception as e:
            logger.error(f"Error processing URL {url}: {str(e)}")
            await self.metrics.record_error(domain, str(e))
            return {
                "status": "error",
                "error": str(e),
                "domain": domain
            }

    async def _execute_with_retry(
        self,
        url: str,
        browser: Any,
        strategy: Dict[str, Any],
        priority: int
    ) -> Dict[str, Any]:
        """
        Executa o scraping com retry inteligente baseado na estratégia.
        """
        max_retries = strategy.get("max_retries", 3)
        base_delay = strategy.get("base_delay", 2)
        
        for attempt in range(max_retries):
            try:
                # Aplica delay exponencial com jitter
                if attempt > 0:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)

                # Executa scraping
                result = await self.engine.scrape(url, browser)
                
                if result.get("status") == "success":
                    return result
                
                # Verifica se deve tentar novamente
                if not self._should_retry(result, attempt, max_retries):
                    return result

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    return {
                        "status": "error",
                        "error": str(e)
                    }

        return {
            "status": "error",
            "error": "Max retries exceeded"
        }

    def _should_retry(self, result: Dict[str, Any], attempt: int, max_retries: int) -> bool:
        """
        Determina se deve tentar novamente baseado no resultado e tentativa.
        """
        if attempt >= max_retries - 1:
            return False

        error = result.get("error", "").lower()
        
        # Não tenta novamente para erros fatais
        fatal_errors = [
            "invalid url",
            "not found",
            "forbidden",
            "unauthorized"
        ]
        
        if any(fatal in error for fatal in fatal_errors):
            return False

        # Tenta novamente para erros temporários
        retry_errors = [
            "timeout",
            "connection",
            "network",
            "temporary"
        ]
        
        return any(retry in error for retry in retry_errors)

    async def get_metrics(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna métricas do processamento.
        """
        metrics = await self.metrics.get_metrics(domain)
        engine_metrics = await self.engine.get_metrics(domain) if domain else {}
        
        return {
            "processing": metrics,
            "engine": engine_metrics,
            "resources": await self.resource_optimizer.get_status()
        }

    async def cleanup(self):
        """Limpa recursos do WorkerEngine."""
        await self.engine.cleanup()
        await self.metrics.cleanup()
        await self.resource_optimizer.cleanup()
        await self.strategy_manager.cleanup()
        logger.info("WorkerEngine cleaned up successfully") 