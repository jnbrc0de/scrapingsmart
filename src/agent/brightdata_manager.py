from typing import Dict, Any, Optional
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from ..config.settings import settings

class BrightdataManager:
    """Gerenciador de conexões com Brightdata."""
    
    def __init__(self):
        self.logger = logging.getLogger("brightdata_manager")
        self.config = settings.brightdata
        self.session_id = self.config.session_id
        self.last_rotation = datetime.now()
        self.current_ip = None
        self._session = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Inicializa o gerenciador."""
        if not self.config.enabled:
            self.logger.warning("Brightdata está desabilitado")
            self._initialized = True
            return
            
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        # Verifica IP inicial
        ip = await self.check_current_ip()
        self._initialized = True
        
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
            
    def get_proxy_url(self) -> str:
        """Retorna URL do proxy."""
        if not self.config.enabled:
            return None
            
        return f"http://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}"
        
    async def check_current_ip(self) -> Optional[str]:
        """Verifica IP atual."""
        if not self.config.enabled:
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
        if not self.config.enabled:
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
        if not self.config.enabled:
            return False
            
        time_since_last_rotation = datetime.now() - self.last_rotation
        return time_since_last_rotation.total_seconds() >= self.config.rotation_interval
        
    async def get_proxy_config(self) -> Dict[str, Any]:
        """Retorna configuração do proxy."""
        if not self.config.enabled:
            return None
            
        # Verifica se precisa rotacionar
        if await self.should_rotate():
            await self.rotate_ip()
            
        return {
            "server": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "password": self.config.password,
            "session_id": self.session_id,
            "country": self.config.country
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerenciador."""
        return {
            "enabled": self.config.enabled,
            "current_ip": self.current_ip,
            "last_rotation": self.last_rotation.isoformat() if self.last_rotation else None,
            "rotation_interval": self.config.rotation_interval,
            "session_id": self.session_id
        } 