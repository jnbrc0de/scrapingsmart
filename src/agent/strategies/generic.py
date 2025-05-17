from typing import Dict, Any, Optional, List
from .base import BaseStrategy, StrategyResult
import re
import logging
from bs4 import BeautifulSoup

class GenericStrategy(BaseStrategy):
    """Estratégia genérica para extração de dados de qualquer site."""
    
    def __init__(self):
        super().__init__()
        self.priority = 0  # Baixa prioridade para URLs genéricas
        self.common_selectors = {
            'title': [
                'h1', '.product-title', '.item-title', '.title',
                '[itemprop="name"]', '.product-name', '.productName'
            ],
            'price': [
                '[itemprop="price"]', '.price', '.product-price',
                '.current-price', '.sale-price', '.regular-price'
            ],
            'description': [
                '[itemprop="description"]', '.description', '.product-description',
                '.item-description', '.details', '.product-details'
            ],
            'image': [
                '[itemprop="image"]', '.product-image img', '.item-image img',
                '.main-image img', '.gallery-image img'
            ],
            'rating': [
                '[itemprop="ratingValue"]', '.rating', '.product-rating',
                '.item-rating', '.stars'
            ],
            'reviews': [
                '[itemprop="reviewCount"]', '.review-count', '.product-reviews',
                '.item-reviews', '.total-reviews'
            ]
        }
        
    async def execute(self, url: str, browser_manager: Any) -> StrategyResult:
        """Executa a estratégia genérica para extração de dados."""
        try:
            # Obtém a página
            page = await browser_manager.get_page(url)
            content = await page.content()
            
            # Verifica por CAPTCHA ou bloqueio
            if self._is_captcha(content):
                return StrategyResult(
                    success=False,
                    captcha_detected=True,
                    error="CAPTCHA detectado"
                )
                
            if self._is_blocked(content):
                return StrategyResult(
                    success=False,
                    blocked=True,
                    error="Acesso bloqueado"
                )
            
            # Tenta extrair dados usando seletores comuns
            data = {}
            soup = self._parse_html(content)
            
            # Extrai título
            title = self._find_element(soup, self.common_selectors['title'])
            if title:
                data['title'] = self._extract_title(title)
            
            # Extrai preço
            price = self._find_element(soup, self.common_selectors['price'])
            if price:
                data['price'] = self._extract_price(price)
            
            # Extrai descrição
            description = self._find_element(soup, self.common_selectors['description'])
            if description:
                data['description'] = self._clean_text(description)
            
            # Extrai imagem
            image = self._find_element(soup, self.common_selectors['image'], attr='src')
            if image:
                data['image_url'] = image
            
            # Extrai avaliação
            rating = self._find_element(soup, self.common_selectors['rating'])
            if rating:
                data['rating'] = self._extract_rating(rating)
            
            # Extrai número de reviews
            reviews = self._find_element(soup, self.common_selectors['reviews'])
            if reviews:
                data['reviews_count'] = self._extract_reviews_count(reviews)
            
            # Tenta extrair dados adicionais usando heurísticas
            self._extract_additional_data(soup, data)
            
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
                error="Não foi possível extrair dados essenciais"
            )
            
        except Exception as e:
            self.logger.error(f"Erro na extração genérica: {str(e)}")
            return StrategyResult(
                success=False,
                error=str(e)
            )
            
    def _find_element(self, soup: BeautifulSoup, selectors: List[str], attr: Optional[str] = None) -> Optional[str]:
        """Tenta encontrar um elemento usando uma lista de seletores."""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if attr:
                    return element.get(attr)
                return element.text.strip()
        return None
        
    def _extract_rating(self, text: str) -> Optional[float]:
        """Extrai avaliação de um texto."""
        if not text:
            return None
            
        # Tenta encontrar números com ponto ou vírgula
        match = re.search(r'(\d+[.,]\d+)', text)
        if match:
            try:
                return float(match.group(1).replace(',', '.'))
            except ValueError:
                pass
                
        # Tenta encontrar números inteiros
        match = re.search(r'(\d+)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
                
        return None
        
    def _extract_additional_data(self, soup: BeautifulSoup, data: Dict[str, Any]) -> None:
        """Tenta extrair dados adicionais usando heurísticas."""
        # Procura por metadados
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name', '').lower()
            content = tag.get('content', '')
            
            if 'price' in name and not data.get('price'):
                data['price'] = self._extract_price(content)
            elif 'description' in name and not data.get('description'):
                data['description'] = self._clean_text(content)
            elif 'image' in name and not data.get('image_url'):
                data['image_url'] = content
                
        # Procura por dados estruturados
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                import json
                json_data = json.loads(script.string)
                if isinstance(json_data, dict):
                    if 'price' in json_data and not data.get('price'):
                        data['price'] = self._extract_price(str(json_data['price']))
                    if 'description' in json_data and not data.get('description'):
                        data['description'] = self._clean_text(json_data['description'])
                    if 'image' in json_data and not data.get('image_url'):
                        data['image_url'] = json_data['image']
            except:
                continue
                
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validação específica para dados genéricos."""
        if not super()._validate_data(data):
            return False
            
        # Validações específicas para dados genéricos
        if 'price' in data and data['price']:
            # Verifica se o preço está em um intervalo razoável
            price = float(str(data['price']).replace(',', '.'))
            if price <= 0 or price > 1000000:  # Preço máximo de R$ 1 milhão
                return False
                
        if 'rating' in data and data['rating']:
            # Verifica se a avaliação está em um intervalo válido
            rating = float(str(data['rating']).replace(',', '.'))
            if rating < 0 or rating > 5:  # Avaliação de 0 a 5
                return False
                
        return True 