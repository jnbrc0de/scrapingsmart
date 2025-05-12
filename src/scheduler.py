import asyncio
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import random
from loguru import logger
from supabase import create_client, Client
from dataclasses import dataclass
from collections import defaultdict
from config.settings import settings

# Configuration
BASE_INTERVAL = 6 * 60 * 60  # 6 hours in seconds
RANDOM_VARIATION = 30 * 60  # 30 minutes in seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 600  # 10 minutes in seconds
DOMAIN_COOLDOWN = 3 * 60 * 60  # 3 hours in seconds
DOMAIN_RATE_LIMIT = 300  # 5 minutes in seconds
PRIORITY_THRESHOLD = 24 * 60 * 60  # 24 hours in seconds

@dataclass
class URLMetadata:
    url: str
    domain: str
    priority: int
    proxy_tag: Optional[str]
    fingerprint_tag: Optional[str]
    next_scrape_at: datetime
    retry_count: int = 0
    status: str = "active"

@dataclass
class BrowserSession:
    domain: str
    last_used: datetime
    is_active: bool = True

class SchedulerError(Exception):
    """Base exception for scheduler errors."""
    pass

class DatabaseError(SchedulerError):
    """Exception for database-related errors."""
    pass

class QueueError(SchedulerError):
    """Exception for queue-related errors."""
    pass

class SmartScheduler:
    def __init__(self):
        """Initialize the scheduler with Supabase connection."""
        try:
            self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            self.url_queue: Dict[str, List[str]] = defaultdict(list)
            self.domain_last_scrape: Dict[str, datetime] = {}
            self.domain_blocked: Set[str] = set()
            self.domain_errors: Dict[str, int] = defaultdict(int)
            self.active_sessions: Dict[str, BrowserSession] = {}
            self.domain_cooldowns: Dict[str, datetime] = {}
            self.processing_locks: Set[str] = set()
            self.semaphore = asyncio.Semaphore(settings.scraping.max_concurrent)
            self._setup_logging()
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {str(e)}")
            raise SchedulerError(f"Initialization failed: {str(e)}")

    def _setup_logging(self):
        """Configure logging with loguru."""
        try:
            logger.add(
                "logs/scheduler_{time}.log",
                rotation="100 MB",
                retention="7 days",
                level="INFO",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
            )
        except Exception as e:
            logger.error(f"Failed to setup logging: {str(e)}")
            raise SchedulerError(f"Logging setup failed: {str(e)}")

    async def load_monitored_urls(self) -> List[URLMetadata]:
        """Load active URLs from Supabase with proper filtering."""
        try:
            response = self.supabase.table("monitored_urls") \
                .select("*") \
                .in_("status", ["active", "warning"]) \
                .lte("next_scrape_at", datetime.utcnow().isoformat()) \
                .execute()

            urls = []
            for url_data in response.data:
                metadata = URLMetadata(
                    url=url_data["url"],
                    domain=url_data["domain"],
                    priority=self._calculate_priority(url_data),
                    proxy_tag=url_data.get("proxy_tag"),
                    fingerprint_tag=url_data.get("fingerprint_tag"),
                    next_scrape_at=datetime.fromisoformat(url_data["next_scrape_at"]),
                    retry_count=url_data.get("retry_count", 0),
                    status=url_data["status"]
                )
                urls.append(metadata)

            logger.info(f"Loaded {len(urls)} URLs for scheduling")
            return urls

        except Exception as e:
            logger.error(f"Error loading monitored URLs: {str(e)}")
            raise DatabaseError(f"Failed to load URLs: {str(e)}")

    def _calculate_priority(self, url_data: dict) -> int:
        """Calculate priority based on various factors."""
        try:
            priority = 0
            
            if url_data.get("has_frequent_price_changes"):
                priority += 3

            last_change = url_data.get("last_price_change_at")
            if last_change:
                last_change_time = datetime.fromisoformat(last_change)
                if (datetime.utcnow() - last_change_time).total_seconds() < settings.PRIORITY_THRESHOLD:
                    priority += 2

            last_scrape = url_data.get("last_check")
            if last_scrape:
                last_scrape_time = datetime.fromisoformat(last_scrape)
                if (datetime.utcnow() - last_scrape_time).total_seconds() > settings.PRIORITY_THRESHOLD:
                    priority += 1

            return priority
        except Exception as e:
            logger.error(f"Error calculating priority: {str(e)}")
            return 0  # Default to lowest priority on error

    async def check_domain_cooldown(self, domain: str) -> bool:
        """Check if domain is in cooldown period."""
        try:
            # Check recent CAPTCHA blocks
            response = await self.supabase.table("scrape_logs") \
                .select("created_at") \
                .eq("domain", domain) \
                .eq("error_type", "captcha-blocked") \
                .gte("created_at", (datetime.utcnow() - timedelta(hours=settings.CAPTCHA_WINDOW_HOURS)).isoformat()) \
                .execute()

            if len(response.data) >= settings.MAX_CAPTCHA_BLOCKS:
                self.domain_blocked.add(domain)
                logger.warning(f"Domain {domain} is in cooldown due to multiple CAPTCHA blocks")
                return True

            # Check general error rate
            if self.domain_errors[domain] >= settings.MAX_DOMAIN_ERRORS:
                logger.warning(f"Domain {domain} is in cooldown due to high error rate")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking domain cooldown: {str(e)}")
            return True  # Default to cooldown on error

    def _calculate_next_scrape_time(self, url: URLMetadata) -> datetime:
        """Calculate next scrape time with randomization."""
        try:
            base_time = datetime.utcnow() + timedelta(seconds=settings.BASE_INTERVAL)
            
            # Add random variation
            variation = secrets.randbelow(settings.RANDOM_VARIATION * 2) - settings.RANDOM_VARIATION
            next_time = base_time + timedelta(seconds=variation)

            # Add cooldown for blocked domains
            if url.domain in self.domain_blocked:
                next_time += timedelta(seconds=settings.DOMAIN_COOLDOWN)

            return next_time
        except Exception as e:
            logger.error(f"Error calculating next scrape time: {str(e)}")
            # Default to base interval on error
            return datetime.utcnow() + timedelta(seconds=settings.BASE_INTERVAL)

    async def schedule_urls(self, urls: List[URLMetadata]):
        """Schedule URLs for processing with intelligent batching."""
        try:
            # Group URLs by domain
            domain_groups = defaultdict(list)
            for url in urls:
                domain = url.domain
                if self._can_process_domain(domain):
                    domain_groups[domain].append(url)

            # Process domains in parallel with batching
            tasks = []
            for domain, domain_urls in domain_groups.items():
                # Split into batches
                batches = [domain_urls[i:i + settings.BATCH_SIZE] 
                          for i in range(0, len(domain_urls), settings.BATCH_SIZE)]
                
                for batch in batches:
                    task = asyncio.create_task(
                        self._process_domain_batch(domain, batch)
                    )
                    tasks.append(task)

            await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error scheduling URLs: {str(e)}")
            raise QueueError(f"Failed to schedule URLs: {str(e)}")

    async def _process_domain_batch(self, domain: str, urls: List[URLMetadata]) -> None:
        """Process a batch of URLs from the same domain."""
        async with self.semaphore:
            try:
                # Get or create browser session
                session = await self._get_browser_session(domain)
                
                if not session:
                    logger.warning(f"Could not create session for domain: {domain}")
                    return

                # Process URLs in batch
                for url in urls:
                    await self._process_url(url, session)

                # Update session last used time
                session.last_used = datetime.now()

            except Exception as e:
                logger.error(f"Error processing batch for domain {domain}: {e}")
                self._handle_domain_error(domain)
            finally:
                self.processing_locks.discard(domain)

    async def _get_browser_session(self, domain: str) -> BrowserSession:
        """Get or create a browser session for a domain."""
        if domain in self.active_sessions:
            session = self.active_sessions[domain]
            if session.is_active:
                return session

        # Create new session
        session = BrowserSession(domain=domain, last_used=datetime.now())
        self.active_sessions[domain] = session
        return session

    def _can_process_domain(self, domain: str) -> bool:
        """Check if a domain can be processed."""
        if domain in self.processing_locks:
            return False

        if domain in self.domain_cooldowns:
            if datetime.now() < self.domain_cooldowns[domain]:
                return False

        return True

    def _handle_domain_error(self, domain: str) -> None:
        """Handle errors for a domain."""
        self.domain_cooldowns[domain] = datetime.now() + timedelta(minutes=30)
        if domain in self.active_sessions:
            self.active_sessions[domain].is_active = False

    async def _process_url(self, url: URLMetadata, session: BrowserSession) -> None:
        """Process a single URL using the provided session."""
        try:
            # Add random variation to interval
            interval = BASE_INTERVAL + random.uniform(
                -settings.INTERVAL_VARIATION,
                settings.INTERVAL_VARIATION
            )
            
            # Process URL
            # ... existing URL processing code ...

        except Exception as e:
            logger.error(f"Error processing URL {url.url}: {e}")
            raise

    async def update_url_status(self, url: URLMetadata, success: bool):
        """Update URL status in Supabase."""
        try:
            if success:
                data = {
                    "next_scrape_at": self._calculate_next_scrape_time(url).isoformat(),
                    "retry_count": 0,
                    "status": "active"
                }
                self.domain_errors[url.domain] = max(0, self.domain_errors[url.domain] - 1)
            else:
                data = {
                    "retry_count": url.retry_count + 1,
                    "status": "warning" if url.retry_count + 1 >= settings.MAX_RETRIES else "active"
                }
                self.domain_errors[url.domain] += 1

            await self.supabase.table("monitored_urls") \
                .update(data) \
                .eq("url", url.url) \
                .execute()

        except Exception as e:
            logger.error(f"Error updating URL status: {str(e)}")
            raise DatabaseError(f"Failed to update URL status: {str(e)}")

    async def cleanup_sessions(self) -> None:
        """Clean up inactive sessions."""
        current_time = datetime.now()
        inactive_sessions = [
            domain for domain, session in self.active_sessions.items()
            if (current_time - session.last_used) > timedelta(hours=1)
        ]
        
        for domain in inactive_sessions:
            del self.active_sessions[domain]

    async def update_next_scrape_time(self, url: URLMetadata, success: bool):
        """
        Atualiza o campo next_scrape_at para garantir agendamento 2x ao dia com jitter aleatório.
        """
        try:
            next_time = self._calculate_next_scrape_time(url)
            await self.supabase.table("monitored_urls").update({
                "next_scrape_at": next_time.isoformat(),
                "last_check": datetime.utcnow().isoformat(),
                "status": "active" if success else "warning"
            }).eq("url", url.url).execute()
            logger.info(f"[SCHEDULER] Próxima coleta para {url.url} agendada para {next_time}")
        except Exception as e:
            logger.error(f"Erro ao atualizar next_scrape_at para {url.url}: {str(e)}")

    async def run(self):
        """
        Loop principal do scheduler: carrega URLs, agenda execuções, atualiza next_scrape_at.
        """
        while True:
            try:
                urls = await self.load_monitored_urls()
                await self.schedule_urls(urls)
                # Aguarda até o próximo ciclo (ex: 10 minutos)
                await asyncio.sleep(settings.scraping.loop_interval)
            except Exception as e:
                logger.error(f"Erro no loop do scheduler: {str(e)}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        # Create and run scheduler
        scheduler = SmartScheduler()
        asyncio.run(scheduler.run())
    except Exception as e:
        logger.critical(f"Fatal error in scheduler: {str(e)}")
        raise
