"""
Metrics Collector - Tracks system performance and quality
Enterprise-grade observability
"""
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import json
from pathlib import Path
from metrics_database import MetricsDatabase


class MetricsCollector:
    """Collects and tracks metrics for observability"""
    
    def __init__(self, metrics_dir: str = "metrics", use_database: bool = True):
        """
        Initialize metrics collector
        
        Args:
            metrics_dir: Directory to store metrics
            use_database: Whether to use database for persistence
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        
        # Initialize database if enabled
        self.use_database = use_database
        self.db = None
        if use_database:
            try:
                self.db = MetricsDatabase(db_path=str(self.metrics_dir / "metrics.db"))
            except Exception as e:
                print(f"⚠️  Database initialization failed: {e}, using in-memory only")
                self.use_database = False
        
        # In-memory metrics (for quick access)
        self.query_count = 0
        self.response_times = []
        self.retrieval_qualities = []
        self.answer_qualities = []
        self.user_satisfaction = []
        self.error_count = 0
        
        # Per-session metrics
        self.session_metrics = defaultdict(dict)
        
        # Query type distribution
        self.query_types = defaultdict(int)
        
        # Source usage
        self.source_usage = defaultdict(int)
    
    def record_query(self, query: str, query_type: str, response_time: float,
                    chunks_used: int, session_id: str = "default"):
        """
        Record a query execution
        
        Args:
            query: User query
            query_type: Type of query
            response_time: Time taken to respond (seconds)
            chunks_used: Number of chunks used
            session_id: Session identifier
        """
        self.query_count += 1
        self.response_times.append(response_time)
        self.query_types[query_type] += 1
        
        # Record session metrics
        if session_id not in self.session_metrics:
            self.session_metrics[session_id] = {
                'query_count': 0,
                'avg_response_time': 0,
                'total_time': 0
            }
        
        session_metric = self.session_metrics[session_id]
        session_metric['query_count'] += 1
        session_metric['total_time'] += response_time
        session_metric['avg_response_time'] = session_metric['total_time'] / session_metric['query_count']
        
        # Store in database if enabled
        if self.use_database and self.db:
            try:
                # Call with only required parameters (request_id is optional)
                self.db.record_query(query, query_type, response_time, chunks_used, session_id)
            except Exception as e:
                print(f"⚠️  Failed to record query in database: {e}")
    
    def record_retrieval_quality(self, query: str, chunks: List[Dict], 
                                relevant_count: int):
        """
        Record retrieval quality
        
        Args:
            query: User query
            chunks: Retrieved chunks
            relevant_count: Number of relevant chunks
        """
        if chunks:
            quality_score = relevant_count / len(chunks)
            self.retrieval_qualities.append(quality_score)
            
            # Track source usage
            for chunk in chunks:
                source_id = chunk.get('source_id', 'unknown')
                self.source_usage[source_id] += 1
    
    def record_answer_quality(self, query: str, answer: str, 
                              has_source: bool, confidence: Optional[str] = None):
        """
        Record answer quality metrics
        
        Args:
            query: User query
            answer: Generated answer
            has_source: Whether answer has source
            confidence: Confidence level
        """
        quality_score = 0.0
        
        # Base score
        if answer and len(answer) > 10:
            quality_score += 0.3
        
        # Source citation
        if has_source:
            quality_score += 0.3
        
        # Confidence boost
        if confidence:
            confidence_scores = {'HIGH': 0.4, 'MEDIUM': 0.2, 'LOW': 0.1}
            quality_score += confidence_scores.get(confidence, 0.0)
        
        self.answer_qualities.append(min(quality_score, 1.0))
        
        # Store in database if enabled
        if self.use_database and self.db:
            try:
                self.db.record_answer_quality(query, answer, has_source, confidence, min(quality_score, 1.0))
            except Exception as e:
                print(f"⚠️  Failed to record answer quality in database: {e}")
    
    def record_feedback(self, session_id: str, query: str, 
                       feedback_type: str, value: Optional[float] = None):
        """
        Record user feedback
        
        Args:
            session_id: Session identifier
            query: Original query
            feedback_type: 'thumbs_up', 'thumbs_down', 'rating', 'text'
            value: Optional numeric value (for rating)
        """
        if feedback_type == 'thumbs_up':
            self.user_satisfaction.append(1.0)
        elif feedback_type == 'thumbs_down':
            self.user_satisfaction.append(0.0)
        elif feedback_type == 'rating' and value is not None:
            # Normalize to 0-1
            normalized = value / 5.0 if value <= 5 else value / 10.0
            self.user_satisfaction.append(normalized)
        
        # Store in database if enabled
        if self.use_database and self.db:
            try:
                self.db.record_feedback(session_id, query, "", feedback_type, value, None)
            except Exception as e:
                print(f"⚠️  Failed to record feedback in database: {e}")
    
    def record_error(self, error_type: str, error_message: str, error_category: Optional[str] = None):
        """
        Record an error
        
        Args:
            error_type: Type of error
            error_message: Error message
            error_category: Optional error category
        """
        self.error_count += 1
        
        # Store in database if enabled
        if self.use_database and self.db:
            try:
                # Call with only required parameters (context is optional in db method)
                self.db.record_error(error_type, error_message, error_category or "unknown")
            except Exception as e:
                print(f"⚠️  Failed to record error in database: {e}")
    
    def get_metrics_summary(self) -> Dict:
        """
        Get summary of all metrics
        
        Returns:
            Dict with metric summaries
        """
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        avg_retrieval_quality = sum(self.retrieval_qualities) / len(self.retrieval_qualities) if self.retrieval_qualities else 0
        avg_answer_quality = sum(self.answer_qualities) / len(self.answer_qualities) if self.answer_qualities else 0
        avg_satisfaction = sum(self.user_satisfaction) / len(self.user_satisfaction) if self.user_satisfaction else 0
        
        return {
            'total_queries': self.query_count,
            'avg_response_time_seconds': round(avg_response_time, 3),
            'avg_retrieval_quality': round(avg_retrieval_quality, 3),
            'avg_answer_quality': round(avg_answer_quality, 3),
            'avg_user_satisfaction': round(avg_satisfaction, 3),
            'error_count': self.error_count,
            'query_type_distribution': dict(self.query_types),
            'top_sources': dict(sorted(self.source_usage.items(), key=lambda x: x[1], reverse=True)[:10]),
            'active_sessions': len(self.session_metrics)
        }
    
    def save_metrics(self, filename: Optional[str] = None):
        """
        Save metrics to file
        
        Args:
            filename: Optional filename (default: timestamped)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"
        
        filepath = self.metrics_dir / filename
        
        metrics_data = {
            'summary': self.get_metrics_summary(),
            'session_metrics': dict(self.session_metrics),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        return str(filepath)

