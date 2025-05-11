import asyncio
import random
import time
from datetime import datetime
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config.settings import settings
from urllib.parse import urlparse
from .circuit_breaker import CircuitBreaker, CircuitOpenError
from .browser.manager import BrowserManager
from .extractor import Extractor
from .db import Database
from .monitoring.apm import APMManager
from .monitoring.alerts import AlertManager

@dataclass
class ScrapeResult:
    status: str
    price: Optional[float] = None
    currency: str = "BRL"
    availability: bool = True
    timestamp: str = datetime.utcnow().isoformat()
    seller: Optional[str] = None
    domain: Optional[str] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    queue_time: float = 0.0
    success: bool = True

class ScrapingEngine:
    """
    Engine principal de scraping assíncrono, usando Playwright, extractor e integração com DB.
    """
    def __init__(self, config):
        self.config = config
        self.browser_manager = BrowserManager(config)
        self.extractor = Extractor(config)
        self.db = Database(config)
        self.apm = APMManager(config)
        self.alert_manager = AlertManager(config)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.get('circuit_breaker_failure_threshold', 5),
            recovery_timeout=config.get('circuit_breaker_recovery_timeout', 60),
            half_open_timeout=config.get('circuit_breaker_half_open_timeout', 30),
            success_threshold=config.get('circuit_breaker_success_threshold', 2)
        )
        self.domain_timeouts: Dict[str, float] = {}
        self.domain_error_counts: Dict[str, int] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            "logs/engine_{time}.log",
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    async def _get_domain_timeout(self, domain: str) -> float:
        """Get adaptive timeout for domain based on historical performance."""
        if domain in self.domain_timeouts:
            return self.domain_timeouts[domain]
        return settings.DEFAULT_TIMEOUT

    async def _update_domain_timeout(self, domain: str, processing_time: float):
        """Update domain timeout based on processing time."""
        current_timeout = await self._get_domain_timeout(domain)
        # Exponential moving average with 0.3 weight for new values
        new_timeout = current_timeout * 0.7 + processing_time * 1.5 * 0.3
        self.domain_timeouts[domain] = min(new_timeout, settings.MAX_TIMEOUT)

    async def _simulate_human_behavior(self, page: Page):
        """Simulate realistic human behavior on the page."""
        try:
            # Random initial delay
            await asyncio.sleep(random.uniform(1.0, 3.0))

            # Scroll behavior
            viewport_height = await page.evaluate("window.innerHeight")
            total_height = await page.evaluate("document.body.scrollHeight")
            scroll_steps = random.randint(3, 6)
            
            for step in range(scroll_steps):
                # Calculate scroll position (70-80% of total height)
                scroll_to = min(
                    total_height * 0.8,
                    viewport_height * (step + 1) * random.uniform(0.7, 0.8)
                )
                
                # Smooth scroll with random speed
                await page.evaluate(f"""
                    window.scrollTo({{
                        top: {scroll_to},
                        behavior: 'smooth'
                    }});
                """)
                
                # Random pause between scrolls
                await asyncio.sleep(random.uniform(0.5, 2.0))

            # Hover over important elements
            for selector in [".product-image", ".price", ".buy-button"]:
                try:
                    element = await page.wait_for_selector(selector, timeout=1000)
                    if element:
                        await element.hover()
                        await asyncio.sleep(random.uniform(0.3, 1.0))
                except:
                    continue

        except Exception as e:
            logger.warning(f"Error in human behavior simulation: {str(e)}")

    async def _check_for_captcha(self, page: Page) -> bool:
        """Check if page contains CAPTCHA."""
        captcha_indicators = [
            "iframe[src*='captcha']",
            "iframe[src*='recaptcha']",
            ".g-recaptcha",
            "[class*='captcha']",
            "text='captcha'",
            "text='verificação'"
        ]
        
        for indicator in captcha_indicators:
            try:
                if await page.query_selector(indicator):
                    return True
            except:
                continue
        return False

    async def _handle_error(self, domain: str, error: str, url: str) -> Tuple[bool, str]:
        """Handle scraping errors and determine retry strategy."""
        self.domain_error_counts[domain] = self.domain_error_counts.get(domain, 0) + 1
        
        if "captcha" in error.lower():
            await self.alert_manager.send_alert(
                level="warning",
                message=f"CAPTCHA detected on {domain}",
                details={"url": url, "error": error}
            )
            return False, "captcha-blocked"
        
        if self.domain_error_counts[domain] >= 3:
            await self.alert_manager.send_alert(
                level="error",
                message=f"Domain {domain} marked as broken",
                details={"url": url, "error": error}
            )
            return False, "broken"
        
        return True, "warning"

    async def scrape(self, url: str) -> Dict:
        """
        Executa o scraping de uma URL com proteção do circuit breaker.
        """
        domain = urlparse(url).netloc
        start_time = time.time()
        
        with self.apm.start_span("scrape", {"url": url, "domain": domain}) as span:
            try:
                result = await self.circuit_breaker.execute(
                    domain,
                    self._scrape_with_recovery,
                    url
                )
                
                # Record metrics
                processing_time = time.time() - start_time
                self.apm.record_metric(
                    "scrape_duration",
                    processing_time,
                    {"domain": domain, "success": True}
                )
                
                # Check for alerts
                await self.alert_manager.check_metrics({
                    "latency": processing_time,
                    "domain": domain
                })
                
                return result
                
            except CircuitOpenError as e:
                self.apm.record_error(e, {"url": url, "domain": domain})
                logger.warning(f"Circuit breaker open for {domain}: {e}")
                raise
                
            except Exception as e:
                self.apm.record_error(e, {"url": url, "domain": domain})
                logger.error(f"Error scraping {url}: {e}")
                raise

    async def _scrape_with_recovery(self, url: str) -> Dict:
        """
        Executa o scraping com recuperação de sessão.
        """
        domain = urlparse(url).netloc
        max_retries = self.config.get('max_retries', 3)
        
        with self.apm.start_span("scrape_with_recovery", {"url": url, "domain": domain}) as span:
            for attempt in range(max_retries):
                try:
                    # Tenta recuperar sessão existente
                    if attempt > 0:
                        await self.browser_manager.recover_session(domain)
                    
                    # Obtém página
                    page = await self.browser_manager.get_page(domain)
                    
                    # Navega para URL
                    await page.goto(url, wait_until='networkidle')
                    
                    # Extrai dados
                    data = await self.extractor.extract(page)
                    
                    # Salva sessão para recuperação futura
                    await self.browser_manager.save_session(domain)
                    
                    return data
                    
                except Exception as e:
                    self.apm.record_error(e, {
                        "url": url,
                        "domain": domain,
                        "attempt": attempt + 1
                    })
                    
                    logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                    
                    if attempt == max_retries - 1:
                        raise
                    
                    # Lida com crash do navegador
                    await self.browser_manager.handle_crash(domain)
                    
                    # Espera antes de tentar novamente
                    await asyncio.sleep(2 ** attempt)

    async def cleanup(self):
        """Limpa recursos do engine."""
        await self.browser_manager.cleanup()
        await self.db.close()
        await self.apm.cleanup()
        await self.alert_manager.cleanup()

    async def get_metrics(self, domain: str) -> Dict:
        """Retorna métricas do engine para um domínio."""
        circuit_metrics = await self.circuit_breaker.get_metrics(domain)
        return {
            'circuit_breaker': circuit_metrics,
            'browser': {
                'has_session': domain in self.browser_manager._sessions
            },
            'apm': {
                'spans': self.apm.get_spans(domain),
                'errors': self.apm.get_errors(domain)
            },
            'alerts': {
                'active': self.alert_manager.get_active_alerts(),
                'history': self.alert_manager.get_alert_history()
            }
        }

    async def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Get statistics for a specific domain."""
        return {
            "timeout": await self._get_domain_timeout(domain),
            "error_count": self.domain_error_counts.get(domain, 0),
            "status": "broken" if self.domain_error_counts.get(domain, 0) >= 3 else "active"
        }

if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize dependencies (replace with actual implementations)
        config = None
        engine = ScrapingEngine(config)
        
        # Example URL
        url = "https://example.com"
        
        # Test scraping
        result = await engine.scrape(url)
        print(f"Scraping result: {result}")
    
    asyncio.run(main())
