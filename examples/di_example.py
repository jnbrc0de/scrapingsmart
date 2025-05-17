import os
import asyncio
import logging
from datetime import datetime
from src.services.container import container
from src.services.config import config
from src.browser.manager_di import BrowserManager
from src.strategies.magalu import MagaluStrategy

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configura o evento loop para Windows
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def run_example():
    """Executa exemplo de scraping usando injeção de dependência."""
    # Inicializa contêiner de serviços
    logger.info("Inicializando serviços...")
    await container.initialize()
    
    # Obtém serviços
    cache = container.get_cache()
    metrics = container.get_metrics()
    
    # Inicializa navegador
    browser_manager = BrowserManager()
    await browser_manager.initialize()
    
    # URL de teste
    url = "https://www.magazineluiza.com.br/apple-iphone-16-128gb-rosa-61-48mp-ios-5g/p/238802900/te/ip16/"
    domain = "magazineluiza.com.br"
    
    # Verifica cache
    cached_data = cache.get(url)
    if cached_data:
        logger.info(f"Dados encontrados no cache: {cached_data}")
        metrics.record_cache(domain, True)  # Hit
        await cleanup(browser_manager)
        return cached_data
        
    metrics.record_cache(domain, False)  # Miss
    
    try:
        # Criar estratégia
        strategy = MagaluStrategy()
        
        # Registrar início da extração
        start_time = datetime.now()
        
        # Executar scraping
        page = await browser_manager.new_page(domain)
        result = await strategy.execute(url, browser_manager)
        
        # Calcular duração
        duration = (datetime.now() - start_time).total_seconds()
        
        # Registrar métricas
        metrics.record_extraction(domain, result.success, duration)
        
        if result.captcha_detected:
            metrics.record_captcha(domain)
            
        if result.blocked:
            metrics.record_block(domain)
            
        if not result.success:
            metrics.record_error(domain, result.error or "unknown_error")
            
        # Armazenar no cache se bem-sucedido
        if result.success and result.data:
            cache.set(url, result.data)
            
        # Exibir resultados
        if result.success:
            logger.info(f"Resultados: {result.data}")
        else:
            logger.error(f"Falha na extração: {result.error}")
            
        # Exportar métricas
        metrics.export_metrics()
        
        return result
        
    except Exception as e:
        logger.exception(f"Erro na execução: {str(e)}")
        metrics.record_error(domain, f"execution_error: {str(e)}")
        return None
    finally:
        await cleanup(browser_manager)
        
async def cleanup(browser_manager):
    """Limpa recursos."""
    await browser_manager.close()
    await container.cleanup()
        
if __name__ == "__main__":
    asyncio.run(run_example()) 