"""
Pacote de estratégias de scraping.

Contém estratégias específicas para diferentes sites de comércio eletrônico.
Cada estratégia implementa a classe base Strategy com seus seletores específicos.
"""

from .magalu import MagaluStrategy
from .americanas import AmericanasStrategy
from .amazon import AmazonStrategy
from .generic import GenericMarketplaceStrategy

__all__ = [
    'MagaluStrategy', 
    'AmericanasStrategy', 
    'AmazonStrategy',
    'GenericMarketplaceStrategy'
] 