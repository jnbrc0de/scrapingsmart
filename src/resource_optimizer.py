from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
import logging
from datetime import datetime
import json
import gzip
import zlib
from collections import defaultdict
import threading
from queue import Queue
import time
import psutil
import numpy as np
from src.config.settings import settings
from concurrent.futures import ThreadPoolExecutor
import weakref

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    data: Any
    timestamp: datetime
    size: int
    access_count: int
    last_accessed: datetime

class ResourceOptimizer:
    def __init__(self):
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.connection_pool: Dict[str, List[Any]] = defaultdict(list)
        self.request_queue: Queue = Queue()
        self._setup_logging()
        self._start_optimization_threads()
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=settings.network.max_concurrent_connections)
        self._finalizer = weakref.finalize(self, self.cleanup)

    def _setup_logging(self):
        """Configure logging for resource optimization."""
        logger.setLevel(settings.logging.level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(settings.logging.format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _start_optimization_threads(self):
        """Start background threads for optimization tasks."""
        self.memory_cleanup_thread = threading.Thread(
            target=self._memory_cleanup_worker,
            daemon=True
        )
        self.memory_cleanup_thread.start()

        self.request_batching_thread = threading.Thread(
            target=self._request_batching_worker,
            daemon=True
        )
        self.request_batching_thread.start()

        self.resource_monitor_thread = threading.Thread(
            target=self._resource_monitor_worker,
            daemon=True
        )
        self.resource_monitor_thread.start()

    def optimize_memory_usage(self, data: Dict) -> Dict:
        """Optimize memory usage by reducing data duplication."""
        optimized = {}
        
        # Remove duplicate values using weak references
        value_cache = weakref.WeakValueDictionary()
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                if value in value_cache:
                    optimized[key] = value_cache[value]
                else:
                    value_cache[value] = value
                    optimized[key] = value
            else:
                optimized[key] = value

        # Compress large string values
        for key, value in optimized.items():
            if isinstance(value, str) and len(value) > settings.resource.lazy_loading_threshold:
                optimized[key] = self._compress_data(value)

        return optimized

    def _compress_data(self, data: str) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(
            data.encode('utf-8'),
            compresslevel=settings.network.compression_level
        )

    def _decompress_data(self, data: bytes) -> str:
        """Decompress gzip data."""
        return gzip.decompress(data).decode('utf-8')

    def cache_data(self, key: str, data: Any, size: int) -> None:
        """Cache data with size tracking."""
        with self._lock:
            if size > settings.cache.max_entry_size:
                logger.warning(f"Data too large to cache: {size} bytes")
                return

            # Check if we need to make space
            while self._get_cache_size() + size > settings.cache.max_total_size:
                self._evict_least_valuable_entry()

            # Add to cache
            self.memory_cache[key] = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                size=size,
                access_count=0,
                last_accessed=datetime.now()
            )

    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from cache with access tracking."""
        with self._lock:
            if key not in self.memory_cache:
                return None

            entry = self.memory_cache[key]
            entry.access_count += 1
            entry.last_accessed = datetime.now()

            return entry.data

    def _get_cache_size(self) -> int:
        """Get total size of cached data."""
        return sum(entry.size for entry in self.memory_cache.values())

    def _evict_least_valuable_entry(self) -> None:
        """Remove least valuable entry from cache."""
        if not self.memory_cache:
            return

        # Calculate value score for each entry
        current_time = datetime.now()
        entries = []
        for key, entry in self.memory_cache.items():
            # Value based on recency, access frequency and size
            age = (current_time - entry.last_accessed).total_seconds()
            value_score = (entry.access_count / (1 + age)) * (1 / (1 + entry.size))
            entries.append((key, value_score))

        # Remove entry with lowest value
        if entries:
            worst_key = min(entries, key=lambda x: x[1])[0]
            del self.memory_cache[worst_key]

    def _memory_cleanup_worker(self):
        """Background thread for memory cleanup."""
        while True:
            try:
                # Check cache size periodically
                if self._get_cache_size() > settings.cache.max_total_size:
                    self._evict_least_valuable_entry()

                # Sleep to prevent excessive CPU usage
                time.sleep(settings.cache.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in memory cleanup: {e}")

    def _resource_monitor_worker(self):
        """Background thread for resource monitoring."""
        while True:
            try:
                # Monitor CPU usage
                cpu_percent = psutil.cpu_percent()
                if cpu_percent > settings.resource.max_cpu_percent:
                    logger.warning(f"High CPU usage: {cpu_percent}%")
                    self._reduce_cpu_usage()

                # Monitor memory usage
                memory = psutil.Process().memory_info()
                if memory.rss > settings.resource.max_memory_mb * 1024 * 1024:
                    logger.warning(f"High memory usage: {memory.rss / (1024 * 1024)}MB")
                    self._reduce_memory_usage()

                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")

    def _reduce_cpu_usage(self):
        """Reduce CPU usage by adjusting thread pool size."""
        current_workers = self._executor._max_workers
        if current_workers > 1:
            self._executor._max_workers = max(1, current_workers - 1)
            logger.info(f"Reduced thread pool size to {self._executor._max_workers}")

    def _reduce_memory_usage(self):
        """Reduce memory usage by clearing cache and unused connections."""
        with self._lock:
            # Clear half of the cache
            cache_size = len(self.memory_cache)
            if cache_size > 0:
                entries_to_remove = cache_size // 2
                self._evict_least_valuable_entry()
                logger.info(f"Cleared {entries_to_remove} cache entries")

            # Close unused connections
            for domain, connections in self.connection_pool.items():
                if len(connections) > settings.network.max_concurrent_connections:
                    excess = len(connections) - settings.network.max_concurrent_connections
                    for _ in range(excess):
                        if connections:
                            conn = connections.pop()
                            try:
                                # Implement connection closing logic here
                                pass
                            except Exception as e:
                                logger.error(f"Error closing connection: {e}")

    def optimize_network_requests(self, requests: List[Dict]) -> List[Dict]:
        """Optimize network requests by batching and compression."""
        # Group requests by domain
        domain_groups = defaultdict(list)
        for request in requests:
            domain = request.get('domain', 'default')
            domain_groups[domain].append(request)

        # Batch requests
        batched_requests = []
        for domain, domain_requests in domain_groups.items():
            # Split into batches
            for i in range(0, len(domain_requests), settings.network.request_batch_size):
                batch = domain_requests[i:i + settings.network.request_batch_size]
                batched_requests.append({
                    'domain': domain,
                    'requests': batch,
                    'compressed': self._compress_batch(batch)
                })

        return batched_requests

    def _compress_batch(self, batch: List[Dict]) -> bytes:
        """Compress a batch of requests."""
        return zlib.compress(
            json.dumps(batch).encode('utf-8'),
            level=settings.network.compression_level
        )

    def _decompress_batch(self, compressed: bytes) -> List[Dict]:
        """Decompress a batch of requests."""
        return json.loads(zlib.decompress(compressed).decode('utf-8'))

    def _request_batching_worker(self):
        """Background thread for request batching."""
        while True:
            try:
                # Process queued requests
                if not self.request_queue.empty():
                    requests = []
                    while not self.request_queue.empty() and len(requests) < settings.network.request_batch_size:
                        requests.append(self.request_queue.get())

                    if requests:
                        batched = self.optimize_network_requests(requests)
                        self._process_batched_requests(batched)

                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in request batching: {e}")

    def _process_batched_requests(self, batched_requests: List[Dict]) -> None:
        """Process batched requests."""
        futures = []
        for batch in batched_requests:
            try:
                # Get connection from pool
                connection = self._get_connection(batch['domain'])
                
                # Process batch
                if connection:
                    future = self._executor.submit(self._send_batch, connection, batch)
                    futures.append((connection, future))
                    
            except Exception as e:
                logger.error(f"Error processing batch: {e}")

        # Wait for all batches to complete
        for connection, future in futures:
            try:
                future.result()
                self._return_connection(batch['domain'], connection)
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")

    def _get_connection(self, domain: str) -> Optional[Any]:
        """Get connection from pool or create new one."""
        with self._lock:
            if self.connection_pool[domain]:
                return self.connection_pool[domain].pop()
            return self._create_connection(domain)

    def _return_connection(self, domain: str, connection: Any) -> None:
        """Return connection to pool."""
        with self._lock:
            if connection and len(self.connection_pool[domain]) < settings.network.max_concurrent_connections:
                self.connection_pool[domain].append(connection)

    def _create_connection(self, domain: str) -> Optional[Any]:
        """Create new connection for domain."""
        try:
            # Implement connection creation logic here
            return None
        except Exception as e:
            logger.error(f"Error creating connection: {e}")
            return None

    def _send_batch(self, connection: Any, batch: Dict) -> None:
        """Send batched requests using connection."""
        try:
            # Implement batch sending logic here
            pass
        except Exception as e:
            logger.error(f"Error sending batch: {e}")

    def optimize_cpu_usage(self, data: Dict) -> Dict:
        """Optimize CPU usage by implementing lazy loading."""
        optimized = {}
        
        for key, value in data.items():
            if isinstance(value, (str, bytes)) and len(str(value)) > settings.resource.lazy_loading_threshold:
                # Create lazy loading wrapper
                optimized[key] = self._create_lazy_loader(value)
            else:
                optimized[key] = value

        return optimized

    def _create_lazy_loader(self, data: Any) -> Any:
        """Create lazy loading wrapper for data."""
        class LazyLoader:
            def __init__(self, data):
                self._data = data
                self._loaded = False
                self._value = None
                self._lock = threading.Lock()

            def __get__(self, instance, owner):
                if not self._loaded:
                    with self._lock:
                        if not self._loaded:  # Double-checked locking
                            self._value = self._process_data(self._data)
                            self._loaded = True
                return self._value

            def _process_data(self, data):
                # Implement data processing logic here
                return data

        return LazyLoader(data)

    def cleanup(self):
        """Cleanup resources."""
        # Clear memory cache
        self.memory_cache.clear()

        # Close connections
        for domain, connections in self.connection_pool.items():
            for connection in connections:
                try:
                    # Implement connection closing logic here
                    pass
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            self.connection_pool[domain].clear()

        # Shutdown thread pool
        self._executor.shutdown(wait=True) 