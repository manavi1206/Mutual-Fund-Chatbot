"""
Streamlit UI for HDFC Mutual Fund FAQ Assistant
Clean, modern, professional design
"""
import streamlit as st
import os

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
    initial_sidebar_state="collapsed"
)

# Clean, modern CSS
st.markdown("""
<style>
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Full page - subtle gradient */
    .stApp {
        background: linear-gradient(180deg, #f0fdf9 0%, #e8faf6 50%, #e0f7f3 100%);
        min-height: 100vh;
    }
    
    /* Main container */
    .main .block-container {
        max-width: 1000px;
        padding: 1rem;
        padding-top: 2rem;
    }
    
    /* Chat container - clean white card */
    .chat-wrapper {
        background: white;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        padding: 2rem;
        margin-bottom: 1rem;
        min-height: 70vh;
        display: flex;
        flex-direction: column;
    }
    
    /* Header */
    .app-header {
        text-align: center;
        padding: 1.5rem 0 2rem 0;
        border-bottom: 1px solid #e5e5e5;
        margin-bottom: 2rem;
    }
    
    .app-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #00d09c;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .app-subtitle {
        font-size: 0.95rem;
        color: #666;
        margin-top: 0.5rem;
    }
    
    /* Chat messages area */
    .messages-area {
        flex: 1;
        overflow-y: auto;
        padding: 1rem 0;
        margin-bottom: 1rem;
    }
    
    /* Chat message styling */
    .stChatMessage {
        margin-bottom: 1.25rem;
    }
    
    /* User message */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) {
        background: linear-gradient(135deg, #f0fdf9 0%, #e8faf6 100%);
        border-radius: 16px;
        padding: 1rem 1.25rem;
        border-left: 3px solid #00d09c;
    }
    
    /* Assistant message */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) {
        background: #fafafa;
        border-radius: 16px;
        padding: 1rem 1.25rem;
        border: 1px solid #e5e5e5;
    }
    
    /* Source link */
    .source-link {
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid #e5e5e5;
    }
    
    .source-link a {
        color: #00d09c;
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .source-link a:hover {
        text-decoration: underline;
    }
    
    /* Input area */
    .input-area {
        border-top: 1px solid #e5e5e5;
        padding-top: 1.5rem;
        margin-top: auto;
    }
    
    .stChatInputContainer {
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        background: #fafafa;
    }
    
    .stChatInputContainer:focus-within {
        border-color: #00d09c;
        background: white;
    }
    
    /* Welcome section */
    .welcome-box {
        text-align: center;
        padding: 3rem 2rem;
        background: #f8f9fa;
        border-radius: 16px;
        margin: 2rem 0;
    }
    
    .welcome-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.75rem;
    }
    
    .welcome-text {
        color: #666;
        font-size: 0.95rem;
        line-height: 1.6;
        max-width: 600px;
        margin: 0 auto 1.5rem auto;
    }
    
    /* Quick action buttons */
    .quick-actions {
        display: flex;
        gap: 0.75rem;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 1.5rem;
    }
    
    .quick-btn {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 0.75rem 1.25rem;
        color: #1a1a1a;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .quick-btn:hover {
        border-color: #00d09c;
        color: #00d09c;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 208, 156, 0.15);
    }
    
    /* Disclaimer */
    .disclaimer {
        background: #fff4e6;
        border-left: 3px solid #ff9800;
        border-radius: 8px;
        padding: 1rem;
        margin: 1.5rem 0;
        font-size: 0.85rem;
        color: #666;
    }
    
    /* Footer */
    .app-footer {
        text-align: center;
        color: #888;
        font-size: 0.85rem;
        padding: 1rem 0;
    }
    
    /* Hide sidebar */
    section[data-testid="stSidebar"] {
        display: none;
    }
    
    /* Button styling */
    .stButton > button {
        background: #00d09c;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background: #00b887;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 208, 156, 0.3);
    }
    
    /* Loading spinner */
    .stSpinner > div {
        border-color: #00d09c;
    }
</style>
""", unsafe_allow_html=True)

# Initialize RAG system
@st.cache_resource(show_spinner=False)
def init_rag_system():
    """Initialize RAG system with caching"""
    return RAGSystem()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'rag_system' not in st.session_state:
    with st.spinner("🔄 Loading..."):
        try:
            st.session_state.rag_system = init_rag_system()
        except Exception as e:
            st.error(f"❌ Failed to initialize: {str(e)}")
            st.info("💡 Make sure GEMINI_API_KEY is set in Streamlit secrets")
            st.stop()

# Main chat wrapper
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="app-header">
    <div class="app-title">💼 HDFC Mutual Fund FAQ Assistant</div>
    <div class="app-subtitle">Get instant, factual answers about HDFC mutual fund schemes</div>
</div>
""", unsafe_allow_html=True)

# Messages area
st.markdown('<div class="messages-area">', unsafe_allow_html=True)

# Welcome message (only if no messages)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="welcome-box">
        <div class="welcome-title">👋 Welcome!</div>
        <div class="welcome-text">
            Ask me anything about HDFC mutual funds. I can help you with expense ratios, 
            exit loads, minimum SIP amounts, fund managers, investment strategies, and more.
        </div>
        <div class="quick-actions">
            <div class="quick-btn" onclick="this.style.display='none'">📊 Expense Ratio</div>
            <div class="quick-btn" onclick="this.style.display='none'">💰 Minimum SIP</div>
            <div class="quick-btn" onclick="this.style.display='none'">📈 Fund Manager</div>
            <div class="quick-btn" onclick="this.style.display='none'">🚪 Exit Load</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick action buttons (using Streamlit buttons)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Expense Ratio", use_container_width=True, key="q1"):
            st.session_state.messages.append({"role": "user", "content": "What is the expense ratio of HDFC Large Cap Fund?"})
            st.rerun()
    
    with col2:
        if st.button("💰 Minimum SIP", use_container_width=True, key="q2"):
            st.session_state.messages.append({"role": "user", "content": "What is the minimum SIP amount?"})
            st.rerun()
    
    with col3:
        if st.button("📈 Fund Manager", use_container_width=True, key="q3"):
            st.session_state.messages.append({"role": "user", "content": "Who manages the HDFC Flexi Cap Fund?"})
            st.rerun()
    
    with col4:
        if st.button("🚪 Exit Load", use_container_width=True, key="q4"):
            st.session_state.messages.append({"role": "user", "content": "What is the exit load for HDFC ELSS?"})
            st.rerun()
    
    # Disclaimer
    st.markdown("""
    <div class="disclaimer">
        ⚠️ <strong>Facts-Only Assistant</strong> - This chatbot provides factual information only, not investment advice. 
        For personalized guidance, consult a SEBI-registered financial advisor.
    </div>
    """, unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant" and message.get("source"):
            st.markdown(f'<div class="source-link">📎 <a href="{message["source"]}" target="_blank">View Source</a></div>', 
                       unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input area
st.markdown('<div class="input-area">', unsafe_allow_html=True)

if prompt := st.chat_input("Ask about HDFC mutual funds..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 Searching..."):
            try:
                response = st.session_state.rag_system.query(
                    prompt,
                    session_id="streamlit_session",
                    user_role="premium"
                )
                
                answer = response.get('answer', 'I could not find an answer to your question.')
                source_url = response.get('source_url', '')
                
                st.markdown(answer)
                
                if source_url:
                    st.markdown(f'<div class="source-link">📎 <a href="{source_url}" target="_blank">View Source</a></div>', 
                               unsafe_allow_html=True)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "source": source_url
                })
                
            except Exception as e:
                error_msg = f"❌ Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="app-footer">
    🔒 No PII collected | 📊 26 official sources | 📅 Updated: November 2025
</div>
""", unsafe_allow_html=True)
