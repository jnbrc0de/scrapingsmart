import asyncio
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

from src.config.settings import settings
from src.supabase_client import get_supabase_client
from src.worker_engine import WorkerEngine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

MAX_RETRIES = 3
QUEUE_TABLE = 'scraping_queue'
RESULTS_TABLE = 'scraping_results'

async def update_queue_item(supabase, item_id: int, status: str, error_message: str = None, result: Dict[str, Any] = None) -> None:
    """
    Atualiza o status de um item na fila.
    """
    update_data = {
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
    }
    
    if error_message:
        update_data['error_message'] = error_message
    
    if result:
        update_data['result'] = result
    
    try:
        await supabase.from_(QUEUE_TABLE).update(update_data).eq('id', item_id).execute()
    except Exception as e:
        logger.error(f"Erro ao atualizar item {item_id} na fila: {e}")

async def save_result(supabase, queue_item: Dict[str, Any], result: Dict[str, Any]) -> None:
    """
    Salva o resultado do scraping na tabela de resultados.
    """
    result_data = {
        'queue_item_id': queue_item['id'],
        'url': queue_item['url'],
        'result': result,
        'created_at': datetime.utcnow().isoformat(),
    }
    
    try:
        await supabase.from_(RESULTS_TABLE).insert(result_data).execute()
    except Exception as e:
        logger.error(f"Erro ao salvar resultado para URL {queue_item['url']}: {e}")

async def process_url_from_queue(worker_engine: WorkerEngine, supabase) -> Optional[dict]:
    """
    Busca uma URL na fila do Supabase e a processa.
    Retorna os dados processados ou None se a fila estiver vazia.
    """
    try:
        # Busca o próximo item da fila
        response = await supabase.from_(QUEUE_TABLE)\
            .select('*')\
            .eq('status', 'pending')\
            .lt('retry_count', MAX_RETRIES)\
            .order('priority', desc=True)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not response.data:
            return None
            
        queue_item = response.data[0]
        item_id = queue_item['id']
        
        # Marca como processando
        await update_queue_item(supabase, item_id, 'processing')
        logger.info(f"Processando URL: {queue_item['url']}")
        
        try:
            # Executa o scraping usando o WorkerEngine
            result = await worker_engine.process_url(
                url=queue_item['url'],
                priority=queue_item.get('priority', 0)
            )
            
            if result.get('status') == 'success':
                # Salva o resultado
                await save_result(supabase, queue_item, result)
                
                # Marca como completo
                await update_queue_item(
                    supabase, 
                    item_id, 
                    'completed',
                    result=result
                )
                
                logger.info(f"URL processada com sucesso: {queue_item['url']}")
                return result
            else:
                # Incrementa o contador de tentativas
                retry_count = queue_item.get('retry_count', 0) + 1
                
                # Atualiza o status para failed se excedeu o número máximo de tentativas
                status = 'failed' if retry_count >= MAX_RETRIES else 'pending'
                
                await update_queue_item(
                    supabase,
                    item_id,
                    status,
                    error_message=result.get('error')
                )
                
                return None
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Erro ao processar URL {queue_item['url']}: {error_message}")
            
            # Incrementa o contador de tentativas
            retry_count = queue_item.get('retry_count', 0) + 1
            
            # Atualiza o status para failed se excedeu o número máximo de tentativas
            status = 'failed' if retry_count >= MAX_RETRIES else 'pending'
            
            await update_queue_item(
                supabase,
                item_id,
                status,
                error_message=error_message
            )
            
            return None

    except Exception as e:
        logger.error(f"Erro ao processar URL da fila: {e}")
        return None

async def worker_main():
    """
    Loop principal do Worker.
    """
    supabase = get_supabase_client()
    worker_engine = WorkerEngine(config=settings)
    await worker_engine.initialize()

    logger.info("Worker iniciado. Aguardando URLs na fila...")

    while True:
        try:
            item_processado = await process_url_from_queue(worker_engine, supabase)
            
            if not item_processado:
                logger.info("Fila vazia, aguardando...")
                await asyncio.sleep(10)  # Espera mais tempo se a fila estiver vazia
            else:
                logger.info("Item processado com sucesso!")
                await asyncio.sleep(1)  # Pequena pausa entre processamentos
                
        except Exception as e:
            logger.error(f"Erro no loop principal do worker: {e}")
            await asyncio.sleep(30)  # Espera mais tempo em caso de erro grave

if __name__ == "__main__":
    asyncio.run(worker_main()) 