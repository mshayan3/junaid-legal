"""
Chat UI Components
"""
import streamlit as st
from typing import List, Dict, Any, Optional


def render_chat_message(
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
    message_id: Optional[int] = None,
    show_sources: bool = True
):
    """Render a chat message with optional sources"""
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)

            if show_sources and sources:
                render_sources(sources, message_id)


def render_sources(sources: List[Dict[str, Any]], message_id: Optional[int] = None):
    """Render citation sources in an expandable section"""
    if not sources:
        return

    with st.expander(f"📚 Sources ({len(sources)} references)", expanded=False):
        for source in sources:
            col1, col2 = st.columns([3, 1])

            with col1:
                location = source.get('location', 'Document')
                st.markdown(f"**{source.get('index', '')}. {location}**")

                if source.get('page_number'):
                    st.caption(f"Page {source['page_number']}")

            with col2:
                similarity = source.get('similarity', 0)
                color = "green" if similarity > 0.8 else "orange" if similarity > 0.6 else "red"
                st.markdown(
                    f"<span style='color:{color}'>Relevance: {similarity:.0%}</span>",
                    unsafe_allow_html=True
                )

            # Content preview
            preview = source.get('content_preview', '')
            if preview:
                st.caption(preview)

            st.divider()


def render_chat_input(key: str = "chat_input"):
    """Render chat input with placeholder"""
    return st.chat_input(
        placeholder="Ask a question about the documents...",
        key=key
    )


def render_welcome_message():
    """Render welcome message for new chats"""
    st.markdown("""
    ### Welcome to the Legal Document Assistant! 👋

    I can help you navigate and understand legal documents, including:
    - **Punjab Service Sales Tax Act**
    - **Related legal regulations**
    - **Definitions and interpretations**

    **How to use:**
    1. Upload your documents in the **Documents** section
    2. Ask questions in natural language
    3. Get accurate answers with citations

    **Example questions:**
    - "What is the definition of 'taxable service' under the Act?"
    - "Explain the registration requirements for service providers"
    - "What are the penalties for non-compliance?"

    ---
    *Start by typing your question below...*
    """)


def render_suggested_questions():
    """Render suggested questions for users"""
    questions = [
        "What is the scope of the Punjab Service Sales Tax Act?",
        "Who is required to register under this Act?",
        "What are the tax rates applicable?",
        "Explain the definition of 'taxable services'",
        "What are the penalties for late payment?"
    ]

    st.markdown("**💡 Suggested Questions:**")

    cols = st.columns(2)
    for i, question in enumerate(questions):
        col = cols[i % 2]
        with col:
            if st.button(question, key=f"suggested_{i}", use_container_width=True):
                return question

    return None


def render_typing_indicator():
    """Render typing indicator while waiting for response"""
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("*Thinking...*")


def render_error_message(error: str):
    """Render error message"""
    st.error(f"⚠️ An error occurred: {error}")


def render_metrics_bar(metrics: Dict[str, Any]):
    """Render performance metrics bar"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Response Time",
            f"{metrics.get('total_time_ms', 0):.0f}ms"
        )

    with col2:
        st.metric(
            "Sources Used",
            metrics.get('chunks_retrieved', 0)
        )

    with col3:
        st.metric(
            "Relevance",
            f"{metrics.get('avg_similarity', 0):.0%}"
        )

    with col4:
        st.metric(
            "Tokens Used",
            metrics.get('total_tokens', 0)
        )


def render_feedback_buttons(message_id: int):
    """Render feedback buttons for a message"""
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("👍", key=f"thumbs_up_{message_id}", help="Helpful"):
            return {"rating": 5, "feedback": "positive"}

    with col2:
        if st.button("👎", key=f"thumbs_down_{message_id}", help="Not helpful"):
            return {"rating": 1, "feedback": "negative"}

    return None
