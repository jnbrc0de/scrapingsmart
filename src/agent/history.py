from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os
import logging

@dataclass
class StrategyAttempt:
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0

class StrategyHistory:
    def __init__(self, storage_path: str = "data/strategy_history"):
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        self.history: Dict[str, List[StrategyAttempt]] = {}
        self._ensure_storage_path()
        
    def _ensure_storage_path(self):
        """Garante que o diretório de armazenamento existe."""
        os.makedirs(self.storage_path, exist_ok=True)
        
    def record_attempt(self, 
                      strategy_name: str, 
                      success: bool, 
                      error: Optional[str] = None,
                      data: Optional[Dict[str, Any]] = None,
                      execution_time: float = 0.0):
        """Registra uma tentativa de estratégia."""
        if strategy_name not in self.history:
            self.history[strategy_name] = []
            
        attempt = StrategyAttempt(
            timestamp=datetime.now(),
            success=success,
            error=error,
            data=data,
            execution_time=execution_time
        )
        
        self.history[strategy_name].append(attempt)
        self._save_history()
        
    def get_strategy_stats(self, strategy_name: str) -> Dict[str, Any]:
        """Retorna estatísticas de uma estratégia."""
        if strategy_name not in self.history:
            return {
                "attempts": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "last_error": None
            }
            
        attempts = self.history[strategy_name]
        total_attempts = len(attempts)
        successful_attempts = sum(1 for a in attempts if a.success)
        avg_time = sum(a.execution_time for a in attempts) / total_attempts if total_attempts > 0 else 0
        
        return {
            "attempts": total_attempts,
            "success_rate": (successful_attempts / total_attempts) * 100 if total_attempts > 0 else 0,
            "avg_execution_time": avg_time,
            "last_error": attempts[-1].error if attempts and not attempts[-1].success else None
        }
        
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Retorna estatísticas de todas as estratégias."""
        return {
            strategy_name: self.get_strategy_stats(strategy_name)
            for strategy_name in self.history.keys()
        }
        
    def get_recent_errors(self, strategy_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retorna os erros mais recentes de uma estratégia."""
        if strategy_name not in self.history:
            return []
            
        errors = [
            {
                "timestamp": a.timestamp.isoformat(),
                "error": a.error,
                "execution_time": a.execution_time
            }
            for a in self.history[strategy_name]
            if not a.success
        ]
        
        return errors[-limit:]
        
    def _save_history(self):
        """Salva o histórico em disco."""
        try:
            for strategy_name, attempts in self.history.items():
                file_path = os.path.join(self.storage_path, f"{strategy_name}.json")
                
                # Converte para formato serializável
                serializable_attempts = [
                    {
                        "timestamp": a.timestamp.isoformat(),
                        "success": a.success,
                        "error": a.error,
                        "data": a.data,
                        "execution_time": a.execution_time
                    }
                    for a in attempts
                ]
                
                with open(file_path, 'w') as f:
                    json.dump(serializable_attempts, f, indent=2)
                    
        except Exception as e:
            self.logger.error(f"Erro ao salvar histórico: {str(e)}")
            
    def load_history(self):
        """Carrega o histórico do disco."""
        try:
            for filename in os.listdir(self.storage_path):
                if filename.endswith('.json'):
                    strategy_name = filename[:-5]  # Remove .json
                    file_path = os.path.join(self.storage_path, filename)
                    
                    with open(file_path, 'r') as f:
                        attempts_data = json.load(f)
                        
                    self.history[strategy_name] = [
                        StrategyAttempt(
                            timestamp=datetime.fromisoformat(a['timestamp']),
                            success=a['success'],
                            error=a['error'],
                            data=a['data'],
                            execution_time=a['execution_time']
                        )
                        for a in attempts_data
                    ]
                    
        except Exception as e:
            self.logger.error(f"Erro ao carregar histórico: {str(e)}")
            
    def clear_history(self, strategy_name: Optional[str] = None):
        """Limpa o histórico."""
        if strategy_name:
            self.history.pop(strategy_name, None)
            file_path = os.path.join(self.storage_path, f"{strategy_name}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            self.history.clear()
            for filename in os.listdir(self.storage_path):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.storage_path, filename)) 