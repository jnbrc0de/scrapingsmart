# Sistema de Testes

## Visão Geral

O sistema de testes é responsável por garantir a qualidade e confiabilidade do código através de testes automatizados em diferentes níveis.

## Estrutura de Testes

### 1. Testes Unitários
- Testam componentes isolados
- Verificam lógica de negócio
- Validam funções puras
- Testam edge cases

### 2. Testes de Integração
- Testam interação entre componentes
- Validam fluxos de dados
- Verificam integrações externas
- Testam cenários reais

### 3. Testes End-to-End
- Testam fluxos completos
- Validam comportamento do sistema
- Verificam integrações
- Testam cenários de produção

## Testes Unitários

### 1. Estrutura
```python
# tests/unit/test_extractor.py
import pytest
from src.extractor import Extractor

class TestExtractor:
    @pytest.fixture
    def extractor(self):
        return Extractor()

    def test_extract_price(self, extractor):
        html = '<div class="price">R$ 100,00</div>'
        price = extractor.extract_price(html)
        assert price == 100.00

    def test_extract_price_with_discount(self, extractor):
        html = '''
        <div class="price">R$ 100,00</div>
        <div class="discount">R$ 80,00</div>
        '''
        price = extractor.extract_price(html)
        assert price == 80.00

    def test_extract_price_invalid(self, extractor):
        html = '<div class="price">Invalid</div>'
        with pytest.raises(ValueError):
            extractor.extract_price(html)
```

### 2. Mocks
```python
# tests/unit/test_browser.py
import pytest
from unittest.mock import Mock, patch
from src.browser import Browser

class TestBrowser:
    @pytest.fixture
    def mock_page(self):
        page = Mock()
        page.goto.return_value = None
        page.content.return_value = '<html>Test</html>'
        return page

    @pytest.fixture
    def browser(self, mock_page):
        with patch('playwright.async_api.Page', return_value=mock_page):
            return Browser()

    async def test_navigate(self, browser, mock_page):
        await browser.navigate('https://example.com')
        mock_page.goto.assert_called_once_with('https://example.com')

    async def test_get_content(self, browser, mock_page):
        content = await browser.get_content()
        assert content == '<html>Test</html>'
```

### 3. Parametrização
```python
# tests/unit/test_parser.py
import pytest
from src.parser import Parser

@pytest.mark.parametrize('input,expected', [
    ('R$ 100,00', 100.00),
    ('R$ 1.000,00', 1000.00),
    ('R$ 1.000.000,00', 1000000.00),
])
def test_parse_price(input, expected):
    parser = Parser()
    assert parser.parse_price(input) == expected
```

## Testes de Integração

### 1. Estrutura
```python
# tests/integration/test_scraping_flow.py
import pytest
from src.scraper import Scraper
from src.database import Database

class TestScrapingFlow:
    @pytest.fixture
    async def scraper(self):
        scraper = Scraper()
        await scraper.initialize()
        yield scraper
        await scraper.cleanup()

    @pytest.fixture
    async def database(self):
        db = Database()
        await db.connect()
        yield db
        await db.disconnect()

    async def test_complete_flow(self, scraper, database):
        # Testa fluxo completo de scraping
        url = 'https://example.com/product/1'
        result = await scraper.scrape(url)
        
        # Verifica extração
        assert result.price is not None
        assert result.title is not None
        
        # Verifica persistência
        saved = await database.get_product(url)
        assert saved.price == result.price
```

### 2. Fixtures
```python
# tests/integration/conftest.py
import pytest
import asyncio
from src.config import TestConfig

@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope='session')
async def test_config():
    config = TestConfig()
    await config.initialize()
    yield config
    await config.cleanup()

@pytest.fixture
async def test_database(test_config):
    db = await test_config.get_database()
    yield db
    await db.cleanup()
```

### 3. Mocks de Serviços
```python
# tests/integration/test_external_services.py
import pytest
from unittest.mock import AsyncMock
from src.services import ExternalService

class TestExternalServices:
    @pytest.fixture
    def mock_service(self):
        service = AsyncMock(spec=ExternalService)
        service.get_data.return_value = {'status': 'success'}
        return service

    async def test_service_integration(self, mock_service):
        result = await mock_service.get_data()
        assert result['status'] == 'success'
```

## Testes End-to-End

### 1. Estrutura
```python
# tests/e2e/test_scraping_system.py
import pytest
from src.system import ScrapingSystem

class TestScrapingSystem:
    @pytest.fixture
    async def system(self):
        system = ScrapingSystem()
        await system.start()
        yield system
        await system.stop()

    async def test_complete_system(self, system):
        # Configura URLs para teste
        urls = [
            'https://example.com/product/1',
            'https://example.com/product/2'
        ]
        
        # Inicia scraping
        await system.add_urls(urls)
        await system.wait_for_completion()
        
        # Verifica resultados
        results = await system.get_results()
        assert len(results) == 2
        assert all(r.status == 'success' for r in results)
```

### 2. Configuração
```python
# tests/e2e/conftest.py
import pytest
import os
from src.config import E2EConfig

@pytest.fixture(scope='session')
def e2e_config():
    return E2EConfig(
        database_url=os.getenv('TEST_DATABASE_URL'),
        proxy_url=os.getenv('TEST_PROXY_URL'),
        browser_path=os.getenv('TEST_BROWSER_PATH')
    )

@pytest.fixture(scope='session')
async def test_environment(e2e_config):
    # Configura ambiente de teste
    await e2e_config.setup()
    yield e2e_config
    await e2e_config.teardown()
```

### 3. Dados de Teste
```python
# tests/e2e/test_data.py
TEST_PRODUCTS = [
    {
        'url': 'https://example.com/product/1',
        'expected_price': 100.00,
        'expected_title': 'Product 1'
    },
    {
        'url': 'https://example.com/product/2',
        'expected_price': 200.00,
        'expected_title': 'Product 2'
    }
]

TEST_ERROR_CASES = [
    {
        'url': 'https://example.com/invalid',
        'expected_error': 'ProductNotFound'
    },
    {
        'url': 'https://example.com/timeout',
        'expected_error': 'TimeoutError'
    }
]
```

## Cobertura de Testes

### 1. Configuração
```yaml
# .coveragerc
[run]
source = src
omit = 
    */tests/*
    */migrations/*
    */__init__.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
```

### 2. Relatório
```python
# tests/coverage_report.py
import coverage
import pytest

def generate_coverage_report():
    cov = coverage.Coverage()
    cov.start()
    
    # Executa testes
    pytest.main(['tests/'])
    
    cov.stop()
    cov.save()
    
    # Gera relatório
    cov.report()
    cov.html_report(directory='coverage_html')
```

## CI/CD

### 1. Pipeline
```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### 2. Ambiente
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  test:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      - TEST_DATABASE_URL=postgresql://test:test@db:5432/test
      - TEST_PROXY_URL=http://proxy:8080
    depends_on:
      - db
      - proxy

  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=test

  proxy:
    image: nginx:alpine
    ports:
      - "8080:80"
```

## Próximos Passos

1. Implementar testes de performance
2. Adicionar testes de carga
3. Melhorar cobertura
4. Expandir cenários
5. Implementar testes de segurança 