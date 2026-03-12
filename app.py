"""
Legal Document Assistant - Main Application
Professional RAG-based chatbot with Streamlit
"""
import streamlit as st
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from config import APP_NAME, APP_DESCRIPTION, APP_VERSION
from database.db import init_db
from auth.authentication import AuthManager


# Page configuration
st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/legal-doc-assistant',
        'Report a bug': 'https://github.com/yourusername/legal-doc-assistant/issues',
        'About': f"### {APP_NAME}\n{APP_DESCRIPTION}\nVersion: {APP_VERSION}"
    }
)


# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Headers */
    h1 {
        color: #1E3A5F;
        font-weight: 700;
    }

    h2, h3 {
        color: #2C5282;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F7FAFC;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }

    /* Chat messages */
    .stChatMessage {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Input fields */
    .stTextInput > div > div > input {
        border-radius: 8px;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #2C5282;
    }

    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 8px;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed #CBD5E0;
        border-radius: 12px;
        padding: 1rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #F7FAFC;
    }

    ::-webkit-scrollbar-thumb {
        background: #CBD5E0;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #A0AEC0;
    }

    /* Login form styling */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    defaults = {
        'user': None,
        'authenticated': False,
        'current_session_id': None,
        'messages': [],
        'selected_documents': [],
        'settings': {
            'model': 'gpt-4o-mini',
            'temperature': 0.3,
            'top_k': 5,
            'show_sources': True,
            'show_metrics': False
        }
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_login_page():
    """Render login/registration page"""
    st.markdown(f"# ⚖️ {APP_NAME}")
    st.markdown(f"*{APP_DESCRIPTION}*")

    tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Register", "🔑 Forgot Password"])

    with tab1:
        with st.form("login_form"):
            st.markdown("### Welcome Back!")
            email_or_username = st.text_input("Email or Username", placeholder="Enter your email or username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

            if submitted:
                if not email_or_username or not password:
                    st.error("Please fill in all fields")
                else:
                    success, message, user_data = AuthManager.login(email_or_username, password)
                    if success:
                        st.session_state.user = user_data
                        st.session_state.authenticated = True
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    with tab2:
        with st.form("register_form"):
            st.markdown("### Create Account")
            reg_email = st.text_input("Email", placeholder="your.email@example.com", key="reg_email")
            reg_username = st.text_input("Username", placeholder="Choose a username", key="reg_username")
            reg_fullname = st.text_input("Full Name (Optional)", placeholder="Your full name", key="reg_fullname")
            reg_password = st.text_input("Password", type="password", placeholder="Create a password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="reg_confirm")

            submitted = st.form_submit_button("Register", use_container_width=True, type="primary")

            if submitted:
                if not reg_email or not reg_username or not reg_password:
                    st.error("Please fill in all required fields")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match")
                else:
                    success, message, user_data = AuthManager.register(
                        email=reg_email,
                        username=reg_username,
                        password=reg_password,
                        full_name=reg_fullname if reg_fullname else None
                    )
                    if success:
                        st.success("Registration successful! Please login.")
                    else:
                        st.error(message)

    with tab3:
        with st.form("forgot_form"):
            st.markdown("### Reset Password")
            st.caption("Enter your email to receive a password reset link.")
            reset_email = st.text_input("Email", placeholder="your.email@example.com", key="reset_email")

            submitted = st.form_submit_button("Send Reset Link", use_container_width=True)

            if submitted:
                if not reset_email:
                    st.error("Please enter your email")
                else:
                    success, message, token = AuthManager.request_password_reset(reset_email)
                    if success and token:
                        # In production, send email with token
                        st.info(f"Password reset token (for demo): {token}")
                        st.success("If the email exists, a reset link has been sent.")
                    else:
                        st.success("If the email exists, a reset link has been sent.")


def render_main_app():
    """Render main application after login"""
    user = st.session_state.user

    # Sidebar
    with st.sidebar:
        st.markdown(f"### ⚖️ {APP_NAME}")
        st.divider()

        # User info
        st.markdown(f"👤 **{user.get('full_name') or user.get('username', 'User')}**")
        st.caption(user.get('email', ''))

        role = user.get('role', 'user')
        if role in ['admin', 'superadmin']:
            st.markdown(f"🛡️ *{role.title()}*")

        st.divider()

        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.authenticated = False
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.rerun()

    # Main content - show welcome message
    st.markdown(f"# Welcome to {APP_NAME}! 👋")

    st.markdown("""
    Navigate using the sidebar to access different features:

    ### 📍 Available Pages:

    - **💬 Chat** - Ask questions about your legal documents
    - **📁 Documents** - Upload and manage your PDF documents
    - **📊 Analytics** - View usage statistics and insights
    - **⚙️ Settings** - Configure your preferences
    """)

    if role in ['admin', 'superadmin']:
        st.markdown("- **👥 Admin** - Manage users and system settings")

    st.divider()

    # Quick stats
    col1, col2, col3 = st.columns(3)

    from database.db import DatabaseManager

    with col1:
        docs = DatabaseManager.get_user_documents(user['id'])
        st.metric("📄 Your Documents", len(docs))

    with col2:
        sessions = DatabaseManager.get_user_sessions(user['id'])
        st.metric("💬 Chat Sessions", len(sessions))

    with col3:
        from database.vector_store import VectorStore
        try:
            vs = VectorStore()
            stats = vs.get_collection_stats()
            st.metric("🧩 Total Chunks", stats.get('total_chunks', 0))
        except Exception:
            st.metric("🧩 Total Chunks", "N/A")

    st.divider()

    st.info("👈 Select **Chat** from the sidebar to start asking questions about your documents!")


def main():
    """Main application entry point"""
    # Initialize database
    init_db()

    # Initialize admin user
    AuthManager.initialize_admin()

    # Initialize session state
    init_session_state()

    # Check authentication
    if not st.session_state.authenticated:
        render_login_page()
    else:
        render_main_app()


if __name__ == "__main__":
    main()
