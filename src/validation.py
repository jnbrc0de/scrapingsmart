from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
from datetime import datetime
import logging
from config.settings import MIN_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    issues: List[str]
    context: Dict

class PriceValidator:
    def __init__(self):
        self.price_patterns = {
            'brl': r'R\$\s*(\d+[.,]\d{2})',
            'usd': r'\$\s*(\d+[.,]\d{2})',
            'eur': r'€\s*(\d+[.,]\d{2})',
            'generic': r'(\d+[.,]\d{2})'
        }
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for validation."""
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def validate_price_context(self, price: float, context: Dict) -> ValidationResult:
        """Validate price within its context."""
        issues = []
        confidence = 1.0

        # Check price range
        if 'expected_range' in context:
            min_price, max_price = context['expected_range']
            if not min_price <= price <= max_price:
                issues.append(f"Price {price} outside expected range [{min_price}, {max_price}]")
                confidence *= 0.5

        # Check price history
        if 'price_history' in context:
            history = context['price_history']
            if history:
                avg_price = sum(history) / len(history)
                std_dev = self._calculate_std_dev(history)
                
                if abs(price - avg_price) > 3 * std_dev:
                    issues.append(f"Price {price} deviates significantly from history (avg: {avg_price:.2f})")
                    confidence *= 0.7

        # Check related prices
        if 'related_prices' in context:
            related = context['related_prices']
            if related:
                min_related = min(related)
                max_related = max(related)
                if not min_related <= price <= max_related:
                    issues.append(f"Price {price} outside related prices range [{min_related}, {max_related}]")
                    confidence *= 0.6

        return ValidationResult(
            is_valid=confidence >= MIN_CONFIDENCE_THRESHOLD,
            confidence=confidence,
            issues=issues,
            context={'validation_time': datetime.now()}
        )

    def validate_price_consistency(self, prices: Dict[str, float]) -> ValidationResult:
        """Validate consistency between different price types."""
        issues = []
        confidence = 1.0

        # Check PIX price
        if 'pix_price' in prices and 'regular_price' in prices:
            if prices['pix_price'] >= prices['regular_price']:
                issues.append("PIX price should be lower than regular price")
                confidence *= 0.5

        # Check installment prices
        if 'installment_price' in prices and 'regular_price' in prices:
            installment = prices['installment_price']
            if installment <= prices['regular_price']:
                issues.append("Installment price should be higher than regular price")
                confidence *= 0.5

        # Check old price
        if 'old_price' in prices and 'regular_price' in prices:
            if prices['old_price'] <= prices['regular_price']:
                issues.append("Old price should be higher than current price")
                confidence *= 0.5

        return ValidationResult(
            is_valid=confidence >= MIN_CONFIDENCE_THRESHOLD,
            confidence=confidence,
            issues=issues,
            context={'validation_time': datetime.now()}
        )

    def validate_availability(self, availability: str, context: Dict) -> ValidationResult:
        """Validate product availability information."""
        issues = []
        confidence = 1.0

        valid_states = {'in_stock', 'low_stock', 'out_of_stock', 'pre_order'}
        if availability not in valid_states:
            issues.append(f"Invalid availability state: {availability}")
            confidence *= 0.5

        # Check consistency with price
        if 'price' in context:
            if availability == 'out_of_stock' and context['price'] > 0:
                issues.append("Product marked as out of stock but has price")
                confidence *= 0.7

        return ValidationResult(
            is_valid=confidence >= MIN_CONFIDENCE_THRESHOLD,
            confidence=confidence,
            issues=issues,
            context={'validation_time': datetime.now()}
        )

    def validate_promotion(self, promotion: Dict, context: Dict) -> ValidationResult:
        """Validate promotion information."""
        issues = []
        confidence = 1.0

        # Check promotion dates
        if 'start_date' in promotion and 'end_date' in promotion:
            if promotion['start_date'] > promotion['end_date']:
                issues.append("Promotion start date after end date")
                confidence *= 0.5

        # Check discount amount
        if 'discount_amount' in promotion and 'original_price' in context:
            if promotion['discount_amount'] >= context['original_price']:
                issues.append("Discount amount greater than or equal to original price")
                confidence *= 0.5

        return ValidationResult(
            is_valid=confidence >= MIN_CONFIDENCE_THRESHOLD,
            confidence=confidence,
            issues=issues,
            context={'validation_time': datetime.now()}
        )

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        squared_diff_sum = sum((x - mean) ** 2 for x in values)
        return (squared_diff_sum / len(values)) ** 0.5

    def extract_price_from_text(self, text: str, currency: str = 'brl') -> Optional[float]:
        """Extract price from text using appropriate pattern."""
        pattern = self.price_patterns.get(currency, self.price_patterns['generic'])
        match = re.search(pattern, text)
        if match:
            try:
                price_str = match.group(1).replace(',', '.')
                return float(price_str)
            except (ValueError, IndexError):
                return None
        return None

    def validate_page_format(self, html: str, expected_elements: List[str]) -> ValidationResult:
        """Validate page format and structure."""
        issues = []
        confidence = 1.0

        for element in expected_elements:
            if element not in html:
                issues.append(f"Expected element not found: {element}")
                confidence *= 0.8

        return ValidationResult(
            is_valid=confidence >= MIN_CONFIDENCE_THRESHOLD,
            confidence=confidence,
            issues=issues,
            context={'validation_time': datetime.now()}
        ) 