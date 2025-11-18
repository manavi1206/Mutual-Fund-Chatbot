"""
Query Classification System - Categorizes user queries for specialized handling
"""
import re
from typing import Dict, List, Tuple


class QueryClassifier:
    """Classifies queries into types for specialized retrieval and answer generation"""
    
    def __init__(self):
        # Query type patterns
        self.patterns = {
            'entity': [
                r'\bwho\b', r'\bmanager\b', r'\bmanages\b', r'\bfund manager\b',
                r'\binvestment manager\b', r'\bportfolio manager\b', r'\bmanaged by\b'
            ],
            'metric': [
                r'\bexpense ratio\b', r'\bter\b', r'\btotal expense ratio\b',
                r'\bexit load\b', r'\bredemption charge\b', r'\bminimum sip\b',
                r'\bminimum investment\b', r'\bminimum amount\b', r'\block-in\b',
                r'\block in\b', r'\briskometer\b', r'\brisk-o-meter\b', r'\bbenchmark\b'
            ],
            'list': [
                r'\btop\s+\d+\b', r'\btop holdings\b', r'\bportfolio composition\b',
                r'\bholdings\b', r'\blist of\b', r'\bwhat are the\b.*\bholdings\b',
                r'\basset allocation\b', r'\bsector allocation\b'
            ],
            'how_to': [
                r'\bhow to\b', r'\bhow do i\b', r'\bhow can i\b', r'\bhow do you\b',
                r'\bdownload\b', r'\bredeem\b', r'\binvest\b', r'\bapply\b',
                r'\bwithdraw\b', r'\bswitch\b', r'\bget\b.*\bstatement\b', r'\bget\b.*\breport\b'
            ],
            'comparison': [
                r'\bcompare\b', r'\bdifference\b', r'\bversus\b', r'\bvs\b',
                r'\bwhich is better\b', r'\bwhich one\b.*\bbetter\b'
            ]
        }
        
        # Query expansion synonyms (comprehensive)
        self.synonyms = {
            'expense ratio': ['ter', 'total expense ratio', 'expense', 'expense ratio', 'ter%', 'total expense'],
            'fund manager': ['manager', 'investment manager', 'portfolio manager', 'fund manager', 'manages', 'managed by', 'fund manager name'],
            'top holdings': ['holdings', 'portfolio', 'top holdings', 'portfolio composition', 'asset allocation', 'top 10', 'top 5', 'investments'],
            'exit load': ['exit load', 'redemption charge', 'exit charge', 'redemption fee', 'exit fee'],
            'minimum sip': ['minimum sip', 'minimum investment', 'minimum amount', 'min sip', 'sip minimum', 'minimum subscription'],
            'lock-in': ['lock-in', 'lock in', 'lockin', 'lock-in period', 'lock period', 'elss lock-in'],
            'benchmark': ['benchmark', 'benchmark index', 'index', 'benchmarking'],
            'riskometer': ['riskometer', 'risk-o-meter', 'risk o meter', 'risk meter', 'risk level']
        }
        
        # Query reformulation patterns (for better matching)
        self.reformulations = {
            'who': ['fund manager', 'investment manager', 'manager name', 'who manages'],
            'what is': ['expense ratio', 'exit load', 'minimum sip', 'benchmark'],
            'how to': ['download', 'redeem', 'invest', 'apply', 'get statement']
        }
    
    def classify(self, query: str) -> str:
        """
        Classify query into type: entity, metric, list, how_to, comparison, or general
        
        Args:
            query: User query text
            
        Returns:
            Query type string
        """
        query_lower = query.lower()
        
        # Check each pattern type
        for query_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return query_type
        
        return 'general'
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand query with synonyms for better retrieval
        
        Args:
            query: Original query
            
        Returns:
            List of expanded query terms (keywords to search for)
        """
        query_lower = query.lower()
        expanded_terms = [query]
        
        # Add synonyms for key terms
        for key_term, synonyms in self.synonyms.items():
            if key_term in query_lower:
                for synonym in synonyms:
                    if synonym != key_term and synonym not in expanded_terms:
                        expanded_terms.append(synonym)
        
        # Also extract important keywords from query
        important_words = []
        for key_term in self.synonyms.keys():
            if key_term in query_lower:
                important_words.extend(self.synonyms[key_term])
        
        # Add fund names if present
        fund_names = ['large cap', 'flexi cap', 'flexicap', 'elss', 'hybrid', 'equity']
        for fund in fund_names:
            if fund in query_lower:
                important_words.append(fund)
        
        return list(set(expanded_terms + important_words))
    
    def get_expanded_keywords(self, query: str) -> List[str]:
        """
        Get expanded keywords for retrieval boosting
        
        Args:
            query: Original query
            
        Returns:
            List of keywords to boost in retrieval
        """
        query_lower = query.lower()
        keywords = []
        
        # Get synonyms for terms in query
        for key_term, synonyms in self.synonyms.items():
            if key_term in query_lower:
                keywords.extend(synonyms)
        
        # Add query type specific keywords
        query_type = self.classify(query)
        keywords.extend(self.get_keywords_for_type(query_type))
        
        return list(set(keywords))
    
    def get_keywords_for_type(self, query_type: str) -> List[str]:
        """
        Get important keywords to boost for a query type
        
        Args:
            query_type: Type of query
            
        Returns:
            List of keywords to boost
        """
        keyword_map = {
            'entity': ['fund manager', 'manager', 'investment manager', 'portfolio manager', 'equity analyst', 'name', 'tenure', 'manages', 'managed by', 'who manages', 'fund manager name'],
            'metric': ['expense ratio', 'ter', 'exit load', 'minimum', 'sip', 'lock-in', 'benchmark', 'riskometer'],
            'list': ['holdings', 'portfolio', 'top', 'composition', 'allocation', 'sector'],
            'how_to': ['how', 'download', 'redeem', 'invest', 'apply', 'steps', 'process'],
            'comparison': ['compare', 'difference', 'versus', 'vs', 'better'],
            'general': []
        }
        
        return keyword_map.get(query_type, [])

