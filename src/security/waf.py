from typing import Dict, List, Optional, Tuple
import re
import logging
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class WAFRule:
    name: str
    pattern: str
    severity: str
    description: str
    action: str = "block"
    enabled: bool = True

class WAF:
    def __init__(self):
        self.rules: List[WAFRule] = []
        self._setup_default_rules()
        self._compiled_patterns: Dict[str, re.Pattern] = {}

    def _setup_default_rules(self):
        """Setup default WAF rules."""
        self.rules = [
            WAFRule(
                name="sql_injection",
                pattern=r"(?i)(\b(select|insert|update|delete|drop|union|exec|where)\b.*\b(from|into|table|database)\b)",
                severity="high",
                description="SQL Injection attempt detected"
            ),
            WAFRule(
                name="xss_attack",
                pattern=r"(?i)(<script.*?>.*?</script>|<.*?javascript:.*?>|<.*?\\s+on.*?=.*?>)",
                severity="high",
                description="XSS attack attempt detected"
            ),
            WAFRule(
                name="path_traversal",
                pattern=r"(?i)(\.\.\/|\.\.\\|~\/|~\\|\/etc\/|\/var\/|\/usr\/|\/bin\/|\/sbin\/)",
                severity="high",
                description="Path traversal attempt detected"
            ),
            WAFRule(
                name="command_injection",
                pattern=r"(?i)(\b(cat|chmod|curl|wget|nc|netcat|bash|sh|cmd|powershell)\b.*\b(>|<|\||;|&)\b)",
                severity="critical",
                description="Command injection attempt detected"
            ),
            WAFRule(
                name="sensitive_data",
                pattern=r"(?i)(\b(password|secret|key|token|api_key|auth)\b.*\b(=|:)\b.*\b([a-zA-Z0-9]{8,})\b)",
                severity="medium",
                description="Potential sensitive data exposure"
            )
        ]
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        for rule in self.rules:
            try:
                self._compiled_patterns[rule.name] = re.compile(rule.pattern)
            except Exception as e:
                logger.error(f"Error compiling pattern for rule {rule.name}: {e}")

    async def inspect_request(self, request_data: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Inspect a request for security violations.
        Returns: (is_allowed, rule_name, description)
        """
        try:
            # Convert request data to string for inspection
            request_str = json.dumps(request_data)
            
            for rule in self.rules:
                if not rule.enabled:
                    continue
                    
                pattern = self._compiled_patterns.get(rule.name)
                if not pattern:
                    continue
                    
                if pattern.search(request_str):
                    logger.warning(
                        f"WAF rule triggered: {rule.name} - {rule.description} "
                        f"(Severity: {rule.severity})"
                    )
                    return False, rule.name, rule.description
                    
            return True, None, None
            
        except Exception as e:
            logger.error(f"Error inspecting request: {e}")
            return False, "error", str(e)

    def add_rule(self, rule: WAFRule):
        """Add a new WAF rule."""
        try:
            self._compiled_patterns[rule.name] = re.compile(rule.pattern)
            self.rules.append(rule)
            logger.info(f"Added new WAF rule: {rule.name}")
        except Exception as e:
            logger.error(f"Error adding WAF rule {rule.name}: {e}")

    def update_rule(self, rule_name: str, enabled: bool = None, action: str = None):
        """Update an existing WAF rule."""
        for rule in self.rules:
            if rule.name == rule_name:
                if enabled is not None:
                    rule.enabled = enabled
                if action is not None:
                    rule.action = action
                logger.info(f"Updated WAF rule: {rule_name}")
                return
        logger.warning(f"WAF rule not found: {rule_name}")

    def get_rules(self) -> List[Dict]:
        """Get all WAF rules."""
        return [
            {
                "name": rule.name,
                "pattern": rule.pattern,
                "severity": rule.severity,
                "description": rule.description,
                "action": rule.action,
                "enabled": rule.enabled
            }
            for rule in self.rules
        ]

    def get_rule_stats(self) -> Dict:
        """Get statistics about WAF rules."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "severity_counts": {
                "high": len([r for r in self.rules if r.severity == "high"]),
                "medium": len([r for r in self.rules if r.severity == "medium"]),
                "low": len([r for r in self.rules if r.severity == "low"])
            }
        } 