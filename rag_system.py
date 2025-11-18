"""
Main RAG System - Combines retrieval and Q&A
"""
from rag_retriever import RAGRetriever
from rag_qa import RAGQA
from rag_qa_llm import RAGQALLM
from conversation_manager import ConversationManager
from safety_filters import SafetyFilters
from access_control import AccessControl, UserRole
# Removed unused imports:
# from resilience_handler import ResilienceHandler
# from tenant_manager import TenantManager, TenantIsolation
# from proactive_assistant import ProactiveAssistant
from typing import Optional
import os

# Load config from environment variables only (security best practice)
# Do NOT load from config.py file to avoid exposing API keys
DEFAULT_USE_LLM = os.getenv("USE_LLM", "true").lower() == "true" if os.getenv("USE_LLM") else None
DEFAULT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# Validate API keys are set
if DEFAULT_USE_LLM:
    if DEFAULT_LLM_PROVIDER == "gemini" and not os.getenv("GEMINI_API_KEY"):
        import logging
        logging.getLogger(__name__).warning("GEMINI_API_KEY not set, LLM features disabled")
        DEFAULT_USE_LLM = False
    elif DEFAULT_LLM_PROVIDER == "openai" and not os.getenv("OPENAI_API_KEY"):
        import logging
        logging.getLogger(__name__).warning("OPENAI_API_KEY not set, LLM features disabled")
        DEFAULT_USE_LLM = False


class RAGSystem:
    def __init__(self, use_llm: bool = None, llm_provider: str = None, api_key: str = None):
        """
        Initialize RAG System
        
        Args:
            use_llm: Whether to use LLM for answer generation. If None, auto-detects based on API keys
            llm_provider: "openai", "gemini", or "local". If None, uses config or auto-detects
            api_key: Optional API key (if not provided, reads from environment)
        """
        self.retriever = RAGRetriever()
        
        # Use defaults from config if available
        if llm_provider is None:
            llm_provider = DEFAULT_LLM_PROVIDER
        if use_llm is None:
            use_llm = DEFAULT_USE_LLM
        
        # Auto-detect LLM availability if use_llm is None
        if use_llm is None:
            openai_key = api_key if llm_provider == "openai" else os.getenv("OPENAI_API_KEY")
            gemini_key = api_key if llm_provider == "gemini" else os.getenv("GEMINI_API_KEY")
            use_llm = bool(openai_key or gemini_key)
            if use_llm and not api_key:
                # Auto-select provider based on available keys
                if openai_key:
                    llm_provider = "openai"
                elif gemini_key:
                    llm_provider = "gemini"
        
        if use_llm:
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY") if llm_provider == "openai" else os.getenv("GEMINI_API_KEY")
            self.qa = RAGQALLM(llm_provider=llm_provider, api_key=api_key)
        else:
            self.qa = RAGQA()
        
        # Initialize conversation manager for session memory
        self.conversation_manager = ConversationManager()
        
        # Initialize safety filters
        self.safety_filters = SafetyFilters()
        
        # Initialize access control
        self.access_control = AccessControl()
        
        # Note: ResilienceHandler, TenantManager, and ProactiveAssistant removed (simplified codebase)
    
    def query(self, user_query: str, top_k: int = 3, chat_history: list = None, 
              session_id: str = "default", response_style: str = "default",
              user_role: UserRole = UserRole.PUBLIC, tenant_id: Optional[str] = None) -> dict:
        """
        Main query interface
        
        Args:
            user_query: User's question
            top_k: Number of chunks to retrieve
            chat_history: Optional list of previous messages for context (not used yet, reserved for future)
            
        Returns:
            Dict with 'answer', 'source_url', 'refused', 'chunks_used'
        """
        # Get conversation context
        context = self.conversation_manager.get_context_for_query(session_id, user_query)
        
        # Use expanded query if available
        query_to_use = context.get('expanded_query', user_query)
        
        # Add user message to history
        self.conversation_manager.add_message(session_id, 'user', user_query)
        
        # FIRST: Check for unrelated queries BEFORE retrieving chunks (early exit)
        import re
        query_lower = user_query.lower()
        
        # Check for clearly unrelated queries (president, politics, general knowledge, etc.)
        unrelated_patterns = [
            r'president\s+of\s+(india|usa|america|united\s+states|us|u\.s\.)',
            r'prime\s+minister\s+of',
            r'capital\s+of\s+(india|delhi|mumbai|bangalore)',
            r'who\s+is\s+(?:the\s+)?(president|prime\s+minister|ceo)\s+of',
            r'weather\s+in',
            r'news\s+about',
            r'sports\s+(score|match|game)',
            r'(movie|film)\s+(review|rating)',
            r'recipe\s+for',
        ]
        
        is_unrelated = False
        for pattern in unrelated_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                is_unrelated = True
                break
        
        # Also check for "who is the X" where X is not fund-related
        if re.search(r'who\s+is\s+(?:the\s+)?(\w+)', query_lower):
            match = re.search(r'who\s+is\s+(?:the\s+)?(\w+)', query_lower)
            if match:
                word_after = match.group(1).lower()
                mf_roles = ['manager', 'fund', 'portfolio', 'investment']
                unrelated_roles = ['president', 'prime', 'minister', 'ceo', 'king', 'queen', 'leader']
                if word_after in unrelated_roles:
                    is_unrelated = True
                elif 'of' in query_lower and word_after not in mf_roles:
                    is_unrelated = True
        
        # Check if query is about mutual funds at all
        mf_keywords = ['mutual fund', 'fund', 'scheme', 'hdfc', 'elss', 'sip', 'nav', 'expense ratio', 
                       'exit load', 'redemption', 'investment', 'portfolio', 'manager', 'benchmark', 
                       'riskometer', 'lock-in', 'lockin', 'minimum', 'allotment', 'units', 'groww']
        is_about_mf = any(kw in query_lower for kw in mf_keywords)
        
        if is_unrelated and not is_about_mf:
            return {
                'answer': "I only provide information about HDFC Mutual Funds. I don't have information about that topic. Please ask me about HDFC schemes, expense ratios, exit loads, fund managers, or other mutual fund-related questions.",
                'source_url': None,
                'refused': True,
                'query_type': 'general'
            }
        
        # Retrieve relevant chunks (optimized: get more chunks initially, use re-ranking)
        chunks = self.retriever.retrieve(query_to_use, top_k=max(top_k, 20), use_reranking=True)
        
        # Apply access control filtering
        chunks = self.access_control.filter_chunks_by_role(chunks, user_role)
        
        # Note: Tenant filtering removed (simplified codebase)
        
        # Check query for safety
        query_safe, query_reason, query_flags = self.safety_filters.check_content(user_query)
        if not query_safe:
            return {
                'answer': f"I cannot process this query: {query_reason}",
                'source_url': None,
                'refused': True,
                'safety_flags': query_flags
            }
        
        # Generate answer with context and style
        result = self.qa.generate_answer(
            user_query, 
            chunks, 
            conversation_context=context,
            response_style=response_style
        )
        
        # If clarification was requested, mark it in conversation manager
        if result.get('needs_clarification', False):
            self.conversation_manager.set_pending_clarification(session_id, user_query, 'fund_selection')
        else:
            # Clear any pending clarification since we got a proper answer
            self.conversation_manager.clear_pending_clarification(session_id)
        
        # Filter answer for safety
        filtered_answer, answer_flags = self.safety_filters.filter_response(
            result.get('answer', ''),
            user_query
        )
        result['answer'] = filtered_answer
        if answer_flags:
            result['safety_flags'] = answer_flags
        result['chunks_used'] = len(chunks)
        
        # Add assistant response to history
        self.conversation_manager.add_message(session_id, 'assistant', result.get('answer', ''))
        
        # Update context entities if scheme was mentioned
        if 'scheme' in result:
            self.conversation_manager.update_working_memory(session_id, 'scheme', result['scheme'])
        
        # Note: Proactive assistant features removed (simplified codebase)
        
        # Add conversation metadata
        result['conversation_summary'] = context.get('summary', '')
        result['session_id'] = session_id
        
        return result

