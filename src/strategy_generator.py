from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime
import json
from bs4 import BeautifulSoup
import re
from src.config.settings import (
    MIN_CONFIDENCE_THRESHOLD,
    MAX_FALLBACK_STRATEGIES
)

logger = logging.getLogger(__name__)

@dataclass
class Strategy:
    name: str
    selectors: Dict[str, str]
    confidence: float
    success_rate: float
    last_used: datetime
    context: Dict

class StrategyGenerator:
    def __init__(self):
        self.success_patterns: Dict[str, List[Dict]] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for strategy generation."""
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def detect_changes(self, domain: str, html: str) -> Tuple[bool, Dict]:
        """Detect changes in page structure and content."""
        changes = {
            'structure_changed': False,
            'content_changed': False,
            'selectors_changed': False,
            'details': []
        }

        current_soup = BeautifulSoup(html, 'html.parser')
        current_structure = self._extract_structure(current_soup)
        current_content = self._extract_content(current_soup)

        # Compare with last known structure
        if domain in self.success_patterns:
            last_pattern = self.success_patterns[domain][-1]
            old_structure = last_pattern.get('structure', {})
            old_content = last_pattern.get('content', {})

            # Compare structure
            if current_structure != old_structure:
                changes['structure_changed'] = True
                changes['details'].append({
                    'type': 'structure',
                    'diff': self._compare_structures(current_structure, old_structure)
                })

            # Compare content
            if current_content != old_content:
                changes['content_changed'] = True
                changes['details'].append({
                    'type': 'content',
                    'diff': self._compare_contents(current_content, old_content)
                })

        return any([changes['structure_changed'], changes['content_changed'], changes['selectors_changed']]), changes

    def generate_strategy(self, domain: str, html: str, successful_selectors: Dict[str, str]) -> Strategy:
        """Generate a new strategy based on successful selectors and patterns."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract common patterns from successful selectors
        patterns = self._extract_patterns(successful_selectors)
        
        # Generate new selectors based on patterns
        new_selectors = self._generate_selectors(soup, patterns)
        
        # Calculate confidence based on pattern matching
        confidence = self._calculate_confidence(new_selectors, patterns)
        
        strategy = Strategy(
            name=f"auto_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            selectors=new_selectors,
            confidence=confidence,
            success_rate=0.0,
            last_used=datetime.now(),
            context={
                'generated_from': successful_selectors,
                'patterns_used': patterns,
                'last_html': html
            }
        )

        # Update success patterns
        self._update_success_patterns(domain, strategy, True)

        return strategy

    def _update_success_patterns(self, domain: str, strategy: Strategy, success: bool) -> None:
        """Update success patterns based on strategy performance."""
        if domain not in self.success_patterns:
            self.success_patterns[domain] = []

        # Extract patterns from successful strategy
        if success:
            patterns = self._extract_patterns(strategy.selectors)
            self.success_patterns[domain].append({
                'patterns': patterns,
                'timestamp': datetime.now(),
                'confidence': strategy.confidence,
                'structure': self._extract_structure(BeautifulSoup(strategy.context['last_html'], 'html.parser')),
                'content': self._extract_content(BeautifulSoup(strategy.context['last_html'], 'html.parser'))
            })

            # Keep only recent patterns
            if len(self.success_patterns[domain]) > 10:
                self.success_patterns[domain].pop(0)

    def _extract_structure(self, soup: BeautifulSoup) -> Dict:
        """Extract structural elements from HTML."""
        structure = {}
        for tag in soup.find_all():
            if tag.name not in structure:
                structure[tag.name] = []
            structure[tag.name].append({
                'classes': tag.get('class', []),
                'id': tag.get('id'),
                'attributes': {k: v for k, v in tag.attrs.items() if k not in ['class', 'id']}
            })
        return structure

    def _extract_content(self, soup: BeautifulSoup) -> Dict:
        """Extract content elements from HTML."""
        content = {}
        for tag in soup.find_all():
            if tag.string and tag.string.strip():
                content[tag.name] = content.get(tag.name, []) + [tag.string.strip()]
        return content

    def _extract_patterns(self, selectors: Dict[str, str]) -> List[Dict]:
        """Extract common patterns from selectors."""
        patterns = []
        for selector_type, selector in selectors.items():
            # Extract tag patterns
            tag_pattern = re.search(r'^(\w+)', selector)
            if tag_pattern:
                patterns.append({
                    'type': 'tag',
                    'value': tag_pattern.group(1)
                })

            # Extract class patterns
            class_patterns = re.findall(r'\.([\w-]+)', selector)
            for class_name in class_patterns:
                patterns.append({
                    'type': 'class',
                    'value': class_name
                })

            # Extract ID patterns
            id_pattern = re.search(r'#([\w-]+)', selector)
            if id_pattern:
                patterns.append({
                    'type': 'id',
                    'value': id_pattern.group(1)
                })

        return patterns

    def _generate_selectors(self, soup: BeautifulSoup, patterns: List[Dict]) -> Dict[str, str]:
        """Generate new selectors based on patterns."""
        selectors = {}
        
        # Try to find price elements
        price_elements = self._find_price_elements(soup, patterns)
        if price_elements:
            selectors['price'] = self._generate_selector(price_elements[0])

        # Try to find title elements
        title_elements = self._find_title_elements(soup, patterns)
        if title_elements:
            selectors['title'] = self._generate_selector(title_elements[0])

        # Try to find availability elements
        availability_elements = self._find_availability_elements(soup, patterns)
        if availability_elements:
            selectors['availability'] = self._generate_selector(availability_elements[0])

        return selectors

    def _find_price_elements(self, soup: BeautifulSoup, patterns: List[Dict]) -> List:
        """Find potential price elements."""
        elements = []
        
        # Look for elements with price-like content
        for element in soup.find_all():
            if element.string:
                text = element.string.strip()
                if re.match(r'R\$\s*\d+[.,]\d{2}', text):
                    elements.append(element)

        # Filter by patterns
        return [e for e in elements if self._matches_patterns(e, patterns)]

    def _find_title_elements(self, soup: BeautifulSoup, patterns: List[Dict]) -> List:
        """Find potential title elements."""
        elements = []
        
        # Look for heading elements
        for tag in ['h1', 'h2', 'h3']:
            elements.extend(soup.find_all(tag))

        # Filter by patterns
        return [e for e in elements if self._matches_patterns(e, patterns)]

    def _find_availability_elements(self, soup: BeautifulSoup, patterns: List[Dict]) -> List:
        """Find potential availability elements."""
        elements = []
        
        # Look for elements with availability-like content
        for element in soup.find_all():
            if element.string:
                text = element.string.strip().lower()
                if any(word in text for word in ['em estoque', 'disponível', 'indisponível']):
                    elements.append(element)

        # Filter by patterns
        return [e for e in elements if self._matches_patterns(e, patterns)]

    def _matches_patterns(self, element, patterns: List[Dict]) -> bool:
        """Check if element matches any of the patterns."""
        for pattern in patterns:
            if pattern['type'] == 'tag' and element.name == pattern['value']:
                return True
            if pattern['type'] == 'class' and pattern['value'] in element.get('class', []):
                return True
            if pattern['type'] == 'id' and element.get('id') == pattern['value']:
                return True
        return False

    def _generate_selector(self, element) -> str:
        """Generate a CSS selector for an element."""
        selector_parts = []
        
        # Add tag
        selector_parts.append(element.name)
        
        # Add ID if present
        if element.get('id'):
            selector_parts.append(f"#{element['id']}")
        
        # Add classes if present
        if element.get('class'):
            selector_parts.extend(f".{cls}" for cls in element['class'])
        
        return ' '.join(selector_parts)

    def _calculate_confidence(self, selectors: Dict[str, str], patterns: List[Dict]) -> float:
        """Calculate confidence score for generated selectors."""
        if not selectors:
            return 0.0

        # Count matching patterns
        pattern_matches = sum(
            1 for selector in selectors.values()
            for pattern in patterns
            if pattern['value'] in selector
        )

        # Calculate base confidence
        base_confidence = pattern_matches / (len(patterns) * len(selectors))

        # Adjust for selector specificity
        specificity_scores = []
        for selector in selectors.values():
            score = 0
            if '#' in selector:  # ID selector
                score += 0.5
            if '.' in selector:  # Class selector
                score += 0.3
            if ' ' in selector:  # Descendant selector
                score += 0.2
            specificity_scores.append(score)

        specificity_confidence = sum(specificity_scores) / len(specificity_scores)

        return (base_confidence + specificity_confidence) / 2

    def _compare_structures(self, current: Dict, old: Dict) -> Dict:
        """Compare two structure dictionaries and return differences."""
        diff = {
            'added': [],
            'removed': [],
            'modified': []
        }

        # Check for added and modified elements
        for tag, elements in current.items():
            if tag not in old:
                diff['added'].append(tag)
            else:
                for i, element in enumerate(elements):
                    if i >= len(old[tag]):
                        diff['added'].append(f"{tag}[{i}]")
                    elif element != old[tag][i]:
                        diff['modified'].append(f"{tag}[{i}]")

        # Check for removed elements
        for tag in old:
            if tag not in current:
                diff['removed'].append(tag)

        return diff

    def _compare_contents(self, current: Dict, old: Dict) -> Dict:
        """Compare two content dictionaries and return differences."""
        diff = {
            'added': [],
            'removed': [],
            'modified': []
        }

        # Check for added and modified content
        for tag, contents in current.items():
            if tag not in old:
                diff['added'].append(tag)
            else:
                for i, content in enumerate(contents):
                    if i >= len(old[tag]):
                        diff['added'].append(f"{tag}[{i}]")
                    elif content != old[tag][i]:
                        diff['modified'].append(f"{tag}[{i}]")

        # Check for removed content
        for tag in old:
            if tag not in current:
                diff['removed'].append(tag)

        return diff 