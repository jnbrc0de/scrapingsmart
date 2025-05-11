from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging
from datetime import datetime
import json
from collections import defaultdict
import numpy as np
from config.settings import settings
from concurrent.futures import ThreadPoolExecutor
import threading
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class DomainSimilarity:
    domain: str
    similarity_score: float
    common_patterns: List[Dict]
    shared_attributes: List[str]

class DomainLearningManager:
    def __init__(self):
        self.domain_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.domain_metrics: Dict[str, Dict] = defaultdict(dict)
        self.similarity_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._setup_logging()
        self._initialize_cache()
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=settings.network.max_concurrent_connections)

    def _setup_logging(self):
        """Configure logging for domain learning."""
        logger.setLevel(settings.logging.level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(settings.logging.format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _initialize_cache(self):
        """Initialize LRU cache with size limits."""
        self.pattern_cache = {}
        self.metrics_cache = {}
        self.similarity_cache = {}

    def update_domain_patterns(self, domain: str, patterns: List[Dict], success: bool) -> None:
        """Update patterns for a domain with success/failure feedback."""
        with self._lock:
            if domain not in self.domain_patterns:
                self.domain_patterns[domain] = []

            # Add new patterns with metadata
            for pattern in patterns:
                pattern_entry = {
                    'pattern': pattern,
                    'success_count': 1 if success else 0,
                    'failure_count': 0 if success else 1,
                    'last_used': datetime.now(),
                    'success_rate': 1.0 if success else 0.0
                }
                self.domain_patterns[domain].append(pattern_entry)

            # Update success rates and clean old patterns
            self._update_pattern_success_rates(domain)
            self._clean_old_patterns(domain)

            # Invalidate similarity cache for this domain
            self._invalidate_similarity_cache(domain)

    def _update_pattern_success_rates(self, domain: str) -> None:
        """Update success rates for all patterns in a domain."""
        for pattern in self.domain_patterns[domain]:
            total = pattern['success_count'] + pattern['failure_count']
            if total > 0:
                pattern['success_rate'] = pattern['success_count'] / total

    def _clean_old_patterns(self, domain: str) -> None:
        """Remove old and ineffective patterns."""
        current_time = datetime.now()
        self.domain_patterns[domain] = [
            p for p in self.domain_patterns[domain]
            if (
                (current_time - p['last_used']).days < settings.cache.max_pattern_age_days and
                p['success_rate'] >= settings.cache.min_success_rate and
                p['success_count'] + p['failure_count'] >= 5
            )
        ]

    @lru_cache(maxsize=1000)
    def find_similar_domains(self, domain: str, threshold: float = None) -> List[DomainSimilarity]:
        """Find domains with similar patterns and structure."""
        if threshold is None:
            threshold = settings.learning.pattern_similarity_threshold

        if domain not in self.similarity_matrix:
            self._calculate_domain_similarity(domain)

        similar_domains = []
        for other_domain, similarity in self.similarity_matrix[domain].items():
            if similarity >= threshold:
                common_patterns = self._find_common_patterns(domain, other_domain)
                shared_attributes = self._find_shared_attributes(domain, other_domain)
                
                similar_domains.append(DomainSimilarity(
                    domain=other_domain,
                    similarity_score=similarity,
                    common_patterns=common_patterns,
                    shared_attributes=shared_attributes
                ))

        return sorted(similar_domains, key=lambda x: x.similarity_score, reverse=True)

    def _calculate_domain_similarity(self, domain: str) -> None:
        """Calculate similarity between domains based on patterns and structure."""
        if domain not in self.domain_patterns:
            return

        def calculate_similarity(other_domain: str) -> Tuple[str, float]:
            if domain == other_domain:
                return other_domain, 0.0

            pattern_similarity = self._calculate_pattern_similarity(
                self.domain_patterns[domain],
                self.domain_patterns[other_domain]
            )

            structure_similarity = self._calculate_structure_similarity(
                self.domain_metrics.get(domain, {}),
                self.domain_metrics.get(other_domain, {})
            )

            similarity = 0.7 * pattern_similarity + 0.3 * structure_similarity
            return other_domain, similarity

        # Calculate similarities in parallel
        futures = [
            self._executor.submit(calculate_similarity, other_domain)
            for other_domain in self.domain_patterns
        ]

        # Update similarity matrix
        for future in futures:
            other_domain, similarity = future.result()
            self.similarity_matrix[domain][other_domain] = similarity
            self.similarity_matrix[other_domain][domain] = similarity

    def _calculate_pattern_similarity(self, patterns1: List[Dict], patterns2: List[Dict]) -> float:
        """Calculate similarity between pattern sets."""
        if not patterns1 or not patterns2:
            return 0.0

        features1 = self._extract_pattern_features(patterns1)
        features2 = self._extract_pattern_features(patterns2)

        return self._cosine_similarity(features1, features2)

    def _extract_pattern_features(self, patterns: List[Dict]) -> Dict[str, float]:
        """Extract numerical features from patterns."""
        features = defaultdict(float)
        for pattern in patterns:
            p = pattern['pattern']
            if 'type' in p:
                features[f"type_{p['type']}"] += 1
            if 'value' in p:
                features[f"value_{p['value']}"] += 1
            features['success_rate'] += pattern['success_rate']
        return features

    def _cosine_similarity(self, features1: Dict[str, float], features2: Dict[str, float]) -> float:
        """Calculate cosine similarity between feature vectors."""
        all_features = set(features1.keys()) | set(features2.keys())
        
        vec1 = np.array([features1.get(f, 0) for f in all_features])
        vec2 = np.array([features2.get(f, 0) for f in all_features])
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return np.dot(vec1, vec2) / (norm1 * norm2)

    def _calculate_structure_similarity(self, metrics1: Dict, metrics2: Dict) -> float:
        """Calculate similarity between domain structures."""
        if not metrics1 or not metrics2:
            return 0.0

        common_metrics = set(metrics1.keys()) & set(metrics2.keys())
        if not common_metrics:
            return 0.0

        similarities = []
        for metric in common_metrics:
            val1 = metrics1[metric]
            val2 = metrics2[metric]
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                max_val = max(val1, val2)
                if max_val > 0:
                    similarities.append(1 - abs(val1 - val2) / max_val)

        return np.mean(similarities) if similarities else 0.0

    def _find_common_patterns(self, domain1: str, domain2: str) -> List[Dict]:
        """Find patterns that are successful in both domains."""
        patterns1 = {p['pattern']['value']: p for p in self.domain_patterns[domain1]}
        patterns2 = {p['pattern']['value']: p for p in self.domain_patterns[domain2]}

        common = []
        for value, pattern1 in patterns1.items():
            if value in patterns2:
                pattern2 = patterns2[value]
                if pattern1['success_rate'] > 0.7 and pattern2['success_rate'] > 0.7:
                    common.append({
                        'pattern': pattern1['pattern'],
                        'success_rate_domain1': pattern1['success_rate'],
                        'success_rate_domain2': pattern2['success_rate']
                    })

        return common

    def _find_shared_attributes(self, domain1: str, domain2: str) -> List[str]:
        """Find HTML attributes commonly used in both domains."""
        attrs1: Set[str] = set()
        attrs2: Set[str] = set()

        for pattern in self.domain_patterns[domain1]:
            if 'attributes' in pattern['pattern']:
                attrs1.update(pattern['pattern']['attributes'])

        for pattern in self.domain_patterns[domain2]:
            if 'attributes' in pattern['pattern']:
                attrs2.update(pattern['pattern']['attributes'])

        return list(attrs1 & attrs2)

    def transfer_knowledge(self, source_domain: str, target_domain: str) -> List[Dict]:
        """Transfer successful patterns from source to target domain."""
        similar_domains = self.find_similar_domains(source_domain)
        if not similar_domains:
            return []

        transferred_patterns = []
        for similar in similar_domains:
            if similar.domain == target_domain:
                continue

            successful_patterns = [
                p for p in self.domain_patterns[similar.domain]
                if p['success_rate'] > 0.8
            ]

            for pattern in successful_patterns:
                adapted_pattern = self._adapt_pattern(pattern, target_domain)
                if adapted_pattern:
                    transferred_patterns.append(adapted_pattern)

        return transferred_patterns

    def _adapt_pattern(self, pattern: Dict, target_domain: str) -> Optional[Dict]:
        """Adapt a pattern for a new domain."""
        if any(p['pattern'] == pattern['pattern'] for p in self.domain_patterns[target_domain]):
            return None

        return {
            'pattern': pattern['pattern'].copy(),
            'success_count': 0,
            'failure_count': 0,
            'last_used': datetime.now(),
            'success_rate': 0.5
        }

    def optimize_strategies(self, domain: str) -> None:
        """Optimize strategies for a domain."""
        with self._lock:
            self._update_pattern_priorities(domain)
            self._generate_pattern_variants(domain)
            self._remove_ineffective_patterns(domain)

    def _update_pattern_priorities(self, domain: str) -> None:
        """Update priorities based on success rate and recency."""
        if domain not in self.domain_patterns:
            return

        current_time = datetime.now()
        for pattern in self.domain_patterns[domain]:
            days_old = (current_time - pattern['last_used']).days
            time_decay = settings.learning.success_rate_decay ** days_old
            pattern['priority'] = pattern['success_rate'] * time_decay

        self.domain_patterns[domain].sort(key=lambda x: x['priority'], reverse=True)

    def _generate_pattern_variants(self, domain: str) -> None:
        """Generate variants of successful patterns."""
        if domain not in self.domain_patterns:
            return

        successful_patterns = [
            p for p in self.domain_patterns[domain]
            if p['success_rate'] > 0.8
        ]

        for pattern in successful_patterns:
            variants = self._create_pattern_variants(pattern['pattern'])
            for variant in variants:
                self.domain_patterns[domain].append({
                    'pattern': variant,
                    'success_count': 0,
                    'failure_count': 0,
                    'last_used': datetime.now(),
                    'success_rate': 0.5
                })

    def _create_pattern_variants(self, pattern: Dict) -> List[Dict]:
        """Create variants of a pattern with small modifications."""
        variants = []

        if 'selector' in pattern:
            base_selector = pattern['selector']
            variants.extend([
                {'selector': f"{base_selector} > *"},
                {'selector': f"{base_selector} *"},
                {'selector': f"{base_selector}:first-child"}
            ])

        if 'attributes' in pattern:
            base_attrs = pattern['attributes']
            variants.extend([
                {'attributes': base_attrs + ['data-price']},
                {'attributes': base_attrs + ['data-value']},
                {'attributes': base_attrs + ['data-product-price']}
            ])

        return variants

    def _remove_ineffective_patterns(self, domain: str) -> None:
        """Remove patterns that are not performing well."""
        if domain not in self.domain_patterns:
            return

        self.domain_patterns[domain] = [
            p for p in self.domain_patterns[domain]
            if (
                p['success_rate'] >= settings.cache.min_success_rate or
                p['success_count'] + p['failure_count'] < 5
            )
        ]

    def get_optimized_patterns(self, domain: str, limit: int = None) -> List[Dict]:
        """Get optimized patterns for a domain."""
        if limit is None:
            limit = settings.learning.max_fallback_strategies

        if domain not in self.domain_patterns:
            return []

        sorted_patterns = sorted(
            self.domain_patterns[domain],
            key=lambda x: (x['priority'], x['success_rate']),
            reverse=True
        )

        return [p['pattern'] for p in sorted_patterns[:limit]]

    def _invalidate_similarity_cache(self, domain: str) -> None:
        """Invalidate similarity cache for a domain."""
        self.find_similar_domains.cache_clear()

    def cleanup(self):
        """Cleanup resources."""
        self._executor.shutdown(wait=True)
        self.find_similar_domains.cache_clear() 