import os
import json
import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.config.settings import settings

@dataclass
class BrowserProfile:
    """Represents a browser profile configuration."""
    user_agent: str
    viewport: Dict[str, int]
    language: str
    timezone: str
    platform: str
    hardware_concurrency: int
    device_memory: int
    plugins: List[Dict[str, str]]
    webgl_vendor: str
    webgl_renderer: str

class BrowserPool:
    """Manages a pool of browser instances."""
    def __init__(self, max_browsers: int = 10):
        self.max_browsers = max_browsers
        self.semaphore = asyncio.Semaphore(max_browsers)
        self.browsers: Dict[str, Browser] = {}
        self.contexts: Dict[str, BrowserContext] = {}
        self.usage_count: Dict[str, int] = {}
        self.last_used: Dict[str, datetime] = {}
        self.playwright = None

    async def initialize(self):
        """Initialize the browser pool."""
        self.playwright = await async_playwright().start()
        logger.info("Browser pool initialized")

    async def cleanup(self):
        """Clean up all browser instances."""
        for browser in self.browsers.values():
            await browser.close()
        await self.playwright.stop()
        logger.info("Browser pool cleaned up")

    async def get_browser(self, domain: str) -> Browser:
        """Get or create a browser instance for a domain."""
        async with self.semaphore:
            if domain not in self.browsers or self._should_restart_browser(domain):
                await self._create_browser(domain)
            self.usage_count[domain] += 1
            self.last_used[domain] = datetime.utcnow()
            return self.browsers[domain]

    def _should_restart_browser(self, domain: str) -> bool:
        """Check if a browser should be restarted."""
        if domain not in self.usage_count:
            return True
        
        usage = self.usage_count[domain]
        last_used = self.last_used[domain]
        
        return (
            usage >= settings.MAX_BROWSER_USES or
            datetime.utcnow() - last_used > timedelta(hours=2)
        )

    async def _create_browser(self, domain: str):
        """Create a new browser instance."""
        try:
            browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            self.browsers[domain] = browser
            self.usage_count[domain] = 0
            self.last_used[domain] = datetime.utcnow()
            logger.info(f"Created new browser for domain: {domain}")
        except Exception as e:
            logger.error(f"Failed to create browser for domain {domain}: {str(e)}")
            raise

class BrowserManager:
    """Manages browser instances with anti-detection features."""
    def __init__(self, config=None, notifier=None):
        self.config = config or settings
        self.pool = BrowserPool(max_browsers=self.config.MAX_BROWSERS)
        self.notifier = notifier
        self._setup_logging()
        self._load_profiles()
        self._browsers: Dict[str, Browser] = {}
        self._pages: Dict[str, Page] = {}
        self._sessions: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self._session_file = self.config.SESSION_FILE
        self._load_sessions()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(self.config.LOG_DIR / "browser_{time}.log"),
            rotation=self.config.LOG_ROTATION_SIZE,
            retention=f"{self.config.LOG_RETENTION_DAYS} days",
            level=self.config.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    def _load_profiles(self):
        """Load browser profiles from stealth_profiles.py."""
        try:
            from .stealth_profiles import PROFILES
            self.profiles = PROFILES
            logger.info(f"Loaded {len(self.profiles)} browser profiles")
        except Exception as e:
            logger.error(f"Failed to load browser profiles: {str(e)}")
            raise

    async def initialize(self):
        """Initialize the browser manager."""
        await self.pool.initialize()
        logger.info("Browser manager initialized")

    async def cleanup(self):
        """Clean up the browser manager."""
        await self.pool.cleanup()
        logger.info("Browser manager cleaned up")

    async def get_browser(self, domain: str) -> Browser:
        """Get or create a browser instance for a domain."""
        async with self._lock:
            if domain not in self._browsers:
                browser = await self.pool.get_browser(domain)
                self._browsers[domain] = browser
            return self._browsers[domain]

    async def close_browser(self, browser: Browser):
        """Close a browser instance."""
        try:
            await browser.close()
            # Remove from internal tracking
            for domain, b in list(self._browsers.items()):
                if b == browser:
                    del self._browsers[domain]
                    if domain in self._pages:
                        del self._pages[domain]
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
            if self.notifier:
                await self.notifier.send_alert(
                    level="error",
                    message=f"Browser cleanup failed: {str(e)}",
                    event="browser_cleanup_error"
                )

    async def get_browser_context(self, domain: str) -> BrowserContext:
        """Get a browser context with anti-detection features."""
        try:
            browser = await self.get_browser(domain)
            profile = self._get_random_profile()
            
            context = await browser.new_context(
                viewport=profile.viewport,
                user_agent=profile.user_agent,
                locale=profile.language,
                timezone_id=profile.timezone,
                geolocation={"latitude": -23.5505, "longitude": -46.6333},
                permissions=["geolocation"],
                proxy={
                    "server": self.config.PROXY_SERVER,
                    "username": self.config.PROXY_USERNAME,
                    "password": self.config.PROXY_PASSWORD
                } if self.config.PROXY_ENABLED else None
            )

            # Apply anti-detection scripts
            await self._apply_anti_detection(context, profile)
            
            return context
        except Exception as e:
            logger.error(f"Failed to create browser context for {domain}: {str(e)}")
            if self.notifier:
                await self.notifier.send_alert(
                    level="error",
                    message=f"Browser context creation failed: {str(e)}",
                    domain=domain,
                    event="browser_error"
                )
            raise

    def _get_random_profile(self) -> BrowserProfile:
        """Get a random browser profile."""
        return random.choice(self.profiles)

    async def _apply_anti_detection(self, context: BrowserContext, profile: BrowserProfile):
        """Apply anti-detection measures to the browser context."""
        # Block resources
        await context.route("**/*", lambda route: route.abort() 
            if any(resource in route.request.resource_type for resource in self.config.block_resources_list)
            else route.continue_()
        )
        
        # Apply stealth scripts
        await context.add_init_script("""
            // Override navigator properties
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => %d
            });
            
            // Override device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => %d
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => %s
            });
            
            // Override WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return '%s';
                }
                if (parameter === 37446) {
                    return '%s';
                }
                return getParameter.apply(this, arguments);
            };
        """ % (
            profile.hardware_concurrency,
            profile.device_memory,
            json.dumps(profile.plugins),
            profile.webgl_vendor,
            profile.webgl_renderer
        ))

    async def close_browser_context(self, context: BrowserContext):
        """Close a browser context and clean up."""
        try:
            # Clear cookies and storage
            await context.clear_cookies()
            await context.clear_permissions()
            
            # Close all pages
            for page in context.pages:
                await page.close()
            
            # Close context
            await context.close()
            
            logger.info("Browser context closed and cleaned up")
        except Exception as e:
            logger.error(f"Error closing browser context: {str(e)}")
            if self.notifier:
                await self.notifier.send_alert(
                    level="warning",
                    message=f"Browser context cleanup failed: {str(e)}",
                    event="browser_cleanup_error"
                )

    async def rotate_proxy(self, context: BrowserContext):
        """Rotate the proxy for a browser context."""
        try:
            # Close current context
            await self.close_browser_context(context)
            
            # Create new context with new proxy
            new_context = await self.get_browser_context(context.domain)
            
            logger.info("Proxy rotated successfully")
            return new_context
        except Exception as e:
            logger.error(f"Failed to rotate proxy: {str(e)}")
            if self.notifier:
                await self.notifier.send_alert(
                    level="error",
                    message=f"Proxy rotation failed: {str(e)}",
                    event="proxy_rotation_error"
                )
            raise

    def _load_sessions(self):
        """Carrega sessões salvas do arquivo."""
        session_file = self.config.TEMP_DIR / self._session_file
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    self._sessions = json.load(f)
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                self._sessions = {}

    def _save_sessions(self):
        """Salva sessões no arquivo."""
        try:
            session_file = self.config.TEMP_DIR / self._session_file
            with open(session_file, 'w') as f:
                json.dump(self._sessions, f)
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")

    async def get_page(self, domain: str) -> Page:
        """Get or create a page for a domain."""
        async with self._lock:
            if domain not in self._pages:
                browser = await self.get_browser(domain)
                page = await browser.new_page()
                await self._setup_page(page, domain)
                self._pages[domain] = page
            return self._pages[domain]

    async def _setup_page(self, page: Page, domain: str):
        """Setup a new page with profile and settings."""
        # Apply stealth profile
        await self._apply_stealth_profile(page, domain)
        
        # Set timeout
        page.set_default_timeout(self.config.PAGE_LOAD_TIMEOUT)
        
        # Set viewport
        await page.set_viewport_size({
            'width': 1920,
            'height': 1080
        })

    async def _apply_stealth_profile(self, page: Page, domain: str):
        """Apply stealth profile to page."""
        # Implement anti-detection techniques
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Apply custom headers
        await page.set_extra_http_headers({
            'User-Agent': self._get_random_profile().user_agent,
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        })

    async def save_session(self, domain: str):
        """Salva o estado da sessão para recuperação posterior."""
        async with self._lock:
            if domain in self._pages:
                page = self._pages[domain]
                cookies = await page.context.cookies()
                storage = await page.evaluate("""() => {
                    return {
                        localStorage: Object.fromEntries(
                            Object.entries(localStorage)
                        ),
                        sessionStorage: Object.fromEntries(
                            Object.entries(sessionStorage)
                        )
                    }
                }""")
                
                self._sessions[domain] = {
                    'cookies': cookies,
                    'storage': storage,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self._save_sessions()

    async def recover_session(self, domain: str) -> bool:
        """Tenta recuperar uma sessão salva."""
        async with self._lock:
            if domain not in self._sessions:
                return False
                
            session = self._sessions[domain]
            timestamp = datetime.fromisoformat(session['timestamp'])
            
            # Verifica se a sessão ainda é válida
            if datetime.utcnow() - timestamp > timedelta(hours=24):
                del self._sessions[domain]
                self._save_sessions()
                return False
            
            try:
                page = await self.get_page(domain)
                
                # Restaura cookies
                await page.context.add_cookies(session['cookies'])
                
                # Restaura storage
                await page.evaluate("""(storage) => {
                    Object.entries(storage.localStorage).forEach(([key, value]) => {
                        localStorage.setItem(key, value);
                    });
                    Object.entries(storage.sessionStorage).forEach(([key, value]) => {
                        sessionStorage.setItem(key, value);
                    });
                }""", session['storage'])
                
                logger.info(f"Successfully recovered session for {domain}")
                return True
                
            except Exception as e:
                logger.error(f"Error recovering session for {domain}: {e}")
                return False

    async def handle_crash(self, domain: str):
        """Lida com crash do navegador."""
        async with self._lock:
            if domain in self._browsers:
                try:
                    await self._browsers[domain].close()
                except:
                    pass
                del self._browsers[domain]
            
            if domain in self._pages:
                del self._pages[domain]
            
            # Tenta recuperar sessão
            await self.recover_session(domain)

if __name__ == "__main__":
    # Example usage
    async def main():
        manager = BrowserManager()
        await manager.initialize()
        
        try:
            # Get a browser context
            context = await manager.get_browser_context("example.com")
            
            # Create a new page
            page = await context.new_page()
            
            # Navigate to a URL
            await page.goto("https://example.com")
            
            # Clean up
            await manager.close_browser_context(context)
            
        finally:
            await manager.cleanup()
    
    import asyncio
    asyncio.run(main())
