from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
from dataclasses import dataclass
import logging
from config.settings import (
    CIRCUIT_BREAKER_THRESHOLD,
    CIRCUIT_BREAKER_WINDOW,
    CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT,
    MAX_RETRIES,
    BASE_RETRY_DELAY
)

logger = logging.getLogger(__name__)

@dataclass
class CircuitState:
    failures: int = 0
    last_failure: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open
    last_success: Optional[datetime] = None
    retry_count: int = 0

class DomainCircuitBreaker:
    def __init__(self):
        self.circuits: Dict[str, CircuitState] = {}
        self._lock = asyncio.Lock()

    async def record_failure(self, domain: str, error_type: str) -> None:
        """Record a failure for a domain and update circuit state."""
        async with self._lock:
            if domain not in self.circuits:
                self.circuits[domain] = CircuitState()

            circuit = self.circuits[domain]
            circuit.failures += 1
            circuit.last_failure = datetime.now()
            
            # Check if we should open the circuit
            if (circuit.failures >= CIRCUIT_BREAKER_THRESHOLD and 
                circuit.state == "closed"):
                circuit.state = "open"
                logger.warning(f"Circuit opened for domain {domain} after {circuit.failures} failures")
                
                # Schedule half-open state
                asyncio.create_task(self._schedule_half_open(domain))

    async def record_success(self, domain: str) -> None:
        """Record a success for a domain and update circuit state."""
        async with self._lock:
            if domain not in self.circuits:
                self.circuits[domain] = CircuitState()

            circuit = self.circuits[domain]
            circuit.last_success = datetime.now()
            
            if circuit.state == "half-open":
                circuit.state = "closed"
                circuit.failures = 0
                circuit.retry_count = 0
                logger.info(f"Circuit closed for domain {domain} after successful request")

    async def can_execute(self, domain: str) -> bool:
        """Check if a request can be executed for a domain."""
        async with self._lock:
            if domain not in self.circuits:
                return True

            circuit = self.circuits[domain]
            
            if circuit.state == "closed":
                return True
                
            if circuit.state == "open":
                # Check if we should transition to half-open
                if (circuit.last_failure and 
                    datetime.now() - circuit.last_failure > timedelta(seconds=CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT)):
                    circuit.state = "half-open"
                    return True
                return False
                
            if circuit.state == "half-open":
                return True

            return False

    async def get_retry_delay(self, domain: str) -> float:
        """Calculate adaptive retry delay for a domain."""
        async with self._lock:
            if domain not in self.circuits:
                return BASE_RETRY_DELAY

            circuit = self.circuits[domain]
            
            if circuit.retry_count >= MAX_RETRIES:
                return -1  # No more retries
                
            # Exponential backoff with jitter
            delay = BASE_RETRY_DELAY * (2 ** circuit.retry_count)
            jitter = delay * 0.1 * (1 + (circuit.retry_count / MAX_RETRIES))
            
            circuit.retry_count += 1
            return delay + jitter

    async def _schedule_half_open(self, domain: str) -> None:
        """Schedule transition to half-open state."""
        await asyncio.sleep(CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT)
        
        async with self._lock:
            if domain in self.circuits:
                circuit = self.circuits[domain]
                if circuit.state == "open":
                    circuit.state = "half-open"
                    logger.info(f"Circuit half-opened for domain {domain}")

    async def reset_circuit(self, domain: str) -> None:
        """Reset circuit state for a domain."""
        async with self._lock:
            if domain in self.circuits:
                self.circuits[domain] = CircuitState()
                logger.info(f"Circuit reset for domain {domain}")

    async def get_circuit_stats(self, domain: str) -> Dict:
        """Get current circuit statistics for a domain."""
        async with self._lock:
            if domain not in self.circuits:
                return {
                    "state": "closed",
                    "failures": 0,
                    "retry_count": 0
                }

            circuit = self.circuits[domain]
            return {
                "state": circuit.state,
                "failures": circuit.failures,
                "retry_count": circuit.retry_count,
                "last_failure": circuit.last_failure.isoformat() if circuit.last_failure else None,
                "last_success": circuit.last_success.isoformat() if circuit.last_success else None
            } 