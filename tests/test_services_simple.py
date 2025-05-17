import pytest
import os
import asyncio
from pathlib import Path

from src.services.config import config
from src.services.container import container
from src.services.cache import CacheManager
from src.services.metrics import MetricsManager
from src.services.proxy import ProxyManager

# Configuração do asyncio para Windows
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

@pytest.mark.asyncio
async def test_services():
    """Testa todos os serviços em uma única função."""
    try:
        # Inicializa o contêiner
        await container.initialize()
        
        # Testa o contêiner
        assert container.is_initialized()
        assert container.get('cache') is not None
        assert container.get('metrics') is not None
        assert container.get('proxy') is not None
        assert isinstance(container.get_cache(), CacheManager)
        assert isinstance(container.get_metrics(), MetricsManager)
        assert isinstance(container.get_proxy(), ProxyManager)
        
        # Testa o cache
        cache = container.get_cache()
        test_key = "test_key"
        test_value = {"name": "Test", "value": 42}
        assert cache.set(test_key, test_value)
        cached_value = cache.get(test_key)
        assert cached_value is not None
        assert cached_value == test_value
        assert cache.delete(test_key)
        assert cache.get(test_key) is None
        
        # Testa métricas
        metrics = container.get_metrics()
        # Nome da estratégia para teste
        strategy_name = "test"
        metrics.record_extraction(strategy_name, True, 1.5, 0.9)
        metrics.record_error(strategy_name, "connection_error")
        metrics.record_cache(strategy_name, True)  # Hit
        
        # Obtém resumo e verifica métricas
        summary = metrics.get_metrics_summary()
        assert summary["extractions"]["total"] > 0
        assert summary["extractions"]["success"] > 0
        assert summary["errors"] > 0
        assert summary["cache"]["hits"] > 0
        
        # Verifica se a estratégia está nas estatísticas
        assert strategy_name in summary["strategies"]
        strategy_stats = summary["strategies"][strategy_name]
        assert strategy_stats["extractions"]["total"] > 0
        assert strategy_stats["extractions"]["success"] > 0
        
        # Testa proxy
        proxy = container.get_proxy()
        assert proxy.is_initialized
        ip = await proxy.get_current_ip()
        assert ip is not None
        proxy_config = await proxy.get_proxy_config()
        if proxy.config['enabled']:
            assert proxy_config is not None
        stats = proxy.get_stats()
        assert stats["current_ip"] is not None
        
        # Testa config
        assert config.get('cache.memory_enabled') is not None
        assert config.get('proxy.rotation_interval') is not None
        assert config.get('browser.headless') is not None
        original_value = config.get('browser.headless')
        config.set('browser.headless', not original_value)
        assert config.get('browser.headless') == (not original_value)
        config.set('browser.headless', original_value)
        
    finally:
        # Limpa recursos
        await container.cleanup()

if __name__ == "__main__":
    asyncio.run(test_services()) 