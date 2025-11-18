"""
Clarification Handler - Detects ambiguous queries and asks clarifying questions
Enterprise-grade conversation intelligence
"""
import re
from typing import List, Dict, Optional, Tuple


class ClarificationHandler:
    """Handles clarification questions for ambiguous queries"""
    
    def __init__(self):
        """Initialize clarification handler"""
        # Patterns that indicate ambiguity
        self.ambiguous_patterns = [
            r'\b(it|this|that|they|them)\b',  # Pronouns without clear referent
            r'\b(which|what)\s+(fund|scheme)\b',  # Vague "which fund"
            r'\b(compare|difference)\b',  # Comparison without clear subjects
            r'\b(all|every|each)\s+(fund|scheme)\b',  # "all funds" - which ones?
        ]
        
        # Context-dependent patterns (need conversation history)
        self.context_dependent_patterns = [
            r'\b(also|and|what about|how about)\b',  # Follow-ups
            r'\b(more|details|information)\b',  # Vague requests
        ]
        
        # Metric/attribute keywords that require a fund to be specified
        self.metric_keywords = [
            'minimum sip', 'min sip', 'sip minimum',
            'minimum investment', 'min investment', 'minimum amount',
            'expense ratio', 'ter', 'total expense ratio',
            'exit load', 'redemption charge', 'exit charge',
            'lock-in', 'lock in', 'lockin period',
            'benchmark', 'benchmark index',
            'riskometer', 'risk-o-meter', 'risk level',
            'returns', 'performance', 'nav',
            'fund manager', 'manager', 'who manages',
            'aum', 'assets under management',
            'holdings', 'top holdings', 'portfolio'
        ]
        
        # Fund name patterns to check if a fund is mentioned
        self.fund_patterns = [
            r'large\s*cap', r'largecap',
            r'flexi\s*cap', r'flexicap',
            r'elss', r'taxsaver', r'tax\s*saver',
            r'hybrid', r'hybrid equity'
        ]
    
    def needs_clarification(self, query: str, conversation_context: Optional[Dict] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if query needs clarification
        
        Returns:
            (needs_clarification: bool, clarification_question: Optional[str])
        """
        query_lower = query.lower()
        
        # FIRST CHECK: Metric query without fund name (most common case)
        # Check if query asks about a metric but doesn't specify which fund
        fund_mentioned = self._has_fund_name(query_lower)
        metric_mentioned = self._has_metric(query_lower)
        
        if metric_mentioned and not fund_mentioned:
            # Determine which metric is being asked about
            clarification = self._generate_metric_clarification(query_lower)
            if clarification:
                return True, clarification
        
        # Check for ambiguous patterns
        for pattern in self.ambiguous_patterns:
            if re.search(pattern, query_lower):
                clarification = self._generate_clarification(query, pattern)
                if clarification:
                    return True, clarification
        
        # Check for context-dependent patterns
        if conversation_context:
            history = conversation_context.get('history', [])
            entities = conversation_context.get('entities', {})
            
            # If query uses pronouns but no clear context
            if re.search(r'\b(it|this|that)\b', query_lower) and not entities:
                return True, (
                    "I'd be happy to help! Could you clarify which fund you're asking about?\n\n"
                    "1. **HDFC Large Cap Fund**\n"
                    "2. **HDFC Flexi Cap Fund**\n"
                    "3. **HDFC TaxSaver (ELSS)**\n"
                    "4. **HDFC Hybrid Equity Fund**"
                )
            
            # If query says "which fund" without context
            if re.search(r'which\s+(fund|scheme)', query_lower) and 'scheme' not in entities:
                return True, (
                    "Which fund would you like to know about?\n\n"
                    "1. **HDFC Large Cap Fund**\n"
                    "2. **HDFC Flexi Cap Fund**\n"
                    "3. **HDFC TaxSaver (ELSS)**\n"
                    "4. **HDFC Hybrid Equity Fund**"
                )
            
            # If comparison without clear subjects
            if re.search(r'\b(compare|difference|vs|versus)\b', query_lower):
                schemes_mentioned = self._extract_schemes(query)
                if len(schemes_mentioned) < 2:
                    return True, (
                        "I can help you compare funds! Which two funds would you like to compare?\n\n"
                        "**Example:** 'Compare HDFC Large Cap and HDFC Flexi Cap'\n\n"
                        "**Available funds:**\n"
                        "1. **HDFC Large Cap Fund**\n"
                        "2. **HDFC Flexi Cap Fund**\n"
                        "3. **HDFC TaxSaver (ELSS)**\n"
                        "4. **HDFC Hybrid Equity Fund**"
                    )
        
        return False, None
    
    def _generate_clarification(self, query: str, pattern: str) -> Optional[str]:
        """Generate a clarification question based on the ambiguous pattern"""
        query_lower = query.lower()
        
        if 'which' in query_lower or 'what' in query_lower:
            if 'fund' in query_lower or 'scheme' in query_lower:
                return (
                    "Which fund are you asking about?\n\n"
                    "1. **HDFC Large Cap Fund**\n"
                    "2. **HDFC Flexi Cap Fund**\n"
                    "3. **HDFC TaxSaver (ELSS)**\n"
                    "4. **HDFC Hybrid Equity Fund**"
                )
        
        if 'compare' in query_lower or 'difference' in query_lower:
            return (
                "I can help you compare funds! Which metrics or funds would you like to compare?\n\n"
                "**Example:** 'Compare exit loads of HDFC Large Cap and HDFC Flexi Cap'\n\n"
                "**Available funds:**\n"
                "1. **HDFC Large Cap Fund**\n"
                "2. **HDFC Flexi Cap Fund**\n"
                "3. **HDFC TaxSaver (ELSS)**\n"
                "4. **HDFC Hybrid Equity Fund**"
            )
        
        if 'all' in query_lower or 'every' in query_lower:
            if 'fund' in query_lower:
                return (
                    "I have information about 4 HDFC funds. What would you like to know about them?\n\n"
                    "1. **HDFC Large Cap Fund**\n"
                    "2. **HDFC Flexi Cap Fund**\n"
                    "3. **HDFC TaxSaver (ELSS)**\n"
                    "4. **HDFC Hybrid Equity Fund**"
                )
        
        return None
    
    def _extract_schemes(self, query: str) -> List[str]:
        """Extract scheme names mentioned in query"""
        schemes = []
        scheme_keywords = {
            'large cap': 'HDFC Large Cap Fund',
            'flexi cap': 'HDFC Flexi Cap Fund',
            'elss': 'HDFC TaxSaver (ELSS)',
            'taxsaver': 'HDFC TaxSaver (ELSS)',
            'hybrid': 'HDFC Hybrid Equity Fund'
        }
        
        query_lower = query.lower()
        for keyword, scheme_name in scheme_keywords.items():
            if keyword in query_lower:
                schemes.append(scheme_name)
        
        return schemes
    
    def suggest_followups(self, query: str, answer: str, chunks: List[Dict]) -> List[str]:
        """
        Suggest follow-up questions based on the current query and answer
        
        Returns:
            List of suggested follow-up questions
        """
        suggestions = []
        query_lower = query.lower()
        
        # If query is about a metric, suggest related metrics
        if any(metric in query_lower for metric in ['exit load', 'expense ratio', 'ter', 'minimum sip']):
            if 'exit load' in query_lower:
                suggestions.append("What is the expense ratio?")
                suggestions.append("What is the minimum SIP amount?")
            elif 'expense ratio' in query_lower or 'ter' in query_lower:
                suggestions.append("What is the exit load?")
                suggestions.append("What is the benchmark?")
            elif 'minimum sip' in query_lower:
                suggestions.append("What is the minimum lumpsum amount?")
                suggestions.append("What is the exit load?")
        
        # If query is about a scheme, suggest scheme details
        if any(scheme in query_lower for scheme in ['large cap', 'flexi cap', 'elss', 'hybrid']):
            suggestions.append("What is the expense ratio?")
            suggestions.append("What is the exit load?")
            suggestions.append("What is the benchmark?")
        
        # If query is about fund manager, suggest other schemes
        if 'fund manager' in query_lower or 'manager' in query_lower:
            suggestions.append("Who manages the other HDFC funds?")
            suggestions.append("What is the investment strategy?")
        
        # Limit to 3 suggestions
        return suggestions[:3]
    
    def _has_fund_name(self, query_lower: str) -> bool:
        """Check if a fund name is mentioned in the query"""
        for pattern in self.fund_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True
        return False
    
    def _has_metric(self, query_lower: str) -> bool:
        """Check if a metric keyword is mentioned in the query"""
        for metric in self.metric_keywords:
            if metric in query_lower:
                return True
        return False
    
    def _generate_metric_clarification(self, query_lower: str) -> Optional[str]:
        """Generate a clarification question for metric queries without fund specification"""
        # Determine which metric is being asked about
        metric_name = None
        
        if 'minimum sip' in query_lower or 'min sip' in query_lower or 'sip minimum' in query_lower:
            metric_name = "minimum SIP"
        elif 'minimum investment' in query_lower or 'min investment' in query_lower or 'minimum amount' in query_lower:
            metric_name = "minimum investment"
        elif 'expense ratio' in query_lower or 'ter' in query_lower:
            metric_name = "expense ratio"
        elif 'exit load' in query_lower or 'redemption charge' in query_lower:
            metric_name = "exit load"
        elif 'lock-in' in query_lower or 'lock in' in query_lower or 'lockin' in query_lower:
            metric_name = "lock-in period"
        elif 'benchmark' in query_lower:
            metric_name = "benchmark"
        elif 'riskometer' in query_lower or 'risk-o-meter' in query_lower or 'risk level' in query_lower:
            metric_name = "riskometer level"
        elif 'returns' in query_lower or 'performance' in query_lower:
            metric_name = "returns/performance"
        elif 'fund manager' in query_lower or 'manager' in query_lower or 'who manages' in query_lower:
            metric_name = "fund manager"
        elif 'aum' in query_lower or 'assets under management' in query_lower:
            metric_name = "AUM"
        elif 'holdings' in query_lower or 'top holdings' in query_lower or 'portfolio' in query_lower:
            metric_name = "holdings"
        elif 'nav' in query_lower:
            metric_name = "NAV"
        
        if metric_name:
            # Use proper markdown formatting with clear line breaks (GPT/Gemini style)
            return (
                f"I'd be happy to help you with the **{metric_name}**! "
                f"Which HDFC fund are you asking about?\n\n"
                f"1. **HDFC Large Cap Fund**\n"
                f"2. **HDFC Flexi Cap Fund**\n"
                f"3. **HDFC TaxSaver (ELSS)**\n"
                f"4. **HDFC Hybrid Equity Fund**"
            )
        
        # Generic clarification if we couldn't identify the specific metric
        return (
            "I'd be happy to help! Which HDFC fund would you like to know about?\n\n"
            "1. **HDFC Large Cap Fund**\n"
            "2. **HDFC Flexi Cap Fund**\n"
            "3. **HDFC TaxSaver (ELSS)**\n"
            "4. **HDFC Hybrid Equity Fund**"
        )

