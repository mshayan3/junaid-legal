"""
Settings Page - User preferences and account settings
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import DatabaseManager
from auth.authentication import AuthManager
from utils.export import ExportManager
from utils.helpers import format_datetime

# Page config
st.set_page_config(
    page_title="Settings - Legal Document Assistant",
    page_icon="⚙️",
    layout="wide"
)


def main():
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to access settings.")
        st.stop()

    user = st.session_state.user

    st.markdown("# ⚙️ Settings")
    st.markdown("Manage your account and preferences.")

    # Tabs for different settings
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "🔐 Security", "🎨 Preferences", "📥 Export Data"])

    with tab1:
        st.markdown("### Profile Information")

        # Get current user info
        user_info = AuthManager.get_user_info(user['id'])

        if user_info:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Account Details")

                st.text_input("Username", value=user_info.get('username', ''), disabled=True)
                st.text_input("Email", value=user_info.get('email', ''), disabled=True)

                # Editable fields
                with st.form("profile_form"):
                    new_fullname = st.text_input(
                        "Full Name",
                        value=user_info.get('full_name') or '',
                        placeholder="Enter your full name"
                    )

                    submitted = st.form_submit_button("Update Profile", use_container_width=True)

                    if submitted:
                        success, message = AuthManager.update_profile(
                            user['id'],
                            full_name=new_fullname if new_fullname else None
                        )
                        if success:
                            st.success(message)
                            # Update session state
                            st.session_state.user['full_name'] = new_fullname
                        else:
                            st.error(message)

            with col2:
                st.markdown("#### Account Status")

                st.markdown(f"**Role:** {user_info.get('role', 'user').title()}")
                st.markdown(f"**Status:** {'🟢 Active' if user_info.get('is_active') else '🔴 Inactive'}")
                st.markdown(f"**Verified:** {'✅ Yes' if user_info.get('is_verified') else '❌ No'}")

                st.divider()

                st.markdown("**Joined:** " + format_datetime(user_info.get('created_at'), '%B %d, %Y'))
                st.markdown("**Last Login:** " + format_datetime(user_info.get('last_login'), '%B %d, %Y %H:%M'))

    with tab2:
        st.markdown("### Security Settings")

        st.markdown("#### Change Password")

        with st.form("password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")

            submitted = st.form_submit_button("Change Password", use_container_width=True)

            if submitted:
                if not current_password or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    success, message = AuthManager.change_password(
                        user['id'],
                        current_password,
                        new_password
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

        st.divider()

        st.markdown("#### Password Requirements")
        st.markdown("""
        - At least 8 characters long
        - Contains at least one uppercase letter
        - Contains at least one lowercase letter
        - Contains at least one digit
        """)

    with tab3:
        st.markdown("### Preferences")

        st.markdown("#### Chat Settings")

        # Initialize preferences in session state if not exists
        if 'settings' not in st.session_state:
            st.session_state.settings = {
                'model': 'gpt-4o-mini',
                'temperature': 0.3,
                'top_k': 5,
                'show_sources': True,
                'show_metrics': False
            }

        settings = st.session_state.settings

        # Model selection
        model = st.selectbox(
            "AI Model",
            options=['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
            index=['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'].index(settings.get('model', 'gpt-4o-mini')),
            help="Select the AI model for generating responses"
        )

        # Temperature
        temperature = st.slider(
            "Response Creativity",
            min_value=0.0,
            max_value=1.0,
            value=settings.get('temperature', 0.3),
            step=0.1,
            help="Higher values make responses more creative but less focused"
        )

        # Number of sources
        top_k = st.slider(
            "Number of Sources",
            min_value=1,
            max_value=10,
            value=settings.get('top_k', 5),
            help="Number of document chunks to retrieve for context"
        )

        st.divider()

        st.markdown("#### Display Settings")

        show_sources = st.checkbox(
            "Show Sources",
            value=settings.get('show_sources', True),
            help="Display source citations with responses"
        )

        show_metrics = st.checkbox(
            "Show Performance Metrics",
            value=settings.get('show_metrics', False),
            help="Display response time and token usage"
        )

        # Save settings button
        if st.button("💾 Save Preferences", use_container_width=True, type="primary"):
            st.session_state.settings = {
                'model': model,
                'temperature': temperature,
                'top_k': top_k,
                'show_sources': show_sources,
                'show_metrics': show_metrics
            }
            st.success("Preferences saved!")

    with tab4:
        st.markdown("### Export Your Data")

        st.markdown("""
        You can export your data from the application. This includes:
        - Chat history
        - Uploaded documents metadata
        - Query logs
        """)

        st.divider()

        st.markdown("#### Chat History Export")

        # Get user's chat sessions
        sessions = DatabaseManager.get_user_sessions(user['id'])

        if sessions:
            session_options = {f"{s.title} ({format_datetime(s.created_at, '%Y-%m-%d')})": s.id for s in sessions}

            selected_session = st.selectbox(
                "Select Chat Session",
                options=list(session_options.keys())
            )

            export_format = st.radio(
                "Export Format",
                options=["Markdown", "Text", "HTML", "JSON"],
                horizontal=True
            )

            if st.button("📥 Export Chat", use_container_width=True):
                session_id = session_options[selected_session]
                messages = DatabaseManager.get_session_messages(session_id)

                # Convert to dict format
                messages_data = [
                    {
                        'role': m.role,
                        'content': m.content,
                        'sources': m.sources,
                        'created_at': format_datetime(m.created_at)
                    }
                    for m in messages
                ]

                exporter = ExportManager()

                if export_format == "Markdown":
                    content = exporter.export_chat_to_markdown(messages_data, selected_session)
                    file_ext = "md"
                    mime = "text/markdown"
                elif export_format == "Text":
                    content = exporter.export_chat_to_text(messages_data, selected_session)
                    file_ext = "txt"
                    mime = "text/plain"
                elif export_format == "HTML":
                    content = exporter.export_chat_to_html(messages_data, selected_session)
                    file_ext = "html"
                    mime = "text/html"
                else:  # JSON
                    content = exporter.export_chat_to_json(messages_data, {'title': selected_session})
                    file_ext = "json"
                    mime = "application/json"

                st.download_button(
                    label=f"Download {export_format}",
                    data=content,
                    file_name=f"chat_export.{file_ext}",
                    mime=mime
                )
        else:
            st.info("No chat sessions to export.")

        st.divider()

        st.markdown("#### All Chat History")

        if sessions:
            if st.button("📥 Export All Chats", use_container_width=True, type="secondary"):
                all_chats = []

                for session in sessions:
                    messages = DatabaseManager.get_session_messages(session.id)
                    messages_data = [
                        {
                            'role': m.role,
                            'content': m.content,
                            'sources': m.sources,
                            'created_at': format_datetime(m.created_at)
                        }
                        for m in messages
                    ]

                    all_chats.append({
                        'session_title': session.title,
                        'session_id': session.id,
                        'created_at': format_datetime(session.created_at),
                        'messages': messages_data
                    })

                import json
                content = json.dumps(all_chats, indent=2, default=str)

                st.download_button(
                    label="Download All Chats (JSON)",
                    data=content,
                    file_name="all_chats_export.json",
                    mime="application/json"
                )

        st.divider()

        # Danger zone
        st.markdown("### ⚠️ Danger Zone")

        with st.expander("Delete All My Data", expanded=False):
            st.warning("This will permanently delete all your chat history and uploaded documents. This action cannot be undone.")

            confirm_text = st.text_input(
                "Type 'DELETE' to confirm",
                placeholder="Type DELETE to confirm"
            )

            if st.button("🗑️ Delete All My Data", type="secondary", use_container_width=True):
                if confirm_text == "DELETE":
                    # Delete all user's sessions
                    for session in sessions:
                        DatabaseManager.delete_session(session.id)

                    # Delete all user's documents
                    from database.vector_store import DocumentIngestionPipeline
                    pipeline = DocumentIngestionPipeline()

                    docs = DatabaseManager.get_user_documents(user['id'])
                    for doc in docs:
                        pipeline.remove_document(doc.id)

                    st.success("All your data has been deleted.")
                    st.rerun()
                else:
                    st.error("Please type 'DELETE' to confirm")


if __name__ == "__main__":
    main()
