import pytest
import asyncio
import os
from datetime import datetime

# Skip all tests in this file until we update the implementation
pytestmark = pytest.mark.skip(reason="Brightdata tests need to be updated for new architecture")

@pytest.fixture
async def brightdata_manager():
    """Fixture para o gerenciador do Brightdata."""
    from src.agent.brightdata_manager import BrightdataManager
    manager = BrightdataManager()
    await manager.initialize()
    yield manager
    
@pytest.fixture
async def browser_manager():
    """Fixture para o gerenciador de navegador."""
    from src.agent.browser_manager import BrowserManager
    manager = BrowserManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()
    
@pytest.mark.asyncio
async def test_brightdata_initialization(brightdata_manager):
    """Testa inicialização do Brightdata."""
    assert brightdata_manager.config.enabled, "Brightdata deve estar habilitado"
    assert brightdata_manager.is_initialized, "Brightdata deve estar inicializado"
    
    # Verifica configuração
    assert brightdata_manager.config.username is not None
    assert brightdata_manager.config.password is not None
    
@pytest.mark.asyncio
async def test_ip_check(brightdata_manager):
    """Testa verificação de IP."""
    ip = await brightdata_manager.check_current_ip()
    assert ip is not None
    assert ip != "127.0.0.1"  # Não deve ser localhost
    
@pytest.mark.asyncio
async def test_ip_rotation(brightdata_manager):
    """Testa rotação de IP."""
    # Obtém IP inicial
    initial_ip = await brightdata_manager.check_current_ip()
    
    # Rotaciona IP
    rotated = await brightdata_manager.rotate_ip()
    assert rotated is True
    
    # Obtém novo IP
    new_ip = await brightdata_manager.check_current_ip()
    
    # Verifica se mudou
    assert new_ip is not None
    assert new_ip != initial_ip
    
@pytest.mark.asyncio
async def test_browser_with_brightdata(browser_manager):
    """Testa navegador com Brightdata."""
    # Cria página
    page = await browser_manager.new_page()
    
    # Navega para site que mostra IP
    await page.goto("https://lumtest.com/myip.json")
    
    # Obtém conteúdo
    content = await page.content()
    assert "ip" in content
    
    # Fecha página
    await page.close()
    
@pytest.mark.asyncio
async def test_automatic_rotation(browser_manager):
    """Testa rotação automática de IP."""
    # Configura intervalo curto para teste
    browser_manager.brightdata.config.rotation_interval = 60
    
    # Obtém IP inicial
    initial_ip = await browser_manager.brightdata.check_current_ip()
    
    # Verifica se deve rotacionar
    should_rotate = await browser_manager.brightdata.should_rotate()
    assert should_rotate is False
    
    # Simula passagem de tempo
    browser_manager.brightdata.last_rotation = datetime.now().replace(
        minute=datetime.now().minute - 2
    )
    
    # Verifica novamente
    should_rotate = await browser_manager.brightdata.should_rotate()
    assert should_rotate is True

if __name__ == "__main__":
    # Configura asyncio para Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Executa testes
    pytest.main([__file__, "-v"]) 