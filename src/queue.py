import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import heapq
from loguru import logger
from config.settings import settings

@dataclass
class QueueItem:
    url: str
    domain: str
    last_checked: datetime
    priority_score: float
    retries: int = 0
    status: str = "pending"
    fingerprint_profile: Optional[str] = None
    added_at: datetime = datetime.utcnow()
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None

    def __lt__(self, other):
        """Compare items for priority queue ordering."""
        return self.priority_score > other.priority_score

class QueueError(Exception):
    """Base exception for queue errors."""
    pass

class QueueFullError(QueueError):
    """Exception raised when queue is full."""
    pass

class QueueEmptyError(QueueError):
    """Exception raised when queue is empty."""
    pass

class ScrapingQueue:
    def __init__(self, max_workers: int = 10):
        """Initialize the scraping queue with concurrency control."""
        self.priority_queue: List[QueueItem] = []
        self.processing_items: Set[str] = set()
        self.domain_last_scrape: Dict[str, datetime] = {}
        self.domain_success_rate: Dict[str, float] = defaultdict(lambda: 1.0)
        self.domain_error_count: Dict[str, int] = defaultdict(int)
        self.semaphore = asyncio.Semaphore(max_workers)
        self._lock = asyncio.Lock()
        self._paused = False
        self._stop_event = asyncio.Event()
        self._setup_logging()
        
        # Metrics
        self.total_processed = 0
        self.total_errors = 0
        self.processing_times: Dict[str, List[float]] = defaultdict(list)
        self.queue_times: Dict[str, List[float]] = defaultdict(list)

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            "logs/queue_{time}.log",
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    async def add_item(self, item: QueueItem) -> None:
        """Add an item to the priority queue."""
        async with self._lock:
            if len(self.priority_queue) >= settings.MAX_QUEUE_SIZE:
                raise QueueFullError("Queue is at maximum capacity")
            
            # Calculate priority score
            item.priority_score = await self._calculate_priority_score(item)
            
            # Add to priority queue
            heapq.heappush(self.priority_queue, item)
            logger.debug(f"Added {item.url} to queue with priority {item.priority_score}")

    async def _calculate_priority_score(self, item: QueueItem) -> float:
        """Calculate priority score based on multiple factors."""
        score = 0.0
        
        # Time since last check (0-1 score)
        time_since_check = (datetime.utcnow() - item.last_checked).total_seconds()
        time_score = min(time_since_check / settings.PRIORITY_THRESHOLD, 1.0)
        score += time_score * 0.4  # 40% weight
        
        # Domain success rate (0-1 score)
        domain_success = self.domain_success_rate[item.domain]
        score += domain_success * 0.3  # 30% weight
        
        # Error count penalty
        error_penalty = min(item.error_count / settings.MAX_RETRIES, 1.0)
        score -= error_penalty * 0.2  # 20% penalty
        
        # Retry count penalty
        retry_penalty = min(item.retries / settings.MAX_RETRIES, 1.0)
        score -= retry_penalty * 0.1  # 10% penalty
        
        return max(0.0, min(1.0, score))

    async def get_next_item(self) -> Optional[QueueItem]:
        """Get the next item from the queue respecting domain rate limits."""
        async with self._lock:
            if not self.priority_queue or self._paused:
                return None
            
            # Try to find an item that respects domain rate limits
            for _ in range(len(self.priority_queue)):
                item = heapq.heappop(self.priority_queue)
                
                # Check domain rate limit
                last_scrape = self.domain_last_scrape.get(item.domain)
                if last_scrape:
                    time_since_last = (datetime.utcnow() - last_scrape).total_seconds()
                    if time_since_last < settings.DOMAIN_RATE_LIMIT:
                        # Put back in queue with lower priority
                        item.priority_score *= 0.9
                        heapq.heappush(self.priority_queue, item)
                        continue
                
                # Update domain last scrape time
                self.domain_last_scrape[item.domain] = datetime.utcnow()
                self.processing_items.add(item.url)
                item.status = "processing"
                item.processing_start = datetime.utcnow()
                
                return item
            
            return None

    async def mark_complete(self, item: QueueItem, success: bool, error: Optional[str] = None) -> None:
        """Mark an item as complete and update metrics."""
        async with self._lock:
            self.processing_items.remove(item.url)
            item.processing_end = datetime.utcnow()
            
            if success:
                item.status = "done"
                self.total_processed += 1
                # Update domain success rate
                self.domain_success_rate[item.domain] = (
                    self.domain_success_rate[item.domain] * 0.9 + 0.1
                )
            else:
                item.status = "error"
                self.total_errors += 1
                item.error_count += 1
                item.last_error = error
                # Update domain error count
                self.domain_error_count[item.domain] += 1
                # Decrease domain success rate
                self.domain_success_rate[item.domain] *= 0.9
            
            # Update processing time metrics
            if item.processing_start and item.processing_end:
                processing_time = (item.processing_end - item.processing_start).total_seconds()
                self.processing_times[item.domain].append(processing_time)
            
            # Update queue time metrics
            queue_time = (item.processing_start - item.added_at).total_seconds()
            self.queue_times[item.domain].append(queue_time)
            
            logger.info(
                f"Completed {item.url} with status {item.status} "
                f"(processing time: {processing_time:.2f}s, queue time: {queue_time:.2f}s)"
            )

    async def retry_item(self, item: QueueItem) -> None:
        """Retry an item with exponential backoff."""
        if item.retries >= settings.MAX_RETRIES:
            item.status = "broken"
            logger.warning(f"Item {item.url} marked as broken after {item.retries} retries")
            return
        
        item.retries += 1
        item.status = "retry"
        item.priority_score = await self._calculate_priority_score(item)
        
        # Add back to queue with lower priority
        async with self._lock:
            heapq.heappush(self.priority_queue, item)
            logger.info(f"Retrying {item.url} (attempt {item.retries})")

    async def pause(self) -> None:
        """Pause queue processing."""
        async with self._lock:
            self._paused = True
            logger.info("Queue paused")

    async def resume(self) -> None:
        """Resume queue processing."""
        async with self._lock:
            self._paused = False
            logger.info("Queue resumed")

    async def flush(self) -> None:
        """Clear the queue."""
        async with self._lock:
            self.priority_queue.clear()
            self.processing_items.clear()
            logger.info("Queue flushed")

    async def get_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        async with self._lock:
            return {
                "queue_size": len(self.priority_queue),
                "processing": len(self.processing_items),
                "total_processed": self.total_processed,
                "total_errors": self.total_errors,
                "paused": self._paused,
                "domain_stats": {
                    domain: {
                        "success_rate": self.domain_success_rate[domain],
                        "error_count": self.domain_error_count[domain],
                        "avg_processing_time": sum(times) / len(times) if times else 0,
                        "avg_queue_time": sum(qtimes) / len(qtimes) if qtimes else 0
                    }
                    for domain in set(list(self.domain_success_rate.keys()) + 
                                    list(self.domain_error_count.keys()))
                    for times in [self.processing_times.get(domain, [])]
                    for qtimes in [self.queue_times.get(domain, [])]
                }
            }

    async def process_queue(self, engine, metrics, db, notifier):
        """Main queue processing loop."""
        logger.info("Starting queue processor")
        
        while not self._stop_event.is_set():
            try:
                if self._paused:
                    await asyncio.sleep(1)
                    continue
                
                async with self.semaphore:
                    item = await self.get_next_item()
                    if not item:
                        await asyncio.sleep(1)
                        continue
                    
                    try:
                        # Process item
                        result = await engine.scrape(item)
                        
                        # Update metrics
                        await metrics.record_scrape(
                            domain=item.domain,
                            success=result.success,
                            processing_time=result.processing_time,
                            queue_time=result.queue_time
                        )
                        
                        # Update database
                        await db.update_url_status(
                            url=item.url,
                            status="active" if result.success else "error",
                            last_check=datetime.utcnow()
                        )
                        
                        # Mark complete
                        await self.mark_complete(item, result.success, result.error)
                        
                        # Handle errors
                        if not result.success:
                            if item.retries < settings.MAX_RETRIES:
                                await self.retry_item(item)
                            else:
                                await notifier.send_alert(
                                    level="error",
                                    message=f"URL {item.url} failed after {item.retries} retries",
                                    details=result.error
                                )
                    
                    except Exception as e:
                        logger.error(f"Error processing {item.url}: {str(e)}")
                        await self.mark_complete(item, False, str(e))
                        await self.retry_item(item)
                
            except Exception as e:
                logger.error(f"Error in queue processor: {str(e)}")
                await asyncio.sleep(settings.QUEUE_PROCESS_INTERVAL)

    async def stop(self):
        """Stop the queue processor."""
        self._stop_event.set()
        logger.info("Queue processor stopped")

if __name__ == "__main__":
    # Example usage
    async def main():
        queue = ScrapingQueue()
        
        # Add some test items
        await queue.add_item(QueueItem(
            url="https://example.com",
            domain="example.com",
            last_checked=datetime.utcnow() - timedelta(hours=1),
            priority_score=0.5
        ))
        
        # Start processing
        try:
            await queue.process_queue(None, None, None, None)  # Replace with actual dependencies
        except KeyboardInterrupt:
            await queue.stop()
    
    asyncio.run(main())
