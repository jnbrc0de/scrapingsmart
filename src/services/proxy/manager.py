from typing import Dict, Any, Optional
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
import random
import os

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Gerenciador unificado de proxies e IPs.
    
    Suporta:
    - Integração com Brightdata
    - Rotação automática de IPs
    - Gerenciamento de sessões
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa o gerenciador de proxies.
        
        Args:
            config: Configuração do proxy
                enabled: bool - Se o proxy está habilitado
                provider: str - Provedor de proxy ('brightdata', 'luminati', etc.)
                username: str - Nome de usuário
                password: str - Senha
                host: str - Host do proxy
                port: int - Porta do proxy
                country: str - Código do país para geolocalização
                rotation_interval: int - Intervalo de rotação em segundos
        """
        # Configuração padrão
        self.config = {
            'enabled': False,
            'provider': 'brightdata',
            'username': '',
            'password': '',
            'host': 'brd.superproxy.io',
            'port': 22225,
            'country': 'br',
            'session_id': None,
            'rotation_interval': 300  # 5 minutos em segundos
        }
        
        # Atualiza com configurações fornecidas
        if config:
            self.config.update(config)
            
        # Inicialização
        self.logger = logging.getLogger("proxy_manager")
        self.session_id = self.config['session_id'] or f"s_{random.randint(1000000, 9999999)}"
        self.last_rotation = datetime.now()
        self.current_ip = None
        self._session = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Inicializa o gerenciador."""
        if not self.config['enabled']:
            self.logger.warning(f"{self.config['provider']} está desabilitado")
            self._initialized = True
            return
            
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        # Verifica IP inicial
        ip = await self.check_current_ip()
        self._initialized = True
        
        self.logger.info(f"Gerenciador de proxy inicializado com IP: {ip}")
        
    async def close(self) -> None:
        """Fecha conexões."""
        if self._session:
            await self._session.close()
            self._session = None
            
    @property
    def is_initialized(self) -> bool:
        """Retorna se o gerenciador foi inicializado."""
        return self._initialized
            
    async def get_current_ip(self) -> str:
        """Obtém o IP atual."""
        if not self.current_ip:
            await self.check_current_ip()
        return self.current_ip or "127.0.0.1"
            
    def get_proxy_url(self) -> Optional[str]:
        """Retorna URL do proxy."""
        if not self.config['enabled']:
            return None
            
        return f"http://{self.config['username']}:{self.config['password']}@{self.config['host']}:{self.config['port']}"
        
    async def check_current_ip(self) -> Optional[str]:
        """Verifica IP atual."""
        if not self.config['enabled']:
            self.current_ip = "127.0.0.1"  # IP local quando desabilitado
            return self.current_ip
            
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
                
            async with self._session.get("https://lumtest.com/myip.json", proxy=self.get_proxy_url()) as response:
                if response.status == 200:
                    data = await response.json()
                    self.current_ip = data.get("ip")
                    self.logger.info(f"IP atual: {self.current_ip}")
                    return self.current_ip
                else:
                    self.logger.error(f"Erro ao verificar IP: {response.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Erro ao verificar IP: {str(e)}")
            return None
            
    async def rotate_ip(self) -> bool:
        """Força rotação de IP."""
        if not self.config['enabled']:
            return True
            
        try:
            # Adiciona parâmetro de rotação na URL
            rotation_url = f"{self.get_proxy_url()}/rotate"
            
            if not self._session:
                self._session = aiohttp.ClientSession()
                
            async with self._session.get(rotation_url) as response:
                if response.status == 200:
                    self.last_rotation = datetime.now()
                    await self.check_current_ip()
                    self.logger.info("IP rotacionado com sucesso")
                    return True
                else:
                    self.logger.error(f"Erro ao rotacionar IP: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Erro ao rotacionar IP: {str(e)}")
            return False
            
    async def should_rotate(self) -> bool:
        """Verifica se deve rotacionar IP."""
        if not self.config['enabled']:
            return False
            
        time_since_last_rotation = datetime.now() - self.last_rotation
        return time_since_last_rotation.total_seconds() >= self.config['rotation_interval']
        
    async def get_proxy_config(self) -> Dict[str, Any]:
        """Retorna configuração do proxy para o navegador."""
        if not self.config['enabled']:
            return None
            
        # Verifica se precisa rotacionar
        if await self.should_rotate():
            await self.rotate_ip()
            
        return {
            "server": self.config['host'],
            "port": self.config['port'],
            "username": self.config['username'],
            "password": self.config['password'],
            "session_id": self.session_id,
            "country": self.config['country']
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerenciador."""
        return {
            "enabled": self.config['enabled'],
            "provider": self.config['provider'],
            "current_ip": self.current_ip,
            "last_rotation": self.last_rotation.isoformat() if self.last_rotation else None,
            "rotation_interval": self.config['rotation_interval'],
            "session_id": self.session_id
        }
        
    def clone_with_new_session(self) -> 'ProxyManager':
        """Cria uma nova instância com nova sessão."""
        config = self.config.copy()
        new_manager = ProxyManager(config)
        new_manager.session_id = f"s_{random.randint(1000000, 9999999)}"
        return new_manager 