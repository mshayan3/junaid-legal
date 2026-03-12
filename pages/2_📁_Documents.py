"""
Documents Page - Upload and manage PDF documents
"""
import streamlit as st
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import PDF_DIR
from database.db import DatabaseManager
from database.vector_store import VectorStore, DocumentIngestionPipeline
from ingestion.pdf_processor import PDFProcessor
from utils.helpers import generate_unique_filename, format_file_size, format_datetime
from components.cards import render_document_card

# Page config
st.set_page_config(
    page_title="Documents - Legal Document Assistant",
    page_icon="📁",
    layout="wide"
)


def save_uploaded_file(uploaded_file, user_id: int) -> dict:
    """Save uploaded file and create database record"""
    # Generate unique filename
    unique_filename = generate_unique_filename(uploaded_file.name)
    file_path = PDF_DIR / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Calculate hash
    file_hash = PDFProcessor.calculate_file_hash(str(file_path))

    # Check for duplicates
    existing = DatabaseManager.get_document_by_hash(file_hash)
    if existing:
        # Remove the saved file
        file_path.unlink()
        return {
            'success': False,
            'error': 'Document already exists',
            'existing_id': existing.id
        }

    # Get PDF info
    try:
        with PDFProcessor(str(file_path)) as processor:
            page_count = processor.page_count
            metadata = processor.get_metadata()
            title = metadata.get('title') or uploaded_file.name
    except Exception as e:
        file_path.unlink()
        return {
            'success': False,
            'error': f'Invalid PDF: {str(e)}'
        }

    # Create database record
    doc = DatabaseManager.create_document(
        filename=unique_filename,
        original_filename=uploaded_file.name,
        file_path=str(file_path),
        file_size=uploaded_file.size,
        file_hash=file_hash,
        uploaded_by=user_id,
        title=title,
        page_count=page_count
    )

    return {
        'success': True,
        'document': doc,
        'document_id': doc.id
    }


def process_document(document_id: int):
    """Process a document and create embeddings"""
    doc = DatabaseManager.get_document_by_id(document_id)
    if not doc:
        return False, "Document not found"

    pipeline = DocumentIngestionPipeline()
    success, message, chunk_count = pipeline.ingest_document(
        file_path=doc.file_path,
        document_id=document_id,
        user_id=doc.uploaded_by,
        show_progress=False
    )

    return success, message


def delete_document(document_id: int):
    """Delete a document and its embeddings"""
    doc = DatabaseManager.get_document_by_id(document_id)
    if not doc:
        return False, "Document not found"

    # Remove from vector store
    pipeline = DocumentIngestionPipeline()
    success, message = pipeline.remove_document(document_id)

    # Remove file
    try:
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass

    return success, message


def main():
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to access documents.")
        st.stop()

    user = st.session_state.user

    st.markdown("# 📁 Document Management")
    st.markdown("Upload, manage, and process your legal documents.")

    # Tabs for different views
    tab1, tab2 = st.tabs(["📤 Upload", "📋 My Documents"])

    with tab1:
        st.markdown("### Upload New Documents")
        st.caption("Supported format: PDF")

        # File uploader
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Select one or more PDF files to upload"
        )

        if uploaded_files:
            st.markdown(f"**{len(uploaded_files)} file(s) selected**")

            # Preview uploaded files
            for file in uploaded_files:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(file.name)
                with col2:
                    st.caption(format_file_size(file.size))
                with col3:
                    st.caption("PDF")

            st.divider()

            # Auto-process option
            auto_process = st.checkbox(
                "Automatically process documents after upload",
                value=True,
                help="Create embeddings immediately after upload"
            )

            # Upload button
            if st.button("📤 Upload Documents", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()

                results = []
                total = len(uploaded_files)

                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {file.name}...")
                    progress_bar.progress((i + 0.5) / total)

                    # Save file
                    result = save_uploaded_file(file, user['id'])
                    result['filename'] = file.name

                    if result['success'] and auto_process:
                        status_text.text(f"Processing {file.name}...")
                        success, message = process_document(result['document_id'])
                        result['processed'] = success
                        result['process_message'] = message

                    results.append(result)
                    progress_bar.progress((i + 1) / total)

                status_text.empty()
                progress_bar.empty()

                # Show results
                st.markdown("### Upload Results")

                success_count = sum(1 for r in results if r['success'])
                fail_count = len(results) - success_count

                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"✅ {success_count} uploaded successfully")
                with col2:
                    if fail_count > 0:
                        st.error(f"❌ {fail_count} failed")

                for result in results:
                    if result['success']:
                        if auto_process and result.get('processed'):
                            st.success(f"✅ {result['filename']} - Uploaded and processed")
                        elif auto_process:
                            st.warning(f"⚠️ {result['filename']} - Uploaded but processing failed: {result.get('process_message', 'Unknown error')}")
                        else:
                            st.info(f"📄 {result['filename']} - Uploaded (pending processing)")
                    else:
                        st.error(f"❌ {result['filename']} - {result.get('error', 'Unknown error')}")

    with tab2:
        st.markdown("### Your Documents")

        # Get user's documents
        documents = DatabaseManager.get_user_documents(user['id'])

        if not documents:
            st.info("No documents uploaded yet. Go to the Upload tab to add documents.")
        else:
            # Stats
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Documents", len(documents))

            with col2:
                processed = sum(1 for d in documents if d.is_processed)
                st.metric("Processed", processed)

            with col3:
                pending = sum(1 for d in documents if not d.is_processed and not d.processing_error)
                st.metric("Pending", pending)

            with col4:
                failed = sum(1 for d in documents if d.processing_error)
                st.metric("Failed", failed)

            st.divider()

            # Filter options
            col1, col2 = st.columns([2, 1])
            with col1:
                filter_status = st.selectbox(
                    "Filter by status",
                    options=["All", "Processed", "Pending", "Failed"],
                    index=0
                )
            with col2:
                sort_by = st.selectbox(
                    "Sort by",
                    options=["Newest first", "Oldest first", "Name A-Z", "Name Z-A"],
                    index=0
                )

            # Apply filters
            filtered_docs = documents

            if filter_status == "Processed":
                filtered_docs = [d for d in documents if d.is_processed]
            elif filter_status == "Pending":
                filtered_docs = [d for d in documents if not d.is_processed and not d.processing_error]
            elif filter_status == "Failed":
                filtered_docs = [d for d in documents if d.processing_error]

            # Apply sorting
            if sort_by == "Newest first":
                filtered_docs = sorted(filtered_docs, key=lambda x: x.created_at, reverse=True)
            elif sort_by == "Oldest first":
                filtered_docs = sorted(filtered_docs, key=lambda x: x.created_at)
            elif sort_by == "Name A-Z":
                filtered_docs = sorted(filtered_docs, key=lambda x: x.original_filename.lower())
            elif sort_by == "Name Z-A":
                filtered_docs = sorted(filtered_docs, key=lambda x: x.original_filename.lower(), reverse=True)

            st.divider()

            # Display documents
            for doc in filtered_docs:
                with st.container():
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        # Status indicator
                        if doc.is_processed:
                            status = "✅ Processed"
                            status_color = "green"
                        elif doc.processing_error:
                            status = "❌ Failed"
                            status_color = "red"
                        else:
                            status = "⏳ Pending"
                            status_color = "orange"

                        title = doc.title or doc.original_filename
                        st.markdown(f"### 📄 {title}")

                        # Metadata
                        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

                        with meta_col1:
                            st.caption(f"📄 Pages: {doc.page_count or 'N/A'}")

                        with meta_col2:
                            st.caption(f"🧩 Chunks: {doc.chunk_count}")

                        with meta_col3:
                            st.caption(f"💾 {format_file_size(doc.file_size)}")

                        with meta_col4:
                            st.caption(f"📅 {format_datetime(doc.created_at, '%Y-%m-%d')}")

                        # Status badge
                        st.markdown(f"**Status:** :{status_color}[{status}]")

                        if doc.processing_error:
                            st.error(f"Error: {doc.processing_error}")

                    with col2:
                        # Action buttons
                        if not doc.is_processed and not doc.processing_error:
                            if st.button("🔄 Process", key=f"process_{doc.id}"):
                                with st.spinner("Processing..."):
                                    success, message = process_document(doc.id)
                                    if success:
                                        st.success("Document processed!")
                                        st.rerun()
                                    else:
                                        st.error(message)

                        if doc.processing_error:
                            if st.button("🔄 Retry", key=f"retry_{doc.id}"):
                                with st.spinner("Reprocessing..."):
                                    success, message = process_document(doc.id)
                                    if success:
                                        st.success("Document processed!")
                                        st.rerun()
                                    else:
                                        st.error(message)

                        if st.button("🗑️ Delete", key=f"delete_{doc.id}", type="secondary"):
                            success, message = delete_document(doc.id)
                            if success:
                                st.success("Document deleted!")
                                st.rerun()
                            else:
                                st.error(message)

                    st.divider()

            # Bulk actions
            if len(filtered_docs) > 1:
                st.markdown("### Bulk Actions")

                col1, col2 = st.columns(2)

                with col1:
                    pending_docs = [d for d in filtered_docs if not d.is_processed and not d.processing_error]
                    if pending_docs:
                        if st.button(f"🔄 Process All Pending ({len(pending_docs)})", use_container_width=True):
                            progress = st.progress(0)
                            for i, doc in enumerate(pending_docs):
                                process_document(doc.id)
                                progress.progress((i + 1) / len(pending_docs))
                            st.success("All pending documents processed!")
                            st.rerun()

                with col2:
                    if st.button("🗑️ Delete All Failed", use_container_width=True, type="secondary"):
                        failed_docs = [d for d in filtered_docs if d.processing_error]
                        for doc in failed_docs:
                            delete_document(doc.id)
                        st.success(f"Deleted {len(failed_docs)} failed documents!")
                        st.rerun()


if __name__ == "__main__":
    main()
