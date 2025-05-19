from typing import Dict, Any, Optional
import logging
import asyncio
import os
import platform
import random
import json
from datetime import datetime
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
        self._last_rotation = datetime.now()
        
    def _get_random_user_agent(self) -> str:
        """Retorna um user agent aleatório e realista."""
        user_agents = [
            # Chrome Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Chrome MacOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Firefox Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            # Firefox MacOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        return random.choice(user_agents)
        
    def _get_random_viewport(self) -> Dict[str, int]:
        """Retorna um viewport aleatório e realista."""
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
        ]
        return random.choice(viewports)
        
    def _get_random_geolocation(self) -> Dict[str, float]:
        """Retorna uma localização aleatória no Brasil."""
        locations = [
            {"latitude": -23.5505, "longitude": -46.6333},  # São Paulo
            {"latitude": -22.9068, "longitude": -43.1729},  # Rio de Janeiro
            {"latitude": -19.9167, "longitude": -43.9345},  # Belo Horizonte
            {"latitude": -30.0346, "longitude": -51.2177},  # Porto Alegre
            {"latitude": -3.1190, "longitude": -60.0217},   # Manaus
        ]
        return random.choice(locations)
        
    async def initialize(self) -> None:
        """Inicializa o gerenciador."""
        try:
            # Inicializa Brightdata
            await self.brightdata.initialize()
            
            # Configura o loop de eventos baseado no sistema operacional
            if platform.system() == 'Windows':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            elif platform.system() == 'Linux':
                # No Linux, usamos o loop padrão
                pass
            
            # Inicializa Playwright
            self._playwright = await async_playwright().start()
            
            # Configura proxy
            proxy_config = await self.brightdata.get_proxy_config()
            
            # Configura argumentos do navegador baseado no sistema operacional
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=IsolateOrigins',
                '--disable-site-isolation-trials',
                '--disable-setuid-sandbox',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--hide-scrollbars',
                '--mute-audio',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-notifications',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-popup-blocking',
                '--disable-save-password-bubble',
                '--disable-translate',
                '--metrics-recording-only',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-domain-reliability',
                '--disable-features=AudioServiceOutOfProcess,IsolateOrigins,site-per-process',
                '--disable-ipc-flooding-protection',
                '--disable-breakpad',
                '--disable-sync',
                '--force-color-profile=srgb',
                '--disable-features=IsolateOrigins',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=IsolateOrigins',
                '--disable-site-isolation-trials',
                '--disable-setuid-sandbox',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--hide-scrollbars',
                '--mute-audio',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-notifications',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-popup-blocking',
                '--disable-save-password-bubble',
                '--disable-translate',
                '--metrics-recording-only',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-domain-reliability',
                '--disable-features=AudioServiceOutOfProcess,IsolateOrigins,site-per-process',
                '--disable-ipc-flooding-protection',
                '--disable-breakpad',
                '--disable-sync',
                '--force-color-profile=srgb',
            ]
            
            # Adiciona argumentos específicos para Linux
            if platform.system() == 'Linux':
                browser_args.extend([
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ])
            
            # Inicializa navegador
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                proxy=proxy_config,
                args=browser_args
            )
            
            self.logger.info(f"Navegador inicializado com sucesso em {platform.system()}")
            
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
                self._last_rotation = datetime.now()
                
            # Cria contexto com configurações anti-detecção
            context = await self._browser.new_context(
                viewport=self._get_random_viewport(),
                user_agent=self._get_random_user_agent(),
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                geolocation=self._get_random_geolocation(),
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'DNT': '1',
                }
            )
            
            # Cria página
            page = await context.new_page()
            
            # Configura timeout
            page.set_default_timeout(self.config.timeout)
            
            # Adiciona scripts anti-detecção
            await page.add_init_script("""
                // Sobrescreve propriedades do navegador
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Simula plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const plugins = [
                            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                            {name: 'Native Client', filename: 'internal-nacl-plugin'}
                        ];
                        plugins.refresh = () => {};
                        plugins.item = (index) => plugins[index];
                        plugins.namedItem = (name) => plugins.find(p => p.name === name);
                        return plugins;
                    }
                });
                
                // Simula linguagens
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });
                
                // Simula hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
                
                // Simula device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
                
                // Simula platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                
                // Simula vendor
                Object.defineProperty(navigator, 'vendor', {
                    get: () => 'Google Inc.'
                });
                
                // Simula user agent
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => window.navigator.userAgent.replace('Headless', '')
                });
                
                // Simula canvas fingerprint
                const originalGetContext = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function(type) {
                    const context = originalGetContext.apply(this, arguments);
                    if (type === '2d') {
                        const originalGetImageData = context.getImageData;
                        context.getImageData = function() {
                            const imageData = originalGetImageData.apply(this, arguments);
                            // Adiciona ruído aleatório
                            for (let i = 0; i < imageData.data.length; i += 4) {
                                imageData.data[i] += Math.random() * 2 - 1;
                            }
                            return imageData;
                        };
                    }
                    return context;
                };
                
                // Simula WebGL fingerprint
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    // Spoof renderer info
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
            """)
            
            # Adiciona comportamento humano
            await page.add_init_script("""
                // Simula movimentos do mouse
                const originalMouseMove = window.MouseEvent;
                window.MouseEvent = function(type, init) {
                    if (type === 'mousemove') {
                        // Adiciona pequeno atraso aleatório
                        setTimeout(() => {
                            originalMouseMove.apply(this, arguments);
                        }, Math.random() * 100);
                    }
                    return originalMouseMove.apply(this, arguments);
                };
                
                // Simula scroll suave
                const originalScroll = window.scroll;
                window.scroll = function() {
                    const start = window.pageYOffset;
                    const end = arguments[1];
                    const duration = 500 + Math.random() * 500;
                    const startTime = performance.now();
                    
                    function animate(currentTime) {
                        const elapsed = currentTime - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const easeInOutCubic = progress => {
                            return progress < 0.5
                                ? 4 * progress * progress * progress
                                : 1 - Math.pow(-2 * progress + 2, 3) / 2;
                        };
                        
                        window.scrollTo(0, start + (end - start) * easeInOutCubic(progress));
                        
                        if (progress < 1) {
                            requestAnimationFrame(animate);
                        }
                    }
                    
                    requestAnimationFrame(animate);
                };
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
                "user_agent": self.config.user_agent,
                "last_rotation": self._last_rotation.isoformat()
            },
            "brightdata": self.brightdata.get_stats()
        } 