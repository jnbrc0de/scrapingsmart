import os
import sys
import asyncio
import pytest
from pathlib import Path
from playwright.async_api import async_playwright

# Adiciona o diretório raiz do projeto ao PYTHONPATH
@pytest.fixture(scope="session", autouse=True)
def setup_python_path():
    """Adiciona o diretório raiz do projeto ao PYTHONPATH."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Configuração do ambiente para o Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    yield
    
    # Limpeza após os testes
    # Aqui você pode adicionar código para limpar arquivos temporários se necessário 

# Não definimos mais o fixture event_loop, deixamos o pytest-asyncio gerenciar isso

@pytest.fixture(scope="session")
async def playwright_browser():
    """Share a single playwright browser instance across tests."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials'
            ]
        )
        yield browser
        
        # Proper cleanup
        try:
            await browser.close()
        except Exception as e:
            print(f"Error closing browser: {e}") 