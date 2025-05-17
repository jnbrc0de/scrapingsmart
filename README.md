# SmartScraping - Sistema Inteligente de Web Scraping

## 📋 Descrição
SmartScraping é um sistema avançado de web scraping que utiliza técnicas de inteligência artificial para extrair dados de forma eficiente e inteligente de diversos sites de e-commerce. O sistema é capaz de se adaptar a diferentes estruturas de sites, lidar com bloqueios e otimizar a extração de dados.

## 🚀 Funcionalidades

### 1. Extração Inteligente
- Detecção automática de estrutura de sites
- Adaptação dinâmica a mudanças de layout
- Suporte a múltiplos sites simultaneamente
- Extração de dados estruturados

### 2. Gerenciamento de Sessão
- Controle de cookies e sessões
- Rotação de proxies
- Gerenciamento de headers
- Tratamento de bloqueios

### 3. Monitoramento e Métricas
- Coleta de métricas em tempo real
- Monitoramento de performance
- Alertas de falhas
- Dashboard de status

### 4. Cache e Histórico
- Sistema de cache inteligente
- Histórico de extrações
- Otimização de requisições
- Persistência de dados

## 🛠️ Tecnologias Utilizadas

- Python 3.8+
- Playwright para automação
- FastAPI para API REST
- SQLite para armazenamento
- Prometheus para métricas
- Docker para containerização

## 📦 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/smartscraping.git
cd smartscraping
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure o ambiente:
```bash
cp env_config.txt .env
# Edite o arquivo .env com suas configurações
```

5. Inicie o sistema:
```bash
python src/main.py
```

## ⚙️ Configuração

### Variáveis de Ambiente
O sistema utiliza as seguintes variáveis de ambiente (definidas no arquivo `.env`):

#### Navegador
- `BROWSER_HEADLESS`: Modo headless do navegador
- `BROWSER_TIMEOUT`: Timeout das requisições
- `BROWSER_USER_AGENT`: User Agent personalizado

#### Proxy
- `USE_PROXY`: Habilitação de proxy
- `PROXY_LIST`: Lista de proxies disponíveis

#### Performance
- `MIN_DELAY`: Delay mínimo entre requisições
- `MAX_DELAY`: Delay máximo entre requisições
- `MAX_RETRIES`: Número máximo de tentativas
- `RETRY_DELAY`: Delay entre tentativas

#### Monitoramento
- `ENABLE_METRICS`: Habilitação de métricas
- `METRICS_PORT`: Porta do servidor de métricas
- `ENABLE_ALERTS`: Habilitação de alertas

#### Armazenamento
- `CACHE_FILE`: Arquivo de cache
- `HISTORY_FILE`: Arquivo de histórico
- `METRICS_FILE`: Arquivo de métricas

## 📊 Estrutura do Projeto

```
smartscraping/
├── src/
│   ├── agent/              # Agentes de scraping
│   ├── browser/            # Gerenciamento do navegador
│   ├── cache/              # Sistema de cache
│   ├── history/            # Histórico de extrações
│   ├── monitoring/         # Monitoramento e métricas
│   └── utils/              # Utilitários
├── data/                   # Dados extraídos
├── logs/                   # Logs do sistema
├── tests/                  # Testes automatizados
├── .env                    # Configurações
├── requirements.txt        # Dependências
└── README.md              # Documentação
```

## 🔄 Fluxo de Funcionamento

1. **Inicialização**
   - Carregamento de configurações
   - Inicialização do navegador
   - Configuração de proxies

2. **Extração**
   - Detecção do site
   - Seleção da estratégia
   - Extração dos dados
   - Validação dos resultados

3. **Processamento**
   - Limpeza dos dados
   - Estruturação
   - Armazenamento
   - Cache

4. **Monitoramento**
   - Coleta de métricas
   - Verificação de erros
   - Envio de alertas
   - Logging

## 🧪 Testes

Execute os testes com:
```bash
pytest tests/
```

## 📈 Métricas

O sistema coleta as seguintes métricas:
- Taxa de sucesso
- Tempo de resposta
- Uso de recursos
- Erros e exceções

## 🔔 Alertas

O sistema envia alertas via:
- Email
- Slack
- Telegram

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Crie um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👥 Autores

- Seu Nome - Desenvolvimento inicial

## 🙏 Agradecimentos

- Todos os contribuidores
- Bibliotecas utilizadas
- Comunidade open source

## 🏭 Deploy e Operação em Produção

### Boas Práticas para Produção
- **Variáveis de Ambiente:** Nunca exponha segredos no código. Configure todas as senhas, tokens e chaves apenas via variáveis de ambiente.
- **Logger:** Configure o logger para nível INFO ou WARNING em produção. Não registre informações sensíveis nos logs.
- **Dependências:** Use sempre o `requirements.txt` com versões fixas para garantir reprodutibilidade.
- **Testes:** Execute todos os testes automatizados antes de cada deploy.
- **Monitoramento:** O sistema possui monitoramento básico. Para escalonamento automático e monitoramento avançado, implemente integrações externas conforme necessário.
- **Limitações:** Algumas funções de escalonamento e monitoramento são placeholders e não realizam ações reais de infraestrutura.

### Exemplo de Deploy
```bash
# 1. Configure variáveis de ambiente (.env)
# 2. Instale dependências
pip install -r requirements.txt
# 3. Execute as migrações e inicializações necessárias
# 4. Inicie o sistema
python src/main.py
``` 