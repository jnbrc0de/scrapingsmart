from typing import Dict, Any, List, Optional
from .base import BaseStrategy, StrategyResult
import re
import logging
from ..strategy import Strategy
from ..browser import BrowserManager

class AmazonStrategy(Strategy):
    """Estratégia para extração de dados da Amazon."""
    
    def __init__(self):
        super().__init__(
            name='amazon',
            patterns=[
                r'amazon\.com\.br',
                r'amazon\.com'
            ],
            selectors={
                'title': '#productTitle',
                'price': '#priceblock_ourprice, #priceblock_dealprice, .a-price .a-offscreen',
                'seller': '#sellerProfileTriggerId, #merchant-info',
                'rating': '#acrPopover',
                'reviews': '#acrCustomerReviewText',
                'availability': '#availability',
                'description': '#productDescription',
                'images': '#landingImage, #imgBlkFront',
                'categories': '#wayfinding-breadcrumbs_feature_div',
                'specifications': '#productDetails_techSpec_section_1, #productDetails_detailBullets_sections1'
            },
            confidence=0.9
        )
        
    async def _extract_data(self, page: Any) -> Dict[str, Any]:
        """Extrai dados da página da Amazon."""
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
            self.logger.error(f"Erro na extração da Amazon: {str(e)}")
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
            if 'em estoque' in availability.lower():
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

    def _extract_reviews_count(self, text: str) -> Optional[int]:
        """Extrai o número de reviews de um texto."""
        if not text:
            return None
            
        match = re.search(r'(\d+(?:,\d+)*)', text)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None
        
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validação específica para dados da Amazon."""
        if not super()._validate_data(data):
            return False
            
        # Validações específicas da Amazon
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