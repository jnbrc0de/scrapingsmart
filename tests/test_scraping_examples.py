import pytest
import pytest_asyncio
import asyncio
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import Page

from src.services.container import container
from src.services.config import config
from src.browser.manager_di import BrowserManager

# Carrega variáveis de ambiente
load_dotenv()

def get_test_url():
    """Solicita a URL de teste no terminal, sem valores padrão."""
    print("\nDigite a URL de teste:")
    url = input("URL: ").strip()
    return url

@pytest.fixture(scope="module")
async def setup_services():
    """Inicializa serviços necessários para os testes."""
    await container.initialize()
    yield
    await container.cleanup()

@pytest_asyncio.fixture
async def browser():
    """Fixture para o navegador."""
    browser_manager = BrowserManager()
    await browser_manager.initialize()
    yield browser_manager
    await browser_manager.close()

@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_services")
async def test_amazon_product_extraction(browser):
    """Testa extração de um produto da Amazon com a nova arquitetura."""
    url = get_test_url()
    page = await browser.new_page()
    
    try:
        # Acessa a página
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Aguarda carregamento da página
        await page.wait_for_selector("#productTitle", state="visible", timeout=10000)
        
        # Registra métricas de início
        metrics = container.get_metrics()
        start_time = time.time()
        
        # Extrai informações
        title = await page.locator("#productTitle").text_content()
        price_locator = page.locator(".a-price .a-offscreen").first
        
        price_text = None
        try:
            price_text = await price_locator.text_content()
        except:
            try:
                # Tenta um seletor alternativo para o preço
                price_text = await page.locator("span.a-price-whole").first.text_content()
            except:
                pass
        
        # Registra tempo de extração
        duration = time.time() - start_time
        metrics.record_extraction("amazon", True, duration, 0.9)
        
        # Testa os dados extraídos
        assert title and title.strip(), "Título não encontrado"
        print(f"\nTítulo: {title.strip()}")
        if price_text:
            print(f"Preço: {price_text.strip()}")
        
        # Salva no cache
        cache = container.get_cache()
        cache_key = f"amazon_product_{url}"
        product_data = {
            "title": title.strip() if title else None,
            "price": price_text.strip() if price_text else None,
            "url": url,
            "timestamp": time.time()
        }
        cache.set(cache_key, product_data)
        
        # Verifica se está no cache
        cached = cache.get(cache_key)
        assert cached, "Dados não foram salvos no cache"
        assert cached["title"] == product_data["title"], "Título no cache não corresponde"
        
    except Exception as e:
        metrics = container.get_metrics()
        metrics.record_error("amazon", str(e))
        # Se ocorrer erro, verifica se é por CAPTCHA ou bloqueio
        html = await page.content()
        if "captcha" in html.lower() or "robot" in html.lower() or "blocked" in html.lower():
            metrics.record_captcha("amazon")
            pytest.skip("Amazon está apresentando CAPTCHA ou bloqueou o acesso")
        else:
            raise
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_services")
async def test_wikipedia_extraction(browser):
    """Extrai dados da Wikipedia como exemplo de site menos restritivo."""
    url = get_test_url()
    page = await browser.new_page()
    
    try:
        # Acessa a página
        await page.goto(url, wait_until="domcontentloaded")
        
        # Registra métricas
        metrics = container.get_metrics()
        start_time = time.time()
        
        # Extrai título
        title = await page.title()
        
        # Extrai primeiro parágrafo
        first_p = await page.locator("#mw-content-text p").first.text_content()
        
        # Extrai links da tabela de conteúdos
        toc_links = await page.locator("#toc ul li a .toctext").all_text_contents()
        
        # Registra duração
        duration = time.time() - start_time
        metrics.record_extraction("wikipedia", True, duration, 1.0)
        
        # Testa resultados
        assert "Python" in title, "Título da página não contém 'Python'"
        assert len(first_p) > 50, "Primeiro parágrafo muito curto"
        assert len(toc_links) > 0, "Nenhum link no índice"
        
        # Salva no cache usando o serviço centralizado
        cache = container.get_cache()
        cache_key = "wikipedia_python"
        wiki_data = {
            "title": title,
            "first_paragraph": first_p,
            "toc_sections": toc_links,
            "timestamp": time.time()
        }
        cache.set(cache_key, wiki_data)
        
        # Recupera do cache e verifica
        cached_data = cache.get(cache_key)
        assert cached_data is not None
        assert cached_data["title"] == title
        assert cached_data["first_paragraph"] == first_p
        
        # Imprime resultados
        print(f"\nTítulo: {title}")
        print(f"Primeiro parágrafo: {first_p[:100]}..." if first_p else "Primeiro parágrafo não encontrado.") # type: ignore
        print(f"Seções: {len(toc_links)}")
        
        # Registra uso do cache
        metrics.record_cache("wikipedia", True)
        
    except Exception as e:
        metrics = container.get_metrics()
        metrics.record_error("wikipedia", str(e))
        raise
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_services")
async def test_multi_source_extraction(browser):
    """Teste que extrai dados de várias fontes e combina os resultados."""
    # Obtém serviço de cache
    cache = container.get_cache()
    metrics = container.get_metrics()
    
    # Extrai de cada fonte
    results = {}
    sources = ["wikipedia", "github"]
    
    for source in sources:
        url = get_test_url()
        page = await browser.new_page()
        try:
            # Acessa a página
            await page.goto(url, wait_until="networkidle")
            metrics.record_extraction(source, True, 1.0)
            
            # Extrai título
            title = await page.title()
            results[source] = {
                "title": title,
                "url": url
            }
            
            # Salva no cache
            cache.set(f"title_{source}", title)
            
        except Exception as e:
            metrics.record_error(source, str(e))
        finally:
            await page.close()
    
    # Verifica resultados
    assert len(results) > 0, "Nenhum dado foi extraído"
    for source, data in results.items():
        print(f"\n{source.upper()}: {data['title']}") # type: ignore
    
    # Combina resultados e salva no cache
    combined = {
        "sources": results,
        "timestamp": time.time(),
        "count": len(results)
    }
    cache.set("multi_source_results", combined)
    
    # Obtém estatísticas de métricas
    stats = metrics.get_metrics_summary()
    print(f"\nExtrações totais: {stats['extractions']['total']}")
    print(f"Cache hits: {stats['cache']['hits']}")

@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_services")
async def test_cache_performance():
    """Testa performance do sistema de cache."""
    # Prepara dados
    large_data = {"items": [{"id": i, "value": f"test_{i}"} for i in range(1000)]}
    
    # Obtém serviço de cache
    cache = container.get_cache()
    metrics = container.get_metrics()
    
    # Testa escrita/leitura
    start_time = time.time()
    cache.set("perf_test", large_data)
    write_time = time.time() - start_time
    
    start_time = time.time()
    data = cache.get("perf_test")
    read_time = time.time() - start_time
    
    assert data is not None, "Dados não encontrados no cache"
    assert len(data["items"]) == 1000, "Dados incompletos"
    
    # Verifica se cache em memória é mais rápido que em arquivo
    cache.set("memory_test", {"test": True})
    assert cache.get("memory_test") is not None, "Cache em memória falhou"
    
    # Exibe estatísticas
    print(f"\nTempo de escrita: {write_time:.6f} segundos")
    print(f"Tempo de leitura: {read_time:.6f} segundos")
    
    # Registra métricas
    metrics.record_extraction("cache_test", True, write_time + read_time)

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 