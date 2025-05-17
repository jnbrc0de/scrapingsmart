from typing import Dict, Any, Optional
import os
import json
from pathlib import Path
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

class Config:
    """
    Configuração centralizada do sistema.
    
    Fornece acesso a todas as configurações do sistema,
    carregadas de variáveis de ambiente e arquivos.
    """
    
    def __init__(self):
        self.base_path = Path(os.environ.get('APP_PATH', os.getcwd()))
        self.env = os.environ.get('APP_ENV', 'development')
        
        # Caminhos padrão
        self.data_path = self.base_path / 'data'
        self.cache_path = self.data_path / 'cache'
        self.logs_path = self.base_path / 'logs'
        self.metrics_path = self.data_path / 'metrics'
        self.screenshots_path = self.base_path / 'screenshots'
        
        # Cria diretórios necessários
        self._ensure_directories()
        
        # Carrega configurações
        self.config = self._load_config()
        
    def _ensure_directories(self):
        """Cria diretórios necessários."""
        paths = [
            self.data_path,
            self.cache_path,
            self.logs_path,
            self.metrics_path,
            self.screenshots_path
        ]
        
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
            
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração de várias fontes."""
        # Configuração padrão
        config = {
            'cache': {
                'memory_enabled': True,
                'file_enabled': True,
                'redis_enabled': os.environ.get('REDIS_ENABLED', 'false').lower() == 'true',
                'cache_path': str(self.cache_path),
                'ttl': int(os.environ.get('CACHE_TTL', '3600')),
                'max_size': int(os.environ.get('CACHE_MAX_SIZE', '1000')),
                'redis_url': os.environ.get('REDIS_URL', None)
            },
            'proxy': {
                'enabled': os.environ.get('PROXY_ENABLED', 'false').lower() == 'true',
                'provider': os.environ.get('PROXY_PROVIDER', 'brightdata'),
                'username': os.environ.get('BRIGHTDATA_USERNAME', ''),
                'password': os.environ.get('BRIGHTDATA_PASSWORD', ''),
                'host': os.environ.get('PROXY_HOST', 'brd.superproxy.io'),
                'port': int(os.environ.get('PROXY_PORT', '22225')),
                'country': os.environ.get('PROXY_COUNTRY', 'br'),
                'rotation_interval': int(os.environ.get('PROXY_ROTATION_INTERVAL', '300'))
            },
            'metrics': {
                'prometheus_enabled': os.environ.get('PROMETHEUS_ENABLED', 'false').lower() == 'true',
                'prometheus_port': int(os.environ.get('PROMETHEUS_PORT', '8000')),
                'file_enabled': True,
                'file_path': str(self.metrics_path),
                'retention_days': int(os.environ.get('METRICS_RETENTION_DAYS', '7'))
            },
            'browser': {
                'headless': os.environ.get('BROWSER_HEADLESS', 'true').lower() == 'true',
                'timeout': int(os.environ.get('BROWSER_TIMEOUT', '30000')),
                'user_agent': os.environ.get('BROWSER_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36')
            },
            'scraping': {
                'min_delay': float(os.environ.get('SCRAPING_MIN_DELAY', '1.0')),
                'max_delay': float(os.environ.get('SCRAPING_MAX_DELAY', '3.0')),
                'max_retries': int(os.environ.get('SCRAPING_MAX_RETRIES', '3')),
                'retry_delay': float(os.environ.get('SCRAPING_RETRY_DELAY', '2.0'))
            },
            'logging': {
                'level': os.environ.get('LOG_LEVEL', 'INFO'),
                'rotation_size': os.environ.get('LOG_ROTATION_SIZE', '10 MB'),
                'retention_days': int(os.environ.get('LOG_RETENTION_DAYS', '7')),
                'file_path': str(self.logs_path)
            }
        }
        
        # Tenta carregar de arquivo local
        config_path = self.base_path / 'config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # Mescla configurações
                    self._deep_update(config, file_config)
            except Exception as e:
                logger.error(f"Erro ao carregar config.json: {str(e)}")
                
        return config
    
    def _deep_update(self, d: Dict, u: Dict) -> Dict:
        """Atualiza recursivamente um dicionário."""
        for k, v in u.items():
            if isinstance(v, Dict) and k in d and isinstance(d[k], Dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d
        
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém configuração por chave, suporta notação com pontos."""
        keys = key.split('.')
        result = self.config
        
        for k in keys:
            if isinstance(result, Dict) and k in result:
                result = result[k]
            else:
                return default
                
        return result
        
    def set(self, key: str, value: Any) -> None:
        """Define configuração por chave, suporta notação com pontos."""
        keys = key.split('.')
        config = self.config
        
        for i, k in enumerate(keys):
            if i == len(keys) - 1:
                config[k] = value
            else:
                if k not in config:
                    config[k] = {}
                config = config[k]
                
    def save(self) -> bool:
        """Salva configuração em arquivo."""
        try:
            config_path = self.base_path / 'config.json'
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {str(e)}")
            return False
            
    def get_browser_config(self) -> Dict[str, Any]:
        """Obtém configuração para o navegador."""
        return self.config['browser']
        
    def get_proxy_config(self) -> Dict[str, Any]:
        """Obtém configuração para proxy."""
        return self.config['proxy']
        
    def get_cache_config(self) -> Dict[str, Any]:
        """Obtém configuração para cache."""
        return self.config['cache']
        
    def get_metrics_config(self) -> Dict[str, Any]:
        """Obtém configuração para métricas."""
        return self.config['metrics']
        
    def get_logging_config(self) -> Dict[str, Any]:
        """Obtém configuração para logging."""
        return self.config['logging']
        
# Instância global
config = Config() 