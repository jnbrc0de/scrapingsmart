from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from enum import Enum

class DiagnosticLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class DiagnosticResult:
    level: DiagnosticLevel
    message: str
    suggestion: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class DiagnosticManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.history: Dict[str, List[DiagnosticResult]] = {}
        
    def analyze_failure(self, 
                       strategy_name: str, 
                       error: str, 
                       url: str,
                       page_content: Optional[str] = None) -> DiagnosticResult:
        """Analisa uma falha e retorna diagnóstico com sugestões."""
        
        # Registra o diagnóstico no histórico
        if strategy_name not in self.history:
            self.history[strategy_name] = []
            
        # Análise de CAPTCHA
        if "captcha" in error.lower():
            result = DiagnosticResult(
                level=DiagnosticLevel.WARNING,
                message="CAPTCHA detectado",
                suggestion="Considere usar rotação de IPs ou aumentar delay entre requisições",
                data={"error": error}
            )
            self.history[strategy_name].append(result)
            return result
            
        # Análise de bloqueio
        if "blocked" in error.lower() or "access denied" in error.lower():
            result = DiagnosticResult(
                level=DiagnosticLevel.ERROR,
                message="Acesso bloqueado",
                suggestion="Implemente rotação de user-agents e use proxies residenciais",
                data={"error": error}
            )
            self.history[strategy_name].append(result)
            return result
            
        # Análise de timeout
        if "timeout" in error.lower():
            result = DiagnosticResult(
                level=DiagnosticLevel.WARNING,
                message="Timeout na requisição",
                suggestion="Aumente o timeout e verifique a conexão",
                data={"error": error}
            )
            self.history[strategy_name].append(result)
            return result
            
        # Análise de mudança de layout
        if page_content and self._detect_layout_change(page_content):
            result = DiagnosticResult(
                level=DiagnosticLevel.ERROR,
                message="Possível mudança no layout da página",
                suggestion="Atualize os seletores CSS/XPath da estratégia",
                data={"error": error, "url": url}
            )
            self.history[strategy_name].append(result)
            return result
            
        # Falha genérica
        result = DiagnosticResult(
            level=DiagnosticLevel.INFO,
            message="Falha na extração",
            suggestion="Verifique os logs para mais detalhes",
            data={"error": error, "url": url}
        )
        self.history[strategy_name].append(result)
        return result
        
    def _detect_layout_change(self, content: str) -> bool:
        """Detecta possíveis mudanças no layout da página."""
        # Verifica elementos comuns que deveriam existir
        common_elements = [
            "product",
            "price",
            "title",
            "description",
            "image"
        ]
        
        # Se nenhum elemento comum for encontrado, provavelmente o layout mudou
        return not any(element in content.lower() for element in common_elements)
        
    def get_strategy_diagnostics(self, strategy_name: str) -> List[DiagnosticResult]:
        """Retorna todos os diagnósticos de uma estratégia."""
        return self.history.get(strategy_name, [])
        
    def get_critical_diagnostics(self) -> List[DiagnosticResult]:
        """Retorna todos os diagnósticos críticos de todas as estratégias."""
        critical = []
        for diagnostics in self.history.values():
            critical.extend([d for d in diagnostics if d.level == DiagnosticLevel.CRITICAL])
        return critical
        
    def clear_history(self, strategy_name: Optional[str] = None):
        """Limpa o histórico de diagnósticos."""
        if strategy_name:
            self.history.pop(strategy_name, None)
        else:
            self.history.clear() 