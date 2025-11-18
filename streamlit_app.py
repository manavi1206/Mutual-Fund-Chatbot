"""
Streamlit UI for HDFC Mutual Fund FAQ Assistant
Milestone 1 - Facts-Only RAG Chatbot
"""
import streamlit as st
import os
import sys

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Import RAG system
from rag_system import RAGSystem

# Page configuration
st.set_page_config(
    page_title="HDFC MF FAQ Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Groww-like styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #00d09c;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .disclaimer {
        background-color: #fff4e6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff9800;
        margin-bottom: 1.5rem;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196f3;
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .source-link {
        font-size: 0.9rem;
        color: #00d09c;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize RAG system (cached to avoid reloading)
@st.cache_resource(show_spinner=False)
def init_rag_system():
    """Initialize RAG system with caching"""
    return RAGSystem()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'rag_system' not in st.session_state:
    with st.spinner("🔄 Loading RAG system... (This takes ~10 seconds on first load)"):
        try:
            st.session_state.rag_system = init_rag_system()
            st.success("✅ RAG system ready!")
        except Exception as e:
            st.error(f"❌ Failed to initialize RAG system: {str(e)}")
            st.info("💡 Make sure GEMINI_API_KEY is set in Streamlit secrets or .env file")
            st.stop()

# Sidebar
with st.sidebar:
    st.markdown("### 💼 HDFC MF FAQ Assistant")
    st.markdown("**Milestone 1** - Facts-Only Chatbot")
    st.markdown("---")
    
    st.markdown("#### 📚 Covered Schemes")
    st.markdown("""
    - **HDFC Large Cap Fund**
    - **HDFC Flexi Cap Fund**
    - **HDFC TaxSaver (ELSS)**
    - **HDFC Hybrid Equity Fund**
    """)
    
    st.markdown("---")
    
    st.markdown("#### 💡 Example Questions")
    st.markdown("Click to try:")
    
    examples = [
        ("Expense Ratio", "What is the expense ratio of HDFC Large Cap Fund?"),
        ("Minimum SIP", "What is the minimum SIP amount?"),
        ("Exit Load", "What is the exit load for HDFC ELSS?"),
        ("Fund Manager", "Who manages the HDFC Flexi Cap Fund?"),
        ("Redemption", "How do I redeem my units?"),
        ("Lock-in Period", "What is the lock-in period of HDFC TaxSaver?"),
        ("Riskometer", "What is the riskometer level for HDFC Large Cap?"),
        ("Investment Strategy", "What is the investment strategy of HDFC Hybrid Equity Fund?"),
    ]
    
    for label, question in examples:
        if st.button(f"📌 {label}", key=f"btn_{label}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("#### ℹ️ About")
    st.markdown("""
    - **Sources**: 26 official documents
    - **Data from**: HDFC AMC, SEBI, AMFI, Groww
    - **Last updated**: Nov 18, 2025
    - **Technology**: RAG + Gemini LLM
    """)
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main area - Header
st.markdown('<div class="main-header">💼 HDFC Mutual Fund FAQ Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Get instant, factual answers about HDFC mutual fund schemes</div>', unsafe_allow_html=True)

# Disclaimer
st.markdown("""
<div class="disclaimer">
    ⚠️ <strong>Facts-Only Assistant</strong><br>
    This chatbot provides <strong>factual information only</strong>, not investment advice. 
    For personalized guidance, please consult a SEBI-registered financial advisor.
</div>
""", unsafe_allow_html=True)

# Welcome message (show only if no messages)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="info-box">
        <strong>👋 Welcome!</strong><br>
        Ask me anything about HDFC mutual funds:<br>
        • Expense ratios, exit loads, minimum SIP amounts<br>
        • Fund managers, investment strategies, benchmarks<br>
        • How to redeem units, download statements, and more!<br><br>
        <em>Try the example questions in the sidebar to get started →</em>
    </div>
    """, unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display source if available (for assistant messages)
        if message["role"] == "assistant" and message.get("source"):
            st.markdown(f'<div class="source-link">📎 <a href="{message["source"]}" target="_blank">View Source</a></div>', 
                       unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Ask about HDFC mutual funds... (e.g., 'What is the expense ratio?')"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Searching knowledge base..."):
            try:
                # Query RAG system
                response = st.session_state.rag_system.query(
                    prompt,
                    session_id="streamlit_session",
                    user_role="premium"
                )
                
                answer = response.get('answer', 'I could not find an answer to your question.')
                source_url = response.get('source_url', '')
                
                # Display answer
                st.markdown(answer)
                
                # Display source link
                if source_url:
                    st.markdown(f'<div class="source-link">📎 <a href="{source_url}" target="_blank">View Source</a></div>', 
                               unsafe_allow_html=True)
                
                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "source": source_url
                })
                
            except Exception as e:
                error_msg = f"❌ Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.info("💡 This might be a temporary issue. Please try again or rephrase your question.")
                
                # Add error to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>
        🔒 <strong>Privacy</strong>: No PII collected | 
        📊 <strong>Sources</strong>: 26 official documents | 
        📅 <strong>Updated</strong>: November 2025<br>
        Built with ❤️ using RAG, FAISS, and Gemini LLM | 
        <a href="https://github.com/manavi1206/Mutual-Fund-Chatbot" target="_blank">View on GitHub</a>
    </small>
</div>
""", unsafe_allow_html=True)

