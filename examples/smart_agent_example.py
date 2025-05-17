import asyncio
import logging
from src.agent.agent import SmartScrapingAgent
from src.agent.strategies.amazon import AmazonStrategy
from src.agent.strategies.generic import GenericStrategy
from src.browser.manager import BrowserManager
from src.agent.diagnostics import DiagnosticManager
from src.agent.history import StrategyHistory
from src.config.settings import get_settings

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Carrega configurações
    settings = get_settings()
    
    # URLs para testar
    urls = [
        "https://www.amazon.com.br/dp/B07ZPKN6YR",  # Produto Amazon
        "https://www.americanas.com.br/produto/123456",  # Produto Americanas
        "https://www.magazineluiza.com.br/p/123456"  # Produto Magazine Luiza
    ]
    
    # Inicializa componentes
    browser_manager = BrowserManager()
    diagnostic_manager = DiagnosticManager()
    history_manager = StrategyHistory()
    
    try:
        # Inicializa o browser
        await browser_manager.initialize()
        
        # Carrega histórico anterior
        history_manager.load_history()
        
        for url in urls:
            logger.info(f"\nProcessando URL: {url}")
            
            # Cria o agente para a URL
            agent = SmartScrapingAgent(url, browser_manager)
            
            # Adiciona estratégias
            await agent.add_strategy(AmazonStrategy())  # Estratégia específica para Amazon
            await agent.add_strategy(GenericStrategy())  # Estratégia genérica como fallback
            
            # Tenta extrair dados
            result = await agent.extract()
            
            if result.success:
                logger.info(f"Sucesso! Estratégia usada: {result.strategy_used}")
                logger.info(f"Dados extraídos: {result.data}")
                
                # Registra sucesso no histórico
                history_manager.record_attempt(
                    strategy_name=result.strategy_used,
                    success=True,
                    data=result.data
                )
            else:
                logger.error(f"Falha na extração: {result.error}")
                
                # Analisa a falha
                diagnostic = diagnostic_manager.analyze_failure(
                    strategy_name=result.strategy_used,
                    error=result.error,
                    url=url
                )
                
                logger.warning(f"Diagnóstico: {diagnostic.message}")
                if diagnostic.suggestion:
                    logger.info(f"Sugestão: {diagnostic.suggestion}")
                
                # Registra falha no histórico
                history_manager.record_attempt(
                    strategy_name=result.strategy_used,
                    success=False,
                    error=result.error
                )
            
            # Mostra estatísticas da estratégia
            stats = history_manager.get_strategy_stats(result.strategy_used)
            logger.info(f"Estatísticas da estratégia {result.strategy_used}:")
            logger.info(f"- Tentativas: {stats['attempts']}")
            logger.info(f"- Taxa de sucesso: {stats['success_rate']:.2f}%")
            logger.info(f"- Tempo médio: {stats['avg_execution_time']:.2f}s")
            
            # Pequena pausa entre requisições
            await asyncio.sleep(settings.MIN_DELAY)
            
    finally:
        # Limpa recursos
        await browser_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 