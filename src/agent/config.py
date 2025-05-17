from typing import Dict, Any
import os
import json
import logging
from pathlib import Path

class Settings:
    """Gerenciador de configurações do sistema."""
    
    def __init__(self):
        self.logger = logging.getLogger("settings")
        self.config_file = os.getenv('CONFIG_FILE', 'config.json')
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo."""
        try:
            # Verifica se arquivo existe
            if not os.path.exists(self.config_file):
                self.logger.warning(f"Arquivo de configuração não encontrado: {self.config_file}")
                return self._get_default_config()
                
            # Carrega configurações
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            # Valida configurações
            self._validate_config(config)
            
            return config
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar configurações: {str(e)}")
            return self._get_default_config()
            
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Valida configurações carregadas."""
        try:
            # Valida seções obrigatórias
            required_sections = [
                'browser',
                'proxy',
                'cache',
                'history',
                'metrics',
                'alert'
            ]
            
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Seção obrigatória não encontrada: {section}")
                    
            # Valida configurações do navegador
            browser = config['browser']
            if not isinstance(browser.get('headless', True), bool):
                raise ValueError("browser.headless deve ser booleano")
                
            if not isinstance(browser.get('timeout', 30), int):
                raise ValueError("browser.timeout deve ser inteiro")
                
            if not isinstance(browser.get('user_agent', ''), str):
                raise ValueError("browser.user_agent deve ser string")
                
            # Valida configurações de proxy
            proxy = config['proxy']
            if not isinstance(proxy.get('enabled', False), bool):
                raise ValueError("proxy.enabled deve ser booleano")
                
            if not isinstance(proxy.get('check_interval', 300), int):
                raise ValueError("proxy.check_interval deve ser inteiro")
                
            # Valida configurações de cache
            cache = config['cache']
            if not isinstance(cache.get('file', ''), str):
                raise ValueError("cache.file deve ser string")
                
            if not isinstance(cache.get('max_size', 1000), int):
                raise ValueError("cache.max_size deve ser inteiro")
                
            if not isinstance(cache.get('ttl', 3600), int):
                raise ValueError("cache.ttl deve ser inteiro")
                
            # Valida configurações de histórico
            history = config['history']
            if not isinstance(history.get('file', ''), str):
                raise ValueError("history.file deve ser string")
                
            if not isinstance(history.get('max_entries', 1000), int):
                raise ValueError("history.max_entries deve ser inteiro")
                
            # Valida configurações de métricas
            metrics = config['metrics']
            if not isinstance(metrics.get('file', ''), str):
                raise ValueError("metrics.file deve ser string")
                
            if not isinstance(metrics.get('retention_days', 30), int):
                raise ValueError("metrics.retention_days deve ser inteiro")
                
            # Valida configurações de alerta
            alert = config['alert']
            if not isinstance(alert.get('enabled', True), bool):
                raise ValueError("alert.enabled deve ser booleano")
                
            if not isinstance(alert.get('channels', {}), dict):
                raise ValueError("alert.channels deve ser dicionário")
                
        except Exception as e:
            self.logger.error(f"Erro ao validar configurações: {str(e)}")
            raise
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna configurações padrão."""
        return {
            'browser': {
                'headless': True,
                'timeout': 30,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            'proxy': {
                'enabled': False,
                'check_interval': 300
            },
            'cache': {
                'file': 'data/cache.json',
                'max_size': 1000,
                'ttl': 3600
            },
            'history': {
                'file': 'data/history.json',
                'max_entries': 1000
            },
            'metrics': {
                'file': 'data/metrics.json',
                'retention_days': 30
            },
            'alert': {
                'enabled': True,
                'channels': {
                    'email': {
                        'enabled': False,
                        'smtp_server': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'username': '',
                        'password': '',
                        'from': '',
                        'to': ''
                    },
                    'slack': {
                        'enabled': False,
                        'webhook_url': '',
                        'channel': '',
                        'username': 'SmartScraping',
                        'icon_emoji': ':robot_face:'
                    },
                    'telegram': {
                        'enabled': False,
                        'bot_token': '',
                        'chat_id': ''
                    }
                }
            }
        }
        
    def save_config(self) -> bool:
        """Salva configurações no arquivo."""
        try:
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Salva configurações
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                
            self.logger.info(f"Configurações salvas em {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar configurações: {str(e)}")
            return False
            
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Atualiza configurações."""
        try:
            # Atualiza configurações
            self.config.update(new_config)
            
            # Valida configurações
            self._validate_config(self.config)
            
            # Salva configurações
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar configurações: {str(e)}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração."""
        try:
            # Divide chave em partes
            parts = key.split('.')
            
            # Navega até o valor
            value = self.config
            for part in parts:
                value = value[part]
                
            return value
            
        except Exception as e:
            self.logger.error(f"Erro ao obter configuração {key}: {str(e)}")
            return default
            
    def set(self, key: str, value: Any) -> bool:
        """Define valor de configuração."""
        try:
            # Divide chave em partes
            parts = key.split('.')
            
            # Navega até o local
            config = self.config
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
                
            # Define valor
            config[parts[-1]] = value
            
            # Valida configurações
            self._validate_config(self.config)
            
            # Salva configurações
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"Erro ao definir configuração {key}: {str(e)}")
            return False

# Instância global de configurações
settings = Settings() 