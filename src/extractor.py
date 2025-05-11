import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger
from playwright.async_api import Page
from config.settings import settings
from bs4 import BeautifulSoup

@dataclass
class ExtractionStrategy:
    domain: str
    strategy_type: str  # regex, xpath, css, semantic, composite
    selector: str
    confidence_score: float = 0.0
    status: str = "active"
    priority: int = 0
    last_success: Optional[datetime] = None
    sample_urls: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.sample_urls is None:
            self.sample_urls = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ExtractionResult:
    price_current: Optional[float] = None
    price_old: Optional[float] = None
    price_pix: Optional[float] = None
    installment_info: Optional[str] = None
    availability: Optional[str] = None
    promotion_badges: List[str] = None
    currency_detected: str = "BRL"
    strategy_used: Optional[str] = None
    confidence: float = 0.0
    success: bool = False
    error: Optional[str] = None

    def __post_init__(self):
        if self.promotion_badges is None:
            self.promotion_badges = []

class ExtractorError(Exception):
    """Base exception for extractor errors."""
    pass

class ValidationError(ExtractorError):
    """Exception for data validation errors."""
    pass

class StrategyError(ExtractorError):
    """Exception for strategy-related errors."""
    pass

class PriceExtractor:
    def __init__(self, db, notifier):
        """Initialize the price extractor with dependencies."""
        self.db = db
        self.notifier = notifier
        self.strategies: Dict[str, List[ExtractionStrategy]] = {}
        self.domain_error_counts: Dict[str, int] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            "logs/extractor_{time}.log",
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    async def load_strategies(self, domain: str) -> List[ExtractionStrategy]:
        """Load extraction strategies for a domain."""
        try:
            # Load from database
            strategies_data = await self.db.get_extraction_strategies(domain)
            
            # Convert to strategy objects
            strategies = []
            for data in strategies_data:
                strategy = ExtractionStrategy(
                    domain=data["domain"],
                    strategy_type=data["strategy_type"],
                    selector=data["selector"],
                    confidence_score=data["confidence_score"],
                    status=data["status"],
                    priority=data["priority"],
                    last_success=datetime.fromisoformat(data["last_success"]) if data["last_success"] else None,
                    sample_urls=data["sample_urls"],
                    metadata=data["metadata"]
                )
                strategies.append(strategy)
            
            # Sort by confidence and priority
            strategies.sort(key=lambda x: (x.confidence_score, -x.priority), reverse=True)
            
            # Cache strategies
            self.strategies[domain] = strategies
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error loading strategies for {domain}: {str(e)}")
            return []

    async def extract_price_data(self, page: Page) -> ExtractionResult:
        """
        Extract price data using multiple strategies and adaptive feedback.
        Tenta múltiplas estratégias por campo, faz fallback e ajusta confiança/prioridade.
        """
        domain = page.url.split("/")[2]
        result = ExtractionResult()
        tried_strategies = []
        try:
            # Load strategies if not cached
            if domain not in self.strategies:
                await self.load_strategies(domain)
            # Try each strategy in order
            for strategy in self.strategies.get(domain, []):
                if strategy.status != "active":
                    continue
                try:
                    # Extract data based on strategy type
                    if strategy.strategy_type == "regex":
                        data = await self._extract_with_regex(page, strategy)
                    elif strategy.strategy_type == "xpath":
                        data = await self._extract_with_xpath(page, strategy)
                    elif strategy.strategy_type == "css":
                        data = await self._extract_with_css(page, strategy)
                    elif strategy.strategy_type == "semantic":
                        data = await self._extract_with_semantic(page, strategy)
                    elif strategy.strategy_type == "composite":
                        data = await self._extract_with_composite(page, strategy)
                    else:
                        continue
                    tried_strategies.append((strategy.strategy_type, strategy.selector, data))
                    # Validate extracted data
                    if await self._validate_data(data):
                        result = ExtractionResult(
                            price_current=data.get("price_current"),
                            price_old=data.get("price_old"),
                            price_pix=data.get("price_pix"),
                            installment_info=data.get("installment_info"),
                            availability=data.get("availability"),
                            promotion_badges=data.get("promotion_badges", []),
                            currency_detected=data.get("currency", "BRL"),
                            strategy_used=strategy.strategy_type,
                            confidence=strategy.confidence_score,
                            success=True
                        )
                        await self._update_strategy_success(strategy)
                        logger.info(f"[EXTRACTOR] Sucesso: {strategy.strategy_type} | {strategy.selector}")
                        break
                    else:
                        logger.info(f"[EXTRACTOR] Falha de validação: {strategy.strategy_type} | {strategy.selector}")
                except Exception as e:
                    logger.warning(f"Strategy {strategy.strategy_type} failed: {str(e)}")
                    continue
            # If no strategy succeeded, try fallback strategies
            if not result.success:
                logger.warning(f"[EXTRACTOR] Todas as estratégias falharam, tentando fallback...")
                result = await self._try_fallback_strategies(page)
            # Handle failures
            if not result.success:
                await self._handle_extraction_failure(domain)
                logger.error(f"[EXTRACTOR] Falha total para domínio {domain}. Estratégias tentadas: {tried_strategies}")
            return result
        except Exception as e:
            logger.error(f"Error extracting data from {domain}: {str(e)}")
            result.error = str(e)
            return result

    async def _extract_with_regex(self, page: Page, strategy: ExtractionStrategy) -> Dict[str, Any]:
        """Extract data using regex patterns."""
        html = await page.content()
        data = {}
        
        # Extract current price
        if price_match := re.search(r"R\$\s*(\d+[.,]\d{2})", html):
            data["price_current"] = float(price_match.group(1).replace(".", "").replace(",", "."))
        
        # Extract old price
        if old_price_match := re.search(r"de\s*R\$\s*(\d+[.,]\d{2})", html):
            data["price_old"] = float(old_price_match.group(1).replace(".", "").replace(",", "."))
        
        # Extract PIX price
        if pix_match := re.search(r"PIX\s*R\$\s*(\d+[.,]\d{2})", html):
            data["price_pix"] = float(pix_match.group(1).replace(".", "").replace(",", "."))
        
        return data

    async def _extract_with_xpath(self, page: Page, strategy: ExtractionStrategy) -> Dict[str, Any]:
        """Extract data using XPath selectors."""
        data = {}
        
        # Extract current price
        price_element = await page.query_selector(strategy.selector)
        if price_element:
            price_text = await price_element.text_content()
            if price_match := re.search(r"R\$\s*(\d+[.,]\d{2})", price_text):
                data["price_current"] = float(price_match.group(1).replace(".", "").replace(",", "."))
        
        return data

    async def _extract_with_css(self, page: Page, strategy: ExtractionStrategy) -> Dict[str, Any]:
        """Extract data using CSS selectors."""
        data = {}
        
        # Extract current price
        price_element = await page.query_selector(strategy.selector)
        if price_element:
            price_text = await price_element.text_content()
            if price_match := re.search(r"R\$\s*(\d+[.,]\d{2})", price_text):
                data["price_current"] = float(price_match.group(1).replace(".", "").replace(",", "."))
        
        return data

    async def _extract_with_semantic(self, page: Page, strategy: ExtractionStrategy) -> Dict[str, Any]:
        """Extract data using semantic attributes."""
        data = {}
        
        # Try different semantic selectors
        selectors = [
            '[itemprop="price"]',
            '[data-price]',
            '[aria-label*="preço"]',
            'meta[property="product:price:amount"]'
        ]
        
        for selector in selectors:
            element = await page.query_selector(selector)
            if element:
                if selector.startswith('meta'):
                    price_text = await element.get_attribute('content')
                else:
                    price_text = await element.text_content()
                
                if price_match := re.search(r"(\d+[.,]\d{2})", price_text):
                    data["price_current"] = float(price_match.group(1).replace(".", "").replace(",", "."))
                    break
        
        return data

    async def _extract_with_composite(self, page: Page, strategy: ExtractionStrategy) -> Dict[str, Any]:
        """Extract data using multiple strategies."""
        data = {}
        
        # Try each sub-strategy
        for sub_strategy in strategy.metadata.get("sub_strategies", []):
            try:
                if sub_strategy["type"] == "regex":
                    sub_data = await self._extract_with_regex(page, ExtractionStrategy(**sub_strategy))
                elif sub_strategy["type"] == "xpath":
                    sub_data = await self._extract_with_xpath(page, ExtractionStrategy(**sub_strategy))
                elif sub_strategy["type"] == "css":
                    sub_data = await self._extract_with_css(page, ExtractionStrategy(**sub_strategy))
                elif sub_strategy["type"] == "semantic":
                    sub_data = await self._extract_with_semantic(page, ExtractionStrategy(**sub_strategy))
                
                data.update(sub_data)
                
            except Exception as e:
                logger.warning(f"Sub-strategy {sub_strategy['type']} failed: {str(e)}")
                continue
        
        return data

    async def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate extracted data."""
        try:
            # Check required fields
            if "price_current" not in data:
                return False
            
            # Validate price_current
            if not isinstance(data["price_current"], (int, float)) or data["price_current"] <= 0:
                return False
            
            # Validate price_pix if present
            if "price_pix" in data and data["price_pix"] > data["price_current"]:
                return False
            
            # Validate price_old if present
            if "price_old" in data and data["price_old"] <= data["price_current"]:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            return False

    async def _update_strategy_success(self, strategy: ExtractionStrategy):
        """Update strategy success metrics."""
        try:
            # Update confidence score
            strategy.confidence_score = min(1.0, strategy.confidence_score + 0.1)
            strategy.last_success = datetime.utcnow()
            
            # Update in database
            await self.db.update_strategy(
                strategy_id=strategy.metadata.get("id"),
                confidence_score=strategy.confidence_score,
                last_success=strategy.last_success.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error updating strategy success: {str(e)}")

    async def _handle_extraction_failure(self, domain: str):
        """Handle extraction failure and update domain status."""
        self.domain_error_counts[domain] = self.domain_error_counts.get(domain, 0) + 1
        
        if self.domain_error_counts[domain] >= 3:
            await self.notifier.send_alert(
                level="error",
                message=f"Domain {domain} marked as broken",
                details={"error_count": self.domain_error_counts[domain]}
            )
        elif self.domain_error_counts[domain] >= 2:
            await self.notifier.send_alert(
                level="warning",
                message=f"Domain {domain} showing signs of issues",
                details={"error_count": self.domain_error_counts[domain]}
            )

    async def _try_fallback_strategies(self, page: Page) -> ExtractionResult:
        """
        Tenta padrões genéricos e heurísticas para extrair preço quando todas as estratégias falham.
        """
        result = ExtractionResult()
        try:
            html = await page.content()
            # Padrões genéricos para preço
            price_patterns = [
                r"R\$\s*(\d+[.,]\d{2})",
                r"(\d+[.,]\d{2})\s*R\$",
                r"preço[:\s]+R\$\s*(\d+[.,]\d{2})",
                r"[Pp]ix\s*R\$\s*(\d+[.,]\d{2})"
            ]
            for pattern in price_patterns:
                if match := re.search(pattern, html):
                    price = float(match.group(1).replace(".", "").replace(",", "."))
                    if price > 0:
                        result.price_current = price
                        result.success = True
                        result.strategy_used = "fallback_regex"
                        result.confidence = 0.3
                        logger.info(f"[EXTRACTOR] Fallback encontrou preço: {price}")
                        break
            # Heurística para preço antigo
            if not result.price_old:
                if match := re.search(r"de\s*R\$\s*(\d+[.,]\d{2})", html):
                    price_old = float(match.group(1).replace(".", "").replace(",", "."))
                    if price_old > 0:
                        result.price_old = price_old
            # Heurística para preço PIX
            if not result.price_pix:
                if match := re.search(r"[Pp]ix\s*R\$\s*(\d+[.,]\d{2})", html):
                    price_pix = float(match.group(1).replace(".", "").replace(",", "."))
                    if price_pix > 0:
                        result.price_pix = price_pix
            # Heurística para disponibilidade
            if "esgotado" in html.lower() or "indisponível" in html.lower():
                result.availability = "out_of_stock"
            elif "em estoque" in html.lower() or "disponível" in html.lower():
                result.availability = "in_stock"
            return result
        except Exception as e:
            logger.error(f"Error in fallback strategies: {str(e)}")
        return result

    async def generate_strategy_variants(self, strategy: ExtractionStrategy) -> List[ExtractionStrategy]:
        """Generate variants of a successful strategy."""
        variants = []
        
        try:
            if strategy.strategy_type == "regex":
                # Generate regex variants
                pattern = strategy.selector
                variants.extend([
                    ExtractionStrategy(
                        domain=strategy.domain,
                        strategy_type="regex",
                        selector=pattern.replace("R\$", "R\\$"),  # Escape $ if not already
                        confidence_score=strategy.confidence_score * 0.8,
                        metadata={"parent_id": strategy.metadata.get("id")}
                    ),
                    ExtractionStrategy(
                        domain=strategy.domain,
                        strategy_type="regex",
                        selector=pattern.replace(" ", "\\s*"),  # More flexible whitespace
                        confidence_score=strategy.confidence_score * 0.8,
                        metadata={"parent_id": strategy.metadata.get("id")}
                    )
                ])
            
            elif strategy.strategy_type == "css":
                # Generate CSS variants
                selector = strategy.selector
                variants.extend([
                    ExtractionStrategy(
                        domain=strategy.domain,
                        strategy_type="css",
                        selector=f"{selector} > span",  # More specific
                        confidence_score=strategy.confidence_score * 0.8,
                        metadata={"parent_id": strategy.metadata.get("id")}
                    ),
                    ExtractionStrategy(
                        domain=strategy.domain,
                        strategy_type="css",
                        selector=f"{selector}:first-child",  # First occurrence
                        confidence_score=strategy.confidence_score * 0.8,
                        metadata={"parent_id": strategy.metadata.get("id")}
                    )
                ])
            
            # Save variants to database
            for variant in variants:
                await self.db.save_strategy(variant)
            
            return variants
            
        except Exception as e:
            logger.error(f"Error generating strategy variants: {str(e)}")
            return []

def extract_price(html: str, url: str) -> float:
    """
    Extrai o preço do HTML usando múltiplas estratégias (regex, CSS, heurística).
    Pode ser expandido para estratégias específicas por domínio.
    """
    # 1. Regex genérica para R$ XX,XX
    match = re.search(r'R\$\s*([0-9\.]+,[0-9]{2})', html)
    if match:
        price = match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(price)
        except Exception:
            pass
    # 2. CSS selectors (exemplo para expansão futura)
    soup = BeautifulSoup(html, 'lxml')
    selectors = [
        '.price, .a-price .a-offscreen, .price-current, [itemprop="price"]',
        '[data-price], .price-tag, .product-price'
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            price_text = re.sub(r'[^0-9,]', '', el.get_text())
            price_text = price_text.replace('.', '').replace(',', '.')
            try:
                return float(price_text)
            except Exception:
                continue
    return None

if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize dependencies (replace with actual implementations)
        db = None
        notifier = None
        
        extractor = PriceExtractor(db, notifier)
        
        # Example strategy
        strategy = ExtractionStrategy(
            domain="example.com",
            strategy_type="css",
            selector=".price-value",
            confidence_score=0.8,
            metadata={"id": "123"}
        )
        
        # Generate variants
        variants = await extractor.generate_strategy_variants(strategy)
        print(f"Generated {len(variants)} variants")
    
    import asyncio
    asyncio.run(main())
