# Documentação Técnica - SmartScraping

## Arquitetura do Sistema

### 1. Componentes Principais

#### 1.1 Agente de Scraping (`src/agent/`)
- Responsável pela lógica principal de extração
- Gerencia estratégias de scraping
- Coordena o fluxo de extração
- Implementa retry e fallback

#### 1.2 Gerenciador de Browser (`src/browser/`)
- Controle do navegador Playwright
- Gerenciamento de sessões
- Rotação de proxies
- Tratamento de cookies

#### 1.3 Sistema de Cache (`src/cache/`)
- Cache em memória
- Persistência em disco
- TTL configurável
- Limpeza automática

#### 1.4 Histórico (`src/history/`)
- Registro de extrações
- Métricas de sucesso
- Análise de performance
- Sugestões de otimização

#### 1.5 Monitoramento (`src/monitoring/`)
- Coleta de métricas
- Alertas
- Dashboard
- Logging

### 2. Estratégias de Scraping

#### 2.1 Estratégia Base
```python
class Strategy:
    def __init__(self, name, patterns, selectors, confidence):
        self.name = name
        self.patterns = patterns
        self.selectors = selectors
        self.confidence = confidence
```

#### 2.2 Estratégias Específicas
- Amazon
- Mercado Livre
- Magazine Luiza
- Outros sites

### 3. Fluxo de Dados

1. **Entrada**
   - URL do produto
   - Configurações
   - Parâmetros de extração

2. **Processamento**
   - Detecção do site
   - Seleção da estratégia
   - Extração dos dados
   - Validação

3. **Saída**
   - Dados estruturados
   - Métricas
   - Logs
   - Alertas

### 4. Sistema de Cache

#### 4.1 Estrutura
```python
{
    "url": {
        "data": {...},
        "timestamp": 1234567890,
        "ttl": 3600
    }
}
```

#### 4.2 Operações
- Get
- Set
- Delete
- Cleanup

### 5. Monitoramento

#### 5.1 Métricas
- Taxa de sucesso
- Tempo de resposta
- Uso de recursos
- Erros

#### 5.2 Alertas
- Email
- Slack
- Telegram

### 6. Segurança

#### 6.1 Proteções
- Rate limiting
- Rotação de proxies
- User agents
- Headers personalizados

#### 6.2 Boas Práticas
- Não exponha chaves
- Use HTTPS
- Valide inputs
- Sanitize outputs

### 7. Performance

#### 7.1 Otimizações
- Cache inteligente
- Conexões persistentes
- Pool de recursos
- Compressão

#### 7.2 Limites
- Requisições concorrentes
- Tamanho do cache
- Timeout
- Retries

### 8. Tratamento de Erros

#### 8.1 Tipos de Erros
- Network
- Timeout
- Parse
- Validation

#### 8.2 Estratégias
- Retry
- Fallback
- Circuit breaker
- Degrade gracefully

### 9. Logging

#### 9.1 Níveis
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

#### 9.2 Formato
```json
{
    "timestamp": "2024-01-01T00:00:00Z",
    "level": "INFO",
    "message": "Mensagem",
    "context": {...}
}
```

### 10. Testes

#### 10.1 Tipos
- Unitários
- Integração
- E2E
- Performance

#### 10.2 Cobertura
- Código
- Casos de uso
- Edge cases
- Erros

### 11. Deployment

#### 11.1 Requisitos
- Python 3.8+
- Playwright
- SQLite
- Prometheus

#### 11.2 Configuração
- Variáveis de ambiente
- Arquivos de configuração
- Logs
- Dados

### 12. Manutenção

#### 12.1 Rotinas
- Backup
- Limpeza
- Monitoramento
- Atualizações

#### 12.2 Troubleshooting
- Logs
- Métricas
- Alertas
- Debug

## Exemplos de Uso

### 1. Extração Básica
```python
from src.agent import SmartScrapingAgent
from src.browser import BrowserManager

async def main():
    browser = BrowserManager()
    agent = SmartScrapingAgent("https://exemplo.com/produto", browser)
    result = await agent.extract()
    print(result.data)
```

### 2. Com Cache
```python
from src.cache import CacheManager

cache = CacheManager()
data = await cache.get("url")
if not data:
    data = await agent.extract()
    await cache.set("url", data)
```

### 3. Com Monitoramento
```python
from src.monitoring import MetricsCollector

metrics = MetricsCollector()
with metrics.timer("extraction"):
    result = await agent.extract()
metrics.record_success(result.success)
```

## Boas Práticas

1. **Código**
   - Documente funções
   - Use type hints
   - Siga PEP 8
   - Escreva testes

2. **Segurança**
   - Valide inputs
   - Sanitize outputs
   - Use HTTPS
   - Proteja chaves

3. **Performance**
   - Use cache
   - Otimize queries
   - Monitore recursos
   - Limpe dados

4. **Manutenção**
   - Mantenha logs
   - Atualize dependências
   - Faça backup
   - Documente mudanças 