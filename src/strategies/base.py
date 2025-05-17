from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from loguru import logger
from playwright.async_api import Browser, Page
import json
import os
from pathlib import Path
import time
from .learning_manager import LearningManager

class BaseStrategy(ABC):
    """Classe base para estratégias de scraping."""
    
    def __init__(self):
        """Inicializa a estratégia base."""
        self._setup_logging()
        self.learning_manager = LearningManager()
        self._ensure_data_directories()
    
    def _setup_logging(self):
        """Configure logging with loguru."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            log_dir / "strategy_{time}.log",
            rotation="10 MB",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def _ensure_data_directories(self):
        """Garante que os diretórios necessários existam."""
        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize strategy."""
        logger.info(f"Initializing {self.__class__.__name__}")
    
    async def cleanup(self):
        """Clean up strategy resources."""
        logger.info(f"Cleaning up {self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, url: str, browser: Browser) -> Dict[str, Any]:
        """Execute the scraping strategy."""
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics."""
        return {
            "name": self.__class__.__name__,
            "status": "active"
        }
    
    async def _get_page(self, browser: Browser, url: str) -> Page:
        """Get a page from browser."""
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            return page
        except Exception as e:
            logger.error(f"Error getting page: {str(e)}")
            raise
    
    async def _extract_price(self, page: Page, domain: str) -> Optional[float]:
        """Extract price from page."""
        try:
            start_time = time.time()
            
            # Primeiro tenta os seletores específicos da estratégia
            price = await self._try_specific_price_selectors(page)
            if price:
                self.learning_manager.update_selector_score(
                    domain, "price", "specific", True, time.time() - start_time
                )
                return price
            
            # Se não encontrar, tenta os seletores aprendidos
            for selector in self.learning_manager.get_best_selectors(domain, "price"):
                try:
                    price_text = await page.evaluate(f"""
                        () => {{
                            const element = document.querySelector('{selector}');
                            return element ? element.textContent : null;
                        }}
                    """)
                    
                    if price_text:
                        try:
                            price = float(price_text.replace('R$', '').replace('.', '').replace(',', '.').strip())
                            self.learning_manager.update_selector_score(
                                domain, "price", selector, True, time.time() - start_time
                            )
                            return price
                        except ValueError:
                            continue
                except Exception:
                    continue
            
            # Se ainda não encontrar, tenta detectar novos seletores
            new_selectors = await self._detect_price_selectors(page)
            if new_selectors:
                for selector in new_selectors:
                    try:
                        price_text = await page.evaluate(f"""
                            () => {{
                                const element = document.querySelector('{selector}');
                                return element ? element.textContent : null;
                            }}
                        """)
                        
                        if price_text:
                            try:
                                price = float(price_text.replace('R$', '').replace('.', '').replace(',', '.').strip())
                                self.learning_manager.update_selector_score(
                                    domain, "price", selector, True, time.time() - start_time
                                )
                                return price
                            except ValueError:
                                continue
                    except Exception:
                        continue
            
            # Se chegou aqui, nenhum seletor funcionou
            self.learning_manager.update_selector_score(
                domain, "price", "all", False, time.time() - start_time
            )
            return None
            
        except Exception as e:
            logger.error(f"Error extracting price: {str(e)}")
            return None
    
    async def _extract_title(self, page: Page, domain: str) -> Optional[str]:
        """Extract product title from page."""
        try:
            start_time = time.time()
            
            # Primeiro tenta os seletores específicos da estratégia
            title = await self._try_specific_title_selectors(page)
            if title:
                self.learning_manager.update_selector_score(
                    domain, "title", "specific", True, time.time() - start_time
                )
                return title
            
            # Se não encontrar, tenta os seletores aprendidos
            for selector in self.learning_manager.get_best_selectors(domain, "title"):
                try:
                    title = await page.evaluate(f"""
                        () => {{
                            const element = document.querySelector('{selector}');
                            return element ? element.textContent : null;
                        }}
                    """)
                    
                    if title:
                        title = title.strip()
                        self.learning_manager.update_selector_score(
                            domain, "title", selector, True, time.time() - start_time
                        )
                        return title
                except Exception:
                    continue
            
            # Se ainda não encontrar, tenta detectar novos seletores
            new_selectors = await self._detect_title_selectors(page)
            if new_selectors:
                for selector in new_selectors:
                    try:
                        title = await page.evaluate(f"""
                            () => {{
                                const element = document.querySelector('{selector}');
                                return element ? element.textContent : null;
                            }}
                        """)
                        
                        if title:
                            title = title.strip()
                            self.learning_manager.update_selector_score(
                                domain, "title", selector, True, time.time() - start_time
                            )
                            return title
                    except Exception:
                        continue
            
            # Se chegou aqui, nenhum seletor funcionou
            self.learning_manager.update_selector_score(
                domain, "title", "all", False, time.time() - start_time
            )
            return None
            
        except Exception as e:
            logger.error(f"Error extracting title: {str(e)}")
            return None
    
    async def _extract_seller(self, page: Page, domain: str) -> Optional[str]:
        """Extract seller information from page."""
        try:
            start_time = time.time()
            
            # Primeiro tenta os seletores específicos da estratégia
            seller = await self._try_specific_seller_selectors(page)
            if seller:
                self.learning_manager.update_selector_score(
                    domain, "seller", "specific", True, time.time() - start_time
                )
                return seller
            
            # Se não encontrar, tenta os seletores aprendidos
            for selector in self.learning_manager.get_best_selectors(domain, "seller"):
                try:
                    seller = await page.evaluate(f"""
                        () => {{
                            const element = document.querySelector('{selector}');
                            return element ? element.textContent : null;
                        }}
                    """)
                    
                    if seller:
                        seller = seller.strip()
                        self.learning_manager.update_selector_score(
                            domain, "seller", selector, True, time.time() - start_time
                        )
                        return seller
                except Exception:
                    continue
            
            # Se ainda não encontrar, tenta detectar novos seletores
            new_selectors = await self._detect_seller_selectors(page)
            if new_selectors:
                for selector in new_selectors:
                    try:
                        seller = await page.evaluate(f"""
                            () => {{
                                const element = document.querySelector('{selector}');
                                return element ? element.textContent : null;
                            }}
                        """)
                        
                        if seller:
                            seller = seller.strip()
                            self.learning_manager.update_selector_score(
                                domain, "seller", selector, True, time.time() - start_time
                            )
                            return seller
                    except Exception:
                        continue
            
            # Se chegou aqui, nenhum seletor funcionou
            self.learning_manager.update_selector_score(
                domain, "seller", "all", False, time.time() - start_time
            )
            return None
            
        except Exception as e:
            logger.error(f"Error extracting seller: {str(e)}")
            return None
    
    async def _try_specific_price_selectors(self, page: Page) -> Optional[float]:
        """Try strategy-specific price selectors."""
        return None
    
    async def _try_specific_title_selectors(self, page: Page) -> Optional[str]:
        """Try strategy-specific title selectors."""
        return None
    
    async def _try_specific_seller_selectors(self, page: Page) -> Optional[str]:
        """Try strategy-specific seller selectors."""
        return None
    
    async def _detect_price_selectors(self, page: Page) -> List[str]:
        """Detect new price selectors."""
        try:
            # Procura por elementos que contenham preços
            selectors = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('*');
                    const priceSelectors = [];
                    
                    for (const element of elements) {
                        const text = element.textContent;
                        if (text && /R\$\s*\d+[.,]\d{2}/.test(text)) {
                            // Gera um seletor único para o elemento
                            const path = [];
                            let current = element;
                            
                            while (current && current !== document.body) {
                                let selector = current.tagName.toLowerCase();
                                if (current.id) {
                                    selector += `#${current.id}`;
                                    path.unshift(selector);
                                    break;
                                }
                                if (current.className) {
                                    selector += `.${current.className.split(' ').join('.')}`;
                                }
                                path.unshift(selector);
                                current = current.parentElement;
                            }
                            
                            priceSelectors.push(path.join(' > '));
                        }
                    }
                    
                    return priceSelectors;
                }
            """)
            
            return selectors
            
        except Exception as e:
            logger.error(f"Error detecting price selectors: {str(e)}")
            return []
    
    async def _detect_title_selectors(self, page: Page) -> List[str]:
        """Detect new title selectors."""
        try:
            # Procura por elementos que parecem títulos de produtos
            selectors = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('h1, h2, .title, .product-title');
                    const titleSelectors = [];
                    
                    for (const element of elements) {
                        const text = element.textContent;
                        if (text && text.length > 10 && text.length < 200) {
                            // Gera um seletor único para o elemento
                            const path = [];
                            let current = element;
                            
                            while (current && current !== document.body) {
                                let selector = current.tagName.toLowerCase();
                                if (current.id) {
                                    selector += `#${current.id}`;
                                    path.unshift(selector);
                                    break;
                                }
                                if (current.className) {
                                    selector += `.${current.className.split(' ').join('.')}`;
                                }
                                path.unshift(selector);
                                current = current.parentElement;
                            }
                            
                            titleSelectors.push(path.join(' > '));
                        }
                    }
                    
                    return titleSelectors;
                }
            """)
            
            return selectors
            
        except Exception as e:
            logger.error(f"Error detecting title selectors: {str(e)}")
            return []
    
    async def _detect_seller_selectors(self, page: Page) -> List[str]:
        """Detect new seller selectors."""
        try:
            # Procura por elementos que parecem informações de vendedor
            selectors = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('.seller, .vendedor, .store, .merchant');
                    const sellerSelectors = [];
                    
                    for (const element of elements) {
                        const text = element.textContent;
                        if (text && text.length > 3 && text.length < 100) {
                            // Gera um seletor único para o elemento
                            const path = [];
                            let current = element;
                            
                            while (current && current !== document.body) {
                                let selector = current.tagName.toLowerCase();
                                if (current.id) {
                                    selector += `#${current.id}`;
                                    path.unshift(selector);
                                    break;
                                }
                                if (current.className) {
                                    selector += `.${current.className.split(' ').join('.')}`;
                                }
                                path.unshift(selector);
                                current = current.parentElement;
                            }
                            
                            sellerSelectors.push(path.join(' > '));
                        }
                    }
                    
                    return sellerSelectors;
                }
            """)
            
            return selectors
            
        except Exception as e:
            logger.error(f"Error detecting seller selectors: {str(e)}")
            return [] 