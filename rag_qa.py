"""
RAG Q&A System - Generates answers from retrieved chunks
"""
import re
from datetime import datetime
from typing import List, Dict


class RAGQA:
    def __init__(self):
        self.advisory_keywords = [
            'should i', 'should you', 'recommend', 'advice', 'suggest',
            'best fund', 'which fund', 'buy or sell', 'invest in',
            'portfolio', 'allocation', 'strategy'
        ]
        self.educational_link = "https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionMutualFunds"
    
    def is_advisory_question(self, query: str) -> bool:
        """Check if query asks for investment advice"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.advisory_keywords)
    
    def format_answer(self, answer: str, source_url: str) -> str:
        """Format answer with citation and timestamp"""
        answer = answer.strip()
        
        # Ensure answer is ≤3 sentences
        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > 3:
            answer = '. '.join(sentences[:3]) + '.'
        
        # Add citation
        if source_url:
            answer += f" [Source]({source_url})"
        
        # Add timestamp
        today = datetime.now().strftime("%Y-%m-%d")
        answer += f" Last updated from sources: {today}."
        
        return answer
    
    def generate_answer(self, query: str, chunks: List[Dict]) -> Dict:
        """
        Generate answer from retrieved chunks
        
        Args:
            query: User query
            chunks: List of retrieved chunks with text and metadata
            
        Returns:
            Dict with 'answer', 'source_url', 'refused' (bool)
        """
        # Check if advisory question
        if self.is_advisory_question(query):
            return {
                'answer': (
                    "I provide factual information only, not investment advice. "
                    "For personalized investment guidance, please consult a registered financial advisor. "
                    f"Learn more about mutual funds: [AMFI Knowledge Center]({self.educational_link})"
                ),
                'source_url': self.educational_link,
                'refused': True
            }
        
        if not chunks:
            return {
                'answer': (
                    "I couldn't find relevant information in the available sources. "
                    "Please try rephrasing your question or ask about expense ratios, exit loads, "
                    "minimum SIP amounts, lock-in periods, riskometers, or benchmarks."
                ),
                'source_url': '',
                'refused': False
            }
        
        # Use top chunk for answer generation
        top_chunk = chunks[0]
        context = top_chunk['text']
        
        # Simple template-based answer (will be replaced with LLM later)
        answer = self._extract_answer_from_context(query, context)
        
        return {
            'answer': self.format_answer(answer, top_chunk['source_url']),
            'source_url': top_chunk['source_url'],
            'refused': False
        }
    
    def _extract_answer_from_context(self, query: str, context: str) -> str:
        """
        Extract relevant answer from context
        This is a simple implementation - will be enhanced with LLM
        """
        query_lower = query.lower()
        
        # Try to find direct answer in context
        sentences = re.split(r'[.!?]+', context)
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # Check if sentence contains query keywords
            query_words = set(query_lower.split())
            sentence_words = set(sentence_lower.split())
            overlap = len(query_words & sentence_words)
            
            if overlap >= 2 or any(word in sentence_lower for word in query_words if len(word) > 4):
                relevant_sentences.append(sentence.strip())
        
        if relevant_sentences:
            # Return first 2-3 relevant sentences
            answer = '. '.join(relevant_sentences[:3])
            if not answer.endswith('.'):
                answer += '.'
            return answer
        
        # Fallback: return first part of context
        return context[:200] + "..." if len(context) > 200 else context

