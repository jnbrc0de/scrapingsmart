# Sistema de Resiliência e Tratamento de Erros

## Visão Geral

O sistema de resiliência é responsável por garantir a continuidade operacional do scraping, implementando mecanismos robustos de tratamento de erros, retry e fallback.

## Componentes

### 1. Circuit Breaker
- Previne falhas em cascata
- Implementa backoff exponencial
- Gerencia estados de circuito
- Controla thresholds

### 2. Retry Manager
- Gerencia tentativas de retry
- Implementa estratégias de backoff
- Controla timeouts
- Gerencia jitter

### 3. Fallback Manager
- Gerencia estratégias alternativas
- Implementa fallback em cascata
- Controla priorização
- Gerencia cache

## Circuit Breaker

### 1. Estados
```python
class CircuitState(Enum):
    CLOSED = "closed"      # Operação normal
    OPEN = "open"         # Falha, não tenta
    HALF_OPEN = "half_open"  # Testando recuperação
```

### 2. Implementação
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def execute(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError()

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

### 3. Configuração
```python
circuit_config = {
    'failure_threshold': 5,
    'recovery_timeout': 60,
    'half_open_timeout': 30,
    'success_threshold': 2
}
```

## Retry Manager

### 1. Estratégias

#### Exponential Backoff
```python
def exponential_backoff(attempt):
    return min(300, (2 ** attempt) + random.uniform(0, 1))
```

#### Fibonacci Backoff
```python
def fibonacci_backoff(attempt):
    a, b = 0, 1
    for _ in range(attempt):
        a, b = b, a + b
    return min(300, a + random.uniform(0, 1))
```

#### Jitter
```python
def add_jitter(delay):
    return delay * (0.5 + random.random())
```

### 2. Implementação
```python
class RetryManager:
    def __init__(self, max_retries=3, backoff_strategy=exponential_backoff):
        self.max_retries = max_retries
        self.backoff_strategy = backoff_strategy

    async def execute(self, func, *args, **kwargs):
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if not self._should_retry(e):
                    break
                    
                delay = self.backoff_strategy(attempt)
                await asyncio.sleep(delay)
        
        raise last_exception
```

### 3. Configuração
```python
retry_config = {
    'max_retries': 3,
    'backoff_strategy': 'exponential',
    'jitter': True,
    'timeout': 30
}
```

## Fallback Manager

### 1. Estratégias

#### Proxy Fallback
```python
class ProxyFallback:
    def __init__(self, proxies):
        self.proxies = proxies
        self.current_index = 0

    async def get_next_proxy(self):
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
```

#### Strategy Fallback
```python
class StrategyFallback:
    def __init__(self, strategies):
        self.strategies = strategies
        self.current_strategy = 0

    async def get_next_strategy(self):
        strategy = self.strategies[self.current_strategy]
        self.current_strategy = (self.current_strategy + 1) % len(self.strategies)
        return strategy
```

### 2. Implementação
```python
class FallbackManager:
    def __init__(self, fallbacks):
        self.fallbacks = fallbacks
        self.current_fallback = 0

    async def execute(self, func, *args, **kwargs):
        last_exception = None
        
        for fallback in self.fallbacks:
            try:
                return await fallback.execute(func, *args, **kwargs)
            except Exception as e:
                last_exception = e
                continue
        
        raise last_exception
```

### 3. Configuração
```python
fallback_config = {
    'proxy_fallback': {
        'enabled': True,
        'max_attempts': 3
    },
    'strategy_fallback': {
        'enabled': True,
        'max_attempts': 2
    },
    'cache_fallback': {
        'enabled': True,
        'ttl': 3600
    }
}
```

## Tratamento de Erros

### 1. Hierarquia de Exceções
```python
class ScraperError(Exception):
    """Base exception for scraper errors"""
    pass

class NetworkError(ScraperError):
    """Network related errors"""
    pass

class ProxyError(NetworkError):
    """Proxy related errors"""
    pass

class BrowserError(ScraperError):
    """Browser related errors"""
    pass

class ExtractionError(ScraperError):
    """Extraction related errors"""
    pass
```

### 2. Handlers

#### Network Handler
```python
async def handle_network_error(error):
    if isinstance(error, ProxyError):
        await proxy_fallback.execute()
    elif isinstance(error, TimeoutError):
        await retry_manager.execute()
    else:
        raise error
```

#### Browser Handler
```python
async def handle_browser_error(error):
    if isinstance(error, BrowserError):
        await browser_manager.restart()
    elif isinstance(error, NavigationError):
        await retry_manager.execute()
    else:
        raise error
```

#### Extraction Handler
```python
async def handle_extraction_error(error):
    if isinstance(error, ExtractionError):
        await strategy_fallback.execute()
    elif isinstance(error, ValidationError):
        await retry_manager.execute()
    else:
        raise error
```

### 3. Logging
```python
async def log_error(error, context):
    logger.error(
        "Error occurred",
        extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'stack_trace': traceback.format_exc()
        }
    )
```

## Monitoramento

### 1. Métricas

#### Circuit Breaker
```python
circuit_metrics = {
    'circuit_state': Gauge(
        'scraper_circuit_state',
        'Current state of circuit breaker',
        ['domain']
    ),
    'circuit_failures': Counter(
        'scraper_circuit_failures',
        'Number of circuit failures',
        ['domain']
    )
}
```

#### Retry
```python
retry_metrics = {
    'retry_attempts': Counter(
        'scraper_retry_attempts',
        'Number of retry attempts',
        ['domain', 'error_type']
    ),
    'retry_success': Counter(
        'scraper_retry_success',
        'Number of successful retries',
        ['domain', 'error_type']
    )
}
```

#### Fallback
```python
fallback_metrics = {
    'fallback_usage': Counter(
        'scraper_fallback_usage',
        'Number of fallback usages',
        ['domain', 'fallback_type']
    ),
    'fallback_success': Counter(
        'scraper_fallback_success',
        'Number of successful fallbacks',
        ['domain', 'fallback_type']
    )
}
```

### 2. Alertas

#### Circuit Breaker
```yaml
alert: CircuitBreakerOpen
expr: scraper_circuit_state == 1
for: 5m
labels:
  severity: critical
annotations:
  summary: "Circuit breaker open"
  description: "Circuit breaker has been open for 5 minutes"
```

#### Retry
```yaml
alert: HighRetryRate
expr: rate(scraper_retry_attempts[5m]) > 10
for: 5m
labels:
  severity: warning
annotations:
  summary: "High retry rate"
  description: "More than 10 retries per 5 minutes"
```

#### Fallback
```yaml
alert: HighFallbackUsage
expr: rate(scraper_fallback_usage[5m]) > 5
for: 5m
labels:
  severity: warning
annotations:
  summary: "High fallback usage"
  description: "More than 5 fallbacks per 5 minutes"
```

## Próximos Passos

1. Implementar análise de padrões de erro
2. Adicionar mais estratégias de fallback
3. Melhorar detecção de problemas
4. Expandir métricas
5. Implementar auto-healing 