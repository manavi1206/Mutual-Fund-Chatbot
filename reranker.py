"""
Re-ranker for retrieval results
Uses cross-encoder model for better relevance scoring
Enterprise-grade retrieval quality
"""
import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import CrossEncoder


class Reranker:
    """Re-ranks retrieval results using cross-encoder model"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize re-ranker
        
        Args:
            model_name: Cross-encoder model name (default: fast and accurate)
        """
        print(f"Loading re-ranker model: {model_name}...")
        try:
            self.model = CrossEncoder(model_name, max_length=512)
            self.model_loaded = True
        except Exception as e:
            print(f"Warning: Could not load re-ranker model: {e}")
            print("Falling back to simple scoring...")
            self.model = None
            self.model_loaded = False
    
    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Re-rank chunks based on query relevance
        
        Args:
            query: User query
            chunks: List of chunk dicts with 'text' field
            top_k: Number of top chunks to return
            
        Returns:
            Re-ranked list of chunks
        """
        if not chunks:
            return []
        
        if not self.model_loaded:
            # Fallback: return chunks as-is (already scored by retriever)
            return chunks[:top_k]
        
        # Prepare query-chunk pairs
        pairs = [[query, chunk.get('text', '')] for chunk in chunks]
        
        # Get relevance scores
        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            print(f"Warning: Re-ranking failed: {e}")
            return chunks[:top_k]
        
        # Combine chunks with scores
        scored_chunks = list(zip(chunks, scores))
        
        # Sort by score (descending)
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Extract top-k chunks and add rerank_score
        reranked = []
        for chunk, score in scored_chunks[:top_k]:
            chunk['rerank_score'] = float(score)
            reranked.append(chunk)
        
        return reranked
    
    def rerank_with_metadata(self, query: str, chunks: List[Dict], 
                            top_k: int = 5, 
                            boost_authority: bool = True,
                            boost_recent: bool = True) -> List[Dict]:
        """
        Re-rank with metadata boosting (authority, recency, etc.)
        
        Args:
            query: User query
            chunks: List of chunk dicts
            top_k: Number of top chunks
            boost_authority: Whether to boost authoritative sources
            boost_recent: Whether to boost recent sources
            
        Returns:
            Re-ranked chunks with combined scores
        """
        if not chunks:
            return []
        
        # First, get semantic relevance scores
        reranked = self.rerank(query, chunks, top_k=len(chunks))
        
        if not boost_authority and not boost_recent:
            return reranked[:top_k]
        
        # Apply metadata boosts
        authority_map = {
            'sid_pdf': 1.2,
            'kim_pdf': 1.1,
            'factsheet_consolidated': 1.0,
            'scheme_overview': 0.9,
            'amfi': 1.1,
            'sebi': 1.15
        }
        
        for chunk in reranked:
            base_score = chunk.get('rerank_score', 0.0)
            
            # Authority boost
            if boost_authority:
                source_type = chunk.get('source_type', '')
                boost = authority_map.get(source_type, 1.0)
                base_score *= boost
            
            # Recency boost (if last_updated available)
            if boost_recent:
                last_updated = chunk.get('last_updated', '')
                if last_updated:
                    # Simple recency boost (can be enhanced)
                    # Assume more recent = slightly higher score
                    base_score *= 1.05
            
            chunk['final_score'] = base_score
        
        # Re-sort by final score
        reranked.sort(key=lambda x: x.get('final_score', 0.0), reverse=True)
        
        return reranked[:top_k]

