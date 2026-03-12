"""
Embedding Manager
Handles OpenAI embeddings generation and batch processing
"""
from typing import List, Dict, Any, Optional
import time
from openai import OpenAI

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from config import OPENAI_API_KEY, EMBEDDING_MODEL


class EmbeddingManager:
    """Manages embedding generation using OpenAI"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = EMBEDDING_MODEL,
        batch_size: int = 100,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        for attempt in range(self.retry_attempts):
            try:
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e

    def generate_embeddings_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches
        Returns list of embeddings in the same order as input texts
        """
        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        for batch_idx in range(0, len(texts), self.batch_size):
            batch = texts[batch_idx:batch_idx + self.batch_size]
            current_batch = batch_idx // self.batch_size + 1

            if show_progress:
                print(f"Processing batch {current_batch}/{total_batches}...")

            for attempt in range(self.retry_attempts):
                try:
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.model
                    )
                    # Sort by index to maintain order
                    batch_embeddings = sorted(
                        response.data,
                        key=lambda x: x.index
                    )
                    all_embeddings.extend([e.embedding for e in batch_embeddings])
                    break
                except Exception as e:
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        raise e

        return all_embeddings

    def embed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        text_key: str = 'content',
        show_progress: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Add embeddings to chunk dictionaries
        Returns chunks with 'embedding' key added
        """
        texts = [chunk[text_key] for chunk in chunks]
        embeddings = self.generate_embeddings_batch(texts, show_progress)

        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding

        return chunks

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for the current model"""
        # Generate a test embedding to get dimension
        test_embedding = self.generate_embedding("test")
        return len(test_embedding)

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
