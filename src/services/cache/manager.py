from typing import Dict, Any, Optional, Union, List
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import threading
from threading import Lock
import redis

# Configuração de logging
logger = logging.getLogger(__name__)

class CacheEntry:
    """Representa uma entrada no cache."""
    def __init__(self, data: Any, expires_at: Optional[datetime] = None):
        self.data = data
        self.timestamp = datetime.now()
        self.expires_at = expires_at
        self.access_count = 0

    @property
    def is_expired(self) -> bool:
        """Verifica se a entrada está expirada."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class CacheManager:
    """
    Gerenciador unificado de cache que suporta múltiplos backends.
    
    Suporta:
    - Cache em memória
    - Cache em arquivo
    - Cache Redis (opcional)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa o gerenciador de cache.
        
        Args:
            config: Configuração do cache
                memory_enabled: bool - Se o cache em memória está habilitado
                file_enabled: bool - Se o cache em arquivo está habilitado
                redis_enabled: bool - Se o cache Redis está habilitado
                cache_path: str - Caminho para o cache em arquivo
                ttl: int - Tempo de vida das entradas em segundos
                max_size: int - Tamanho máximo do cache
                redis_url: str - URL do Redis
        """
        # Configuração padrão
        self.config = {
            'memory_enabled': True,
            'file_enabled': True,
            'redis_enabled': False,
            'cache_path': 'data/cache',
            'ttl': 3600,  # 1 hora em segundos
            'max_size': 1000,
            'redis_url': None,
        }
        
        # Atualiza com configurações fornecidas
        if config:
            self.config.update(config)
            
        # Inicialização
        self.logger = logging.getLogger("cache_manager")
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        
        # Inicializa cache em arquivo
        if self.config['file_enabled']:
            self.cache_path = Path(self.config['cache_path'])
            self.cache_path.mkdir(parents=True, exist_ok=True)
            
        # Inicializa Redis
        self._redis_client = None
        if self.config['redis_enabled'] and self.config['redis_url']:
            try:
                self._redis_client = redis.Redis.from_url(
                    self.config['redis_url'],
                    socket_timeout=2.0,
                    retry_on_timeout=True
                )
                self.logger.info("Redis cache inicializado")
            except Exception as e:
                self.logger.error(f"Erro ao inicializar Redis: {str(e)}")
                
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém valor do cache. Tenta primeiro em memória, depois arquivo, depois Redis.
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor armazenado ou None se não encontrado
        """
        # Tenta memória
        if self.config['memory_enabled']:
            value = self._get_from_memory(key)
            if value is not None:
                return value
                
        # Tenta arquivo
        if self.config['file_enabled']:
            value = self._get_from_file(key)
            if value is not None:
                # Atualiza memória
                if self.config['memory_enabled']:
                    self._add_to_memory(key, value)
                return value
                
        # Tenta Redis
        if self.config['redis_enabled'] and self._redis_client:
            value = self._get_from_redis(key)
            if value is not None:
                # Atualiza memória
                if self.config['memory_enabled']:
                    self._add_to_memory(key, value)
                return value
                
        return None
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Salva valor no cache. Armazena em todos os backends ativos.
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
            ttl: Tempo de vida em segundos (opcional, usa padrão se None)
            
        Returns:
            True se salvo com sucesso, False caso contrário
        """
        ttl = ttl or self.config['ttl']
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        success = True
        
        # Salva na memória
        if self.config['memory_enabled']:
            if not self._add_to_memory(key, value, expires_at):
                success = False
                
        # Salva em arquivo
        if self.config['file_enabled']:
            if not self._add_to_file(key, value, expires_at):
                success = False
                
        # Salva no Redis
        if self.config['redis_enabled'] and self._redis_client:
            if not self._add_to_redis(key, value, ttl):
                success = False
                
        return success
        
    def delete(self, key: str) -> bool:
        """
        Remove valor do cache em todos os backends.
        
        Args:
            key: Chave a ser removida
            
        Returns:
            True se removido com sucesso, False caso contrário
        """
        success = True
        
        # Remove da memória
        if self.config['memory_enabled']:
            with self._lock:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    
        # Remove do arquivo
        if self.config['file_enabled']:
            try:
                filename = self._get_filename(key)
                filepath = self.cache_path / filename
                
                if filepath.exists():
                    with self._lock:
                        filepath.unlink()
            except Exception as e:
                self.logger.error(f"Erro ao remover do arquivo: {str(e)}")
                success = False
                
        # Remove do Redis
        if self.config['redis_enabled'] and self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception as e:
                self.logger.error(f"Erro ao remover do Redis: {str(e)}")
                success = False
                
        return success
        
    def clear(self) -> bool:
        """
        Limpa todo o cache em todos os backends.
        
        Returns:
            True se limpo com sucesso, False caso contrário
        """
        success = True
        
        # Limpa memória
        if self.config['memory_enabled']:
            with self._lock:
                self._memory_cache.clear()
                
        # Limpa arquivos
        if self.config['file_enabled']:
            try:
                with self._lock:
                    for filepath in self.cache_path.glob("*.json"):
                        filepath.unlink()
            except Exception as e:
                self.logger.error(f"Erro ao limpar cache em arquivo: {str(e)}")
                success = False
                
        # Limpa Redis
        if self.config['redis_enabled'] and self._redis_client:
            try:
                self._redis_client.flushdb()
            except Exception as e:
                self.logger.error(f"Erro ao limpar Redis: {str(e)}")
                success = False
                
        return success
        
    def clear_expired(self) -> int:
        """
        Limpa entradas expiradas de todos os backends.
        
        Returns:
            Número de entradas removidas
        """
        count = 0
        
        # Limpa memória
        if self.config['memory_enabled']:
            with self._lock:
                expired_keys = [
                    k for k, v in self._memory_cache.items()
                    if v.is_expired
                ]
                for key in expired_keys:
                    del self._memory_cache[key]
                count += len(expired_keys)
                
        # Limpa arquivos
        if self.config['file_enabled']:
            try:
                file_count = 0
                with self._lock:
                    for filepath in self.cache_path.glob("*.json"):
                        if self._is_file_expired(filepath):
                            filepath.unlink()
                            file_count += 1
                count += file_count
            except Exception as e:
                self.logger.error(f"Erro ao limpar arquivos expirados: {str(e)}")
                
        return count
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            'config': self.config.copy(),
            'memory': {
                'entries': len(self._memory_cache) if self.config['memory_enabled'] else 0,
                'bytes': sum(len(json.dumps(v.data)) for v in self._memory_cache.values()) if self.config['memory_enabled'] else 0
            },
            'file': {
                'entries': 0,
                'size_mb': 0
            },
            'redis': {
                'connected': self._redis_client is not None if self.config['redis_enabled'] else False,
                'keys': 0
            }
        }
        
        # Estatísticas de arquivo
        if self.config['file_enabled']:
            try:
                files = list(self.cache_path.glob("*.json"))
                stats['file']['entries'] = len(files)
                stats['file']['size_mb'] = round(
                    sum(f.stat().st_size for f in files) / (1024 * 1024),
                    2
                )
            except Exception as e:
                self.logger.error(f"Erro ao obter estatísticas de arquivo: {str(e)}")
                
        # Estatísticas de Redis
        if self.config['redis_enabled'] and self._redis_client:
            try:
                stats['redis']['keys'] = self._redis_client.dbsize()
            except Exception as e:
                self.logger.error(f"Erro ao obter estatísticas de Redis: {str(e)}")
                
        return stats
        
    def _get_from_memory(self, key: str) -> Optional[Any]:
        """Obtém valor do cache em memória."""
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if not entry.is_expired:
                    # Atualiza contador de acesso
                    entry.access_count += 1
                    return entry.data
                else:
                    # Remove expirado
                    del self._memory_cache[key]
        return None
        
    def _add_to_memory(self, key: str, value: Any, expires_at: Optional[datetime] = None) -> bool:
        """Adiciona valor ao cache em memória."""
        try:
            entry = CacheEntry(data=value, expires_at=expires_at)
            
            with self._lock:
                # Verifica tamanho máximo
                if len(self._memory_cache) >= self.config['max_size']:
                    # Remove o menos acessado
                    least_used = min(self._memory_cache.items(), key=lambda x: x[1].access_count)
                    del self._memory_cache[least_used[0]]
                
                self._memory_cache[key] = entry
                
            return True
        except Exception as e:
            self.logger.error(f"Erro ao adicionar à memória: {str(e)}")
            return False
            
    def _get_from_file(self, key: str) -> Optional[Any]:
        """Obtém valor do cache em arquivo."""
        try:
            filename = self._get_filename(key)
            filepath = self.cache_path / filename
            
            if not filepath.exists():
                return None
                
            if self._is_file_expired(filepath):
                # Remove arquivo expirado
                with self._lock:
                    filepath.unlink()
                return None
                
            # Lê arquivo
            with open(filepath, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            return cache_data.get('value')
            
        except Exception as e:
            self.logger.error(f"Erro ao ler de arquivo: {str(e)}")
            return None
            
    def _add_to_file(self, key: str, value: Any, expires_at: Optional[datetime] = None) -> bool:
        """Adiciona valor ao cache em arquivo."""
        try:
            filename = self._get_filename(key)
            filepath = self.cache_path / filename
            
            # Prepara dados
            cache_data = {
                'key': key,
                'value': value,
                'timestamp': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat() if expires_at else None
            }
            
            # Salva arquivo
            with self._lock:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar em arquivo: {str(e)}")
            return False
            
    def _get_from_redis(self, key: str) -> Optional[Any]:
        """Obtém valor do cache Redis."""
        try:
            if not self._redis_client:
                return None
                
            raw_data = self._redis_client.get(key)
            if not raw_data:
                return None
                
            # Decodifica JSON
            return json.loads(raw_data)
            
        except Exception as e:
            self.logger.error(f"Erro ao ler do Redis: {str(e)}")
            return None
            
    def _add_to_redis(self, key: str, value: Any, ttl: int) -> bool:
        """Adiciona valor ao cache Redis."""
        try:
            if not self._redis_client:
                return False
                
            # Codifica JSON
            json_data = json.dumps(value)
            
            # Salva com TTL
            self._redis_client.setex(key, ttl, json_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar no Redis: {str(e)}")
            return False
            
    def _get_filename(self, key: str) -> str:
        """Gera nome do arquivo para uma chave."""
        # Gera hash MD5 da chave
        hash_md5 = hashlib.md5(key.encode())
        return f"{hash_md5.hexdigest()}.json"
        
    def _is_file_expired(self, filepath: Path) -> bool:
        """Verifica se arquivo está expirado."""
        try:
            # Verifica se arquivo existe
            if not filepath.exists():
                return True
                
            # Lê arquivo para verificar expires_at explícito
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                if cache_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(cache_data['expires_at'])
                    return datetime.now() > expires_at
            except:
                pass
                
            # Fallback para verificar pela data de modificação
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            return datetime.now() - mtime > timedelta(seconds=self.config['ttl'])
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar expiração de arquivo: {str(e)}")
            return True 