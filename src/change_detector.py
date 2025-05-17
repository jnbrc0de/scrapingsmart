from typing import Dict, List, Optional, Tuple
import hashlib
from datetime import datetime
import logging
from dataclasses import dataclass
from src.config.settings import (
    LAYOUT_CHANGE_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    MAX_FALLBACK_STRATEGIES
)

logger = logging.getLogger(__name__)

@dataclass
class LayoutSignature:
    structure_hash: str
    content_hash: str
    timestamp: datetime
    confidence: float

@dataclass
class ExtractionResult:
    price: Optional[float]
    confidence: float
    strategy_used: str
    fallback_used: bool
    layout_changed: bool

class ChangeDetector:
    def __init__(self):
        self.layout_history: Dict[str, List[LayoutSignature]] = {}
        self.fallback_strategies: Dict[str, List[Dict]] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for change detection."""
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def detect_layout_changes(self, domain: str, current_html: str) -> Tuple[bool, float]:
        """Detect if layout has changed significantly."""
        current_signature = self._generate_layout_signature(current_html)
        
        if domain not in self.layout_history:
            self.layout_history[domain] = []
            return False, 1.0

        previous_signatures = self.layout_history[domain]
        if not previous_signatures:
            return False, 1.0

        # Compare with most recent signature
        last_signature = previous_signatures[-1]
        similarity = self._calculate_similarity(
            current_signature,
            last_signature
        )

        # Update history
        self.layout_history[domain].append(current_signature)
        if len(self.layout_history[domain]) > 10:  # Keep last 10 signatures
            self.layout_history[domain].pop(0)

        # Check if change is significant
        layout_changed = similarity < LAYOUT_CHANGE_THRESHOLD
        if layout_changed:
            logger.warning(
                f"Layout change detected for {domain}. "
                f"Similarity: {similarity:.2f}"
            )

        return layout_changed, similarity

    def _generate_layout_signature(self, html: str) -> LayoutSignature:
        """Generate signature for HTML structure and content."""
        # Extract structural elements (tags, classes, IDs)
        structure = self._extract_structure(html)
        structure_hash = hashlib.md5(structure.encode()).hexdigest()

        # Extract content elements (text, numbers)
        content = self._extract_content(html)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        return LayoutSignature(
            structure_hash=structure_hash,
            content_hash=content_hash,
            timestamp=datetime.now(),
            confidence=1.0
        )

    def _extract_structure(self, html: str) -> str:
        """Extract structural elements from HTML."""
        # TODO: Implement proper HTML parsing
        # Limitação: Parsing HTML detalhado não implementado nesta versão.
        return html

    def _extract_content(self, html: str) -> str:
        """Extract content elements from HTML."""
        # TODO: Implement proper content extraction
        # Limitação: Extração de conteúdo detalhada não implementada nesta versão.
        return html

    def _calculate_similarity(self, current: LayoutSignature, previous: LayoutSignature) -> float:
        """Calculate similarity between two layout signatures."""
        structure_similarity = 1.0 if current.structure_hash == previous.structure_hash else 0.0
        content_similarity = 1.0 if current.content_hash == previous.content_hash else 0.0
        
        # Weight structure more heavily than content
        return 0.7 * structure_similarity + 0.3 * content_similarity

    def get_fallback_strategies(self, domain: str) -> List[Dict]:
        """Get fallback strategies for a domain."""
        if domain not in self.fallback_strategies:
            return []
        return self.fallback_strategies[domain]

    def add_fallback_strategy(self, domain: str, strategy: Dict) -> None:
        """Add a new fallback strategy for a domain."""
        if domain not in self.fallback_strategies:
            self.fallback_strategies[domain] = []

        strategies = self.fallback_strategies[domain]
        strategies.append(strategy)

        # Keep only the most recent strategies
        if len(strategies) > MAX_FALLBACK_STRATEGIES:
            strategies.pop(0)

    def evaluate_extraction(self, result: ExtractionResult) -> bool:
        """Evaluate if extraction result is acceptable."""
        if result.confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.warning(
                f"Low confidence extraction: {result.confidence:.2f} "
                f"using strategy {result.strategy_used}"
            )
            return False

        if result.layout_changed and not result.fallback_used:
            logger.warning(
                f"Layout changed but no fallback used. "
                f"Strategy: {result.strategy_used}"
            )
            return False

        return True

    def get_domain_stats(self, domain: str) -> Dict:
        """Get statistics about layout changes for a domain."""
        if domain not in self.layout_history:
            return {
                "total_changes": 0,
                "last_change": None,
                "average_similarity": 1.0
            }

        signatures = self.layout_history[domain]
        if len(signatures) < 2:
            return {
                "total_changes": 0,
                "last_change": None,
                "average_similarity": 1.0
            }

        changes = 0
        similarities = []
        last_change = None

        for i in range(1, len(signatures)):
            similarity = self._calculate_similarity(
                signatures[i],
                signatures[i-1]
            )
            similarities.append(similarity)

            if similarity < LAYOUT_CHANGE_THRESHOLD:
                changes += 1
                last_change = signatures[i].timestamp

        return {
            "total_changes": changes,
            "last_change": last_change.isoformat() if last_change else None,
            "average_similarity": sum(similarities) / len(similarities)
        } 