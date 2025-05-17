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

class Strategy(ABC):
    """Classe base para todas as estratégias de scraping"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.success_count = 0
        self.failure_count = 0
        self.last_error = None
    
    @abstractmethod
    async def execute(self, url: str, browser_manager: Any) -> StrategyResult:
        """
        Executa a estratégia de scraping.
        
        Args:
            url: URL do produto a ser extraído
            browser_manager: Gerenciador do navegador
            
        Returns:
            StrategyResult: Resultado da extração
        """
        pass
    
    def update_stats(self, success: bool, error: Optional[str] = None) -> None:
        """Atualiza as estatísticas da estratégia"""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            self.last_error = error
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna as estatísticas da estratégia"""
        return {
            "name": self.name,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_error": self.last_error
        } 