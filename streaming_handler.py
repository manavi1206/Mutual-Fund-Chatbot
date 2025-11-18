"""
Streaming Handler - Progressive responses for better UX
Enterprise-grade UX excellence
"""
from typing import Iterator, Dict, Optional, List
import time


class StreamingHandler:
    """Handles streaming responses for progressive UX"""
    
    def __init__(self):
        """Initialize streaming handler"""
        self.chunk_size = 50  # Characters per chunk
        self.delay = 0.05  # Delay between chunks (seconds)
    
    def stream_answer(self, answer: str, metadata: Optional[Dict] = None) -> Iterator[Dict]:
        """
        Stream answer in chunks for progressive display
        
        Args:
            answer: Full answer text
            metadata: Optional metadata (source_url, confidence, etc.)
            
        Yields:
            Dict with 'chunk', 'is_complete', 'metadata'
        """
        # Split answer into chunks
        chunks = self._split_into_chunks(answer)
        
        for i, chunk in enumerate(chunks):
            is_complete = (i == len(chunks) - 1)
            
            yield {
                'chunk': chunk,
                'is_complete': is_complete,
                'progress': (i + 1) / len(chunks),
                'metadata': metadata if is_complete else None
            }
            
            # Small delay for progressive effect
            if not is_complete:
                time.sleep(self.delay)
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into chunks, respecting word boundaries"""
        chunks = []
        words = text.split(' ')
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def stream_with_metadata(self, answer: str, source_url: Optional[str] = None,
                            confidence: Optional[str] = None,
                            suggested_followups: Optional[List[str]] = None) -> Iterator[Dict]:
        """
        Stream answer with metadata
        
        Args:
            answer: Full answer text
            source_url: Source URL
            confidence: Confidence level
            suggested_followups: Suggested follow-up questions
            
        Yields:
            Dict with streaming chunks and final metadata
        """
        metadata = {
            'source_url': source_url,
            'confidence': confidence,
            'suggested_followups': suggested_followups
        }
        
        for chunk_data in self.stream_answer(answer, metadata):
            yield chunk_data

