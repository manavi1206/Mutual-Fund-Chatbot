"""
Streamlit UI for HDFC Mutual Fund FAQ Assistant
Clean, professional layout with centered content and left suggestions
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

# Professional layout CSS
st.markdown("""
<style>
    /* Remove all default padding/margins */
    .stApp {
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Full page - white background */
    .stApp > div {
        background: #ffffff;
    }
    
    /* Main container - no padding */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        padding-top: 0 !important;
    }
    
    /* Fixed header - NO whitespace */
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: white;
        border-bottom: 1px solid #e5e5e5;
        padding: 1rem 2rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        z-index: 1000;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .logo-box {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #00d09c 0%, #00b887 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        color: white;
        flex-shrink: 0;
    }
    
    .header-text {
        flex: 1;
    }
    
    .header-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0;
        line-height: 1.2;
    }
    
    .header-subtitle {
        font-size: 0.8rem;
        color: #888;
        margin: 0;
        line-height: 1.2;
    }
    
    /* Main content wrapper */
    .main-wrapper {
        margin-top: 72px;
        display: flex;
        height: calc(100vh - 72px);
        background: #fafafa;
    }
    
    /* Left sidebar for suggestions */
    .suggestions-sidebar {
        width: 320px;
        background: white;
        border-right: 1px solid #e5e5e5;
        padding: 2rem 1.5rem;
        overflow-y: auto;
        flex-shrink: 0;
    }
    
    .suggestions-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #666;
        margin-bottom: 1.25rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Messages area - centered */
    .messages-container {
        flex: 1;
        overflow-y: auto;
        padding: 2rem;
        background: #fafafa;
        display: flex;
        flex-direction: column;
    }
    
    /* Welcome section - centered */
    .welcome-center {
        max-width: 600px;
        margin: 0 auto;
        text-align: center;
        padding: 2rem 0;
    }
    
    .welcome-icon {
        width: 56px;
        height: 56px;
        background: linear-gradient(135deg, #f0fdf9 0%, #e8faf6 100%);
        border-radius: 14px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.75rem;
        margin-bottom: 1.25rem;
    }
    
    .welcome-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    
    .welcome-desc {
        font-size: 0.95rem;
        color: #666;
        line-height: 1.6;
        margin-bottom: 2rem;
    }
    
    /* Suggestion buttons in sidebar - better styling */
    .suggestions-sidebar .stButton {
        width: 100%;
        margin: 0.75rem 0;
    }
    
    .suggestions-sidebar .stButton > button {
        background: #f8f9fa !important;
        border: 1.5px solid #e5e5e5 !important;
        border-radius: 12px !important;
        padding: 1rem 1.25rem !important;
        text-align: left !important;
        color: #1a1a1a !important;
        font-size: 0.9rem !important;
        font-weight: 400 !important;
        width: 100% !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    
    .suggestions-sidebar .stButton > button:hover {
        border-color: #00d09c !important;
        background: white !important;
        transform: translateX(4px) !important;
        color: #1a1a1a !important;
        box-shadow: 0 2px 8px rgba(0, 208, 156, 0.15) !important;
    }
    
    .suggestions-sidebar .stButton > button:active {
        transform: translateX(2px) !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease;
    }
    
    /* User message - green, right */
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
    
    /* Assistant message - white, left */
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
    }
    
    .source-link a:hover {
        text-decoration: underline;
    }
    
    /* Fixed disclaimer at bottom */
    .fixed-disclaimer {
        position: fixed;
        bottom: 100px;
        left: 0;
        right: 0;
        background: #fff4e6;
        border-top: 1px solid #ff9800;
        padding: 0.75rem 2rem;
        font-size: 0.8rem;
        color: #666;
        z-index: 999;
        text-align: center;
        box-shadow: 0 -1px 3px rgba(0,0,0,0.05);
    }
    
    /* Fixed input area - BIGGER */
    .input-area {
        background: white;
        border-top: 1px solid #e5e5e5;
        padding: 1.5rem 2rem;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 1000;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
    }
    
    .stChatInputContainer {
        border: 2px solid #e5e5e5;
        border-radius: 28px;
        background: #fafafa;
        padding: 1rem 1.5rem;
        font-size: 1rem;
        min-height: 56px;
        transition: all 0.2s;
    }
    
    .stChatInputContainer:focus-within {
        border-color: #00d09c;
        background: white;
        box-shadow: 0 0 0 4px rgba(0, 208, 156, 0.15);
    }
    
    /* Add padding to messages for fixed elements */
    .messages-container {
        padding-bottom: 180px !important;
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
    
    /* Scrollbar */
    .messages-container::-webkit-scrollbar,
    .suggestions-sidebar::-webkit-scrollbar {
        width: 6px;
    }
    
    .messages-container::-webkit-scrollbar-track,
    .suggestions-sidebar::-webkit-scrollbar-track {
        background: transparent;
    }
    
    .messages-container::-webkit-scrollbar-thumb,
    .suggestions-sidebar::-webkit-scrollbar-thumb {
        background: #d0d0d0;
        border-radius: 3px;
    }
    
    .messages-container::-webkit-scrollbar-thumb:hover,
    .suggestions-sidebar::-webkit-scrollbar-thumb:hover {
        background: #b0b0b0;
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

# Fixed header
st.markdown("""
<div class="fixed-header">
    <div class="logo-box">💼</div>
    <div class="header-text">
        <div class="header-title">HDFC MF FAQ Assistant</div>
        <div class="header-subtitle">Facts-only chatbot</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main wrapper
st.markdown('<div class="main-wrapper">', unsafe_allow_html=True)

# Left sidebar for suggestions
st.markdown('<div class="suggestions-sidebar">', unsafe_allow_html=True)
st.markdown('<div class="suggestions-title"><span>💡</span> SUGGESTED QUESTIONS</div>', unsafe_allow_html=True)

suggestions = [
    ("📊", "What is the expense ratio of HDFC Large Cap Fund?"),
    ("💰", "What is the minimum SIP amount?"),
    ("📈", "Who manages the HDFC Flexi Cap Fund?"),
    ("🚪", "What is the exit load for HDFC ELSS?"),
]

for i, (icon, question) in enumerate(suggestions):
    if st.button(f"{icon} {question}", key=f"sugg_{i}", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": question})
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Messages container - centered
st.markdown('<div class="messages-container">', unsafe_allow_html=True)

# Welcome message (only if no messages)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="welcome-center">
        <div class="welcome-icon">👋</div>
        <div class="welcome-title">Hi! How can I help you?</div>
        <div class="welcome-desc">
            Ask me anything about HDFC mutual funds. I can help with expense ratios, 
            exit loads, minimum SIP amounts, fund managers, and more.
        </div>
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
st.markdown('</div>', unsafe_allow_html=True)

# Fixed disclaimer above input
st.markdown("""
<div class="fixed-disclaimer">
    ⚠️ <strong>Facts-Only Assistant</strong> - Provides factual information only, not investment advice.
</div>
""", unsafe_allow_html=True)

# Fixed input area
st.markdown('<div class="input-area">', unsafe_allow_html=True)

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
