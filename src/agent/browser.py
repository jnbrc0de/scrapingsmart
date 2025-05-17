from typing import Dict, Any, Optional
import logging
import asyncio
from playwright.async_api import async_playwright, Browser, Page
from .proxy import ProxyManager
from .config import settings

class BrowserManager:
    """Gerenciador de navegador do sistema."""
    
    def __init__(self, proxy_manager: Optional[ProxyManager] = None):
        self.logger = logging.getLogger("browser_manager")
        self.proxy_manager = proxy_manager
        self.browser: Optional[Browser] = None
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> bool:
        """Inicializa o navegador."""
        try:
            async with self._lock:
                if self.browser:
                    return True
                    
                # Inicia Playwright
                playwright = await async_playwright().start()
                
                # Configura opções do navegador
                browser_options = {
                    'headless': settings.browser.headless,
                    'timeout': settings.browser.timeout
                }
                
                # Adiciona proxy se disponível
                if self.proxy_manager and settings.proxy.enabled:
                    proxy = self.proxy_manager.get_proxy()
                    if proxy:
                        browser_options['proxy'] = {
                            'server': proxy
                        }
                        
                # Inicia navegador
                self.browser = await playwright.chromium.launch(**browser_options)
                self.logger.info("Navegador inicializado")
                return True
                
        except Exception as e:
            self.logger.error(f"Erro ao inicializar navegador: {str(e)}")
            return False
            
    async def get_page(self, url: str) -> Optional[Page]:
        """Obtém uma nova página do navegador."""
        try:
            if not self.browser:
                if not await self.initialize():
                    return None
                    
            # Cria nova página
            page = await self.browser.new_page()
            
            # Configura timeout
            page.set_default_timeout(settings.browser.timeout)
            
            # Configura user agent
            await page.set_extra_http_headers({
                'User-Agent': settings.browser.user_agent
            })
            
            # Navega para URL
            await page.goto(url, wait_until='networkidle')
            
            return page
            
        except Exception as e:
            self.logger.error(f"Erro ao obter página: {str(e)}")
            return None
            
    async def close(self) -> None:
        """Fecha o navegador."""
        try:
            async with self._lock:
                if self.browser:
                    await self.browser.close()
                    self.browser = None
                    self.logger.info("Navegador fechado")
                    
        except Exception as e:
            self.logger.error(f"Erro ao fechar navegador: {str(e)}")
            
    async def restart(self) -> bool:
        """Reinicia o navegador."""
        try:
            await self.close()
            return await self.initialize()
            
        except Exception as e:
            self.logger.error(f"Erro ao reiniciar navegador: {str(e)}")
            return False
            
    async def take_screenshot(self, page: Page, path: str) -> bool:
        """Tira screenshot da página."""
        try:
            await page.screenshot(path=path, full_page=True)
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao tirar screenshot: {str(e)}")
            return False
            
    async def get_page_content(self, page: Page) -> Optional[str]:
        """Obtém conteúdo da página."""
        try:
            return await page.content()
            
        except Exception as e:
            self.logger.error(f"Erro ao obter conteúdo da página: {str(e)}")
            return None
            
    async def wait_for_selector(self, page: Page, selector: str, 
                              timeout: Optional[int] = None) -> bool:
        """Aguarda elemento aparecer na página."""
        try:
            await page.wait_for_selector(
                selector,
                timeout=timeout or settings.browser.timeout
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao aguardar seletor: {str(e)}")
            return False
            
    async def click(self, page: Page, selector: str) -> bool:
        """Clica em um elemento da página."""
        try:
            await page.click(selector)
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao clicar em elemento: {str(e)}")
            return False
            
    async def type(self, page: Page, selector: str, text: str) -> bool:
        """Digite texto em um elemento da página."""
        try:
            await page.fill(selector, text)
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao digitar texto: {str(e)}")
            return False
            
    async def evaluate(self, page: Page, script: str) -> Any:
        """Executa script JavaScript na página."""
        try:
            return await page.evaluate(script)
            
        except Exception as e:
            self.logger.error(f"Erro ao executar script: {str(e)}")
            return None
            
    async def get_cookies(self, page: Page) -> Dict[str, Any]:
        """Obtém cookies da página."""
        try:
            return await page.context.cookies()
            
        except Exception as e:
            self.logger.error(f"Erro ao obter cookies: {str(e)}")
            return {}
            
    async def set_cookies(self, page: Page, cookies: Dict[str, Any]) -> bool:
        """Define cookies na página."""
        try:
            await page.context.add_cookies(cookies)
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao definir cookies: {str(e)}")
            return False 