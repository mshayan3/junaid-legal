"""
Sidebar Components
"""
import streamlit as st
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime


def render_sidebar(user_info: Dict[str, Any]):
    """Render main application sidebar"""
    with st.sidebar:
        # User info section
        st.markdown("### 👤 Profile")
        st.markdown(f"**{user_info.get('full_name') or user_info.get('username', 'User')}**")
        st.caption(user_info.get('email', ''))

        role = user_info.get('role', 'user')
        if role in ['admin', 'superadmin']:
            st.markdown(f"🛡️ *{role.title()}*")

        st.divider()

        # Navigation
        st.markdown("### 📍 Navigation")

        # Quick stats
        st.markdown("### 📊 Quick Stats")

        return True


def render_chat_history_sidebar(
    sessions: List[Dict[str, Any]],
    current_session_id: Optional[int],
    on_select: Callable,
    on_new: Callable,
    on_delete: Callable
):
    """Render chat history in sidebar"""
    with st.sidebar:
        st.markdown("### 💬 Chat History")

        # New chat button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            on_new()

        st.divider()

        if not sessions:
            st.caption("No previous chats")
            return

        # List sessions
        for session in sessions:
            session_id = session.get('id')
            title = session.get('title', 'Untitled')
            updated = session.get('updated_at')

            # Format date
            if updated:
                if isinstance(updated, str):
                    try:
                        updated = datetime.fromisoformat(updated)
                    except ValueError:
                        updated = None

            # Create container for each session
            is_current = session_id == current_session_id

            container = st.container()
            with container:
                col1, col2 = st.columns([4, 1])

                with col1:
                    # Session button
                    button_type = "primary" if is_current else "secondary"
                    if st.button(
                        f"{'📌 ' if is_current else ''}{title[:25]}{'...' if len(title) > 25 else ''}",
                        key=f"session_{session_id}",
                        use_container_width=True,
                        type=button_type
                    ):
                        on_select(session_id)

                with col2:
                    # Delete button
                    if st.button(
                        "🗑️",
                        key=f"delete_{session_id}",
                        help="Delete this chat"
                    ):
                        on_delete(session_id)

                if updated:
                    st.caption(updated.strftime("%b %d, %H:%M"))


def render_document_filter_sidebar(
    documents: List[Dict[str, Any]],
    selected_ids: List[int]
) -> List[int]:
    """Render document filter in sidebar"""
    with st.sidebar:
        st.markdown("### 📁 Document Filter")

        if not documents:
            st.caption("No documents uploaded")
            return []

        st.caption("Select documents to search:")

        new_selected = []

        for doc in documents:
            doc_id = doc.get('id')
            title = doc.get('title') or doc.get('original_filename', 'Unknown')
            is_processed = doc.get('is_processed', False)

            # Only show processed documents
            if is_processed:
                checked = st.checkbox(
                    f"📄 {title[:30]}{'...' if len(title) > 30 else ''}",
                    value=doc_id in selected_ids,
                    key=f"doc_filter_{doc_id}",
                    help=f"Chunks: {doc.get('chunk_count', 0)}"
                )
                if checked:
                    new_selected.append(doc_id)

        if st.button("Select All", key="select_all_docs"):
            return [d['id'] for d in documents if d.get('is_processed')]

        if st.button("Clear Selection", key="clear_docs"):
            return []

        return new_selected


def render_settings_sidebar(
    current_settings: Dict[str, Any],
    on_save: Callable
):
    """Render settings in sidebar"""
    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        # Model selection
        model = st.selectbox(
            "Model",
            options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            index=0,
            key="model_select"
        )

        # Temperature
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=current_settings.get('temperature', 0.3),
            step=0.1,
            key="temp_slider"
        )

        # Top K results
        top_k = st.slider(
            "Number of Sources",
            min_value=1,
            max_value=10,
            value=current_settings.get('top_k', 5),
            key="topk_slider"
        )

        # Show sources
        show_sources = st.checkbox(
            "Show Sources",
            value=current_settings.get('show_sources', True),
            key="sources_toggle"
        )

        # Show metrics
        show_metrics = st.checkbox(
            "Show Performance Metrics",
            value=current_settings.get('show_metrics', False),
            key="metrics_toggle"
        )

        if st.button("Save Settings", key="save_settings"):
            on_save({
                'model': model,
                'temperature': temperature,
                'top_k': top_k,
                'show_sources': show_sources,
                'show_metrics': show_metrics
            })
            st.success("Settings saved!")

        return {
            'model': model,
            'temperature': temperature,
            'top_k': top_k,
            'show_sources': show_sources,
            'show_metrics': show_metrics
        }
