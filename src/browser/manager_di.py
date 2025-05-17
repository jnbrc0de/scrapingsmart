from typing import Dict, Any, Optional
import logging
import asyncio
import os
from pathlib import Path
import random
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from ..services.container import container
from ..services.config import config
from ..services.proxy import ProxyManager

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Gerenciador de navegador com injeção de dependência.
    
    Utiliza os serviços compartilhados para configuração, proxy e métricas.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("browser_manager")
        self._browser = None
        self._playwright = None
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_file = Path('data/browser_sessions.json')
        
    async def initialize(self) -> None:
        """Inicializa o gerenciador."""
        try:
            # Configura o loop de eventos para Windows
            if os.name == 'nt':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            # Inicializa Playwright
            self._playwright = await async_playwright().start()
            
            # Inicializa o navegador
            browser_config = config.get_browser_config()
            proxy_config = None
            
            # Obtém configuração de proxy
            if container.is_initialized():
                proxy_manager = container.get_proxy()
                if proxy_manager.is_initialized:
                    proxy_config = await proxy_manager.get_proxy_config()
            
            # Inicializa navegador
            self._browser = await self._playwright.chromium.launch(
                headless=browser_config['headless'],
                proxy=proxy_config,
                args=[
                    f'--user-agent={browser_config["user_agent"]}',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            
            self.logger.info("Navegador inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar navegador: {str(e)}")
            
            # Registra métrica de erro, se disponível
            if container.is_initialized():
                try:
                    metrics = container.get_metrics()
                    metrics.record_error("browser", "initialization_error")
                except:
                    pass
                    
            raise
            
    async def close(self) -> None:
        """Fecha recursos."""
        try:
            if self._browser:
                try:
                    # First close all contexts
                    contexts = self._browser.contexts
                    for context in contexts:
                        await context.close()
                except Exception as e:
                    self.logger.warning(f"Error closing contexts: {str(e)}")
                
                # Then close the browser
                try:
                    await self._browser.close()
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {str(e)}")
                
                self._browser = None
                
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    self.logger.warning(f"Error stopping playwright: {str(e)}")
                
                self._playwright = None
                
            self.logger.info("Recursos fechados com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao fechar recursos: {str(e)}")
            # Don't re-raise to ensure cleanup continues even with errors
            
    async def new_page(self, domain: str = None) -> Page:
        """
        Cria nova página.
        
        Args:
            domain: Domínio para rotação específica de IP (opcional)
            
        Returns:
            Nova página do navegador
        """
        if not self._browser:
            raise RuntimeError("Navegador não inicializado")
            
        try:
            start_time = datetime.now()
            
            # Verifica se precisa rotacionar IP
            if container.is_initialized() and domain:
                proxy_manager = container.get_proxy()
                if await proxy_manager.should_rotate():
                    await proxy_manager.rotate_ip()
                    
            # Cria contexto com configurações anti-detecção
            browser_config = config.get_browser_config()
            context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=browser_config['user_agent'],
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                geolocation={'latitude': -23.5505, 'longitude': -46.6333},  # São Paulo
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1'
                }
            )
            
            # Cria página
            page = await context.new_page()
            
            # Configura timeout
            page.set_default_timeout(browser_config['timeout'])
            
            # Adiciona scripts anti-detecção
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });
            """)
            
            # Registra métrica de duração, se disponível
            if container.is_initialized():
                try:
                    duration = (datetime.now() - start_time).total_seconds()
                    metrics = container.get_metrics()
                    metrics.record_extraction("browser", True, duration)
                except:
                    pass
            
            return page
            
        except Exception as e:
            self.logger.error(f"Erro ao criar página: {str(e)}")
            
            # Registra métrica de erro, se disponível
            if container.is_initialized():
                try:
                    metrics = container.get_metrics()
                    metrics.record_error("browser", "page_creation_error")
                except:
                    pass
                    
            raise
            
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerenciador."""
        browser_config = config.get_browser_config()
        
        stats = {
            "browser": {
                "headless": browser_config['headless'],
                "timeout": browser_config['timeout'],
                "user_agent": browser_config['user_agent']
            }
        }
        
        # Adiciona estatísticas de proxy, se disponível
        if container.is_initialized():
            try:
                proxy_manager = container.get_proxy()
                stats["proxy"] = proxy_manager.get_stats()
            except:
                stats["proxy"] = {"error": "Não disponível"}
                
        return stats 