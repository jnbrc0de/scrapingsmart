# Sistema de Monitoramento de Preços

Sistema de monitoramento de preços com recursos avançados de scraping, análise de dados e alertas.

## Funcionalidades

- Scraping automatizado de preços
- Análise de dados e tendências
- Sistema de alertas por email e Slack
- Monitoramento de performance
- Logs centralizados
- Health checks
- Métricas Prometheus

## Requisitos

- Python 3.8+
- Elasticsearch
- Prometheus
- Redis (opcional)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
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

4. Configure as variáveis de ambiente:
- Copie o arquivo `.env.example` para `.env`
- Preencha as variáveis necessárias

## Configuração

1. Elasticsearch:
- Instale o Elasticsearch
- Configure a URL no `.env`

2. Prometheus:
- Instale o Prometheus
- Configure a porta no `.env`

3. Alertas:
- Configure as credenciais de email no `.env`
- Configure o webhook do Slack no `.env`

## Uso

1. Inicie o sistema:
```bash
python src/main.py
```

2. Acesse as métricas:
- Prometheus: http://localhost:8000/metrics
- Grafana (opcional): http://localhost:3000

## Estrutura do Projeto

```
.
├── src/
│   ├── monitoring/
│   │   ├── alerts.py
│   │   ├── logger.py
│   │   ├── performance.py
│   │   └── uptime.py
│   └── main.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes. 