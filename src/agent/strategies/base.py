from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class StrategyResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    captcha_detected: bool = False
    blocked: bool = False

class BaseStrategy(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.priority = 0  # Prioridade da estratégia (maior = mais importante)
        
    @abstractmethod
    async def execute(self, url: str, browser_manager: Any) -> StrategyResult:
        """Executa a estratégia de extração."""
        pass
        
    def _is_captcha(self, page_content: str) -> bool:
        """Verifica se há CAPTCHA na página."""
        captcha_indicators = [
            "captcha",
            "recaptcha",
            "verify you are human",
            "verificação de segurança",
            "verifique se você é humano"
        ]
        return any(indicator in page_content.lower() for indicator in captcha_indicators)
        
    def _is_blocked(self, page_content: str) -> bool:
        """Verifica se o acesso foi bloqueado."""
        block_indicators = [
            "access denied",
            "blocked",
            "suspicious activity",
            "too many requests",
            "acesso negado",
            "bloqueado",
            "atividade suspeita",
            "muitas requisições"
        ]
        return any(indicator in page_content.lower() for indicator in block_indicators)
        
    def _extract_price(self, text: str) -> Optional[float]:
        """Extrai preço de um texto."""
        import re
        # Padrões comuns de preço
        patterns = [
            r'R\$\s*(\d+[.,]\d{2})',  # R$ 99,99
            r'(\d+[.,]\d{2})\s*R\$',  # 99,99 R$
            r'(\d+[.,]\d{2})',        # 99,99
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return None
        
    def _extract_title(self, text: str) -> Optional[str]:
        """Extrai título de um texto."""
        # Remove caracteres especiais e espaços extras
        import re
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 10:  # Título mínimo de 10 caracteres
            return text
        return None 