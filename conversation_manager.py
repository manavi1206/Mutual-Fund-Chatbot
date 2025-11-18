"""
Conversation Manager - Handles session memory, context, and conversation history
Enterprise-grade conversation intelligence with persistent storage
"""
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import deque
import hashlib
from session_storage import SessionStorage


class ConversationManager:
    """Manages conversation state, history, and context"""
    
    def __init__(self, max_history: int = 20, max_summary_length: int = 500,
                 use_redis: bool = True, redis_host: str = "localhost", redis_port: int = 6379):
        """
        Initialize conversation manager
        
        Args:
            max_history: Maximum number of messages to keep in history
            max_summary_length: Maximum length of conversation summary
            use_redis: Whether to use Redis for persistent storage
            redis_host: Redis host
            redis_port: Redis port
        """
        self.max_history = max_history
        self.max_summary_length = max_summary_length
        
        # Initialize persistent session storage
        self.storage = SessionStorage(use_redis=use_redis, redis_host=redis_host, redis_port=redis_port)
        
        # Session storage: session_id -> conversation data (in-memory cache)
        self.sessions: Dict[str, Dict] = {}
        
        # Conversation history: deque for efficient append/pop
        self.conversations: Dict[str, deque] = {}
        
        # Working memory: goals, constraints, decisions
        self.working_memory: Dict[str, Dict] = {}
        
        # Load existing sessions from storage
        self._load_persisted_sessions()
    
    def _load_persisted_sessions(self):
        """Load persisted sessions from storage"""
        # This is a simple implementation - in production, you'd load all active sessions
        # For now, we load on-demand in get_or_create_session
        pass
    
    def get_or_create_session(self, session_id: str) -> Dict:
        """Get or create a session"""
        if session_id not in self.sessions:
            # Try to load from persistent storage
            persisted = self.storage.load_session(session_id)
            if persisted:
                self.sessions[session_id] = persisted.get('session_data', {})
                # Restore conversation history
                if 'conversations' in persisted:
                    self.conversations[session_id] = deque(persisted['conversations'], maxlen=self.max_history)
                else:
                    self.conversations[session_id] = deque(maxlen=self.max_history)
                # Restore working memory
                if 'working_memory' in persisted:
                    self.working_memory[session_id] = persisted['working_memory']
                else:
                    self.working_memory[session_id] = {
                        'goals': [],
                        'constraints': [],
                        'decisions': [],
                        'context_entities': {},
                        'pending_clarification': None,
                        'original_query': None
                    }
            else:
                # Create new session
                self.sessions[session_id] = {
                    'created_at': datetime.now().isoformat(),
                    'last_activity': datetime.now().isoformat(),
                    'message_count': 0,
                    'topics_discussed': [],
                    'user_preferences': {}
                }
                self.conversations[session_id] = deque(maxlen=self.max_history)
                self.working_memory[session_id] = {
                    'goals': [],
                    'constraints': [],
                    'decisions': [],
                    'context_entities': {},
                    'pending_clarification': None,  # Track if waiting for clarification response
                    'original_query': None  # Original query that needed clarification
                }
        
        return self.sessions[session_id]
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history"""
        self.get_or_create_session(session_id)
        
        message = {
            'role': role,  # 'user' or 'assistant'
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.conversations[session_id].append(message)
        self.sessions[session_id]['last_activity'] = datetime.now().isoformat()
        self.sessions[session_id]['message_count'] += 1
        
        # Persist session after adding message
        self._persist_session(session_id)
    
    def get_conversation_history(self, session_id: str, last_n: Optional[int] = None) -> List[Dict]:
        """Get conversation history"""
        if session_id not in self.conversations:
            return []
        
        history = list(self.conversations[session_id])
        if last_n:
            return history[-last_n:]
        return history
    
    def get_conversation_summary(self, session_id: str) -> str:
        """Generate a summary of the conversation so far"""
        history = self.get_conversation_history(session_id)
        if not history:
            return ""
        
        # Extract key information
        user_queries = [msg['content'] for msg in history if msg['role'] == 'user']
        assistant_answers = [msg['content'] for msg in history if msg['role'] == 'assistant']
        
        # Simple summary (can be enhanced with LLM)
        summary_parts = []
        
        if user_queries:
            summary_parts.append(f"User has asked {len(user_queries)} questions.")
            if len(user_queries) > 0:
                summary_parts.append(f"Recent topics: {', '.join(user_queries[-3:])}")
        
        # Extract entities from working memory
        entities = self.working_memory.get(session_id, {}).get('context_entities', {})
        if entities:
            entity_str = ", ".join([f"{k}: {v}" for k, v in entities.items()])
            summary_parts.append(f"Context: {entity_str}")
        
        summary = ". ".join(summary_parts)
        
        # Truncate if too long
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length] + "..."
        
        return summary
    
    def update_working_memory(self, session_id: str, entity: str, value: str):
        """Update working memory with context entity"""
        self.get_or_create_session(session_id)
        self.working_memory[session_id]['context_entities'][entity] = value
    
    def get_context_entities(self, session_id: str) -> Dict[str, str]:
        """Get current context entities"""
        if session_id not in self.working_memory:
            return {}
        return self.working_memory[session_id].get('context_entities', {})
    
    def set_pending_clarification(self, session_id: str, original_query: str, clarification_type: str = 'fund_selection'):
        """Mark that we're waiting for a clarification response"""
        self.get_or_create_session(session_id)
        self.working_memory[session_id]['pending_clarification'] = clarification_type
        self.working_memory[session_id]['original_query'] = original_query
    
    def get_pending_clarification(self, session_id: str) -> Optional[Dict]:
        """Get pending clarification state"""
        if session_id not in self.working_memory:
            return None
        if self.working_memory[session_id].get('pending_clarification'):
            return {
                'type': self.working_memory[session_id]['pending_clarification'],
                'original_query': self.working_memory[session_id]['original_query']
            }
        return None
    
    def clear_pending_clarification(self, session_id: str):
        """Clear pending clarification state"""
        if session_id in self.working_memory:
            self.working_memory[session_id]['pending_clarification'] = None
            self.working_memory[session_id]['original_query'] = None
    
    def add_goal(self, session_id: str, goal: str):
        """Add a goal to working memory"""
        self.get_or_create_session(session_id)
        if goal not in self.working_memory[session_id]['goals']:
            self.working_memory[session_id]['goals'].append(goal)
    
    def add_constraint(self, session_id: str, constraint: str):
        """Add a constraint to working memory"""
        self.get_or_create_session(session_id)
        if constraint not in self.working_memory[session_id]['constraints']:
            self.working_memory[session_id]['constraints'].append(constraint)
    
    def get_context_for_query(self, session_id: str, current_query: str) -> Dict:
        """
        Get enriched context for a query based on conversation history
        
        Returns:
            Dict with:
            - history: List of recent messages
            - summary: Conversation summary
            - entities: Context entities
            - expanded_query: Query expanded with context
        """
        self.get_or_create_session(session_id)
        
        # Get recent history (last 5 messages)
        history = self.get_conversation_history(session_id, last_n=5)
        
        # Get summary
        summary = self.get_conversation_summary(session_id)
        
        # Get context entities
        entities = self.get_context_entities(session_id)
        
        # Expand query with context
        expanded_query = self._expand_query_with_context(current_query, history, entities, session_id)
        
        return {
            'history': history,
            'summary': summary,
            'entities': entities,
            'expanded_query': expanded_query
        }
    
    def _expand_query_with_context(self, query: str, history: List[Dict], entities: Dict[str, str], session_id: str) -> str:
        """Expand query using conversation context"""
        # If query is a follow-up (e.g., "what about exit load?"), add context
        query_lower = query.lower()
        
        # FIRST: Check if this is a response to a clarification question
        pending_clarification = self.get_pending_clarification(session_id)
        if pending_clarification:
            original_query = pending_clarification['original_query']
            # Check if current query contains a fund name
            fund_keywords = ['large cap', 'largecap', 'flexi cap', 'flexicap', 'elss', 'taxsaver', 'tax saver', 'hybrid']
            if any(keyword in query_lower for keyword in fund_keywords):
                # User is providing the fund name - combine with original query
                combined_query = f"{original_query} {query}"
                self.clear_pending_clarification(session_id)
                return combined_query
        
        # Check for follow-up patterns
        follow_up_patterns = [
            'what about', 'and', 'also', 'how about', 'tell me more',
            'what is', 'what are', 'who is', 'when is', 'where is'
        ]
        
        is_follow_up = any(pattern in query_lower for pattern in follow_up_patterns)
        
        # If it's a follow-up and we have context, expand
        if is_follow_up and entities:
            # Add context from entities
            context_parts = []
            if 'scheme' in entities:
                context_parts.append(f"for {entities['scheme']}")
            if 'topic' in entities:
                context_parts.append(f"regarding {entities['topic']}")
            
            if context_parts:
                expanded = f"{query} {' '.join(context_parts)}"
                return expanded
        
        # If query mentions a scheme, update context
        scheme_keywords = ['large cap', 'largecap', 'flexi cap', 'flexicap', 'elss', 'hybrid', 'taxsaver', 'tax saver']
        for keyword in scheme_keywords:
            if keyword in query_lower:
                # Extract scheme name
                scheme_map = {
                    'large cap': 'HDFC Large Cap Fund',
                    'largecap': 'HDFC Large Cap Fund',
                    'flexi cap': 'HDFC Flexi Cap Fund',
                    'flexicap': 'HDFC Flexi Cap Fund',
                    'elss': 'HDFC TaxSaver (ELSS)',
                    'taxsaver': 'HDFC TaxSaver (ELSS)',
                    'tax saver': 'HDFC TaxSaver (ELSS)',
                    'hybrid': 'HDFC Hybrid Equity Fund'
                }
                scheme_name = scheme_map.get(keyword)
                if scheme_name and session_id:
                    self.update_working_memory(session_id, 'scheme', scheme_name)
                    self.update_working_memory(session_id, 'last_fund', scheme_name)
                break
        
        # GENERAL CONTEXT APPLICATION: If user asks ANY question without specifying fund,
        # and we have a last_fund in context, intelligently add it
        if session_id:
            last_fund = self.get_context_entities(session_id).get('last_fund')
            if last_fund:
                # Check if current query doesn't mention any fund
                if not any(fund_kw in query_lower for fund_kw in scheme_keywords):
                    # Check if this is a question about fund attributes (not general questions)
                    # Heuristic: If query is a question word or short phrase, likely asking about the fund
                    question_indicators = [
                        query_lower.startswith(('what', 'how', 'who', 'when', 'where', 'which', 'is', 'are', 'does', 'can', 'tell', 'show')),
                        len(query_lower.split()) <= 5,  # Short queries likely about fund
                        '?' in query,  # Explicit question
                    ]
                    # If it looks like a fund-related question, add context
                    if any(question_indicators):
                        return f"{query} for {last_fund}"
        
        return query
    
    def _persist_session(self, session_id: str):
        """Persist session to storage"""
        if session_id in self.sessions:
            session_data = {
                'session_data': self.sessions[session_id],
                'conversations': list(self.conversations.get(session_id, [])),
                'working_memory': self.working_memory.get(session_id, {})
            }
            self.storage.save_session(session_id, session_data, ttl_seconds=3600)
    
    def clear_session(self, session_id: str):
        """Clear a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.conversations:
            del self.conversations[session_id]
        if session_id in self.working_memory:
            del self.working_memory[session_id]
        
        # Delete from persistent storage
        self.storage.delete_session(session_id)
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        if session_id not in self.sessions:
            return {}
        
        return {
            'message_count': self.sessions[session_id]['message_count'],
            'created_at': self.sessions[session_id]['created_at'],
            'last_activity': self.sessions[session_id]['last_activity'],
            'topics_discussed': self.sessions[session_id]['topics_discussed'],
            'context_entities': self.working_memory.get(session_id, {}).get('context_entities', {})
        }

