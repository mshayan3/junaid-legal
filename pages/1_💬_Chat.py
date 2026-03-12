"""
Chat Page - Interactive Q&A with documents
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import DatabaseManager
from rag.chain import RAGChain
from components.chat_ui import (
    render_chat_message, render_welcome_message,
    render_suggested_questions, render_metrics_bar
)

# Page config
st.set_page_config(
    page_title="Chat - Legal Document Assistant",
    page_icon="💬",
    layout="wide"
)


def init_chat_session_state():
    """Initialize chat-specific session state"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'selected_documents' not in st.session_state:
        st.session_state.selected_documents = []


def load_session_messages(session_id: int):
    """Load messages for a session"""
    messages = DatabaseManager.get_session_messages(session_id)
    st.session_state.messages = [
        {
            'role': msg.role,
            'content': msg.content,
            'sources': msg.sources,
            'id': msg.id
        }
        for msg in messages
    ]


def create_new_session(user_id: int):
    """Create a new chat session"""
    session = DatabaseManager.create_chat_session(user_id)
    st.session_state.current_session_id = session.id
    st.session_state.messages = []
    return session.id


def main():
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to access the chat.")
        st.stop()

    user = st.session_state.user
    init_chat_session_state()

    # Sidebar - Chat History
    with st.sidebar:
        st.markdown("### 💬 Chat Sessions")

        # New chat button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            create_new_session(user['id'])
            st.rerun()

        st.divider()

        # Load user's sessions
        sessions = DatabaseManager.get_user_sessions(user['id'])

        if sessions:
            for session in sessions:
                col1, col2 = st.columns([4, 1])

                with col1:
                    is_current = session.id == st.session_state.current_session_id
                    btn_type = "primary" if is_current else "secondary"

                    title = session.title[:25] + "..." if len(session.title) > 25 else session.title
                    if st.button(
                        f"{'📌 ' if is_current else ''}{title}",
                        key=f"session_{session.id}",
                        use_container_width=True,
                        type=btn_type
                    ):
                        st.session_state.current_session_id = session.id
                        load_session_messages(session.id)
                        st.rerun()

                with col2:
                    if st.button("🗑️", key=f"del_{session.id}", help="Delete"):
                        DatabaseManager.delete_session(session.id)
                        if st.session_state.current_session_id == session.id:
                            st.session_state.current_session_id = None
                            st.session_state.messages = []
                        st.rerun()
        else:
            st.caption("No previous chats")

        st.divider()

        # Document filter
        st.markdown("### 📁 Document Filter")
        docs = DatabaseManager.get_user_documents(user['id'])
        processed_docs = [d for d in docs if d.is_processed]

        if processed_docs:
            st.caption("Search in selected documents:")

            # Select all / none
            col1, col2 = st.columns(2)
            with col1:
                if st.button("All", key="select_all", use_container_width=True):
                    st.session_state.selected_documents = [d.id for d in processed_docs]
                    st.rerun()
            with col2:
                if st.button("None", key="select_none", use_container_width=True):
                    st.session_state.selected_documents = []
                    st.rerun()

            for doc in processed_docs:
                title = doc.title or doc.original_filename
                title = title[:20] + "..." if len(title) > 20 else title

                checked = st.checkbox(
                    f"📄 {title}",
                    value=doc.id in st.session_state.selected_documents,
                    key=f"doc_{doc.id}"
                )

                if checked and doc.id not in st.session_state.selected_documents:
                    st.session_state.selected_documents.append(doc.id)
                elif not checked and doc.id in st.session_state.selected_documents:
                    st.session_state.selected_documents.remove(doc.id)
        else:
            st.caption("No processed documents")
            st.info("Upload documents in the Documents page")

        st.divider()

        # Settings
        st.markdown("### ⚙️ Settings")
        show_sources = st.checkbox("Show Sources", value=True, key="show_sources")
        show_metrics = st.checkbox("Show Metrics", value=False, key="show_metrics")

    # Main content
    st.markdown("# 💬 Chat with Your Documents")

    # Create session if none exists
    if st.session_state.current_session_id is None:
        if sessions:
            # Load most recent session
            st.session_state.current_session_id = sessions[0].id
            load_session_messages(sessions[0].id)
        else:
            create_new_session(user['id'])

    # Check if documents are available
    if not processed_docs:
        st.warning("⚠️ No documents have been processed yet. Please upload documents in the Documents section first.")
        st.stop()

    # Display chat messages
    if not st.session_state.messages:
        render_welcome_message()

        # Suggested questions
        selected_question = render_suggested_questions()
        if selected_question:
            st.session_state.pending_question = selected_question
            st.rerun()

    else:
        for message in st.session_state.messages:
            render_chat_message(
                role=message['role'],
                content=message['content'],
                sources=message.get('sources'),
                show_sources=show_sources
            )

    # Handle pending question from suggested
    if 'pending_question' in st.session_state:
        query = st.session_state.pending_question
        del st.session_state.pending_question
    else:
        # Chat input
        query = st.chat_input("Ask a question about your documents...")

    if query:
        # Add user message to state
        st.session_state.messages.append({
            'role': 'user',
            'content': query,
            'sources': None
        })

        # Save user message to database
        DatabaseManager.add_message(
            session_id=st.session_state.current_session_id,
            role='user',
            content=query
        )

        # Display user message
        render_chat_message(role='user', content=query)

        # Generate response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    # Get document filter
                    filter_docs = st.session_state.selected_documents if st.session_state.selected_documents else None

                    # Initialize RAG chain
                    rag_chain = RAGChain()

                    # Generate response
                    result = rag_chain.generate_response(
                        query=query,
                        chat_history=st.session_state.messages[:-1],  # Exclude current message
                        filter_document_ids=filter_docs
                    )

                    answer = result['answer']
                    sources = result['sources']
                    metrics = result['metrics']

                    # Display answer
                    st.markdown(answer)

                    # Display sources
                    if show_sources and sources:
                        with st.expander(f"📚 Sources ({len(sources)} references)", expanded=False):
                            for source in sources:
                                col1, col2 = st.columns([3, 1])

                                with col1:
                                    location = source.get('location', 'Document')
                                    st.markdown(f"**{source.get('index', '')}. {location}**")

                                with col2:
                                    similarity = source.get('similarity', 0)
                                    st.markdown(f"Relevance: {similarity:.0%}")

                                preview = source.get('content_preview', '')
                                if preview:
                                    st.caption(preview)
                                st.divider()

                    # Display metrics
                    if show_metrics:
                        render_metrics_bar(metrics)

                    # Add assistant message to state
                    st.session_state.messages.append({
                        'role': 'assistant',
                        'content': answer,
                        'sources': sources
                    })

                    # Save to database
                    DatabaseManager.add_message(
                        session_id=st.session_state.current_session_id,
                        role='assistant',
                        content=answer,
                        sources=sources
                    )

                    # Log query for analytics
                    DatabaseManager.log_query(
                        user_id=user['id'],
                        query=query,
                        session_id=st.session_state.current_session_id,
                        retrieval_time_ms=metrics.get('retrieval_time_ms'),
                        generation_time_ms=metrics.get('generation_time_ms'),
                        total_time_ms=metrics.get('total_time_ms'),
                        chunks_retrieved=metrics.get('chunks_retrieved'),
                        avg_similarity_score=metrics.get('avg_similarity'),
                        prompt_tokens=metrics.get('prompt_tokens'),
                        completion_tokens=metrics.get('completion_tokens'),
                        total_tokens=metrics.get('total_tokens'),
                        response_length=len(answer)
                    )

                    # Update session title if first message
                    if len(st.session_state.messages) == 2:  # User + Assistant
                        title = rag_chain.generate_title(query)
                        DatabaseManager.update_session_title(
                            st.session_state.current_session_id,
                            title
                        )

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.exception(e)


if __name__ == "__main__":
    main()
