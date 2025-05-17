from typing import Dict, Any, Optional
import logging
from ..agent.strategy import Strategy, StrategyResult
from playwright.async_api import Page

class AmericanasStrategy(Strategy):
    """Estratégia de scraping para as Americanas"""
    
    def __init__(self):
        super().__init__()
        self.selectors = {
            'title': '[data-testid="heading-product-title"]',
            'price': '[data-testid="price-value"]',
            'availability': '[data-testid="availability"]',
            'seller': '[data-testid="seller-name"]',
            'description': '[data-testid="product-description"]'
        }
    
    async def execute(self, url: str, browser_manager: Any) -> StrategyResult:
        """Execute Americanas scraping strategy."""
        try:
            # Obtém página
            page = await browser_manager.new_page()
            await page.goto(url)
            
            # Extrai dados
            data = {}
            
            # Título
            title = await self._extract_title(page)
            if title:
                data['title'] = title
            
            # Preço
            price = await self._extract_price(page)
            if price:
                data['price'] = price
            
            # Vendedor
            seller = await self._extract_seller(page)
            if seller:
                data['seller'] = seller
                
            # Disponibilidade (verificação simplificada)
            data['availability'] = "Disponível" if price and price > 0 else "Indisponível"
            
            # Fecha página
            await page.close()
            
            # Atualiza estatísticas
            self.update_stats(True)
            
            # Retorna resultado
            return StrategyResult(
                success=True,
                data=data
            )
            
        except Exception as e:
            self.update_stats(False, str(e))
            return StrategyResult(
                success=False,
                error=str(e)
            )
    
    async def _extract_price(self, page: Page) -> Optional[float]:
        """Extract price from Americanas page."""
        try:
            # Tenta diferentes seletores específicos das Americanas
            price_text = await page.evaluate("""
                () => {
                    const selectors = [
                        '[data-testid="price-value"]',
                        '.price__CurrentPrice-sc-1q8vx0m-1',
                        '.price__CurrentPrice',
                        '.price__Value'
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            return element.textContent;
                        }
                    }
                    return null;
                }
            """)
            
            if price_text:
                # Remove R$ e converte para float
                price = float(price_text.replace('R$', '').replace('.', '').replace(',', '.').strip())
                return price
            
            return None
            
        except Exception as e:
            logging.error(f"Error extracting Americanas price: {str(e)}")
            return None
    
    async def _extract_title(self, page: Page) -> Optional[str]:
        """Extract title from Americanas page."""
        try:
            title = await page.evaluate("""
                () => {
                    const selectors = [
                        '[data-testid="heading-product-title"]',
                        '.product-title',
                        '.title__Title-sc-1q8vx0m-0'
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            return element.textContent;
                        }
                    }
                    return null;
                }
            """)
            return title.strip() if title else None
            
        except Exception as e:
            logging.error(f"Error extracting Americanas title: {str(e)}")
            return None
    
    async def _extract_seller(self, page: Page) -> Optional[str]:
        """Extract seller from Americanas page."""
        try:
            seller = await page.evaluate("""
                () => {
                    const selectors = [
                        '[data-testid="seller-name"]',
                        '.seller-name',
                        '.seller__name'
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            return element.textContent;
                        }
                    }
                    return null;
                }
            """)
            return seller.strip() if seller else None
            
        except Exception as e:
            logging.error(f"Error extracting Americanas seller: {str(e)}")
            return None 