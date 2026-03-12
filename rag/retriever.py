"""
Document Retriever
Handles semantic search and context retrieval
"""
from typing import List, Dict, Any, Optional
import time

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from database.vector_store import VectorStore
from ingestion.embeddings import EmbeddingManager
from config import TOP_K_RESULTS, SIMILARITY_THRESHOLD


class DocumentRetriever:
    """Retrieves relevant document chunks for queries"""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        top_k: int = TOP_K_RESULTS,
        min_similarity: float = SIMILARITY_THRESHOLD
    ):
        self.vector_store = vector_store or VectorStore()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.top_k = top_k
        self.min_similarity = min_similarity

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_document_ids: Optional[List[int]] = None,
        min_similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant documents for a query
        Returns results with timing information
        """
        start_time = time.time()

        # Generate query embedding
        query_embedding = self.embedding_manager.generate_embedding(query)
        embedding_time = time.time() - start_time

        # Search vector store
        search_start = time.time()
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k or self.top_k,
            filter_document_ids=filter_document_ids,
            min_similarity=min_similarity or self.min_similarity
        )
        search_time = time.time() - search_start

        total_time = time.time() - start_time

        # Calculate average similarity
        avg_similarity = 0.0
        if results:
            avg_similarity = sum(r['similarity'] for r in results) / len(results)

        return {
            'results': results,
            'query': query,
            'metrics': {
                'embedding_time_ms': round(embedding_time * 1000, 2),
                'search_time_ms': round(search_time * 1000, 2),
                'total_time_ms': round(total_time * 1000, 2),
                'chunks_retrieved': len(results),
                'avg_similarity': round(avg_similarity, 4)
            }
        }

    def format_context(
        self,
        results: List[Dict[str, Any]],
        include_metadata: bool = True,
        max_context_length: int = 8000
    ) -> str:
        """
        Format retrieved results into context string for LLM
        """
        if not results:
            return "No relevant context found in the documents."

        context_parts = []
        current_length = 0

        for i, result in enumerate(results, 1):
            content = result.get('content', '')
            metadata = result.get('metadata', {})

            # Build context entry
            entry_parts = [f"--- Source {i} ---"]

            if include_metadata:
                location_parts = []
                if metadata.get('chapter'):
                    location_parts.append(metadata['chapter'])
                if metadata.get('section'):
                    location_parts.append(metadata['section'])
                if metadata.get('article'):
                    location_parts.append(metadata['article'])
                if metadata.get('page_number'):
                    location_parts.append(f"Page {metadata['page_number']}")

                if location_parts:
                    entry_parts.append(f"Location: {' > '.join(location_parts)}")

                entry_parts.append(f"Relevance: {result.get('similarity', 0):.2%}")

            entry_parts.append(f"\n{content}")
            entry = '\n'.join(entry_parts)

            # Check if adding this would exceed max length
            if current_length + len(entry) > max_context_length:
                break

            context_parts.append(entry)
            current_length += len(entry)

        return '\n\n'.join(context_parts)

    def get_sources_for_citation(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format sources for citation display in UI
        """
        sources = []

        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})

            source = {
                'index': i,
                'content_preview': result.get('content', '')[:200] + '...',
                'similarity': result.get('similarity', 0),
                'chapter': metadata.get('chapter'),
                'section': metadata.get('section'),
                'article': metadata.get('article'),
                'page_number': metadata.get('page_number'),
                'document_id': metadata.get('document_id')
            }

            # Create location string
            location_parts = []
            if source['chapter']:
                location_parts.append(source['chapter'])
            if source['section']:
                location_parts.append(source['section'])
            if source['article']:
                location_parts.append(source['article'])

            source['location'] = ' > '.join(location_parts) if location_parts else 'Document'
            sources.append(source)

        return sources


class HybridRetriever(DocumentRetriever):
    """
    Enhanced retriever with hybrid search capabilities
    Combines semantic search with keyword matching
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyword_boost(
        self,
        results: List[Dict[str, Any]],
        query: str,
        boost_factor: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Boost results that contain exact query terms
        """
        query_terms = set(query.lower().split())

        for result in results:
            content = result.get('content', '').lower()
            matching_terms = sum(1 for term in query_terms if term in content)
            term_ratio = matching_terms / len(query_terms) if query_terms else 0

            # Apply boost
            original_sim = result.get('similarity', 0)
            boosted_sim = min(1.0, original_sim + (boost_factor * term_ratio))
            result['similarity'] = boosted_sim
            result['keyword_boost'] = term_ratio

        # Re-sort by boosted similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results

    def retrieve_hybrid(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_document_ids: Optional[List[int]] = None,
        use_keyword_boost: bool = True
    ) -> Dict[str, Any]:
        """
        Hybrid retrieval combining semantic and keyword search
        """
        # Get semantic search results
        retrieval_result = self.retrieve(
            query=query,
            top_k=(top_k or self.top_k) * 2,  # Get more for re-ranking
            filter_document_ids=filter_document_ids
        )

        results = retrieval_result['results']

        # Apply keyword boost if enabled
        if use_keyword_boost and results:
            results = self.keyword_boost(results, query)

        # Trim to requested top_k
        results = results[:top_k or self.top_k]

        retrieval_result['results'] = results
        retrieval_result['metrics']['hybrid_search'] = use_keyword_boost

        return retrieval_result
