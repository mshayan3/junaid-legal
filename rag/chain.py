"""
RAG Chain
Combines retrieval with LLM generation for question answering
"""
from typing import List, Dict, Any, Optional, Generator
import time
from openai import OpenAI

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from config import OPENAI_API_KEY, OPENAI_MODEL
from rag.retriever import DocumentRetriever, HybridRetriever
from rag.prompts import SYSTEM_PROMPT, get_rag_prompt, get_title_generation_prompt


class RAGChain:
    """RAG Chain for question answering with citations"""

    def __init__(
        self,
        retriever: Optional[DocumentRetriever] = None,
        api_key: Optional[str] = None,
        model: str = OPENAI_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        use_hybrid_search: bool = True
    ):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        if use_hybrid_search:
            self.retriever = retriever or HybridRetriever()
        else:
            self.retriever = retriever or DocumentRetriever()

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)

    def _format_chat_history(
        self,
        messages: List[Dict[str, str]],
        max_messages: int = 10
    ) -> str:
        """Format chat history for context"""
        if not messages:
            return ""

        # Take only recent messages
        recent = messages[-max_messages:]

        formatted = []
        for msg in recent:
            role = "User" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', '')[:500]  # Truncate long messages
            formatted.append(f"{role}: {content}")

        return '\n'.join(formatted)

    def generate_response(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        filter_document_ids: Optional[List[int]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a response for a query using RAG
        Returns response with sources and metrics
        """
        start_time = time.time()

        # Step 1: Retrieve relevant documents
        if isinstance(self.retriever, HybridRetriever):
            retrieval_result = self.retriever.retrieve_hybrid(
                query=query,
                filter_document_ids=filter_document_ids
            )
        else:
            retrieval_result = self.retriever.retrieve(
                query=query,
                filter_document_ids=filter_document_ids
            )

        retrieval_time = retrieval_result['metrics']['total_time_ms']

        # Step 2: Format context
        context = self.retriever.format_context(retrieval_result['results'])
        sources = self.retriever.get_sources_for_citation(retrieval_result['results'])

        # Step 3: Format chat history
        history_str = self._format_chat_history(chat_history) if chat_history else ""

        # Step 4: Generate prompt
        user_prompt = get_rag_prompt(context, query, history_str)

        # Step 5: Call LLM
        generation_start = time.time()

        if stream:
            return self._generate_stream(
                user_prompt=user_prompt,
                sources=sources,
                retrieval_metrics=retrieval_result['metrics'],
                start_time=start_time,
                retrieval_time=retrieval_time
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        generation_time = (time.time() - generation_start) * 1000
        total_time = (time.time() - start_time) * 1000

        # Extract response
        answer = response.choices[0].message.content

        return {
            'answer': answer,
            'sources': sources,
            'metrics': {
                'retrieval_time_ms': round(retrieval_time, 2),
                'generation_time_ms': round(generation_time, 2),
                'total_time_ms': round(total_time, 2),
                'chunks_retrieved': retrieval_result['metrics']['chunks_retrieved'],
                'avg_similarity': retrieval_result['metrics']['avg_similarity'],
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'model': self.model
            }
        }

    def _generate_stream(
        self,
        user_prompt: str,
        sources: List[Dict[str, Any]],
        retrieval_metrics: Dict[str, Any],
        start_time: float,
        retrieval_time: float
    ) -> Generator[Dict[str, Any], None, None]:
        """Generate streaming response"""
        generation_start = time.time()

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True
        )

        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield {
                    'type': 'content',
                    'content': content
                }

        generation_time = (time.time() - generation_start) * 1000
        total_time = (time.time() - start_time) * 1000

        # Yield final result with sources and metrics
        yield {
            'type': 'final',
            'answer': full_response,
            'sources': sources,
            'metrics': {
                'retrieval_time_ms': round(retrieval_time, 2),
                'generation_time_ms': round(generation_time, 2),
                'total_time_ms': round(total_time, 2),
                'chunks_retrieved': retrieval_metrics['chunks_retrieved'],
                'avg_similarity': retrieval_metrics['avg_similarity'],
                'model': self.model
            }
        }

    def generate_title(self, first_message: str) -> str:
        """Generate a title for a chat session based on the first message"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": get_title_generation_prompt(first_message)}
                ],
                temperature=0.7,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "New Chat"

    def quick_answer(self, query: str) -> str:
        """
        Quick answer without full RAG (for simple queries)
        Uses only LLM without retrieval
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content
