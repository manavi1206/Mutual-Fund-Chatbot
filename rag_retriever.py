"""
RAG Retriever - Handles vector search and chunk retrieval with hybrid search
Enhanced with hierarchical retrieval (Scheme → Section → Chunk)
"""
import json
import re
from pathlib import Path
from collections import Counter
from typing import List, Optional, Dict, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from query_classifier import QueryClassifier
from reranker import Reranker
from constants import SCHEME_TAG_MAP, FIELD_FILTER_THRESHOLD, SOURCE_AUTHORITY


class RAGRetriever:
    def __init__(self, embeddings_dir="embeddings"):
        self.embeddings_dir = Path(embeddings_dir)
        self.index_path = self.embeddings_dir / "faiss_index.bin"
        self.metadata_path = self.embeddings_dir / "faiss_metadata.json"
        
        print("Loading FAISS index...")
        self.index = faiss.read_index(str(self.index_path))
        
        print("Loading metadata...")
        with open(self.metadata_path) as f:
            self.metadata = json.load(f)
        
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        print("Loading source URL mapping...")
        with open("data_raw/sources_loaded.json") as f:
            sources = json.load(f)
        self.source_url_map = {s['source_id']: s['source_url'] for s in sources}
        
        # Initialize query classifier
        self.query_classifier = QueryClassifier()
        
        # Source authority scores (from constants)
        self.source_authority = SOURCE_AUTHORITY
        
        # Build index maps for fast hierarchical filtering
        self._build_index_maps()
        
        # Initialize re-ranker (optional, can be disabled if model not available)
        self.reranker = Reranker()
        self.use_reranker = self.reranker.model_loaded
        
        print(f"✓ Retriever ready: {self.index.ntotal} vectors indexed")
        if self.use_reranker:
            print("✓ Re-ranker enabled for improved retrieval quality")
    
    def _build_index_maps(self):
        """Build maps for hierarchical retrieval (scheme → field → indices)"""
        self.scheme_indices = {}  # scheme_tag -> [indices]
        self.field_indices = {}   # (scheme_tag, field) -> [indices]
        self.source_indices = {}  # source_id -> [indices]
        
        for idx, meta in enumerate(self.metadata):
            scheme_tag = meta.get('scheme_tag', '')
            field = meta.get('field', '')
            source_id = meta.get('source_id', '')
            
            # Scheme-level index
            if scheme_tag:
                if scheme_tag not in self.scheme_indices:
                    self.scheme_indices[scheme_tag] = []
                self.scheme_indices[scheme_tag].append(idx)
            
            # Field-level index (for metric queries)
            if scheme_tag and field:
                key = (scheme_tag, field)
                if key not in self.field_indices:
                    self.field_indices[key] = []
                self.field_indices[key].append(idx)
            
            # Source-level index
            if source_id:
                if source_id not in self.source_indices:
                    self.source_indices[source_id] = []
                self.source_indices[source_id].append(idx)
    
    def _identify_scheme_from_query(self, query: str) -> Optional[str]:
        """Identify scheme from query (hierarchical step 1)"""
        query_lower = query.lower()
        
        scheme_map = {
            'largecap': ['large cap', 'largecap', 'large-cap'],
            'flexicap': ['flexi cap', 'flexicap', 'flexi-cap'],
            'elss': ['elss', 'tax saver', 'tax-saver', 'equity linked saving'],
            'hybrid': ['hybrid', 'hybrid equity']
        }
        
        for scheme_tag, keywords in scheme_map.items():
            if any(kw in query_lower for kw in keywords):
                return scheme_tag
        
        return None
    
    def _identify_field_from_query(self, query: str) -> Optional[str]:
        """Identify field from query (hierarchical step 2)"""
        query_lower = query.lower()
        
        field_map = {
            'exit_load': ['exit load', 'redemption charge', 'exit charge'],
            'expense_ratio': ['expense ratio', 'ter', 'total expense ratio'],
            'minimum_sip': ['minimum sip', 'min sip', 'minimum investment'],
            'lock_in': ['lock-in', 'lock in', 'lockin'],
            'benchmark': ['benchmark', 'benchmark index'],
            'riskometer': ['riskometer', 'risk-o-meter', 'risk meter']
        }
        
        for field, keywords in field_map.items():
            if any(kw in query_lower for kw in keywords):
                return field
        
        return None
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate BM25-style keyword matching score"""
        text_lower = text.lower()
        score = 0.0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Count occurrences
            count = text_lower.count(keyword_lower)
            if count > 0:
                # BM25-like scoring: more occurrences = higher score, but with diminishing returns
                score += count * (1.0 / (1.0 + count * 0.5))
        
        return score
    
    def _get_source_authority_score(self, source_id: str) -> float:
        """Get authority score for a source"""
        source_lower = source_id.lower()
        for source_type, score in self.source_authority.items():
            if source_type in source_lower:
                return score
        return 0.5  # Default score
    
    def retrieve(self, query: str, top_k: int = 3, include_overview: bool = True, use_hierarchical: bool = True, use_reranking: bool = True):
        """
        Retrieve top-k most relevant chunks using hierarchical hybrid search
        
        Hierarchical Retrieval:
        1. Scheme-level: Filter to relevant scheme (largecap, flexicap, elss, hybrid)
        2. Section-level: Filter to relevant field (exit_load, expense_ratio, etc.) for metric queries
        3. Chunk-level: Vector + keyword search within filtered chunks
        
        Args:
            query: User query text
            top_k: Number of chunks to retrieve
            include_overview: If True, also includes relevant overview chunks for metric queries
            use_hierarchical: If True, uses hierarchical filtering (faster, more accurate)
            use_reranking: If True, uses re-ranking for improved relevance
            
        Returns:
            List of dicts with 'text', 'source_id', 'source_url', 'authority', 'similarity'
        """
        # Classify query
        query_type = self.query_classifier.classify(query)
        query_lower = query.lower()
        
        # Get expanded keywords for boosting (synonyms + type-specific)
        boost_keywords = self.query_classifier.get_expanded_keywords(query)
        
        # HIERARCHICAL STEP 1: Identify scheme
        scheme_tag = None
        candidate_indices = None
        
        if use_hierarchical:
            scheme_tag = self._identify_scheme_from_query(query)
            
            # Map to actual scheme tags used in metadata (from constants)
            actual_scheme_tag = SCHEME_TAG_MAP.get(scheme_tag, scheme_tag) if scheme_tag else None
            
            if actual_scheme_tag and actual_scheme_tag in self.scheme_indices:
                candidate_indices = set(self.scheme_indices[actual_scheme_tag])
            elif scheme_tag:
                # Scheme identified but not in index - might be "ALL" or missing, search all
                candidate_indices = set(range(len(self.metadata)))
            else:
                # No scheme identified, search all chunks
                candidate_indices = set(range(len(self.metadata)))
        
        # HIERARCHICAL STEP 2: Identify field (for metric queries)
        if use_hierarchical and query_type == 'metric' and actual_scheme_tag:
            field = self._identify_field_from_query(query)
            
            if field:
                # Use the actual scheme tag (LARGE_CAP format)
                field_key = (actual_scheme_tag, field)
                
                field_indices = None
                if field_key in self.field_indices:
                    field_indices = set(self.field_indices[field_key])
                
                if field_indices and len(field_indices) > 0:
                    # Only filter if we have enough chunks (threshold from constants)
                    if len(field_indices) >= FIELD_FILTER_THRESHOLD:
                        candidate_indices = candidate_indices & field_indices
                    # else: Too few field-specific chunks, use scheme-level only
                else:
                    # Field not found for this scheme, also check "ALL" scheme
                    all_field_key = ('ALL', field)
                    if all_field_key in self.field_indices:
                        all_field_indices = set(self.field_indices[all_field_key])
                        if len(all_field_indices) > 0:
                            # Add "ALL" chunks to candidate set
                            candidate_indices = candidate_indices | all_field_indices
        
        # Vector search
        query_vector = self.embedding_model.encode(
            [query], 
            normalize_embeddings=True
        ).astype('float32')
        
        # Adjust search breadth based on query type
        if query_type == 'entity':
            search_k = min(top_k * 5, 40)  # Entity queries need broader search
        elif query_type == 'list':
            search_k = min(top_k * 4, 35)
        elif query_type == 'metric':
            search_k = min(top_k * 3, 30)
        else:
            search_k = min(top_k * 3, 25)
        
        # If hierarchical filtering, search more broadly then filter
        if use_hierarchical and candidate_indices:
            # Search more chunks, then filter
            search_k = min(search_k * 2, len(self.metadata))
        
        distances, indices = self.index.search(query_vector, search_k)
        
        # Check if search returned results
        if distances.size == 0 or indices.size == 0 or len(distances[0]) == 0 or len(indices[0]) == 0:
            return []
        
        # Apply hierarchical filtering if enabled
        if use_hierarchical and candidate_indices and len(candidate_indices) < len(self.metadata):
            filtered_results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx in candidate_indices:
                    filtered_results.append((dist, idx))
            
            if filtered_results:
                # Re-sort filtered results
                filtered_results.sort(key=lambda x: x[0], reverse=True)
                distances = np.array([[d for d, _ in filtered_results[:search_k]]])
                indices = np.array([[i for _, i in filtered_results[:search_k]]])
            # else: Fallback - hierarchical filtering too strict, use all results from search
        
        seen_indices = set()
        seen_texts = set()  # Avoid duplicate text chunks
        
        # Hybrid scoring: vector similarity + keyword matching + source authority
        scored_results = []
        for dist, idx in zip(distances[0], indices[0]):
            meta = self.metadata[idx]
            text = meta['text']
            text_snippet = text[:100]  # Use first 100 chars as fingerprint
            
            # Skip if we've seen this exact text before (duplicate chunk)
            if text_snippet in seen_texts:
                continue
            
            # Vector similarity score (cosine distance, higher is better)
            vector_score = float(dist)
            
            # Keyword matching score (BM25-style)
            keyword_score = self._calculate_keyword_score(text, boost_keywords)
            
            # Source authority score
            source_score = self._get_source_authority_score(meta['source_id'])
            
            # Special boosts for query types
            type_boost = 0.0
            if query_type == 'entity':
                # Boost chunks with names, titles, "Fund Manager" mentions
                if re.search(r'\b(fund manager|manager|investment manager|name|tenure)\b', text, re.IGNORECASE):
                    type_boost += 0.2
                # Boost if contains person names (capitalized words that might be names)
                if re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', text):
                    type_boost += 0.15
            elif query_type == 'metric':
                # Boost chunks with numbers near metric keywords
                if re.search(r'\b(expense|ter|exit load|sip|minimum|lock-in)\b.*\d+|\d+.*\b(expense|ter|exit load|sip|minimum|lock-in)\b', text, re.IGNORECASE):
                    type_boost += 0.2
                # Boost overview sources for current metrics
                if 'overview' in meta['source_id']:
                    type_boost += 0.1
            elif query_type == 'list':
                # Boost chunks with structured data (numbers, lists, percentages)
                if re.search(r'\d+%|\d+\.\d+%|top\s+\d+', text, re.IGNORECASE):
                    type_boost += 0.15
                if 'portfolio' in text.lower() or 'holdings' in text.lower():
                    type_boost += 0.1
            
            # Combined relevance score
            # Weight: vector (0.5) + keywords (0.3) + source (0.15) + type boost (0.05)
            relevance_score = (
                vector_score * 0.5 +
                min(keyword_score, 2.0) * 0.15 +  # Cap keyword score
                source_score * 0.15 +
                type_boost * 0.2
            )
            
            scored_results.append({
                'text': text,
                'chunk_text': text,  # Also include as chunk_text for compatibility
                'source_id': meta['source_id'],
                'source_url': self.source_url_map.get(meta['source_id'], ''),
                'authority': meta.get('authority', ''),
                'scheme_tag': meta['scheme_tag'],
                'field': meta.get('field', ''),  # Include field for direct lookup
                'snippet_keyword': meta.get('snippet_keyword', ''),
                'source_type': meta.get('source_type', ''),
                'last_fetched_date': meta.get('last_fetched_date', ''),
                'similarity': vector_score,
                'relevance_score': relevance_score,
                'keyword_score': keyword_score,
                'index': idx
            })
            seen_texts.add(text_snippet)
            seen_indices.add(idx)
        
        # Sort by combined relevance score
        scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Take top_k results (or more if re-ranking will be applied)
        candidate_count = top_k * 2 if use_reranking and self.use_reranker else top_k
        results = []
        for result in scored_results[:candidate_count]:
            results.append({
                'text': result['text'],
                'chunk_text': result.get('chunk_text', result['text']),  # Include chunk_text
                'source_id': result['source_id'],
                'source_url': result['source_url'],
                'authority': result['authority'],
                'scheme_tag': result['scheme_tag'],
                'field': result.get('field', ''),  # Include field for direct lookup
                'source_type': result.get('source_type', ''),
                'last_fetched_date': result.get('last_fetched_date', ''),
                'snippet_keyword': result['snippet_keyword'],
                'similarity': result['similarity'],
                'relevance_score': result['relevance_score']
            })
        
        # For metric queries, also include overview chunks that might have the actual values
        if include_overview:
            query_lower = query.lower()
            is_metric_query = any(term in query_lower for term in ['expense ratio', 'ter', 'exit load', 'sip', 'lock-in'])
            
            if is_metric_query:
                # Find overview chunks for the fund mentioned in query
                fund_name = None
                if 'large cap' in query_lower:
                    fund_name = 'largecap'
                elif 'flexi cap' in query_lower or 'flexicap' in query_lower:
                    fund_name = 'flexicap'
                elif 'elss' in query_lower:
                    fund_name = 'elss'
                elif 'hybrid' in query_lower:
                    fund_name = 'hybrid'
                
                if fund_name:
                    # Search for overview chunks from this fund that contain the metric
                    overview_source = f'amc_{fund_name}_overview'
                    for idx, meta in enumerate(self.metadata):
                        if idx not in seen_indices and meta['source_id'] == overview_source:
                            chunk_text_lower = meta['text'].lower()
                            # Check if this chunk has the metric we're looking for
                            if 'expense' in query_lower or 'ter' in query_lower:
                                # Look for chunks with "Total Expense Ratio" or TER followed by a number
                                has_ter_pattern = ('total expense ratio' in chunk_text_lower or 'ter' in chunk_text_lower) and any(char.isdigit() for char in meta['text'])
                                # Or chunks that contain common expense ratio values (like 0.97, 1.5, etc.)
                                has_expense_value = 'expense' in chunk_text_lower and any(char.isdigit() for char in meta['text'][:300])
                                
                                if has_ter_pattern or has_expense_value:
                                    # Prefer chunks that have both TER/expense AND a decimal number (likely the actual ratio)
                                    has_decimal = bool(re.search(r'\d+\.\d+', meta['text'][:300]))
                                    if has_decimal or 'total expense ratio' in chunk_text_lower:
                                        results.append({
                                            'text': meta['text'],
                                            'chunk_text': meta['text'],
                                            'source_id': meta['source_id'],
                                            'source_url': self.source_url_map.get(meta['source_id'], ''),
                                            'authority': meta['authority'],
                                            'scheme_tag': meta['scheme_tag'],
                                            'field': meta.get('field', ''),
                                            'source_type': meta.get('source_type', ''),
                                            'last_fetched_date': meta.get('last_fetched_date', ''),
                                            'snippet_keyword': meta['snippet_keyword'],
                                            'similarity': 0.5  # Lower similarity since it's added manually
                                        })
                                        seen_indices.add(idx)
                                        break  # Just add one overview chunk
        
        # Apply re-ranking if enabled
        if use_reranking and self.use_reranker and len(results) > top_k:
            # Re-rank top candidates (2x top_k for better re-ranking)
            candidates_for_rerank = results[:min(len(results), top_k * 2)]
            reranked = self.reranker.rerank_with_metadata(
                query, 
                candidates_for_rerank,
                top_k=top_k,
                boost_authority=True,
                boost_recent=True
            )
            return reranked
        
        return results[:top_k]

