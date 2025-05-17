from typing import Dict, List, Any, Optional, Type
from loguru import logger
from datetime import datetime, timedelta
from src.config.settings import settings
from src.strategies.base import BaseStrategy
from src.strategies.amazon import AmazonStrategy
from src.strategies.magalu import MagaluStrategy
from src.strategies.americanas import AmericanasStrategy
from src.strategies.generic import GenericMarketplaceStrategy
from urllib.parse import urlparse

class StrategyManager:
    """Gerencia estratégias de scraping para diferentes domínios."""
    
    def __init__(self, config=None):
        self.config = config or settings
        self._setup_logging()
        self.strategies: Dict[str, Type[BaseStrategy]] = {}
        self._load_strategies()
    
    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(self.config.LOG_DIR / "strategy_{time}.log"),
            rotation=self.config.LOG_ROTATION_SIZE,
            retention=f"{self.config.LOG_RETENTION_DAYS} days",
            level=self.config.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def _load_strategies(self):
        """Carrega todas as estratégias disponíveis."""
        try:
            # Registra estratégias disponíveis
            self.strategies = {
                "amazon.com.br": AmazonStrategy,
                "amazon.com": AmazonStrategy,
                "magazineluiza.com.br": MagaluStrategy,
                "americanas.com.br": AmericanasStrategy,
                # Demais marketplaces conhecidos (usam a genérica por padrão)
                "mercadolivre.com.br": GenericMarketplaceStrategy,
                "casasbahia.com.br": GenericMarketplaceStrategy,
                "kabum.com.br": GenericMarketplaceStrategy,
                "pontofrio.com.br": GenericMarketplaceStrategy,
                "extra.com.br": GenericMarketplaceStrategy,
                "carrefour.com.br": GenericMarketplaceStrategy,
                "site.fastshop.com.br": GenericMarketplaceStrategy,
            }
            logger.info(f"Loaded {len(self.strategies)} strategies")
        except Exception as e:
            logger.error(f"Error loading strategies: {str(e)}")
            raise
    
    async def initialize(self):
        """Initialize strategy manager."""
        for strategy in self.strategies.values():
            await strategy().initialize()
        logger.info("Strategy manager initialized")
    
    async def cleanup(self):
        """Clean up strategy manager resources."""
        for strategy in self.strategies.values():
            await strategy().cleanup()
        logger.info("Strategy manager cleaned up")
    
    def get_strategy(self, url: str) -> Optional[BaseStrategy]:
        """Retorna a estratégia apropriada para a URL."""
        try:
            domain = urlparse(url).netloc
            if not domain:
                raise ValueError("Invalid URL: no domain found")
            
            # Tenta encontrar uma estratégia específica para o domínio
            strategy_class = self.strategies.get(domain)
            if strategy_class:
                return strategy_class()
            
            # Se não encontrar, tenta encontrar uma estratégia genérica para domínios conhecidos
            for domain_pattern, strategy_class in self.strategies.items():
                if domain.endswith(domain_pattern):
                    return strategy_class()
            
            # Fallback: retorna a estratégia genérica para qualquer domínio
            logger.warning(f"No specific strategy found for domain: {domain}. Using GenericMarketplaceStrategy.")
            return GenericMarketplaceStrategy()
            
        except Exception as e:
            logger.error(f"Error getting strategy: {str(e)}")
            return GenericMarketplaceStrategy()
    
    async def execute_strategy(self, url: str, browser: Any) -> Dict[str, Any]:
        """Executa a estratégia apropriada para a URL."""
        try:
            strategy = self.get_strategy(url)
            if not strategy:
                return {
                    "status": "error",
                    "error": f"No strategy found for URL: {url}"
                }
            
            return await strategy.execute(url, browser)
            
        except Exception as e:
            logger.error(f"Error executing strategy: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_strategy_stats(self, domain: str = None) -> Dict:
        """Get statistics for strategies."""
        stats = {}
        
        if domain:
            if domain in self.strategies:
                stats[domain] = await self.get_strategy(domain).get_stats()
        else:
            for domain, strategy_class in self.strategies.items():
                strategy = strategy_class()
                stats[domain] = await strategy.get_stats()
        
        return stats

    async def get_strategies(self, domain: str) -> List[Dict[str, Any]]:
        """Obtém estratégias para um domínio específico."""
        # Se não temos estratégias ou precisamos atualizar
        if domain not in self.strategies or self._needs_update(domain):
            await self._load_strategies()
        
        strategy = self.get_strategy(domain)
        return strategy.strategies if strategy else []

    async def update_success(self, strategy_id: str):
        """Atualiza métricas após sucesso de uma estratégia."""
        for domain, strategy_class in self.strategies.items():
            strategy = strategy_class()
            for strategy_info in self.get_strategies(domain):
                if strategy_info['id'] == strategy_id:
                    strategy_info['success_count'] = strategy_info.get('success_count', 0) + 1
                    strategy_info['last_success'] = datetime.now()
                    strategy_info['confidence'] = min(1.0, strategy_info.get('confidence', 0.5) + 0.1)
                    break

    async def update_failure(self, strategy_id: str):
        """Atualiza métricas após falha de uma estratégia."""
        for domain, strategy_class in self.strategies.items():
            strategy = strategy_class()
            for strategy_info in self.get_strategies(domain):
                if strategy_info['id'] == strategy_id:
                    strategy_info['failure_count'] = strategy_info.get('failure_count', 0) + 1
                    strategy_info['confidence'] = max(0.1, strategy_info.get('confidence', 0.5) - 0.1)
                    break

    def _needs_update(self, domain: str) -> bool:
        """Verifica se as estratégias precisam ser atualizadas."""
        if domain not in self.last_update:
            return True
        
        return (
            datetime.now() - self.last_update[domain] > 
            self.update_interval
        ) 