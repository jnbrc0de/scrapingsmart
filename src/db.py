import os
import json
import time
import asyncio
import backoff
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from functools import lru_cache
from loguru import logger
from supabase import create_client, Client
from pydantic import BaseModel, HttpUrl, validator
from config.settings import settings

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
    def __init__(self):
        """Initialize database connection with retry logic."""
        self.client = self._init_connection()
        self._validate_schema()
        self._setup_logging()
        self._setup_cache()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            "logs/db_{time}.log",
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        max_time=30
    )
    def _init_connection(self) -> Client:
        """Initialize Supabase connection with retry logic."""
        try:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            # Test connection
            client.table("meta_info").select("version").execute()
            logger.info("Successfully connected to Supabase")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            raise ConnectionError(f"Database connection failed: {str(e)}")

    def _setup_cache(self):
        """Setup LRU cache for frequently accessed data."""
        self._cache_urls = lru_cache(maxsize=1000, ttl=300)  # 5 minutes
        self._cache_strategies = lru_cache(maxsize=100, ttl=1800)  # 30 minutes

    def _validate_schema(self):
        """Validate database schema version."""
        try:
            result = self.client.table("meta_info").select("version").execute()
            current_version = result.data[0]["version"]
            if current_version != settings.EXPECTED_SCHEMA_VERSION:
                logger.warning(f"Schema version mismatch. Expected {settings.EXPECTED_SCHEMA_VERSION}, got {current_version}")
                self._migrate_schema(current_version)
        except Exception as e:
            logger.error(f"Schema validation failed: {str(e)}")
            raise DatabaseError(f"Schema validation failed: {str(e)}")

    def _migrate_schema(self, current_version: int):
        """Migrate database schema to latest version."""
        try:
            # Implement schema migrations here
            pass
        except Exception as e:
            logger.error(f"Schema migration failed: {str(e)}")
            raise DatabaseError(f"Schema migration failed: {str(e)}")

    # Monitored URLs operations
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def add_url(self, url_data: Dict[str, Any]) -> str:
        """Add a new URL to monitor."""
        try:
            # Validate data
            url = MonitoredUrl(**url_data)
            
            # Insert into database
            result = self.client.table("monitored_urls").insert(url.dict()).execute()
            
            # Clear cache
            self._cache_urls.cache_clear()
            
            return result.data[0]["id"]
        except Exception as e:
            logger.error(f"Error adding URL: {str(e)}")
            raise DatabaseError(f"Failed to add URL: {str(e)}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def get_urls_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get URLs by status."""
        try:
            result = self.client.table("monitored_urls").select("*").eq("status", status).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting URLs by status: {str(e)}")
            raise DatabaseError(f"Failed to get URLs: {str(e)}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def update_url_status(self, url_id: str, status: str):
        """Update URL status."""
        try:
            self.client.table("monitored_urls").update({"status": status}).eq("id", url_id).execute()
            self._cache_urls.cache_clear()
        except Exception as e:
            logger.error(f"Error updating URL status: {str(e)}")
            raise DatabaseError(f"Failed to update URL status: {str(e)}")

    # Price history operations
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def insert_price_history_bulk(self, prices: List[Dict[str, Any]]):
        """Insert multiple price records in bulk."""
        try:
            # Validate data
            validated_prices = [PriceHistory(**price).dict() for price in prices]
            
            # Insert in batches
            batch_size = 100
            for i in range(0, len(validated_prices), batch_size):
                batch = validated_prices[i:i + batch_size]
                self.client.table("price_history").insert(batch).execute()
                
        except Exception as e:
            logger.error(f"Error inserting price history: {str(e)}")
            raise DatabaseError(f"Failed to insert price history: {str(e)}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def get_price_history(self, url_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get price history for a URL."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            result = self.client.table("price_history")\
                .select("*")\
                .eq("url_id", url_id)\
                .gte("timestamp", start_date.isoformat())\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting price history: {str(e)}")
            raise DatabaseError(f"Failed to get price history: {str(e)}")

    # Scrape logs operations
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def log_scrape_attempt(self, log_data: Dict[str, Any]):
        """Log a scraping attempt."""
        try:
            # Validate data
            log = ScrapeLog(**log_data)
            
            # Insert into database
            self.client.table("scrape_logs").insert(log.dict()).execute()
            
        except Exception as e:
            logger.error(f"Error logging scrape attempt: {str(e)}")
            raise DatabaseError(f"Failed to log scrape attempt: {str(e)}")

    # Extraction strategies operations
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def upsert_extraction_strategy(self, strategy_data: Dict[str, Any]):
        """Insert or update an extraction strategy."""
        try:
            # Validate data
            strategy = ExtractionStrategy(**strategy_data)
            
            # Upsert into database
            self.client.table("extraction_strategies")\
                .upsert(strategy.dict())\
                .execute()
            
            # Clear cache
            self._cache_strategies.cache_clear()
            
        except Exception as e:
            logger.error(f"Error upserting extraction strategy: {str(e)}")
            raise DatabaseError(f"Failed to upsert strategy: {str(e)}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def get_strategies_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get extraction strategies for a domain."""
        try:
            result = self.client.table("extraction_strategies")\
                .select("*")\
                .eq("domain", domain)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting strategies: {str(e)}")
            raise DatabaseError(f"Failed to get strategies: {str(e)}")

    # Aggregations operations
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def insert_aggregation(self, aggregation_data: Dict[str, Any]):
        """Insert an aggregation record."""
        try:
            # Validate data
            aggregation = Aggregation(**aggregation_data)
            
            # Insert into database
            self.client.table("aggregations").insert(aggregation.dict()).execute()
            
        except Exception as e:
            logger.error(f"Error inserting aggregation: {str(e)}")
            raise DatabaseError(f"Failed to insert aggregation: {str(e)}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def get_price_trend(self, url_id: str) -> Dict[str, Any]:
        """Get price trend for a URL."""
        try:
            result = self.client.table("aggregations")\
                .select("*")\
                .eq("url_id", url_id)\
                .order("period_end", desc=True)\
                .limit(1)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting price trend: {str(e)}")
            raise DatabaseError(f"Failed to get price trend: {str(e)}")

    # Analytics queries
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def get_failed_urls(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get URLs with most failures in the last N days."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            result = self.client.table("scrape_logs")\
                .select("url_id, count(*)")\
                .neq("status", "success")\
                .gte("timestamp", start_date.isoformat())\
                .group("url_id")\
                .order("count", desc=True)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting failed URLs: {str(e)}")
            raise DatabaseError(f"Failed to get failed URLs: {str(e)}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def get_blocked_domains(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get domains with highest block rate."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            result = self.client.table("scrape_logs")\
                .select("domain, count(*)")\
                .eq("error_type", "captcha")\
                .gte("timestamp", start_date.isoformat())\
                .group("domain")\
                .order("count", desc=True)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting blocked domains: {str(e)}")
            raise DatabaseError(f"Failed to get blocked domains: {str(e)}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def get_price_variations(self, threshold: float = 10.0, days: int = 30) -> List[Dict[str, Any]]:
        """Get products with price variation above threshold."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            result = self.client.table("aggregations")\
                .select("*")\
                .gte("price_change_percent", threshold)\
                .gte("period_start", start_date.isoformat())\
                .order("price_change_percent", desc=True)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting price variations: {str(e)}")
            raise DatabaseError(f"Failed to get price variations: {str(e)}")

if __name__ == "__main__":
    # Example usage
    async def main():
        db = Database()
        
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
        await db.insert_price_history_bulk([{
            "url_id": url_id,
            "price": 99.99,
            "currency": "BRL"
        }])
        
        # Get price trend
        trend = await db.get_price_trend(url_id)
        print(f"Price trend: {trend}")
    
    import asyncio
    asyncio.run(main())
