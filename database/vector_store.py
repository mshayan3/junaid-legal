"""
ChromaDB Vector Store Manager
Handles document embeddings storage and retrieval
"""
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from config import CHROMA_DIR, TOP_K_RESULTS, SIMILARITY_THRESHOLD


class VectorStore:
    """ChromaDB Vector Store Manager"""

    def __init__(
        self,
        collection_name: str = "legal_documents",
        persist_directory: str = None
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory or str(CHROMA_DIR)

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> List[str]:
        """
        Add documents with embeddings to the vector store
        Returns list of IDs
        """
        if len(documents) != len(embeddings):
            raise ValueError("Documents and embeddings must have the same length")

        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            doc_id = doc.get('chroma_id') or f"doc_{doc.get('document_id', 0)}_{doc.get('chunk_index', 0)}"
            ids.append(doc_id)
            texts.append(doc.get('content', ''))
            metadatas.append({
                'document_id': str(doc.get('document_id', '')),
                'chunk_index': str(doc.get('chunk_index', 0)),
                'chapter': doc.get('chapter') or '',
                'section': doc.get('section') or '',
                'article': doc.get('article') or '',
                'page_number': str(doc.get('page_number', '')),
            })

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        return ids

    def query(
        self,
        query_embedding: List[float],
        n_results: int = TOP_K_RESULTS,
        filter_document_ids: Optional[List[int]] = None,
        min_similarity: float = SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents
        Returns list of results with similarity scores
        """
        where_filter = None
        if filter_document_ids:
            where_filter = {
                "document_id": {"$in": [str(d) for d in filter_document_ids]}
            }

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Process results
        processed_results = []

        if results and results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                # Convert distance to similarity (cosine distance to similarity)
                distance = results['distances'][0][i] if results['distances'] else 0
                similarity = 1 - distance  # For cosine distance

                if similarity >= min_similarity:
                    processed_results.append({
                        'id': doc_id,
                        'content': results['documents'][0][i] if results['documents'] else '',
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'similarity': round(similarity, 4),
                        'distance': round(distance, 4)
                    })

        return processed_results

    def delete_by_document_id(self, document_id: int) -> int:
        """
        Delete all chunks for a specific document
        Returns number of deleted items
        """
        # Get all IDs for this document
        results = self.collection.get(
            where={"document_id": str(document_id)},
            include=[]
        )

        if results and results['ids']:
            self.collection.delete(ids=results['ids'])
            return len(results['ids'])

        return 0

    def delete_by_ids(self, ids: List[str]) -> int:
        """Delete documents by their IDs"""
        if ids:
            self.collection.delete(ids=ids)
            return len(ids)
        return 0

    def get_document_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document"""
        results = self.collection.get(
            where={"document_id": str(document_id)},
            include=["documents", "metadatas"]
        )

        chunks = []
        if results and results['ids']:
            for i, chunk_id in enumerate(results['ids']):
                chunks.append({
                    'id': chunk_id,
                    'content': results['documents'][i] if results['documents'] else '',
                    'metadata': results['metadatas'][i] if results['metadatas'] else {}
                })

        return chunks

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        count = self.collection.count()

        # Get unique document IDs
        results = self.collection.get(include=["metadatas"])
        document_ids = set()

        if results and results['metadatas']:
            for metadata in results['metadatas']:
                if metadata and 'document_id' in metadata:
                    document_ids.add(metadata['document_id'])

        return {
            'total_chunks': count,
            'unique_documents': len(document_ids),
            'collection_name': self.collection_name
        }

    def clear_collection(self):
        """Clear all documents from the collection"""
        # Delete and recreate the collection
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def update_document(
        self,
        doc_id: str,
        embedding: Optional[List[float]] = None,
        document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update a specific document"""
        update_kwargs = {"ids": [doc_id]}

        if embedding is not None:
            update_kwargs["embeddings"] = [embedding]
        if document is not None:
            update_kwargs["documents"] = [document]
        if metadata is not None:
            # Convert all values to strings for ChromaDB
            update_kwargs["metadatas"] = [{
                k: str(v) if v is not None else ''
                for k, v in metadata.items()
            }]

        self.collection.update(**update_kwargs)


class DocumentIngestionPipeline:
    """
    Complete pipeline for document ingestion
    Handles PDF processing, chunking, embedding, and storage
    """

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()

    def ingest_document(
        self,
        file_path: str,
        document_id: int,
        user_id: int,
        show_progress: bool = False
    ) -> Tuple[bool, str, int]:
        """
        Complete document ingestion pipeline
        Returns (success, message, chunk_count)
        """
        from ingestion.pdf_processor import PDFProcessor
        from ingestion.chunker import process_and_chunk_document
        from ingestion.embeddings import EmbeddingManager
        from database.db import DatabaseManager

        try:
            # Step 1: Process PDF
            if show_progress:
                print("Processing PDF...")

            pdf_result = PDFProcessor.process_file(file_path)

            if not pdf_result['success']:
                return False, f"PDF processing failed: {pdf_result['error']}", 0

            # Step 2: Chunk document
            if show_progress:
                print("Chunking document...")

            chunks = process_and_chunk_document(
                pdf_result['structured_content'],
                document_id=document_id
            )

            if not chunks:
                return False, "No content could be extracted from the document", 0

            # Step 3: Generate embeddings
            if show_progress:
                print(f"Generating embeddings for {len(chunks)} chunks...")

            embedding_manager = EmbeddingManager()
            chunks_with_embeddings = embedding_manager.embed_chunks(
                chunks,
                show_progress=show_progress
            )

            # Step 4: Store in vector database
            if show_progress:
                print("Storing in vector database...")

            embeddings = [c['embedding'] for c in chunks_with_embeddings]
            self.vector_store.add_documents(chunks_with_embeddings, embeddings)

            # Step 5: Store chunk metadata in SQLite
            if show_progress:
                print("Storing chunk metadata...")

            # Remove embeddings before storing in SQLite (too large)
            for chunk in chunks_with_embeddings:
                chunk.pop('embedding', None)

            DatabaseManager.create_chunks(document_id, chunks_with_embeddings)

            # Step 6: Update document status
            DatabaseManager.update_document_status(
                document_id,
                is_processed=True,
                chunk_count=len(chunks)
            )

            return True, f"Successfully processed {len(chunks)} chunks", len(chunks)

        except Exception as e:
            # Update document with error
            DatabaseManager.update_document_status(
                document_id,
                is_processed=False,
                error=str(e)
            )
            return False, f"Ingestion failed: {str(e)}", 0

    def remove_document(self, document_id: int) -> Tuple[bool, str]:
        """
        Remove a document from the vector store and database
        Returns (success, message)
        """
        from database.db import DatabaseManager

        try:
            # Remove from vector store
            deleted_count = self.vector_store.delete_by_document_id(document_id)

            # Remove from database (cascades to chunks)
            DatabaseManager.delete_document(document_id)

            return True, f"Removed document and {deleted_count} chunks"

        except Exception as e:
            return False, f"Failed to remove document: {str(e)}"
