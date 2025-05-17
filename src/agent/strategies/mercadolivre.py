from typing import Dict, Any, List, Optional
from .base import BaseStrategy, StrategyResult
import re
import logging

class MercadoLivreStrategy(BaseStrategy):
    """Estratégia para extração de dados do Mercado Livre."""
    
    def __init__(self):
        super().__init__()
        self.priority = 100  # Alta prioridade para URLs do Mercado Livre
        self.selectors = {
            'title': '.ui-pdp-title',
            'price': '.ui-pdp-price__part .ui-pdp-price__main .ui-pdp-price__second-line',
            'description': '.ui-pdp-description__content',
            'image': '.ui-pdp-gallery__figure img',
            'rating': '.ui-pdp-review__rating',
            'reviews': '.ui-pdp-review__amount',
            'seller': '.ui-pdp-seller__info-name',
            'shipping': '.ui-pdp-media__title',
            'condition': '.ui-pdp-subtitle',
            'stock': '.ui-pdp-stock-information',
            'categories': '.ui-pdp-breadcrumb',
            'specifications': '.ui-pdp-specs__table'
        }
        
    async def execute(self, url: str, browser_manager: Any) -> StrategyResult:
        """Executa a estratégia específica para o Mercado Livre."""
        try:
            # Obtém a página
            page = await browser_manager.get_page(url)
            content = await page.content()
            
            # Verifica por CAPTCHA ou bloqueio
            if self._is_captcha(content):
                return StrategyResult(
                    success=False,
                    captcha_detected=True,
                    error="CAPTCHA detectado no Mercado Livre"
                )
                
            if self._is_blocked(content):
                return StrategyResult(
                    success=False,
                    blocked=True,
                    error="Acesso bloqueado pelo Mercado Livre"
                )
            
            # Tenta extrair dados usando seletores específicos do Mercado Livre
            data = {}
            
            # Extrai título
            title_element = await page.query_selector(self.selectors['title'])
            if title_element:
                title = await title_element.text_content()
                data['title'] = self._extract_title(title)
            
            # Extrai preço
            price_element = await page.query_selector(self.selectors['price'])
            if price_element:
                price_text = await price_element.text_content()
                data['price'] = self._process_price(price_text)
            
            # Extrai descrição
            desc_element = await page.query_selector(self.selectors['description'])
            if desc_element:
                data['description'] = await desc_element.text_content()
            
            # Extrai imagem
            img_element = await page.query_selector(self.selectors['image'])
            if img_element:
                data['image_url'] = await img_element.get_attribute('src')
            
            # Extrai avaliação
            rating_element = await page.query_selector(self.selectors['rating'])
            if rating_element:
                data['rating'] = self._process_rating(await rating_element.text_content())
            
            # Extrai número de reviews
            reviews_element = await page.query_selector(self.selectors['reviews'])
            if reviews_element:
                reviews_text = await reviews_element.text_content()
                data['reviews_count'] = self._process_reviews(reviews_text)
                
            # Extrai vendedor
            seller_element = await page.query_selector(self.selectors['seller'])
            if seller_element:
                data['seller'] = await seller_element.text_content()
                
            # Extrai informações de envio
            shipping_element = await page.query_selector(self.selectors['shipping'])
            if shipping_element:
                data['shipping'] = await shipping_element.text_content()
                
            # Extrai condição do produto
            condition_element = await page.query_selector(self.selectors['condition'])
            if condition_element:
                data['condition'] = await condition_element.text_content()
                
            # Extrai informações de estoque
            stock_element = await page.query_selector(self.selectors['stock'])
            if stock_element:
                data['stock'] = self._process_availability(await stock_element.text_content())
            
            # Extrai categorias
            categories_element = await page.query_selector(self.selectors['categories'])
            if categories_element:
                data['categories'] = self._process_categories(await categories_element.text_content())
            
            # Extrai especificações
            specifications_element = await page.query_selector(self.selectors['specifications'])
            if specifications_element:
                data['specifications'] = self._process_specifications(await specifications_element.text_content())
            
            # Valida e limpa os dados
            if self._validate_data(data):
                # Calcula confiança da extração
                confidence = self._calculate_confidence(data)
                
                return StrategyResult(
                    success=True,
                    data=data,
                    confidence=confidence
                )
            
            return StrategyResult(
                success=False,
                error="Não foi possível extrair dados essenciais do Mercado Livre"
            )
            
        except Exception as e:
            self.logger.error(f"Erro na extração do Mercado Livre: {str(e)}")
            return StrategyResult(
                success=False,
                error=str(e)
            )
            
    def _process_price(self, price: str) -> float:
        """Processa preço."""
        try:
            # Remove caracteres não numéricos
            price = re.sub(r'[^\d,.]', '', price)
            
            # Converte para float
            return float(price.replace(',', '.'))
            
        except Exception as e:
            self.logger.error(f"Erro ao processar preço: {str(e)}")
            return 0.0
            
    def _process_rating(self, rating: str) -> float:
        """Processa avaliação."""
        try:
            # Extrai número
            match = re.search(r'(\d+[.,]\d+)', rating)
            if match:
                return float(match.group(1).replace(',', '.'))
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Erro ao processar avaliação: {str(e)}")
            return 0.0
            
    def _process_reviews(self, reviews: str) -> int:
        """Processa número de reviews."""
        try:
            # Extrai número
            match = re.search(r'(\d+)', reviews)
            if match:
                return int(match.group(1))
            return 0
            
        except Exception as e:
            self.logger.error(f"Erro ao processar reviews: {str(e)}")
            return 0
            
    def _process_availability(self, availability: str) -> str:
        """Processa disponibilidade."""
        try:
            # Remove espaços extras
            availability = ' '.join(availability.split())
            
            # Verifica disponibilidade
            if 'disponível' in availability.lower():
                return 'in_stock'
            elif 'esgotado' in availability.lower():
                return 'out_of_stock'
            else:
                return 'unknown'
                
        except Exception as e:
            self.logger.error(f"Erro ao processar disponibilidade: {str(e)}")
            return 'unknown'
            
    def _process_images(self, images: str) -> List[str]:
        """Processa imagens."""
        try:
            # Extrai URLs das imagens
            urls = re.findall(r'https?://[^\s<>"]+?(?:\.jpg|\.jpeg|\.png|\.gif)', images)
            return list(set(urls))  # Remove duplicatas
            
        except Exception as e:
            self.logger.error(f"Erro ao processar imagens: {str(e)}")
            return []
            
    def _process_categories(self, categories: str) -> List[str]:
        """Processa categorias."""
        try:
            # Extrai categorias
            cats = re.findall(r'>([^<]+)<', categories)
            return [cat.strip() for cat in cats if cat.strip()]
            
        except Exception as e:
            self.logger.error(f"Erro ao processar categorias: {str(e)}")
            return []
            
    def _process_specifications(self, specs: str) -> Dict[str, str]:
        """Processa especificações."""
        try:
            # Extrai pares chave-valor
            pairs = re.findall(r'<tr[^>]*>.*?<th[^>]*>(.*?)</th>.*?<td[^>]*>(.*?)</td>', specs)
            return {k.strip(): v.strip() for k, v in pairs}
            
        except Exception as e:
            self.logger.error(f"Erro ao processar especificações: {str(e)}")
            return {}
        
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validação específica para dados do Mercado Livre."""
        if not super()._validate_data(data):
            return False
            
        # Validações específicas do Mercado Livre
        if 'price' in data and data['price']:
            # Verifica se o preço está em um intervalo razoável
            price = float(str(data['price']).replace(',', '.'))
            if price <= 0 or price > 1000000:  # Preço máximo de R$ 1 milhão
                return False
                
        if 'rating' in data and data['rating']:
            # Verifica se a avaliação está em um formato válido
            rating_match = re.search(r'(\d+[.,]\d+)', str(data['rating']))
            if not rating_match:
                return False
                
        return True 