# Documentação de Arquitetura - SmartScraping

## Arquitetura Refatorada

Esta documentação explica as mudanças arquiteturais realizadas para melhorar a organização, manutenção e performance do sistema de scraping.

### Motivações para Refatoração

1. **Eliminar Código Duplicado** - Havia múltiplas implementações de funcionalidades semelhantes (cache, métricas, etc.)
2. **Centralizar Configurações** - Diferentes partes do sistema tinham suas próprias configurações
3. **Melhorar Testabilidade** - Componentes fortemente acoplados dificultavam testes unitários
4. **Facilitar Manutenção** - Estrutura anterior tinha muitos arquivos com responsabilidades sobrepostas

### Nova Estrutura de Diretórios

```
src/
├── services/               # Serviços compartilhados centralizados
│   ├── cache/              # Implementação unificada de cache
│   ├── metrics/            # Implementação unificada de métricas
│   ├── proxy/              # Gerenciamento centralizado de proxies
│   ├── config.py           # Configurações centralizadas
│   └── container.py        # Contêiner de injeção de dependência
├── browser/                # Gerenciamento de navegador
│   ├── manager.py          # Implementação original (para compatibilidade)
│   └── manager_di.py       # Nova implementação com injeção de dependência
├── strategies/             # Estratégias de scraping para sites específicos
│   ├── base.py             # Classe base para todas as estratégias
│   ├── magalu.py           # Estratégia para Magazine Luiza
│   └── ...                 # Outras estratégias específicas
└── agent/                  # Agentes de scraping
    └── agent.py            # Implementação do agente SmartScraping
```

### Serviços Compartilhados

#### 1. Configuração Centralizada (`services/config.py`)

- Carrega configurações de variáveis de ambiente e arquivos
- Fornece acesso centralizado por notação de pontos
- Gerencia caminhos de arquivos e diretórios

#### 2. Gerenciador de Cache Unificado (`services/cache/manager.py`)

- Suporta múltiplos backends (memória, arquivo, Redis)
- Implementa políticas de expiração e LRU
- Interface consistente para toda a aplicação

#### 3. Gerenciador de Métricas Unificado (`services/metrics/manager.py`)

- Coleta métricas em memória ou arquivo
- Exportação opcional para Prometheus
- Sistema de alertas baseado em limiares

#### 4. Gerenciador de Proxy Unificado (`services/proxy/manager.py`)

- Gerencia conexões com provedores de proxy (Brightdata, etc.)
- Rotação automática de IPs
- Tratamento de erros e bloqueios

### Injeção de Dependência

O sistema agora usa injeção de dependência através de um contêiner de serviços:

```python
# Exemplo de uso
from src.services.container import container

# Inicializa serviços
await container.initialize()

# Obtém serviços
cache = container.get_cache()
metrics = container.get_metrics()
proxy = container.get_proxy()

# Uso típico
if cache.get(key):
    metrics.record_cache_hit("domain")
else:
    metrics.record_cache_miss("domain")
```

### Benefícios da Nova Arquitetura

1. **Separação de Responsabilidades** - Cada componente tem uma função específica
2. **Testabilidade** - Componentes podem ser testados isoladamente
3. **Reutilização** - Serviços comuns são compartilhados entre todo o sistema
4. **Configuração Simplificada** - Uma única fonte de configuração
5. **Monitoramento Unificado** - Coleta centralizada de métricas

### Migração

O sistema mantém compatibilidade com a implementação anterior:

1. Arquivos originais foram preservados
2. Novas implementações usam novos nomes de arquivos
3. Classes antigas referenciam as novas implementações

Para migrar código existente:

```python
# Antes
from src.agent.cache_manager import CacheManager
cache = CacheManager()

# Depois
from src.services.container import container
await container.initialize()
cache = container.get_cache()
```

### Próximos Passos

1. Migrar todos os componentes para usar o contêiner de serviços
2. Implementar testes unitários para cada serviço
3. Refatorar agentes e estratégias para usar a injeção de dependência
4. Adicionar mais documentação e exemplos 