from .base import BaseStrategy
from urllib.parse import urlparse

class GenericMarketplaceStrategy(BaseStrategy):
    """Estratégia genérica para qualquer marketplace brasileiro."""

    async def execute(self, url: str, browser):
        from playwright.async_api import Page
        from loguru import logger

        page = None
        try:
            domain = urlparse(url).netloc
            page = await self._get_page(browser, url)
            price = await self._extract_price(page, domain)
            title = await self._extract_title(page, domain)
            seller = await self._extract_seller(page, domain)
            return {
                "status": "success",
                "data": {
                    "price": price,
                    "title": title,
                    "seller": seller,
                    "url": url,
                    "domain": domain
                }
            }
        except Exception as e:
            logger.error(f"Error in Generic strategy: {str(e)}")
            return {"status": "error", "error": str(e)}
        finally:
            if page:
                await page.close() 