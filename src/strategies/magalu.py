from typing import Dict, Any
import logging
from ..agent.strategy import Strategy, StrategyResult

class MagaluStrategy(Strategy):
    """Estratégia de scraping para o Magazine Luiza"""
    
    def __init__(self):
        super().__init__()
        self.selectors = {
            'title': 'h1[data-testid="heading-product-title"]',
            'price': 'p[data-testid="price-value"]',
            'availability': 'p[data-testid="availability"]',
            'seller': 'p[data-testid="seller-name"]',
            'description': 'div[data-testid="product-description"]'
        }
    
    async def execute(self, url: str, browser_manager: Any) -> StrategyResult:
        """
        Executa a estratégia de scraping para o Magazine Luiza.
        
        Args:
            url: URL do produto
            browser_manager: Gerenciador do navegador
            
        Returns:
            StrategyResult: Resultado da extração
        """
        try:
            # Abre a página
            page = await browser_manager.new_page()
            response = await page.goto(url)
            
            # Verifica se a página não foi encontrada (404)
            if response.status == 404:
                await page.close()
                return StrategyResult(
                    success=False,
                    error="Página não encontrada (404)"
                )
            
            # Extrai os dados
            data = {}
            
            # Título
            title_element = await page.query_selector(self.selectors['title'])
            if title_element:
                data['title'] = await title_element.text_content()
            
            # Preço - tenta múltiplos seletores
            price = await self._extract_price(page)
            if price > 0:
                data['price'] = price
            
            # Disponibilidade
            availability_element = await page.query_selector(self.selectors['availability'])
            if availability_element:
                data['availability'] = await availability_element.text_content()
            else:
                # Fallback para disponibilidade
                data['availability'] = "Disponível" if price and price > 0 else "Indisponível"
            
            # Vendedor
            seller_element = await page.query_selector(self.selectors['seller'])
            if seller_element:
                data['seller'] = await seller_element.text_content()
            
            # Descrição
            description_element = await page.query_selector(self.selectors['description'])
            if description_element:
                data['description'] = await description_element.text_content()
            
            # Verifica se é um CAPTCHA
            if await self._check_captcha(page):
                await page.close()
                return StrategyResult(
                    success=False,
                    captcha_detected=True,
                    error="CAPTCHA detectado"
                )
            
            # Verifica se está bloqueado
            if await self._check_blocked(page):
                await page.close()
                return StrategyResult(
                    success=False,
                    blocked=True,
                    error="Acesso bloqueado"
                )
            
            # Verifica se temos pelo menos o título e o preço
            if not data.get('title') or 'price' not in data:
                await page.close()
                return StrategyResult(
                    success=False,
                    error="Não foi possível extrair informações essenciais do produto"
                )
            
            # Atualiza estatísticas
            self.update_stats(True)
            await page.close()
            
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
    
    async def _extract_price(self, page: Any) -> float:
        """Extrai o preço usando múltiplos seletores e técnicas"""
        try:
            # Primeiro tenta os seletores padrão
            price_element = await page.query_selector(self.selectors['price'])
            if price_element:
                price_text = await price_element.text_content()
                price = self._clean_price(price_text)
                if price > 0:
                    return price
            
            # Se não conseguir, tenta seletores alternativos através de JavaScript
            price_text = await page.evaluate("""
                () => {
                    const selectors = [
                        'p[data-testid="price-value"]',
                        '.price-template__text',
                        '.price-template-price',
                        '.price-template-big',
                        '.price__value',
                        '[itemprop="price"]'
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
                return self._clean_price(price_text)
            
            return 0.0
        except Exception as e:
            logging.error(f"Erro ao extrair preço: {str(e)}")
            return 0.0
    
    def _clean_price(self, price_text: str) -> float:
        """Limpa o texto do preço e converte para float"""
        try:
            if not price_text:
                return 0.0
                
            # Remove R$ e espaços
            price_text = price_text.replace('R$', '').strip()
            # Remove pontos de milhares
            price_text = price_text.replace('.', '')
            # Substitui vírgula por ponto
            price_text = price_text.replace(',', '.')
            
            # Extrai apenas números e pontos
            import re
            price_text = re.sub(r'[^\d.]+', '', price_text)
            
            # Converte para float
            price = float(price_text)
            return price
        except Exception as e:
            logging.error(f"Erro ao limpar preço: {price_text} - {str(e)}")
            return 0.0
    
    async def _check_captcha(self, page: Any) -> bool:
        """Verifica se há CAPTCHA na página"""
        try:
            captcha_element = await page.query_selector('div[class*="captcha"]')
            if captcha_element:
                return True
                
            # Verifica conteúdo da página
            has_captcha = await page.evaluate("""
                () => {
                    return document.body.textContent.includes('captcha') ||
                           document.body.textContent.includes('CAPTCHA') ||
                           document.body.textContent.includes('robot') ||
                           document.body.textContent.includes('verificação');
                }
            """)
            return has_captcha
        except:
            return False
    
    async def _check_blocked(self, page: Any) -> bool:
        """Verifica se o acesso está bloqueado"""
        try:
            blocked_element = await page.query_selector('div[class*="blocked"]')
            if blocked_element:
                return True
                
            # Verifica conteúdo da página
            is_blocked = await page.evaluate("""
                () => {
                    return document.body.textContent.includes('bloqueado') ||
                           document.body.textContent.includes('blocked') ||
                           document.body.textContent.includes('acesso negado') ||
                           document.body.textContent.includes('access denied');
                }
            """)
            return is_blocked
        except:
            return False 