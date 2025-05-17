from typing import Dict, Any, Optional, List
import logging
import asyncio
import time
from datetime import datetime
from .browser import BrowserManager
from .strategy_manager import StrategyManager
from .history_manager import HistoryManager
from .cache_manager import CacheManager
from .metrics_manager import MetricsManager
from .notifier import Notifier
from .config import settings

class Extractor:
    """Gerenciador de extração de dados."""
    
    def __init__(self):
        self.logger = logging.getLogger("extractor")
        self.browser_manager = BrowserManager()
        self.strategy_manager = StrategyManager()
        self.history_manager = HistoryManager()
        self.cache_manager = CacheManager()
        self.metrics_manager = MetricsManager()
        self.notifier = Notifier(settings.alert)
        
    async def extract(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """Extrai dados de uma URL."""
        start_time = time.time()
        
        try:
            # Verifica cache
            if use_cache:
                cached_data = self.cache_manager.get(url)
                if cached_data:
                    self.metrics_manager.record_cache(self.strategy_manager.get_strategy_for_url(url).name, True)
                    return cached_data['value']
                    
            # Obtém estratégia
            strategy = self.strategy_manager.get_strategy_for_url(url)
            if not strategy:
                error_msg = f"Nenhuma estratégia adequada encontrada para {url}"
                self.logger.error(error_msg)
                self.metrics_manager.record_error('unknown', 'no_strategy')
                self.notifier.notify_error(error_msg)
                return {'error': error_msg}
                
            # Executa estratégia
            result = await strategy.execute(url, self.browser_manager)
            
            # Registra métricas
            duration = time.time() - start_time
            self.metrics_manager.record_extraction(
                strategy.name,
                result.success,
                duration,
                result.confidence
            )
            
            if not result.success:
                # Registra erro
                self.metrics_manager.record_error(strategy.name, result.error)
                self.notifier.notify_error(
                    f"Erro na extração de {url}",
                    {'error': result.error}
                )
                return {'error': result.error}
                
            # Salva no cache
            if use_cache:
                self.cache_manager.set(url, result.data)
                self.metrics_manager.record_cache(strategy.name, False)
                
            # Salva no histórico
            self.history_manager.save_extraction(url, result.data, strategy.name)
            
            # Notifica sucesso
            self.notifier.notify_success(
                f"Dados extraídos com sucesso de {url}",
                {
                    'strategy': strategy.name,
                    'confidence': result.confidence
                }
            )
            
            return result.data
            
        except Exception as e:
            # Registra erro
            error_msg = str(e)
            self.logger.error(f"Erro na extração: {error_msg}")
            self.metrics_manager.record_error('unknown', 'exception')
            self.notifier.notify_error(
                f"Erro na extração de {url}",
                {'error': error_msg}
            )
            return {'error': error_msg}
            
    async def extract_batch(self, urls: List[str], 
                          use_cache: bool = True,
                          max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """Extrai dados de múltiplas URLs."""
        results = []
        
        # Cria semáforo para limitar concorrência
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.extract(url, use_cache)
                
        # Executa extrações em paralelo
        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        return results
        
    async def extract_with_retry(self, url: str, max_retries: int = 3,
                               use_cache: bool = True) -> Dict[str, Any]:
        """Extrai dados com tentativas de retry."""
        for attempt in range(max_retries):
            try:
                result = await self.extract(url, use_cache)
                
                if 'error' not in result:
                    return result
                    
                # Aguarda antes de tentar novamente
                if attempt < max_retries - 1:
                    await asyncio.sleep(settings.retry.delay)
                    
            except Exception as e:
                self.logger.error(f"Erro na tentativa {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(settings.retry.delay)
                    
        return {'error': 'Máximo de tentativas excedido'}
        
    async def close(self) -> None:
        """Fecha recursos do extrator."""
        try:
            await self.browser_manager.close()
            self.logger.info("Recursos do extrator fechados")
            
        except Exception as e:
            self.logger.error(f"Erro ao fechar recursos: {str(e)}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do extrator."""
        try:
            return {
                'browser': self.browser_manager.get_stats(),
                'strategies': self.strategy_manager.get_strategy_stats(),
                'history': self.history_manager.get_history_stats(),
                'cache': self.cache_manager.get_stats(),
                'metrics': self.metrics_manager.get_metrics_summary()
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {} 