import os
import json
import time
import asyncio
import backoff
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, cast
from dataclasses import dataclass
from functools import lru_cache, wraps
from loguru import logger
from supabase import create_client, Client
from pydantic import BaseModel, HttpUrl, validator
from src.config.settings import settings

T = TypeVar('T')

def timed_lru_cache(seconds: int, maxsize: int = 128):
    """Cache decorator with TTL."""
    def wrapper_decorator(func: Callable[..., T]) -> Callable[..., T]:
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expiration = time.time() + seconds

        @wraps(func)
        def wrapped_func(*args: Any, **kwargs: Any) -> T:
            if time.time() >= func.expiration:
                func.cache_clear()
                func.expiration = time.time() + func.lifetime
            return func(*args, **kwargs)

        return cast(Callable[..., T], wrapped_func)
    return wrapper_decorator

# Pydantic models for data validation
class MonitoredUrl(BaseModel):
    url: HttpUrl
    domain: str
    status: str = "active"
    categoria: Optional[str] = None
    tags: List[str] = []
    interval: int = 3600  # Default 1 hour
    last_checked: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()

class PriceHistory(BaseModel):
    url_id: str
    price: float
    currency: str = "BRL"
    timestamp: datetime = datetime.utcnow()
    raw_data: Dict[str, Any] = {}

class ScrapeLog(BaseModel):
    url_id: str
    status: str
    error_type: Optional[str] = None
    response_time: float
    timestamp: datetime = datetime.utcnow()
    metadata: Dict[str, Any] = {}

class ExtractionStrategy(BaseModel):
    domain: str
    strategy_type: str
    pattern: str
    success_rate: float = 0.0
    last_used: Optional[datetime] = None
    version: int = 1

class Aggregation(BaseModel):
    url_id: str
    weekly_avg: float
    monthly_avg: float
    price_change_percent: float
    trend: str
    period_start: datetime
    period_end: datetime

class DatabaseError(Exception):
    """Base exception for database errors."""
    pass

class ConnectionError(DatabaseError):
    """Raised when there are connection issues."""
    pass

class ValidationError(DatabaseError):
    """Raised when data validation fails."""
    pass

class RateLimitError(DatabaseError):
    """Raised when rate limits are exceeded."""
    pass

class Database:
    """Gerencia conexão e operações com o banco de dados Supabase."""
    
    def __init__(self, config=None):
        self.config = config or settings
        self._setup_logging()
        self.client: Optional[Client] = None
        self._init_connection()
        self._setup_cache()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(self.config.LOG_DIR / "db_{time}.log"),
            rotation=self.config.LOG_ROTATION_SIZE,
            retention=f"{self.config.LOG_RETENTION_DAYS} days",
            level=self.config.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def _init_connection(self):
        """Initialize connection to Supabase."""
        try:
            self.client = create_client(
                self.config.SUPABASE_URL,
                self.config.SUPABASE_KEY
            )
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            raise
    
    async def initialize(self):
        """Initialize database connection."""
        if not self.client:
            self._init_connection()
        logger.info("Database initialized")
    
    async def cleanup(self):
        """Clean up database resources."""
        self.client = None
        logger.info("Database connection closed")
    
    async def save_price(self, data: Dict[str, Any]) -> Dict:
        """Save price data to database."""
        try:
            result = self.client.table('prices').insert(data).execute()
            logger.info(f"Price data saved: {data.get('product_id')}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error saving price data: {str(e)}")
            raise
    
    async def get_price_history(self, product_id: str, days: int = 30) -> List[Dict]:
        """Get price history for a product."""
        try:
            result = self.client.table('prices')\
                .select('*')\
                .eq('product_id', product_id)\
                .order('timestamp', desc=True)\
                .limit(days)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting price history: {str(e)}")
            raise
    
    async def get_latest_price(self, product_id: str) -> Optional[Dict]:
        """Get latest price for a product."""
        try:
            result = self.client.table('prices')\
                .select('*')\
                .eq('product_id', product_id)\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting latest price: {str(e)}")
            raise
    
    async def save_error(self, data: Dict[str, Any]) -> Dict:
        """Save error data to database."""
        try:
            result = self.client.table('errors').insert(data).execute()
            logger.info(f"Error data saved: {data.get('error_type')}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error saving error data: {str(e)}")
            raise
    
    async def get_error_stats(self, domain: str = None) -> Dict:
        """Get error statistics."""
        try:
            query = self.client.table('errors').select('*')
            if domain:
                query = query.eq('domain', domain)
            result = query.execute()
            
            errors = result.data
            return {
                'total': len(errors),
                'by_type': self._group_by_type(errors),
                'by_domain': self._group_by_domain(errors)
            }
        except Exception as e:
            logger.error(f"Error getting error stats: {str(e)}")
            raise
    
    def _group_by_type(self, errors: List[Dict]) -> Dict[str, int]:
        """Group errors by type."""
        groups = {}
        for error in errors:
            error_type = error.get('error_type', 'unknown')
            groups[error_type] = groups.get(error_type, 0) + 1
        return groups
    
    def _group_by_domain(self, errors: List[Dict]) -> Dict[str, int]:
        """Group errors by domain."""
        groups = {}
        for error in errors:
            domain = error.get('domain', 'unknown')
            groups[domain] = groups.get(domain, 0) + 1
        return groups

    def _setup_cache(self):
        """Setup cache for frequently accessed data."""
        # Cache para URLs
        @timed_lru_cache(seconds=300, maxsize=1000)
        def cache_urls(key: str) -> Optional[Dict[str, Any]]:
            return None

        # Cache para estratégias
        @timed_lru_cache(seconds=1800, maxsize=100)
        def cache_strategies(key: str) -> Optional[List[Dict[str, Any]]]:
            return None

        self._cache_urls = cache_urls
        self._cache_strategies = cache_strategies

    async def get_extraction_strategies(self, domain: str) -> List[Dict[str, Any]]:
        """Get extraction strategies for a domain."""
        try:
            # Tentar obter do cache
            cached = self._cache_strategies(domain)
            if cached is not None:
                return cached

            # Se não estiver em cache, buscar do banco
            result = await self.client.table("extraction_strategies")\
                .select("*")\
                .eq("domain", domain)\
                .execute()
            
            # Atualizar cache
            self._cache_strategies(domain)
            return result.data
        except Exception as e:
            logger.error(f"Error getting strategies: {str(e)}")
            raise DatabaseError(f"Failed to get strategies: {str(e)}")

    async def add_url(self, url_data: Dict[str, Any]) -> str:
        """Add a new URL to monitor."""
        try:
            # Validate data
            url = MonitoredUrl(**url_data)
            
            # Insert into database
            result = await self.client.table("monitored_urls").insert(url.dict()).execute()
            
            # Clear cache
            self._cache_urls.cache_clear()
            
            return result.data[0]["id"]
        except Exception as e:
            logger.error(f"Error adding URL: {str(e)}")
            raise DatabaseError(f"Failed to add URL: {str(e)}")

    async def log_scrape_attempt(self, log_data: Dict[str, Any]):
        """Log a scraping attempt."""
        try:
            # Validate data
            log = ScrapeLog(**log_data)
            
            # Insert into database
            await self.client.table("scrape_logs").insert(log.dict()).execute()
            
        except Exception as e:
            logger.error(f"Error logging scrape attempt: {str(e)}")
            raise DatabaseError(f"Failed to log scrape attempt: {str(e)}")

    async def insert_price_history(self, price_data: Dict[str, Any]):
        """Insert a price record."""
        try:
            # Validate data
            price = PriceHistory(**price_data)
            
            # Insert into database
            await self.client.table("price_history").insert(price.dict()).execute()
            
        except Exception as e:
            logger.error(f"Error inserting price history: {str(e)}")
            raise DatabaseError(f"Failed to insert price history: {str(e)}")

    async def upsert_extraction_strategy(self, strategy_data: Dict[str, Any]):
        """Insert or update an extraction strategy."""
        try:
            # Validate data
            strategy = ExtractionStrategy(**strategy_data)
            
            # Upsert into database
            await self.client.table("extraction_strategies")\
                .upsert(strategy.dict())\
                .execute()
            
            # Clear cache
            self._cache_strategies.cache_clear()
            
        except Exception as e:
            logger.error(f"Error upserting extraction strategy: {str(e)}")
            raise DatabaseError(f"Failed to upsert strategy: {str(e)}")

if __name__ == "__main__":
    # Example usage
    async def main():
        db = Database()
        await db._ensure_tables_exist()
        
        # Add a new URL
        url_id = await db.add_url({
            "url": "https://example.com/product",
            "domain": "example.com",
            "status": "active"
        })
        
        # Log a scrape attempt
        await db.log_scrape_attempt({
            "url_id": url_id,
            "status": "success",
            "response_time": 1.5
        })
        
        # Insert price history
        await db.insert_price_history({
            "url_id": url_id,
            "price": 99.99,
            "currency": "BRL"
        })
    
    import asyncio
    asyncio.run(main())
