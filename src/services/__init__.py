"""
Serviços compartilhados para o sistema de scraping.
Este pacote contém implementações centralizadas para cache, métricas e outros serviços.
"""
 
from .config import config
from .cache import CacheManager
from .metrics import MetricsManager
from .proxy import ProxyManager
from .container import container 