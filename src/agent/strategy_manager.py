from typing import Dict, Any, List, Optional
import logging
import re
from datetime import datetime
from .strategy import Strategy
from ..config.settings import settings
from ..strategies.magalu import MagaluStrategy
from ..strategies.americanas import AmericanasStrategy
from ..strategies.amazon import AmazonStrategy

class StrategyManager:
    """Gerenciador de estratégias de scraping"""
    
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.logger = logging.getLogger("strategy_manager")
        self._load_strategies()
        
    def _load_strategies(self) -> None:
        """Carrega estratégias da configuração."""
        try:
            # Registra estratégias específicas para domínios comuns
            self.register_strategy(MagaluStrategy())
            self.register_strategy(AmericanasStrategy())
            self.register_strategy(AmazonStrategy())
            self.logger.info(f"Estratégias carregadas: {len(self.strategies)}")
                    
        except Exception as e:
            self.logger.error(f"Erro ao carregar estratégias: {str(e)}")
            
    def register_strategy(self, strategy: Strategy) -> None:
        """
        Registra uma nova estratégia.
        
        Args:
            strategy: Estratégia a ser registrada
        """
        self.strategies[strategy.name] = strategy
        self.logger.info(f"Estratégia {strategy.name} registrada")
    
    def unregister_strategy(self, strategy_name: str) -> None:
        """
        Remove uma estratégia registrada.
        
        Args:
            strategy_name: Nome da estratégia a ser removida
        """
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            self.logger.info(f"Estratégia {strategy_name} removida")
    
    def get_strategy(self, strategy_name: str) -> Optional[Strategy]:
        """
        Retorna uma estratégia pelo nome.
        
        Args:
            strategy_name: Nome da estratégia
            
        Returns:
            Strategy: Estratégia encontrada ou None
        """
        return self.strategies.get(strategy_name)
    
    def get_strategies(self) -> List[Strategy]:
        """
        Retorna todas as estratégias registradas.
        
        Returns:
            List[Strategy]: Lista de estratégias
        """
        return list(self.strategies.values())
    
    def get_strategy_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Retorna estatísticas de todas as estratégias.
        
        Returns:
            Dict[str, Dict[str, Any]]: Estatísticas das estratégias
        """
        return {
            name: strategy.get_stats()
            for name, strategy in self.strategies.items()
        }
            
    def get_strategy_for_url(self, url: str) -> Optional[Strategy]:
        """Retorna estratégia adequada para URL."""
        try:
            if "magazineluiza.com.br" in url:
                return self.get_strategy("MagaluStrategy")
            elif "americanas.com.br" in url:
                return self.get_strategy("AmericanasStrategy")
            elif "amazon.com.br" in url:
                return self.get_strategy("AmazonStrategy")
            
            # Se não encontrar nenhuma estratégia específica, retorna None
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estratégia: {str(e)}")
            return None
            
    def add_strategy(self, strategy: Strategy) -> bool:
        """Adiciona nova estratégia."""
        try:
            # Verifica se já existe
            if self.get_strategy(strategy.name):
                self.logger.warning(f"Estratégia {strategy.name} já existe")
                return False
                
            self.strategies[strategy.name] = strategy
            self.logger.info(f"Estratégia {strategy.name} adicionada")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao adicionar estratégia: {str(e)}")
            return False
            
    def remove_strategy(self, name: str) -> bool:
        """Remove estratégia."""
        try:
            strategy = self.get_strategy(name)
            if not strategy:
                self.logger.warning(f"Estratégia {name} não encontrada")
                return False
                
            del self.strategies[name]
            self.logger.info(f"Estratégia {name} removida")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao remover estratégia: {str(e)}")
            return False
            
    def update_strategy(self, name: str, config: Dict[str, Any]) -> bool:
        """Atualiza estratégia existente."""
        try:
            strategy = self.get_strategy(name)
            if not strategy:
                self.logger.warning(f"Estratégia {name} não encontrada")
                return False
                
            # Atualiza configuração
            strategy.patterns = config.get('patterns', strategy.patterns)
            strategy.selectors = config.get('selectors', strategy.selectors)
            strategy.confidence = config.get('confidence', strategy.confidence)
            
            self.logger.info(f"Estratégia {name} atualizada")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar estratégia: {str(e)}")
            return False