from typing import Dict, Any, Optional
import logging
from ..agent.strategy import Strategy, StrategyResult
from playwright.async_api import Page

class AmazonStrategy(Strategy):
    """Estratégia de scraping para a Amazon"""
    
    def __init__(self):
        super().__init__()
        self.selectors = {
            'title': '#productTitle',
            'price': '.a-price .a-offscreen',
            'availability': '#availability',
            'seller': '#merchant-info',
            'description': '#productDescription'
        }
    
    async def execute(self, url: str, browser_manager: Any) -> StrategyResult:
        """Execute Amazon scraping strategy."""
        try:
            # Obtém página
            page = await browser_manager.new_page()
            await page.goto(url, wait_until='networkidle')
            
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
                
            # Disponibilidade
            availability = await self._extract_availability(page)
            if availability:
                data['availability'] = availability
            else:
                data['availability'] = "Disponível" if price and price > 0 else "Indisponível"
            
            # Descrição
            description = await self._extract_description(page)
            if description:
                data['description'] = description
            
            # Verifica se é um CAPTCHA
            if await self._check_captcha(page):
                await page.close()
                return StrategyResult(
                    success=False,
                    captcha_detected=True,
                    error="CAPTCHA detectado"
                )
            
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
        """Extract price from Amazon page."""
        try:
            price_text = await page.evaluate("""
                () => {
                    const selectors = [
                        '.a-price .a-offscreen',
                        '#priceblock_ourprice',
                        '#priceblock_dealprice',
                        '.a-price-whole'
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
            logging.error(f"Error extracting Amazon price: {str(e)}")
            return None
    
    async def _extract_title(self, page: Page) -> Optional[str]:
        """Extract title from Amazon page."""
        try:
            title = await page.evaluate("""
                () => {
                    const element = document.querySelector('#productTitle');
                    return element ? element.textContent : null;
                }
            """)
            return title.strip() if title else None
            
        except Exception as e:
            logging.error(f"Error extracting Amazon title: {str(e)}")
            return None
    
    async def _extract_seller(self, page: Page) -> Optional[str]:
        """Extract seller from Amazon page."""
        try:
            seller = await page.evaluate("""
                () => {
                    const element = document.querySelector('#merchant-info');
                    return element ? element.textContent : null;
                }
            """)
            return seller.strip() if seller else "Amazon"
            
        except Exception as e:
            logging.error(f"Error extracting Amazon seller: {str(e)}")
            return None
    
    async def _extract_availability(self, page: Page) -> Optional[str]:
        """Extract availability from Amazon page."""
        try:
            availability = await page.evaluate("""
                () => {
                    const element = document.querySelector('#availability');
                    return element ? element.textContent : null;
                }
            """)
            return availability.strip() if availability else None
            
        except Exception as e:
            logging.error(f"Error extracting Amazon availability: {str(e)}")
            return None
    
    async def _extract_description(self, page: Page) -> Optional[str]:
        """Extract description from Amazon page."""
        try:
            description = await page.evaluate("""
                () => {
                    const element = document.querySelector('#productDescription');
                    return element ? element.textContent : null;
                }
            """)
            return description.strip() if description else None
            
        except Exception as e:
            logging.error(f"Error extracting Amazon description: {str(e)}")
            return None
    
    async def _check_captcha(self, page: Page) -> bool:
        """Check if page has CAPTCHA."""
        try:
            captcha = await page.evaluate("""
                () => {
                    return document.body.textContent.includes('robot') && 
                           document.body.textContent.includes('captcha');
                }
            """)
            return captcha
            
        except Exception as e:
            logging.error(f"Error checking Amazon CAPTCHA: {str(e)}")
            return False 