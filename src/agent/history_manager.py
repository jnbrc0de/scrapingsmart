from typing import Dict, Any, List, Optional
import logging
import json
import os
from datetime import datetime
from .config import settings

class HistoryManager:
    """Gerenciador de histórico de extrações."""
    
    def __init__(self):
        self.logger = logging.getLogger("history_manager")
        self.history_file = settings.history.file
        self.max_entries = settings.history.max_entries
        self._ensure_history_file()
        
    def _ensure_history_file(self) -> None:
        """Garante que arquivo de histórico existe."""
        try:
            if not os.path.exists(self.history_file):
                with open(self.history_file, 'w') as f:
                    json.dump([], f)
                self.logger.info(f"Arquivo de histórico criado: {self.history_file}")
                
        except Exception as e:
            self.logger.error(f"Erro ao criar arquivo de histórico: {str(e)}")
            
    def _load_history(self) -> List[Dict[str, Any]]:
        """Carrega histórico do arquivo."""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar histórico: {str(e)}")
            return []
            
    def _save_history(self, history: List[Dict[str, Any]]) -> bool:
        """Salva histórico no arquivo."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar histórico: {str(e)}")
            return False
            
    def save_extraction(self, url: str, data: Dict[str, Any], 
                       strategy: str) -> bool:
        """Salva extração no histórico."""
        try:
            # Carrega histórico
            history = self._load_history()
            
            # Cria entrada
            entry = {
                'url': url,
                'strategy': strategy,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Adiciona no início
            history.insert(0, entry)
            
            # Limita tamanho
            if len(history) > self.max_entries:
                history = history[:self.max_entries]
                
            # Salva histórico
            return self._save_history(history)
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar extração: {str(e)}")
            return False
            
    def get_extraction_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retorna histórico de extrações."""
        try:
            history = self._load_history()
            
            if limit:
                history = history[:limit]
                
            return history
            
        except Exception as e:
            self.logger.error(f"Erro ao obter histórico: {str(e)}")
            return []
            
    def get_extraction_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Retorna extração específica por URL."""
        try:
            history = self._load_history()
            
            for entry in history:
                if entry['url'] == url:
                    return entry
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao obter extração por URL: {str(e)}")
            return None
            
    def clear_history(self) -> bool:
        """Limpa histórico."""
        try:
            return self._save_history([])
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar histórico: {str(e)}")
            return False
            
    def get_history_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do histórico."""
        try:
            history = self._load_history()
            
            # Agrupa por estratégia
            strategy_stats = {}
            for entry in history:
                strategy = entry['strategy']
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = 0
                strategy_stats[strategy] += 1
                
            return {
                'total_entries': len(history),
                'strategies': strategy_stats,
                'oldest_entry': history[-1]['timestamp'] if history else None,
                'newest_entry': history[0]['timestamp'] if history else None
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {
                'total_entries': 0,
                'strategies': {},
                'oldest_entry': None,
                'newest_entry': None
            } 