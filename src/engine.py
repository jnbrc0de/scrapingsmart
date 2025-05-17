import asyncio
import random
import time
from datetime import datetime
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.config.settings import settings
from urllib.parse import urlparse
from src.circuit_breaker import DomainCircuitBreaker, CircuitOpenError
from .browser.manager import BrowserManager
from src.extractor import PriceExtractor
from .db import Database
from .alert.manager import AlertManager

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
    def __init__(self, config=None, notifier=None):
        self.config = config or settings
        self.notifier = notifier
        self.browser_manager = BrowserManager(config=self.config, notifier=self.notifier)
        self.db = Database(config=self.config)
        self.alert_manager = AlertManager(notifier=self.notifier)
        self.extractor = PriceExtractor(db=self.db, notifier=self.notifier)
        self.circuit_breaker = DomainCircuitBreaker()
        self.domain_timeouts: Dict[str, float] = {}
        self.domain_error_counts: Dict[str, int] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(self.config.LOG_DIR / "engine_{time}.log"),
            rotation=self.config.LOG_ROTATION_SIZE,
            retention=f"{self.config.LOG_RETENTION_DAYS} days",
            level=self.config.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    async def _get_domain_timeout(self, domain: str) -> float:
        """Get adaptive timeout for domain based on historical performance."""
        if domain in self.domain_timeouts:
            return self.domain_timeouts[domain]
        return self.config.DEFAULT_TIMEOUT

    async def _update_domain_timeout(self, domain: str, processing_time: float):
        """Update domain timeout based on processing time."""
        current_timeout = await self._get_domain_timeout(domain)
        # Exponential moving average with 0.3 weight for new values
        new_timeout = current_timeout * 0.7 + processing_time * 1.5 * 0.3
        self.domain_timeouts[domain] = min(new_timeout, self.config.MAX_TIMEOUT)

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

    async def scrape(self, url: str, browser: Browser) -> Dict:
        """
        Executa o scraping de uma URL com proteção do circuit breaker.
        """
        domain = urlparse(url).netloc
        start_time = time.time()
        try:
            result = await self.circuit_breaker.execute(
                domain,
                self._scrape_with_recovery,
                url,
                browser
            )
            # Record metrics (apenas logging local)
            processing_time = time.time() - start_time
            await self.alert_manager.check_metrics({
                "latency": processing_time,
                "domain": domain
            })
            return result
        except CircuitOpenError as e:
            logger.warning(f"Circuit breaker open for {domain}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            raise

    async def _scrape_with_recovery(self, url: str, browser: Browser) -> Dict:
        """
        Executa o scraping com recuperação de sessão.
        """
        domain = urlparse(url).netloc
        max_retries = self.config.get('max_retries', 3)
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
                data = await self.extractor.extract_price_data(page)
                # Salva sessão para recuperação futura
                await self.browser_manager.save_session(domain)
                return {
                    'status': 'success',
                    'page': page,
                    'data': data.__dict__
                }
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    return {
                        'status': 'error',
                        'error': str(e)
                    }
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def cleanup(self):
        """Limpa recursos do engine."""
        await self.browser_manager.cleanup()
        await self.db.close()
        await self.alert_manager.cleanup()

    async def get_metrics(self, domain: str) -> Dict:
        """Retorna métricas do engine para um domínio."""
        circuit_metrics = await self.circuit_breaker.get_metrics(domain)
        return {
            'circuit_breaker': circuit_metrics,
            'browser': {
                'has_session': domain in self.browser_manager._sessions
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
    
    asyncio.run(main())
