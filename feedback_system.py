"""
Feedback System - Collects and processes user feedback
Enterprise-grade observability
"""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json


class FeedbackSystem:
    """Manages user feedback collection and processing"""
    
    def __init__(self, feedback_dir: str = "feedback"):
        """
        Initialize feedback system
        
        Args:
            feedback_dir: Directory to store feedback
        """
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(exist_ok=True)
        
        # In-memory feedback storage
        self.feedback_store = []
    
    def record_feedback(self, session_id: str, query: str, answer: str,
                       feedback_type: str, value: Optional[any] = None,
                       text_feedback: Optional[str] = None) -> str:
        """
        Record user feedback
        
        Args:
            session_id: Session identifier
            query: Original query
            answer: Provided answer
            feedback_type: 'thumbs_up', 'thumbs_down', 'rating', 'correction'
            value: Optional numeric value (for rating)
            text_feedback: Optional text feedback
            
        Returns:
            Feedback ID
        """
        feedback_id = f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        feedback = {
            'id': feedback_id,
            'session_id': session_id,
            'query': query,
            'answer': answer,
            'feedback_type': feedback_type,
            'value': value,
            'text_feedback': text_feedback,
            'timestamp': datetime.now().isoformat()
        }
        
        self.feedback_store.append(feedback)
        
        # Save to file
        self._save_feedback(feedback)
        
        return feedback_id
    
    def _save_feedback(self, feedback: Dict):
        """Save feedback to file"""
        filename = f"feedback_{datetime.now().strftime('%Y%m%d')}.jsonl"
        filepath = self.feedback_dir / filename
        
        # Append to JSONL file
        with open(filepath, 'a') as f:
            f.write(json.dumps(feedback) + '\n')
    
    def get_feedback_summary(self, days: int = 7) -> Dict:
        """
        Get feedback summary for last N days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Summary dict
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_feedback = [
            f for f in self.feedback_store
            if datetime.fromisoformat(f['timestamp']) >= cutoff
        ]
        
        thumbs_up = sum(1 for f in recent_feedback if f['feedback_type'] == 'thumbs_up')
        thumbs_down = sum(1 for f in recent_feedback if f['feedback_type'] == 'thumbs_down')
        ratings = [f['value'] for f in recent_feedback if f['feedback_type'] == 'rating' and f['value']]
        corrections = [f for f in recent_feedback if f['feedback_type'] == 'correction']
        
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        return {
            'total_feedback': len(recent_feedback),
            'thumbs_up': thumbs_up,
            'thumbs_down': thumbs_down,
            'thumbs_up_ratio': thumbs_up / (thumbs_up + thumbs_down) if (thumbs_up + thumbs_down) > 0 else 0,
            'avg_rating': round(avg_rating, 2) if avg_rating else None,
            'corrections': len(corrections),
            'text_feedback_count': sum(1 for f in recent_feedback if f.get('text_feedback'))
        }
    
    def get_corrections(self) -> List[Dict]:
        """Get all correction feedback"""
        return [f for f in self.feedback_store if f['feedback_type'] == 'correction']
    
    def get_negative_feedback(self) -> List[Dict]:
        """Get all negative feedback for review"""
        return [
            f for f in self.feedback_store
            if f['feedback_type'] in ['thumbs_down', 'correction']
        ]

