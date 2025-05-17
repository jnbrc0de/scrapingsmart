from typing import Dict, Any, Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis de ambiente
load_dotenv()

class BrowserSettings(BaseSettings):
    """Configurações do navegador."""
    headless: bool = Field(default=True)
    timeout: int = Field(default=30000)
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        if v < 1000:
            raise ValueError("Timeout deve ser maior que 1000ms")
        return v

class BrightdataSettings(BaseSettings):
    """Configurações do Brightdata."""
    enabled: bool = Field(default=False)
    host: str = Field(default="brd.superproxy.io")
    port: int = Field(default=22225)
    username: str = Field(default="")
    password: str = Field(default="")
    country: str = Field(default="br")
    session_id: Optional[str] = Field(default=None)
    rotation_interval: int = Field(default=300)  # em segundos
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('username', 'password')
    @classmethod
    def validate_credentials(cls, v, info):
        if info.data.get('enabled', False) and not v:
            raise ValueError("Credenciais do Brightdata são obrigatórias quando habilitado")
        return v
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if v < 1 or v > 65535:
            raise ValueError("Porta deve estar entre 1 e 65535")
        return v
    
    @field_validator('rotation_interval')
    @classmethod
    def validate_rotation_interval(cls, v):
        if v < 60:
            raise ValueError("Intervalo de rotação deve ser maior que 60 segundos")
        return v

class DelaySettings(BaseSettings):
    """Configurações de delay."""
    min: float = Field(default=1.0)
    max: float = Field(default=3.0)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('max')
    @classmethod
    def validate_max_delay(cls, v, info):
        if v < info.data.get('min', 0):
            raise ValueError("Delay máximo deve ser maior que o mínimo")
        return v

class RetrySettings(BaseSettings):
    """Configurações de retry."""
    max_attempts: int = Field(default=3)
    delay: float = Field(default=5.0)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('max_attempts')
    @classmethod
    def validate_max_attempts(cls, v):
        if v < 1:
            raise ValueError("Número máximo de tentativas deve ser maior que 0")
        return v

class LoggingSettings(BaseSettings):
    """Configurações de logging."""
    level: str = Field(default="INFO")
    file: str = Field(default="logs/scraper.log")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Nível de log deve ser um dos: {', '.join(valid_levels)}")
        return v.upper()

class MonitoringSettings(BaseSettings):
    """Configurações de monitoramento."""
    enabled: bool = Field(default=True)
    port: int = Field(default=8000)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if v < 1024 or v > 65535:
            raise ValueError("Porta deve estar entre 1024 e 65535")
        return v

class AlertSettings(BaseSettings):
    """Configurações de alertas."""
    enabled: bool = Field(default=False)
    email: Optional[str] = Field(default=None)
    slack_webhook: Optional[str] = Field(default=None)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v, info):
        if info.data.get('enabled', False) and not v and not info.data.get('slack_webhook'):
            raise ValueError("Email ou Slack webhook é obrigatório quando alertas estão habilitados")
        return v

class Settings(BaseSettings):
    """Configurações globais do sistema."""
    browser: BrowserSettings = BrowserSettings()
    brightdata: BrightdataSettings = BrightdataSettings()
    delay: DelaySettings = DelaySettings()
    retry: RetrySettings = RetrySettings()
    logging: LoggingSettings = LoggingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    alert: AlertSettings = AlertSettings()
    
    # Configurações de cache
    cache_enabled: bool = Field(default=True)
    cache_ttl: int = Field(default=3600)  # 1 hora
    
    # Configurações de estratégias
    strategies: List[Dict[str, Any]] = Field(default=[
        {
            "name": "MagaluStrategy",
            "patterns": ["magazineluiza.com.br"],
            "selectors": {
                "title": "h1[data-testid='heading-product-title']",
                "price": "p[data-testid='price-value']",
                "availability": "p[data-testid='availability']",
                "seller": "p[data-testid='seller-name']",
                "description": "div[data-testid='product-description']"
            }
        },
        {
            "name": "AmericanasStrategy",
            "patterns": ["americanas.com.br"],
            "selectors": {
                "title": "h1[data-testid='heading-product-title']",
                "price": "p[data-testid='price-value']",
                "availability": "p[data-testid='availability']",
                "seller": "p[data-testid='seller-name']",
                "description": "div[data-testid='product-description']"
            }
        },
        {
            "name": "AmazonStrategy",
            "patterns": ["amazon.com.br"],
            "selectors": {
                "title": "h1[data-testid='heading-product-title']",
                "price": "p[data-testid='price-value']",
                "availability": "p[data-testid='availability']",
                "seller": "p[data-testid='seller-name']",
                "description": "div[data-testid='product-description']"
            }
        }
    ])
    
    history_path: str = Field(default="data/strategy_history")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

# Instância global de configurações
settings = Settings()

def get_settings() -> Settings:
    """Retorna a instância de configurações."""
    return settings


