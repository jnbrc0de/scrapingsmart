from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
from loguru import logger
import hashlib
from dataclasses import dataclass, asdict, field
import re

@dataclass
class SelectorScore:
    """Pontuação de um seletor."""
    selector: str
    success_count: int = 0
    failure_count: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    avg_response_time: float = 0.0
    pattern_changes: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Taxa de sucesso do seletor."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def score(self) -> float:
        """Pontuação total do seletor."""
        # Fatores que influenciam a pontuação:
        # 1. Taxa de sucesso (0-1)
        # 2. Tempo desde último sucesso (mais recente = melhor)
        # 3. Tempo médio de resposta (mais rápido = melhor)
        # 4. Estabilidade do padrão (menos mudanças = melhor)
        
        base_score = self.success_rate * 100
        
        # Penalidade por tempo desde último sucesso
        if self.last_success:
            days_since_success = (datetime.now() - self.last_success).days
            time_penalty = min(days_since_success * 5, 50)  # Máximo de 50% de penalidade
            base_score -= time_penalty
        
        # Bônus por tempo de resposta
        if self.avg_response_time > 0:
            response_bonus = max(0, 20 - (self.avg_response_time * 10))
            base_score += response_bonus
        
        # Penalidade por mudanças de padrão
        pattern_penalty = len(self.pattern_changes) * 5
        base_score -= pattern_penalty
        
        return max(0, min(100, base_score))

@dataclass
class DomainPattern:
    """Padrão de domínio."""
    domain: str
    selectors: Dict[str, List[SelectorScore]] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    pattern_changes: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def score(self) -> float:
        """Pontuação total do domínio."""
        # Fatores que influenciam a pontuação:
        # 1. Taxa de sucesso geral
        # 2. Tempo desde última atualização
        # 3. Tempo médio de resposta
        # 4. Estabilidade dos padrões
        
        base_score = self.success_rate * 100
        
        # Penalidade por tempo desde última atualização
        days_since_update = (datetime.now() - self.last_updated).days
        time_penalty = min(days_since_update * 2, 30)
        base_score -= time_penalty
        
        # Bônus por tempo de resposta
        if self.avg_response_time > 0:
            response_bonus = max(0, 15 - (self.avg_response_time * 5))
            base_score += response_bonus
        
        # Penalidade por mudanças de padrão
        pattern_penalty = len(self.pattern_changes) * 3
        base_score -= pattern_penalty
        
        return max(0, min(100, base_score))

class LearningManager:
    """Gerenciador de aprendizado e pontuação."""
    
    def __init__(self):
        self.data_file = Path("data/learning_data.json")
        self.domains: Dict[str, DomainPattern] = {}
        self._load_data()
    
    def _load_data(self):
        """Carrega dados de aprendizado."""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for domain, pattern in data.items():
                        self.domains[domain] = self._deserialize_domain_pattern(pattern)
        except Exception as e:
            logger.error(f"Error loading learning data: {str(e)}")
    
    def _save_data(self):
        """Salva dados de aprendizado."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(
                    {domain: self._serialize_domain_pattern(pattern) 
                     for domain, pattern in self.domains.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str
                )
        except Exception as e:
            logger.error(f"Error saving learning data: {str(e)}")
    
    def _serialize_domain_pattern(self, pattern: DomainPattern) -> Dict:
        """Serializa padrão de domínio para JSON."""
        return {
            "domain": pattern.domain,
            "selectors": {
                field: [
                    {
                        "selector": s.selector,
                        "success_count": s.success_count,
                        "failure_count": s.failure_count,
                        "last_success": s.last_success.isoformat() if s.last_success else None,
                        "last_failure": s.last_failure.isoformat() if s.last_failure else None,
                        "avg_response_time": s.avg_response_time,
                        "pattern_changes": s.pattern_changes
                    }
                    for s in selectors
                ]
                for field, selectors in pattern.selectors.items()
            },
            "last_updated": pattern.last_updated.isoformat(),
            "success_rate": pattern.success_rate,
            "avg_response_time": pattern.avg_response_time,
            "pattern_changes": pattern.pattern_changes
        }
    
    def _deserialize_domain_pattern(self, data: Dict) -> DomainPattern:
        """Deserializa padrão de domínio de JSON."""
        return DomainPattern(
            domain=data["domain"],
            selectors={
                field: [
                    SelectorScore(
                        selector=s["selector"],
                        success_count=s["success_count"],
                        failure_count=s["failure_count"],
                        last_success=datetime.fromisoformat(s["last_success"]) if s["last_success"] else None,
                        last_failure=datetime.fromisoformat(s["last_failure"]) if s["last_failure"] else None,
                        avg_response_time=s["avg_response_time"],
                        pattern_changes=s["pattern_changes"]
                    )
                    for s in selectors
                ]
                for field, selectors in data["selectors"].items()
            },
            last_updated=datetime.fromisoformat(data["last_updated"]),
            success_rate=data["success_rate"],
            avg_response_time=data["avg_response_time"],
            pattern_changes=data["pattern_changes"]
        )
    
    def get_best_selectors(self, domain: str, field: str) -> List[str]:
        """Retorna os melhores seletores para um domínio e campo."""
        if domain not in self.domains:
            return []
        
        selectors = self.domains[domain].selectors.get(field, [])
        return [s.selector for s in sorted(selectors, key=lambda x: x.score, reverse=True)]
    
    def update_selector_score(
        self,
        domain: str,
        field: str,
        selector: str,
        success: bool,
        response_time: float
    ):
        """Atualiza pontuação de um seletor."""
        if domain not in self.domains:
            self.domains[domain] = DomainPattern(
                domain=domain,
                selectors={},
                last_updated=datetime.now(),
                success_rate=0.0,
                avg_response_time=0.0,
                pattern_changes=[]
            )
        
        if field not in self.domains[domain].selectors:
            self.domains[domain].selectors[field] = []
        
        # Encontra ou cria o seletor
        selector_score = next(
            (s for s in self.domains[domain].selectors[field] if s.selector == selector),
            SelectorScore(selector=selector)
        )
        
        # Atualiza estatísticas
        if success:
            selector_score.success_count += 1
            selector_score.last_success = datetime.now()
        else:
            selector_score.failure_count += 1
            selector_score.last_failure = datetime.now()
        
        # Atualiza tempo médio de resposta
        if selector_score.avg_response_time == 0:
            selector_score.avg_response_time = response_time
        else:
            selector_score.avg_response_time = (
                selector_score.avg_response_time * 0.9 + response_time * 0.1
            )
        
        # Adiciona seletor se for novo
        if selector_score not in self.domains[domain].selectors[field]:
            self.domains[domain].selectors[field].append(selector_score)
        
        # Atualiza estatísticas do domínio
        self._update_domain_stats(domain)
        
        # Salva alterações
        self._save_data()
    
    def _update_domain_stats(self, domain: str):
        """Atualiza estatísticas do domínio."""
        pattern = self.domains[domain]
        
        # Calcula taxa de sucesso geral
        total_success = sum(
            s.success_count
            for selectors in pattern.selectors.values()
            for s in selectors
        )
        total_attempts = sum(
            s.success_count + s.failure_count
            for selectors in pattern.selectors.values()
            for s in selectors
        )
        pattern.success_rate = total_success / total_attempts if total_attempts > 0 else 0.0
        
        # Calcula tempo médio de resposta
        response_times = [
            s.avg_response_time
            for selectors in pattern.selectors.values()
            for s in selectors
            if s.avg_response_time > 0
        ]
        pattern.avg_response_time = (
            sum(response_times) / len(response_times)
            if response_times else 0.0
        )
        
        # Atualiza timestamp
        pattern.last_updated = datetime.now()
    
    def detect_pattern_changes(self, domain: str, field: str, content: str):
        """Detecta mudanças no padrão do conteúdo."""
        if domain not in self.domains:
            return
        
        # Gera hash do conteúdo
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Verifica se houve mudança
        last_change = next(
            (change for change in reversed(self.domains[domain].pattern_changes)
             if change["field"] == field),
            None
        )
        
        if last_change and last_change["content_hash"] != content_hash:
            # Detecta tipo de mudança
            change_type = self._analyze_change_type(
                last_change["content"],
                content
            )
            
            # Registra mudança
            self.domains[domain].pattern_changes.append({
                "field": field,
                "timestamp": datetime.now().isoformat(),
                "content_hash": content_hash,
                "change_type": change_type
            })
            
            # Atualiza seletores afetados
            self._update_affected_selectors(domain, field, change_type)
            
            # Salva alterações
            self._save_data()
    
    def _analyze_change_type(self, old_content: str, new_content: str) -> str:
        """Analisa o tipo de mudança no conteúdo."""
        if not old_content or not new_content:
            return "new"
        
        # Verifica se é mudança estrutural
        old_tags = set(re.findall(r"<[^>]+>", old_content))
        new_tags = set(re.findall(r"<[^>]+>", new_content))
        
        if old_tags != new_tags:
            return "structural"
        
        # Verifica se é mudança de estilo
        old_styles = set(re.findall(r'style="[^"]+"', old_content))
        new_styles = set(re.findall(r'style="[^"]+"', new_content))
        
        if old_styles != new_styles:
            return "styling"
        
        # Verifica se é mudança de conteúdo
        old_text = re.sub(r"<[^>]+>", "", old_content).strip()
        new_text = re.sub(r"<[^>]+>", "", new_content).strip()
        
        if old_text != new_text:
            return "content"
        
        return "unknown"
    
    def _update_affected_selectors(self, domain: str, field: str, change_type: str):
        """Atualiza seletores afetados por mudanças."""
        if domain not in self.domains:
            return
        
        for selector in self.domains[domain].selectors.get(field, []):
            # Adiciona informação de mudança
            selector.pattern_changes.append({
                "timestamp": datetime.now().isoformat(),
                "change_type": change_type
            })
            
            # Ajusta pontuação baseado no tipo de mudança
            if change_type == "structural":
                selector.success_count = max(0, selector.success_count - 5)
            elif change_type == "styling":
                selector.success_count = max(0, selector.success_count - 2)
    
    def get_domain_score(self, domain: str) -> float:
        """Retorna pontuação de um domínio."""
        if domain not in self.domains:
            return 0.0
        return self.domains[domain].score
    
    def get_best_domains(self, limit: int = 5) -> List[str]:
        """Retorna os domínios com melhor pontuação."""
        return [
            domain for domain, _ in sorted(
                self.domains.items(),
                key=lambda x: x[1].score,
                reverse=True
            )[:limit]
        ] 