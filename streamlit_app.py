"""
Streamlit UI for HDFC Mutual Fund FAQ Assistant
Modern, clean design inspired by SayHalo with Groww colors
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

# Modern, clean CSS - SayHalo inspired with Groww colors
st.markdown("""
<style>
    /* Hide all Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Full page gradient background - Light pastel green tones */
    .stApp {
        background: linear-gradient(135deg, #f0fdf9 0%, #e0faf4 25%, #d1f7ef 50%, #c2f4ea 75%, #b3f1e5 100%);
        min-height: 100vh;
    }
    
    /* Main container - Large rounded card */
    .main .block-container {
        max-width: 900px;
        padding: 2rem 1rem;
        margin: 0 auto;
    }
    
    /* Chat container - Rounded card with shadow */
    .chat-container {
        background: white;
        border-radius: 24px;
        padding: 3rem 2.5rem;
        box-shadow: 0 20px 60px rgba(0, 208, 156, 0.15);
        margin: 2rem auto;
        min-height: 600px;
        display: flex;
        flex-direction: column;
    }
    
    /* Header section */
    .header-section {
        text-align: center;
        margin-bottom: 3rem;
    }
    
    .logo-icon {
        width: 64px;
        height: 64px;
        background: linear-gradient(135deg, #00d09c 0%, #00b887 100%);
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 24px rgba(0, 208, 156, 0.3);
    }
    
    .greeting-text {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        margin: 0.5rem 0;
        letter-spacing: -0.5px;
    }
    
    .subtitle-text {
        font-size: 1.1rem;
        color: #666;
        margin: 0.5rem 0 1rem 0;
        font-weight: 400;
    }
    
    .description-text {
        font-size: 0.95rem;
        color: #888;
        line-height: 1.6;
        max-width: 500px;
        margin: 0 auto;
    }
    
    /* Topic cards section */
    .topics-container {
        display: flex;
        gap: 1rem;
        margin: 2rem 0;
        flex-wrap: wrap;
        justify-content: center;
    }
    
    .topic-card {
        flex: 1;
        min-width: 200px;
        background: #f8f9fa;
        border-radius: 16px;
        padding: 1.5rem;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid transparent;
        text-align: center;
    }
    
    .topic-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0, 208, 156, 0.2);
        border-color: #00d09c;
        background: white;
    }
    
    .topic-icon {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #00d09c 0%, #00b887 100%);
        border-radius: 12px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .topic-title {
        font-size: 1rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0.5rem 0;
    }
    
    .topic-subtitle {
        font-size: 0.85rem;
        color: #888;
        margin-top: 0.25rem;
    }
    
    /* Chat messages area */
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        margin: 2rem 0;
        padding: 1rem 0;
        min-height: 300px;
    }
    
    /* Custom chat message styling */
    .stChatMessage {
        margin-bottom: 1.5rem;
        animation: fadeIn 0.3s ease-in;
    }
    
    /* User message */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) {
        background: linear-gradient(135deg, #f0fdf9 0%, #e0faf4 100%);
        border-radius: 18px;
        padding: 1rem 1.25rem;
        border-left: 4px solid #00d09c;
    }
    
    /* Assistant message */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) {
        background: white;
        border-radius: 18px;
        padding: 1rem 1.25rem;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Input bar section */
    .input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 1.5rem 0 0 0;
        border-top: 1px solid #e0e0e0;
        margin-top: 2rem;
    }
    
    /* Chat input styling */
    .stChatInputContainer {
        border: 2px solid #e0e0e0;
        border-radius: 16px;
        padding: 0.75rem 1rem;
        background: #f8f9fa;
        transition: all 0.3s ease;
    }
    
    .stChatInputContainer:focus-within {
        border-color: #00d09c;
        background: white;
        box-shadow: 0 0 0 4px rgba(0, 208, 156, 0.1);
    }
    
    /* Source link */
    .source-link {
        font-size: 0.85rem;
        color: #00d09c;
        margin-top: 0.75rem;
        font-weight: 500;
    }
    
    .source-link a {
        color: #00d09c;
        text-decoration: none;
        transition: color 0.2s;
    }
    
    .source-link a:hover {
        color: #00b887;
        text-decoration: underline;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Welcome message when no chat */
    .welcome-section {
        text-align: center;
        padding: 2rem 0;
    }
    
    /* Disclaimer - subtle */
    .disclaimer-box {
        background: #fff4e6;
        border-radius: 12px;
        padding: 1rem;
        margin: 1.5rem 0;
        border-left: 3px solid #ff9800;
        font-size: 0.85rem;
        color: #666;
    }
    
    /* Loading spinner */
    .stSpinner > div {
        border-color: #00d09c;
    }
    
    /* Hide sidebar completely */
    section[data-testid="stSidebar"] {
        display: none;
    }
    
    /* Topic buttons - styled like cards */
    .stButton > button {
        background: #f8f9fa;
        border: 2px solid transparent;
        border-radius: 16px;
        padding: 1.5rem;
        color: #1a1a1a;
        font-weight: 500;
        transition: all 0.3s ease;
        height: auto;
        white-space: normal;
        line-height: 1.6;
    }
    
    .stButton > button:hover {
        background: white;
        border-color: #00d09c;
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0, 208, 156, 0.2);
    }
    
    .stButton > button:focus {
        box-shadow: 0 0 0 4px rgba(0, 208, 156, 0.1);
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

# Main chat container
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Header section (only show when no messages)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="header-section">
        <div class="logo-icon">💼</div>
        <div class="greeting-text">Hi! 👋</div>
        <div class="subtitle-text">Can I help you with HDFC Mutual Funds?</div>
        <div class="description-text">
            Ready to assist you with factual information about HDFC mutual fund schemes. 
            Ask me about expense ratios, exit loads, minimum SIP, fund managers, and more!
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Topic cards
    col1, col2, col3 = st.columns(3)
    
    topics = [
        ("📊", "Expense Ratio", "Fund Costs", "What is the expense ratio of HDFC Large Cap Fund?"),
        ("💰", "Minimum SIP", "Investment Amount", "What is the minimum SIP amount?"),
        ("📈", "Fund Manager", "Who's Managing", "Who manages the HDFC Flexi Cap Fund?"),
    ]
    
    for i, (icon, title, subtitle, question) in enumerate(topics):
        with [col1, col2, col3][i]:
            if st.button(f"{icon}\n\n**{title}**\n{subtitle}", use_container_width=True, key=f"topic_{i}"):
                st.session_state.messages.append({"role": "user", "content": question})
                st.rerun()
    
    # Disclaimer
    st.markdown("""
    <div class="disclaimer-box">
        ⚠️ <strong>Facts-Only Assistant</strong> - This chatbot provides factual information only, not investment advice. 
        For personalized guidance, consult a SEBI-registered financial advisor.
    </div>
    """, unsafe_allow_html=True)

# Chat messages
st.markdown('<div class="chat-messages">', unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant" and message.get("source"):
            st.markdown(f'<div class="source-link">📎 <a href="{message["source"]}" target="_blank">View Source</a></div>', 
                       unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Chat input
st.markdown('<div class="input-container">', unsafe_allow_html=True)

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
<div style='text-align: center; color: #888; padding: 2rem 0; font-size: 0.85rem;'>
    🔒 No PII collected | 📊 26 official sources | 📅 Updated: November 2025
</div>
""", unsafe_allow_html=True)
