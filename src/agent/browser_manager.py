from typing import Dict, Any, Optional
import logging
import asyncio
import os
from playwright.async_api import async_playwright, Browser, Page
from ..config.settings import settings
from .brightdata_manager import BrightdataManager

class BrowserManager:
    """Gerenciador de navegador."""
    
    def __init__(self):
        self.logger = logging.getLogger("browser_manager")
        self.config = settings.browser
        self.brightdata = BrightdataManager()
        self._browser = None
        self._playwright = None
        
    async def initialize(self) -> None:
        """Inicializa o gerenciador."""
        try:
            # Inicializa Brightdata
            await self.brightdata.initialize()
            
            # Configura o loop de eventos para Windows
            if os.name == 'nt':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            # Inicializa Playwright
            self._playwright = await async_playwright().start()
            
            # Configura proxy
            proxy_config = await self.brightdata.get_proxy_config()
            
            # Inicializa navegador
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                proxy=proxy_config,
                args=[
                    f'--user-agent={self.config.user_agent}',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            
            self.logger.info("Navegador inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar navegador: {str(e)}")
            raise
            
    async def close(self) -> None:
        """Fecha recursos."""
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
                
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
                
            await self.brightdata.close()
            
            self.logger.info("Recursos fechados com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao fechar recursos: {str(e)}")
            
    async def new_page(self) -> Page:
        """Cria nova página."""
        if not self._browser:
            raise RuntimeError("Navegador não inicializado")
            
        try:
            # Verifica se precisa rotacionar IP
            if await self.brightdata.should_rotate():
                await self.brightdata.rotate_ip()
                
            # Cria contexto com configurações anti-detecção
            context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.config.user_agent,
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
            page.set_default_timeout(self.config.timeout)
            
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
            
            return page
            
        except Exception as e:
            self.logger.error(f"Erro ao criar página: {str(e)}")
            raise
            
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerenciador."""
        return {
            "browser": {
                "headless": self.config.headless,
                "timeout": self.config.timeout,
                "user_agent": self.config.user_agent
            },
            "brightdata": self.brightdata.get_stats()
        } 