"""
Card Components for Dashboard
"""
import streamlit as st
from typing import Dict, Any, Optional, Callable
from datetime import datetime


def render_metric_card(
    title: str,
    value: Any,
    delta: Optional[Any] = None,
    delta_color: str = "normal",
    icon: str = "📊"
):
    """Render a metric card"""
    st.metric(
        label=f"{icon} {title}",
        value=value,
        delta=delta,
        delta_color=delta_color
    )


def render_document_card(
    document: Dict[str, Any],
    on_delete: Optional[Callable] = None,
    on_reprocess: Optional[Callable] = None,
    show_actions: bool = True
):
    """Render a document card"""
    doc_id = document.get('id')
    title = document.get('title') or document.get('original_filename', 'Unknown')
    is_processed = document.get('is_processed', False)
    chunk_count = document.get('chunk_count', 0)
    page_count = document.get('page_count', 0)
    file_size = document.get('file_size', 0)
    created_at = document.get('created_at')
    error = document.get('processing_error')

    with st.container():
        # Header with status indicator
        col1, col2 = st.columns([4, 1])

        with col1:
            status_icon = "✅" if is_processed else "⏳" if not error else "❌"
            st.markdown(f"### {status_icon} {title}")

        with col2:
            if is_processed:
                st.success("Processed")
            elif error:
                st.error("Failed")
            else:
                st.warning("Pending")

        # Metadata
        col1, col2, col3 = st.columns(3)

        with col1:
            st.caption(f"📄 Pages: {page_count or 'N/A'}")

        with col2:
            st.caption(f"🧩 Chunks: {chunk_count}")

        with col3:
            # Format file size
            if file_size:
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                st.caption(f"💾 Size: {size_str}")

        # Upload date
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    pass

            if isinstance(created_at, datetime):
                st.caption(f"📅 Uploaded: {created_at.strftime('%Y-%m-%d %H:%M')}")

        # Error message if any
        if error:
            st.error(f"Error: {error}")

        # Actions
        if show_actions:
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if on_delete:
                    if st.button("🗑️ Delete", key=f"delete_doc_{doc_id}", type="secondary"):
                        on_delete(doc_id)

            with col2:
                if on_reprocess and not is_processed:
                    if st.button("🔄 Retry", key=f"reprocess_{doc_id}"):
                        on_reprocess(doc_id)

        st.divider()


def render_user_card(
    user: Dict[str, Any],
    on_edit: Optional[Callable] = None,
    on_toggle_status: Optional[Callable] = None,
    on_delete: Optional[Callable] = None,
    current_user_id: Optional[int] = None,
    show_actions: bool = True
):
    """Render a user card for admin panel"""
    user_id = user.get('id')
    username = user.get('username', 'Unknown')
    email = user.get('email', '')
    full_name = user.get('full_name') or username
    role = user.get('role', 'user')
    is_active = user.get('is_active', True)
    is_verified = user.get('is_verified', False)
    last_login = user.get('last_login')
    created_at = user.get('created_at')

    is_self = user_id == current_user_id

    with st.container():
        # Header
        col1, col2 = st.columns([3, 1])

        with col1:
            role_icon = "👑" if role == "superadmin" else "🛡️" if role == "admin" else "👤"
            status_icon = "🟢" if is_active else "🔴"
            st.markdown(f"### {role_icon} {full_name} {status_icon}")
            st.caption(f"@{username} • {email}")

        with col2:
            if role == "superadmin":
                st.info("Super Admin")
            elif role == "admin":
                st.warning("Admin")
            else:
                st.success("User") if is_active else st.error("Inactive")

        # User details
        col1, col2, col3 = st.columns(3)

        with col1:
            st.caption(f"📧 Verified: {'Yes' if is_verified else 'No'}")

        with col2:
            if last_login:
                if isinstance(last_login, str):
                    try:
                        last_login = datetime.fromisoformat(last_login)
                    except ValueError:
                        pass
                if isinstance(last_login, datetime):
                    st.caption(f"🕐 Last login: {last_login.strftime('%Y-%m-%d')}")
            else:
                st.caption("🕐 Never logged in")

        with col3:
            if created_at:
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        pass
                if isinstance(created_at, datetime):
                    st.caption(f"📅 Joined: {created_at.strftime('%Y-%m-%d')}")

        # Actions (not for superadmin or self)
        if show_actions and not is_self and role != "superadmin":
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if on_toggle_status:
                    action = "Deactivate" if is_active else "Activate"
                    if st.button(
                        f"{'🔒' if is_active else '🔓'} {action}",
                        key=f"toggle_{user_id}",
                        type="secondary"
                    ):
                        on_toggle_status(user_id)

            with col2:
                if on_delete:
                    if st.button("🗑️ Delete", key=f"delete_user_{user_id}", type="secondary"):
                        on_delete(user_id)

        if is_self:
            st.caption("*(This is you)*")

        st.divider()


def render_stats_card(
    title: str,
    stats: Dict[str, Any],
    icon: str = "📊"
):
    """Render a statistics card with multiple metrics"""
    st.markdown(f"### {icon} {title}")

    cols = st.columns(len(stats))

    for i, (key, value) in enumerate(stats.items()):
        with cols[i]:
            st.metric(label=key, value=value)


def render_activity_card(
    activities: list,
    title: str = "Recent Activity",
    icon: str = "📋"
):
    """Render an activity feed card"""
    st.markdown(f"### {icon} {title}")

    if not activities:
        st.caption("No recent activity")
        return

    for activity in activities[:10]:  # Show max 10
        timestamp = activity.get('timestamp', '')
        action = activity.get('action', '')
        user = activity.get('user', '')
        details = activity.get('details', '')

        st.markdown(f"**{action}** by *{user}*")
        if details:
            st.caption(details)
        if timestamp:
            st.caption(f"🕐 {timestamp}")
        st.divider()
