from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum

class StrategyResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CAPTCHA = "captcha"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"

@dataclass
class ExtractionResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    strategy_used: Optional[str] = None
    result_type: StrategyResult = StrategyResult.UNKNOWN

class SmartScrapingAgent:
    def __init__(self, url: str, browser_manager: Any):
        self.url = url
        self.browser_manager = browser_manager
        self.domain = self._extract_domain(url)
        self.logger = logging.getLogger(__name__)
        self.strategies = []
        self.history = {}
        self.current_strategy_index = 0
        
    def _extract_domain(self, url: str) -> str:
        """Extrai o domínio da URL."""
        from urllib.parse import urlparse
        return urlparse(url).netloc
        
    async def add_strategy(self, strategy: Any) -> None:
        """Adiciona uma nova estratégia ao agente."""
        self.strategies.append(strategy)
        
    async def extract(self) -> ExtractionResult:
        """Tenta extrair dados usando todas as estratégias disponíveis."""
        for strategy in self.strategies:
            try:
                self.logger.info(f"Tentando estratégia: {strategy.__class__.__name__}")
                result = await strategy.execute(self.url, self.browser_manager)
                
                if result.success:
                    self._update_history(strategy, True)
                    return ExtractionResult(
                        success=True,
                        data=result.data,
                        strategy_used=strategy.__class__.__name__,
                        result_type=StrategyResult.SUCCESS
                    )
                    
                elif result.captcha_detected:
                    self._update_history(strategy, False, "captcha")
                    return ExtractionResult(
                        success=False,
                        error="CAPTCHA detectado",
                        strategy_used=strategy.__class__.__name__,
                        result_type=StrategyResult.CAPTCHA
                    )
                    
                elif result.blocked:
                    self._update_history(strategy, False, "blocked")
                    return ExtractionResult(
                        success=False,
                        error="Acesso bloqueado",
                        strategy_used=strategy.__class__.__name__,
                        result_type=StrategyResult.BLOCKED
                    )
                    
            except Exception as e:
                self.logger.error(f"Erro na estratégia {strategy.__class__.__name__}: {str(e)}")
                self._update_history(strategy, False, str(e))
                
        return ExtractionResult(
            success=False,
            error="Todas as estratégias falharam",
            result_type=StrategyResult.FAILURE
        )
        
    def _update_history(self, strategy: Any, success: bool, error: Optional[str] = None) -> None:
        """Atualiza o histórico de tentativas."""
        strategy_name = strategy.__class__.__name__
        if strategy_name not in self.history:
            self.history[strategy_name] = {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "last_error": None
            }
            
        self.history[strategy_name]["attempts"] += 1
        if success:
            self.history[strategy_name]["successes"] += 1
        else:
            self.history[strategy_name]["failures"] += 1
            self.history[strategy_name]["last_error"] = error
            
    def get_strategy_stats(self) -> Dict[str, Dict[str, Any]]:
        """Retorna estatísticas de todas as estratégias."""
        return self.history 