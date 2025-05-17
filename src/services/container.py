from typing import Dict, Any, Optional, Type, TypeVar, cast
import logging
import asyncio
from .config import config
from .cache.manager import CacheManager
from .metrics.manager import MetricsManager
from .proxy.manager import ProxyManager

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ServiceContainer:
    """
    Contêiner de serviços para injeção de dependência.
    
    Gerencia o ciclo de vida dos serviços compartilhados.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
        
    async def initialize(self) -> None:
        """Inicializa todos os serviços."""
        if self._initialized:
            return
            
        # Cria instâncias dos serviços
        cache_manager = CacheManager(config.get_cache_config())
        metrics_manager = MetricsManager(config.get_metrics_config())
        proxy_manager = ProxyManager(config.get_proxy_config())
        
        # Inicializa serviços assíncronos
        await proxy_manager.initialize()
        
        # Registra serviços
        self.register('cache', cache_manager)
        self.register('metrics', metrics_manager)
        self.register('proxy', proxy_manager)
        
        self._initialized = True
        logger.info("Serviços inicializados")
        
    async def cleanup(self) -> None:
        """Limpa recursos dos serviços."""
        # Limpa serviços assíncronos
        if 'proxy' in self._services:
            await self.get('proxy').close()
            
        self._services.clear()
        self._initialized = False
        logger.info("Serviços limpos")
        
    def register(self, name: str, service: Any) -> None:
        """
        Registra um serviço no contêiner.
        
        Args:
            name: Nome do serviço
            service: Instância do serviço
        """
        self._services[name] = service
        
    def get(self, name: str) -> Any:
        """
        Obtém um serviço pelo nome.
        
        Args:
            name: Nome do serviço
            
        Returns:
            Instância do serviço
            
        Raises:
            KeyError: Se o serviço não existir
        """
        if name not in self._services:
            raise KeyError(f"Serviço não encontrado: {name}")
            
        return self._services[name]
        
    def get_typed(self, name: str, type_cls: Type[T]) -> T:
        """
        Obtém um serviço pelo nome com tipo específico.
        
        Args:
            name: Nome do serviço
            type_cls: Tipo do serviço
            
        Returns:
            Instância do serviço com o tipo especificado
            
        Raises:
            KeyError: Se o serviço não existir
            TypeError: Se o serviço não for do tipo especificado
        """
        service = self.get(name)
        
        if not isinstance(service, type_cls):
            raise TypeError(f"Serviço {name} não é do tipo {type_cls.__name__}")
            
        return cast(type_cls, service)
        
    def get_cache(self) -> CacheManager:
        """Atalho para obter o gerenciador de cache."""
        return self.get_typed('cache', CacheManager)
        
    def get_metrics(self) -> MetricsManager:
        """Atalho para obter o gerenciador de métricas."""
        return self.get_typed('metrics', MetricsManager)
        
    def get_proxy(self) -> ProxyManager:
        """Atalho para obter o gerenciador de proxy."""
        return self.get_typed('proxy', ProxyManager)
        
    def is_initialized(self) -> bool:
        """Verifica se o contêiner foi inicializado."""
        return self._initialized
        
# Instância global
container = ServiceContainer() 