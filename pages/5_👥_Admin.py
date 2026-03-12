"""
Admin Page - User management and system administration
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import DatabaseManager
from database.vector_store import VectorStore
from auth.authentication import AuthManager
from utils.helpers import format_datetime

# Page config
st.set_page_config(
    page_title="Admin - Legal Document Assistant",
    page_icon="👥",
    layout="wide"
)


def main():
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to access admin panel.")
        st.stop()

    user = st.session_state.user

    # Check admin role
    if user.get('role') not in ['admin', 'superadmin']:
        st.error("⛔ Access Denied. You need admin privileges to access this page.")
        st.stop()

    is_superadmin = user.get('role') == 'superadmin'

    st.markdown("# 👥 Admin Panel")
    st.markdown("Manage users and system settings.")

    if is_superadmin:
        st.success("🛡️ Super Admin Mode")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["👥 Users", "📄 All Documents", "🔧 System"])

    with tab1:
        st.markdown("### User Management")

        # Get all users
        all_users = AuthManager.get_all_users()

        # Stats
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Users", len(all_users))

        with col2:
            active = sum(1 for u in all_users if u.get('is_active'))
            st.metric("Active", active)

        with col3:
            admins = sum(1 for u in all_users if u.get('role') in ['admin', 'superadmin'])
            st.metric("Admins", admins)

        with col4:
            verified = sum(1 for u in all_users if u.get('is_verified'))
            st.metric("Verified", verified)

        st.divider()

        # Search and filter
        col1, col2 = st.columns([3, 1])

        with col1:
            search = st.text_input("🔍 Search users", placeholder="Search by username or email")

        with col2:
            role_filter = st.selectbox(
                "Filter by role",
                options=["All", "User", "Admin", "Superadmin"]
            )

        # Filter users
        filtered_users = all_users

        if search:
            search_lower = search.lower()
            filtered_users = [
                u for u in filtered_users
                if search_lower in u.get('username', '').lower()
                or search_lower in u.get('email', '').lower()
                or search_lower in (u.get('full_name') or '').lower()
            ]

        if role_filter != "All":
            filtered_users = [
                u for u in filtered_users
                if u.get('role') == role_filter.lower()
            ]

        st.divider()

        # User list
        for user_item in filtered_users:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 2])

                with col1:
                    # User info
                    role_icon = "👑" if user_item.get('role') == 'superadmin' else "🛡️" if user_item.get('role') == 'admin' else "👤"
                    status_icon = "🟢" if user_item.get('is_active') else "🔴"

                    name = user_item.get('full_name') or user_item.get('username', 'Unknown')
                    st.markdown(f"### {role_icon} {name} {status_icon}")
                    st.caption(f"@{user_item.get('username')} • {user_item.get('email')}")

                with col2:
                    # Status badges
                    st.markdown(f"**Role:** {user_item.get('role', 'user').title()}")
                    st.markdown(f"**Verified:** {'✅' if user_item.get('is_verified') else '❌'}")
                    st.caption(f"Joined: {format_datetime(user_item.get('created_at'), '%Y-%m-%d')}")

                with col3:
                    # Actions (not for self or superadmin if not superadmin)
                    is_self = user_item.get('id') == user['id']
                    is_target_superadmin = user_item.get('role') == 'superadmin'

                    if not is_self and not is_target_superadmin:
                        # Toggle status
                        current_status = user_item.get('is_active', True)
                        action = "Deactivate" if current_status else "Activate"

                        if st.button(
                            f"{'🔒' if current_status else '🔓'} {action}",
                            key=f"toggle_{user_item.get('id')}",
                            use_container_width=True
                        ):
                            success, message = AuthManager.admin_toggle_user_status(
                                user['id'],
                                user_item.get('id')
                            )
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

                        # Role change (superadmin only)
                        if is_superadmin:
                            current_role = user_item.get('role', 'user')
                            new_role = st.selectbox(
                                "Change Role",
                                options=['user', 'admin'],
                                index=0 if current_role == 'user' else 1,
                                key=f"role_{user_item.get('id')}"
                            )

                            if new_role != current_role:
                                if st.button("Update Role", key=f"role_btn_{user_item.get('id')}"):
                                    success, message = AuthManager.admin_update_user(
                                        user['id'],
                                        user_item.get('id'),
                                        role=new_role
                                    )
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)

                        # Delete user (superadmin only)
                        if is_superadmin:
                            if st.button(
                                "🗑️ Delete",
                                key=f"delete_{user_item.get('id')}",
                                type="secondary"
                            ):
                                success, message = AuthManager.admin_delete_user(
                                    user['id'],
                                    user_item.get('id')
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                    elif is_self:
                        st.caption("*(This is you)*")
                    else:
                        st.caption("*(Super Admin)*")

                st.divider()

        # Add new user (superadmin only)
        if is_superadmin:
            st.markdown("### ➕ Add New User")

            with st.form("add_user_form"):
                col1, col2 = st.columns(2)

                with col1:
                    new_email = st.text_input("Email")
                    new_username = st.text_input("Username")

                with col2:
                    new_password = st.text_input("Password", type="password")
                    new_role = st.selectbox("Role", options=['user', 'admin'])

                new_fullname = st.text_input("Full Name (Optional)")

                submitted = st.form_submit_button("Create User", use_container_width=True)

                if submitted:
                    if not new_email or not new_username or not new_password:
                        st.error("Please fill in all required fields")
                    else:
                        success, message, user_data = AuthManager.register(
                            email=new_email,
                            username=new_username,
                            password=new_password,
                            full_name=new_fullname if new_fullname else None
                        )

                        if success:
                            # Update role if admin
                            if new_role == 'admin':
                                AuthManager.admin_update_user(
                                    user['id'],
                                    user_data['id'],
                                    role='admin'
                                )
                            st.success("User created successfully!")
                            st.rerun()
                        else:
                            st.error(message)

    with tab2:
        st.markdown("### All Documents")

        # Get all documents
        all_docs = DatabaseManager.get_all_documents()

        # Stats
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Documents", len(all_docs))

        with col2:
            processed = sum(1 for d in all_docs if d.is_processed)
            st.metric("Processed", processed)

        with col3:
            total_chunks = sum(d.chunk_count for d in all_docs)
            st.metric("Total Chunks", total_chunks)

        st.divider()

        # Document list
        for doc in sorted(all_docs, key=lambda x: x.created_at, reverse=True):
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    status = "✅" if doc.is_processed else "❌" if doc.processing_error else "⏳"
                    st.markdown(f"### {status} {doc.title or doc.original_filename}")

                    # Get uploader info
                    uploader = DatabaseManager.get_user_by_id(doc.uploaded_by)
                    uploader_name = uploader.username if uploader else "Unknown"
                    st.caption(f"Uploaded by: @{uploader_name}")

                with col2:
                    st.caption(f"Pages: {doc.page_count or 'N/A'}")
                    st.caption(f"Chunks: {doc.chunk_count}")
                    st.caption(f"Date: {format_datetime(doc.created_at, '%Y-%m-%d')}")

                with col3:
                    if is_superadmin:
                        if st.button("🗑️", key=f"admin_del_doc_{doc.id}", help="Delete document"):
                            from database.vector_store import DocumentIngestionPipeline
                            pipeline = DocumentIngestionPipeline()
                            pipeline.remove_document(doc.id)
                            st.success("Document deleted!")
                            st.rerun()

                if doc.processing_error:
                    st.error(f"Error: {doc.processing_error}")

                st.divider()

    with tab3:
        st.markdown("### System Settings")

        # Vector store stats
        st.markdown("#### Vector Store")

        try:
            vs = VectorStore()
            stats = vs.get_collection_stats()

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Total Chunks", stats.get('total_chunks', 0))

            with col2:
                st.metric("Unique Documents", stats.get('unique_documents', 0))

            if is_superadmin:
                st.divider()

                st.markdown("#### Danger Zone")

                with st.expander("⚠️ Reset Vector Store", expanded=False):
                    st.warning("This will delete ALL embeddings from the vector store. Documents will need to be reprocessed.")

                    if st.button("🔄 Reset Vector Store", type="secondary"):
                        vs.clear_collection()
                        # Mark all documents as unprocessed
                        for doc in all_docs:
                            DatabaseManager.update_document_status(doc.id, False, 0)
                        st.success("Vector store reset. All documents marked as unprocessed.")
                        st.rerun()

        except Exception as e:
            st.error(f"Could not load vector store: {e}")

        st.divider()

        # Database info
        st.markdown("#### Database Statistics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Users", len(all_users))

        with col2:
            st.metric("Documents", len(all_docs))

        with col3:
            # Count all sessions
            total_sessions = 0
            for u in all_users:
                sessions = DatabaseManager.get_user_sessions(u.get('id'))
                total_sessions += len(sessions)
            st.metric("Chat Sessions", total_sessions)

        # System info
        st.divider()

        st.markdown("#### System Information")

        import platform
        from config import APP_VERSION

        st.markdown(f"**App Version:** {APP_VERSION}")
        st.markdown(f"**Python Version:** {platform.python_version()}")
        st.markdown(f"**Platform:** {platform.system()} {platform.release()}")


if __name__ == "__main__":
    main()
