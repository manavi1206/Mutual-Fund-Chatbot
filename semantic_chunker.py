"""
Semantic Chunker - Advanced chunking using semantic similarity
Enterprise-grade chunking for better retrieval
"""
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticChunker:
    """Chunks text based on semantic similarity rather than fixed sizes"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", 
                 similarity_threshold: float = 0.7,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 600):
        """
        Initialize semantic chunker
        
        Args:
            model_name: Embedding model name
            similarity_threshold: Threshold for splitting chunks
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
        """
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Chunk text semantically
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of chunk dictionaries
        """
        # Split into sentences
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        
        # If text is small enough, return as single chunk
        if len(text) <= self.max_chunk_size:
            return [{
                'text': text,
                'metadata': metadata or {},
                'chunk_index': 0
            }]
        
        # Get embeddings for all sentences
        embeddings = self.model.encode(sentences)
        
        # Group sentences by similarity
        chunks = []
        current_chunk = []
        current_size = 0
        
        for i, sentence in enumerate(sentences):
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed max size, finalize current chunk
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'metadata': metadata or {},
                    'chunk_index': len(chunks)
                })
                current_chunk = [sentence]
                current_size = sentence_size
                continue
            
            # If current chunk is empty, add sentence
            if not current_chunk:
                current_chunk.append(sentence)
                current_size = sentence_size
                continue
            
            # Check similarity with previous sentence
            if i > 0:
                similarity = cosine_similarity(
                    embeddings[i-1:i],
                    embeddings[i:i+1]
                )[0][0]
                
                # If similarity is low, start new chunk
                if similarity < self.similarity_threshold and current_size >= self.min_chunk_size:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'metadata': metadata or {},
                        'chunk_index': len(chunks)
                    })
                    current_chunk = [sentence]
                    current_size = sentence_size
                    continue
            
            # Add to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'metadata': metadata or {},
                'chunk_index': len(chunks)
            })
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        # Simple sentence splitting (can be enhanced with NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

