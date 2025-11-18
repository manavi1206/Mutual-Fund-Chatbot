"""
Streamlit UI for HDFC Mutual Fund FAQ Assistant
Modern chatbot design inspired by Gemini, ChatGPT, Claude
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

# Modern chatbot UI - completely custom
st.markdown("""
<style>
    /* Remove all defaults */
    .stApp {
        padding: 0 !important;
        margin: 0 !important;
        background: #ffffff !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        padding-top: 0 !important;
    }
    
    /* Full page container */
    .chatbot-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        background: #ffffff;
    }
    
    /* Top bar - minimal, aligned with input */
    .top-bar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 60px;
        background: white;
        border-bottom: 1px solid #e5e7eb;
        z-index: 1000;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .top-bar-content {
        display: flex;
        align-items: center;
        gap: 12px;
        max-width: 1200px;
        margin: 0 auto;
        width: 100%;
        padding: 0 24px;
        height: 100%;
    }
    
    .logo {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #00d09c 0%, #00b887 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        color: white;
        flex-shrink: 0;
    }
    
    .app-name {
        font-size: 1rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0;
    }
    
    /* Main chat area - aligned with header and input */
    .chat-area {
        margin-top: 60px;
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        background: #ffffff;
        display: flex;
        flex-direction: column;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Welcome message */
    .welcome-container {
        max-width: 700px;
        margin: 80px auto 40px auto;
        text-align: center;
    }
    
    .welcome-icon {
        width: 64px;
        height: 64px;
        background: #f3f4f6;
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        margin-bottom: 24px;
    }
    
    .welcome-title {
        font-size: 1.75rem;
        font-weight: 600;
        color: #111827;
        margin: 0 0 8px 0;
    }
    
    .welcome-subtitle {
        font-size: 1rem;
        color: #6b7280;
        margin: 0 0 32px 0;
        line-height: 1.5;
    }
    
    
    /* Chat messages */
    .message-wrapper {
        max-width: 700px;
        margin: 0 auto 24px auto;
        width: 100%;
    }
    
    .stChatMessage {
        margin-bottom: 0;
    }
    
    /* User message - right aligned */
    .message-wrapper:has([data-testid="stChatMessageUser"]) {
        display: flex;
        justify-content: flex-end;
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) {
        background: #00d09c;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 16px;
        color: white;
        max-width: 85%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) p {
        color: white !important;
        margin: 0;
        font-size: 0.9375rem;
        line-height: 1.5;
    }
    
    /* Assistant message - left aligned */
    .message-wrapper:has([data-testid="stChatMessageAssistant"]) {
        display: flex;
        justify-content: flex-start;
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) {
        background: #f9fafb;
        border-radius: 18px 18px 18px 4px;
        padding: 16px 20px;
        border: 1px solid #e5e7eb;
        max-width: 85%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) p {
        color: #111827 !important;
        margin: 0;
        font-size: 0.9375rem;
        line-height: 1.6;
    }
    
    /* Source link */
    .source-link {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid #e5e7eb;
    }
    
    .source-link a {
        color: #00d09c;
        text-decoration: none;
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    
    .source-link a:hover {
        text-decoration: underline;
    }
    
    /* Input area - fixed bottom */
    .input-wrapper {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        border-top: 1px solid #e5e7eb;
        padding: 16px 24px;
        z-index: 1000;
        box-shadow: 0 -4px 6px rgba(0,0,0,0.05);
    }
    
    .input-container {
        max-width: 1200px;
        margin: 0 auto;
        position: relative;
        padding: 0 24px;
    }
    
    .stChatInputContainer {
        border: 1px solid #d1d5db;
        border-radius: 24px;
        background: #ffffff;
        padding: 12px 20px;
        font-size: 0.9375rem;
        min-height: 52px;
        transition: all 0.2s;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .stChatInputContainer:focus-within {
        border-color: #00d09c;
        box-shadow: 0 0 0 3px rgba(0, 208, 156, 0.1);
    }
    
    /* Add padding to chat area for fixed input and disclaimer */
    .chat-area {
        padding-bottom: 140px !important;
    }
    
    /* Hide sidebar */
    section[data-testid="stSidebar"] {
        display: none;
    }
    
    /* Scrollbar */
    .chat-area::-webkit-scrollbar {
        width: 8px;
    }
    
    .chat-area::-webkit-scrollbar-track {
        background: transparent;
    }
    
    .chat-area::-webkit-scrollbar-thumb {
        background: #d1d5db;
        border-radius: 4px;
    }
    
    .chat-area::-webkit-scrollbar-thumb:hover {
        background: #9ca3af;
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
    
    .stChatMessage {
        animation: fadeIn 0.3s ease;
    }
    
    /* Disclaimer - below input, aligned */
    .disclaimer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #fff4e6;
        border-top: 1px solid #ff9800;
        padding: 8px 0;
        font-size: 0.75rem;
        color: #666;
        text-align: center;
        z-index: 1001;
    }
    
    .disclaimer-content {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 24px;
    }
    
    /* Adjust input wrapper to account for disclaimer */
    .input-wrapper {
        bottom: 40px !important;
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
    <div class="top-bar-content">
        <div class="logo">💼</div>
        <div class="app-name">HDFC MF FAQ Assistant</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Chat area
st.markdown('<div class="chat-area">', unsafe_allow_html=True)

# Welcome message (only if no messages)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-icon">👋</div>
        <div class="welcome-title">How can I help you today?</div>
        <div class="welcome-subtitle">
            Ask me anything about HDFC mutual funds. I can help with expense ratios, 
            exit loads, minimum SIP amounts, fund managers, and more.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Clickable suggestion chips (styled as pills)
    suggestions = [
        "What is the expense ratio of HDFC Large Cap Fund?",
        "What is the minimum SIP amount?",
        "Who manages the HDFC Flexi Cap Fund?",
        "What is the exit load for HDFC ELSS?",
    ]
    
    # Style buttons as chips
    st.markdown("""
    <style>
    .suggestions-container .stButton > button {
        background: #f9fafb !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 20px !important;
        padding: 10px 16px !important;
        font-size: 0.875rem !important;
        color: #374151 !important;
        font-weight: 400 !important;
        margin: 4px !important;
        box-shadow: none !important;
        transition: all 0.2s !important;
    }
    .suggestions-container .stButton > button:hover {
        background: #f3f4f6 !important;
        border-color: #d1d5db !important;
    }
    </style>
    <div class="suggestions-container" style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 700px; margin: 0 auto;">
    """, unsafe_allow_html=True)
    
    for i, question in enumerate(suggestions):
        if st.button(question, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    st.markdown('<div class="message-wrapper">', unsafe_allow_html=True)
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant" and message.get("source"):
            st.markdown(f'<div class="source-link">📎 <a href="{message["source"]}" target="_blank">View Source</a></div>', 
                       unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input area
st.markdown('<div class="input-wrapper"><div class="input-container">', unsafe_allow_html=True)

if prompt := st.chat_input("Message HDFC MF FAQ Assistant..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
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

st.markdown('</div></div>', unsafe_allow_html=True)

# Disclaimer - below input
st.markdown("""
<div class="disclaimer">
    <div class="disclaimer-content">
        ⚠️ Facts-Only Assistant - Provides factual information only, not investment advice.
    </div>
</div>
""", unsafe_allow_html=True)
