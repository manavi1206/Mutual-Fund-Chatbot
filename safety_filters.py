"""
Safety Filters - Content filtering and safety checks
Enterprise-grade safety & security
"""
import re
from typing import List, Dict, Optional, Tuple


class SafetyFilters:
    """Filters harmful, sensitive, or policy-violating content"""
    
    def __init__(self):
        """Initialize safety filters"""
        # Harmful content patterns
        self.harmful_patterns = [
            r'\b(suicide|self-harm|kill yourself|end your life)\b',
            r'\b(violence|attack|harm|hurt)\s+(yourself|others)\b',
            r'\b(drug|illegal|substance abuse)\b',
        ]
        
        # Sensitive financial patterns (PII, account numbers, etc.)
        self.pii_patterns = [
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
            r'\b\d{10,12}\b',  # Account numbers
            r'\b[A-Z0-9]{10,}\b',  # Account IDs
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        ]
        
        # Policy violation patterns
        self.policy_violations = [
            r'\b(guaranteed return|guaranteed profit|risk-free)\b',
            r'\b(insider|confidential|secret)\s+(information|trading)\b',
            r'\b(manipulate|rig|fix)\s+(market|price)\b',
        ]
    
    def check_content(self, text: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Check content for safety issues
        
        Args:
            text: Text to check
            
        Returns:
            (is_safe: bool, reason: Optional[str], flags: List[str])
        """
        flags = []
        text_lower = text.lower()
        
        # Check for harmful content
        for pattern in self.harmful_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flags.append('harmful_content')
                return False, "Content contains potentially harmful information", flags
        
        # Check for PII
        for pattern in self.pii_patterns:
            if re.search(pattern, text):
                flags.append('pii_detected')
                # Don't block, but flag it
                flags.append('pii_warning')
        
        # Check for policy violations
        for pattern in self.policy_violations:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flags.append('policy_violation')
                return False, "Content violates financial policy guidelines", flags
        
        return True, None, flags
    
    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text
        
        Args:
            text: Text that may contain PII
            
        Returns:
            Text with PII redacted
        """
        redacted = text
        
        # Redact credit card numbers
        redacted = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[REDACTED]', redacted)
        
        # Redact account numbers
        redacted = re.sub(r'\b\d{10,12}\b', '[REDACTED]', redacted)
        
        # Redact SSN
        redacted = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED]', redacted)
        
        return redacted
    
    def filter_response(self, answer: str, query: str) -> Tuple[str, List[str]]:
        """
        Filter response for safety
        
        Args:
            answer: Answer text
            query: Original query
            
        Returns:
            (filtered_answer, flags)
        """
        # Check answer
        is_safe, reason, flags = self.check_content(answer)
        
        if not is_safe:
            # Return safe refusal message
            return f"I cannot provide this information as it may violate safety or policy guidelines. {reason if reason else 'Please consult a financial advisor for personalized advice.'}", flags
        
        # Redact PII if detected
        if 'pii_detected' in flags:
            answer = self.redact_pii(answer)
        
        return answer, flags

