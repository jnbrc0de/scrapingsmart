from typing import Dict, Any, List
import logging
import re
from ..strategy import Strategy, StrategyResult
from ..browser import BrowserManager

class MagaluStrategy(Strategy):
    """Estratégia para extração de dados da Magazine Luiza."""
    
    def __init__(self):
        super().__init__(
            name='magalu',
            patterns=[
                r'magazineluiza\.com\.br'
            ],
            selectors={
                'title': '[data-testid="heading-product-title"]',
                'price': '[data-testid="price-value"]',
                'seller': '[data-testid="seller-name"]',
                'rating': '[data-testid="rating-value"]',
                'reviews': '[data-testid="rating-count"]',
                'availability': '[data-testid="availability"]',
                'description': '[data-testid="description"]',
                'images': '[data-testid="image-selected-thumbnail"] img',
                'categories': '[data-testid="breadcrumb"]',
                'specifications': '[data-testid="specifications"]'
            },
            confidence=0.9
        )
        
    async def _extract_data(self, page: Any) -> Dict[str, Any]:
        """Extrai dados da página da Magazine Luiza."""
        try:
            data = await super()._extract_data(page)
            
            # Processa preço
            if 'price' in data and data['price']:
                data['price'] = self._process_price(data['price'])
                
            # Processa avaliação
            if 'rating' in data and data['rating']:
                data['rating'] = self._process_rating(data['rating'])
                
            # Processa reviews
            if 'reviews' in data and data['reviews']:
                data['reviews'] = self._process_reviews(data['reviews'])
                
            # Processa disponibilidade
            if 'availability' in data and data['availability']:
                data['availability'] = self._process_availability(data['availability'])
                
            # Processa imagens
            if 'images' in data and data['images']:
                data['images'] = self._process_images(data['images'])
                
            # Processa categorias
            if 'categories' in data and data['categories']:
                data['categories'] = self._process_categories(data['categories'])
                
            # Processa especificações
            if 'specifications' in data and data['specifications']:
                data['specifications'] = self._process_specifications(data['specifications'])
                
            return data
            
        except Exception as e:
            self.logger.error(f"Erro na extração da Magazine Luiza: {str(e)}")
            return {}
            
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