"""
Streamlit UI for HDFC Mutual Fund FAQ Assistant
Modern chatbot design inspired by Dribbble
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

# Modern chatbot UI - Dribbble inspired
st.markdown("""
<style>
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Clean white background */
    .stApp {
        background: #ffffff;
        min-height: 100vh;
    }
    
    /* Main container - full width, centered */
    .main .block-container {
        max-width: 900px;
        padding: 0;
        padding-top: 0;
    }
    
    /* Chat container */
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        max-height: 100vh;
        background: white;
    }
    
    /* Top bar */
    .top-bar {
        background: white;
        border-bottom: 1px solid #f0f0f0;
        padding: 1.25rem 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: sticky;
        top: 0;
        z-index: 100;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .top-bar-left {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .logo-circle {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #00d09c 0%, #00b887 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        color: white;
        font-weight: 600;
    }
    
    .app-name {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0;
    }
    
    .app-tagline {
        font-size: 0.85rem;
        color: #888;
        margin: 0;
    }
    
    /* Messages area - scrollable */
    .messages-container {
        flex: 1;
        overflow-y: auto;
        padding: 2rem;
        background: #fafafa;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }
    
    /* Welcome message */
    .welcome-message {
        text-align: center;
        padding: 3rem 2rem;
        max-width: 600px;
        margin: 2rem auto;
    }
    
    .welcome-icon {
        width: 64px;
        height: 64px;
        background: linear-gradient(135deg, #f0fdf9 0%, #e8faf6 100%);
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        margin-bottom: 1.5rem;
    }
    
    .welcome-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    
    .welcome-text {
        font-size: 0.95rem;
        color: #666;
        line-height: 1.6;
        margin-bottom: 2rem;
    }
    
    /* Quick suggestions */
    .suggestions {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        max-width: 500px;
        margin: 0 auto;
    }
    
    .suggestion-btn {
        background: white;
        border: 1px solid #e5e5e5;
        border-radius: 12px;
        padding: 0.875rem 1.25rem;
        text-align: left;
        color: #1a1a1a;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s;
        font-weight: 400;
    }
    
    .suggestion-btn:hover {
        border-color: #00d09c;
        background: #f0fdf9;
        transform: translateX(4px);
    }
    
    /* Chat messages */
    .stChatMessage {
        margin-bottom: 0;
        animation: fadeIn 0.3s ease;
    }
    
    /* User message - right aligned */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) {
        background: linear-gradient(135deg, #00d09c 0%, #00b887 100%);
        border-radius: 18px 18px 4px 18px;
        padding: 0.875rem 1.125rem;
        color: white;
        margin-left: auto;
        margin-right: 0;
        max-width: 75%;
        box-shadow: 0 2px 8px rgba(0, 208, 156, 0.2);
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) p {
        color: white !important;
        margin: 0;
    }
    
    /* Assistant message - left aligned */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) {
        background: white;
        border-radius: 18px 18px 18px 4px;
        padding: 1rem 1.25rem;
        border: 1px solid #e5e5e5;
        margin-left: 0;
        margin-right: auto;
        max-width: 75%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) p {
        color: #1a1a1a !important;
        margin: 0;
        line-height: 1.6;
    }
    
    /* Source link */
    .source-link {
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid rgba(0,0,0,0.05);
    }
    
    .source-link a {
        color: #00d09c;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .source-link a:hover {
        text-decoration: underline;
    }
    
    /* Input area - sticky bottom */
    .input-container {
        background: white;
        border-top: 1px solid #f0f0f0;
        padding: 1.25rem 2rem;
        position: sticky;
        bottom: 0;
        z-index: 100;
        box-shadow: 0 -1px 3px rgba(0,0,0,0.05);
    }
    
    .stChatInputContainer {
        border: 1.5px solid #e5e5e5;
        border-radius: 24px;
        background: #fafafa;
        padding: 0.75rem 1.25rem;
        transition: all 0.2s;
    }
    
    .stChatInputContainer:focus-within {
        border-color: #00d09c;
        background: white;
        box-shadow: 0 0 0 3px rgba(0, 208, 156, 0.1);
    }
    
    /* Animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Hide sidebar */
    section[data-testid="stSidebar"] {
        display: none;
    }
    
    /* Scrollbar styling */
    .messages-container::-webkit-scrollbar {
        width: 6px;
    }
    
    .messages-container::-webkit-scrollbar-track {
        background: transparent;
    }
    
    .messages-container::-webkit-scrollbar-thumb {
        background: #d0d0d0;
        border-radius: 3px;
    }
    
    .messages-container::-webkit-scrollbar-thumb:hover {
        background: #b0b0b0;
    }
    
    /* Disclaimer - subtle */
    .disclaimer {
        background: #fff4e6;
        border-left: 3px solid #ff9800;
        border-radius: 8px;
        padding: 0.875rem 1rem;
        margin: 1rem 0;
        font-size: 0.8rem;
        color: #666;
        line-height: 1.5;
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

# Top bar
st.markdown("""
<div class="top-bar">
    <div class="top-bar-left">
        <div class="logo-circle">💼</div>
        <div>
            <div class="app-name">HDFC MF FAQ Assistant</div>
            <div class="app-tagline">Facts-only chatbot</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Messages container
st.markdown('<div class="messages-container">', unsafe_allow_html=True)

# Welcome message (only if no messages)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="welcome-message">
        <div class="welcome-icon">👋</div>
        <div class="welcome-title">Hi! How can I help you?</div>
        <div class="welcome-text">
            Ask me anything about HDFC mutual funds. I can help with expense ratios, 
            exit loads, minimum SIP amounts, fund managers, and more.
        </div>
        <div class="suggestions">
            <div class="suggestion-btn">📊 What is the expense ratio of HDFC Large Cap Fund?</div>
            <div class="suggestion-btn">💰 What is the minimum SIP amount?</div>
            <div class="suggestion-btn">📈 Who manages the HDFC Flexi Cap Fund?</div>
            <div class="suggestion-btn">🚪 What is the exit load for HDFC ELSS?</div>
        </div>
        <div class="disclaimer">
            ⚠️ <strong>Facts-Only Assistant</strong> - Provides factual information only, not investment advice.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick suggestion buttons (using Streamlit)
    suggestions = [
        ("📊", "What is the expense ratio of HDFC Large Cap Fund?"),
        ("💰", "What is the minimum SIP amount?"),
        ("📈", "Who manages the HDFC Flexi Cap Fund?"),
        ("🚪", "What is the exit load for HDFC ELSS?"),
    ]
    
    for i, (icon, question) in enumerate(suggestions):
        if st.button(f"{icon} {question}", key=f"sugg_{i}", use_container_width=False):
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant" and message.get("source"):
            st.markdown(f'<div class="source-link">📎 <a href="{message["source"]}" target="_blank">View Source</a></div>', 
                       unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input container
st.markdown('<div class="input-container">', unsafe_allow_html=True)

if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
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
