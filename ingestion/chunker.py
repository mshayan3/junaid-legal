"""
Smart Hierarchical Chunker for Legal Documents
Preserves document structure (chapters, sections, articles) in chunks
"""
import re
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from config import CHUNK_SIZE, CHUNK_OVERLAP


@dataclass
class Chunk:
    """Represents a document chunk with metadata"""
    content: str
    chunk_index: int
    document_id: Optional[int] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    article: Optional[str] = None
    page_number: Optional[int] = None
    chroma_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'chunk_index': self.chunk_index,
            'document_id': self.document_id,
            'chapter': self.chapter,
            'section': self.section,
            'article': self.article,
            'page_number': self.page_number,
            'chroma_id': self.chroma_id,
            'metadata': self.metadata
        }


class HierarchicalChunker:
    """
    Smart chunker that preserves document hierarchy
    Designed for legal documents with chapters, sections, articles
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        include_hierarchy_context: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.include_hierarchy_context = include_hierarchy_context

        # Patterns for structure detection
        self.patterns = {
            'chapter': re.compile(
                r'^(?:CHAPTER|Chapter)\s+([IVXLCDM\d]+)[:\.\s]*(.*)$',
                re.MULTILINE
            ),
            'section': re.compile(
                r'^(?:SECTION|Section|SEC\.?|Sec\.?)\s+(\d+[\.\d]*)[:\.\s-]*(.*)$',
                re.MULTILINE
            ),
            'article': re.compile(
                r'^(?:ARTICLE|Article|ART\.?|Art\.?)\s+(\d+[\.\d]*)[:\.\s-]*(.*)$',
                re.MULTILINE
            ),
            'part': re.compile(
                r'^(?:PART|Part)\s+([IVXLCDM\d]+)[:\.\s-]*(.*)$',
                re.MULTILINE
            ),
            'schedule': re.compile(
                r'^(?:SCHEDULE|Schedule)\s+([IVXLCDM\d]+)[:\.\s-]*(.*)$',
                re.MULTILINE
            ),
            'definition': re.compile(
                r'^["\']([^"\']+)["\']:\s*(.*)$',
                re.MULTILINE
            ),
            'numbered_item': re.compile(
                r'^(\d+)\.\s+(.*)$',
                re.MULTILINE
            ),
            'lettered_item': re.compile(
                r'^\(([a-z])\)\s+(.*)$',
                re.MULTILINE
            )
        }

    def _detect_structure(self, text: str) -> Dict[str, Any]:
        """Detect hierarchical structure in text"""
        structure = {
            'chapter': None,
            'section': None,
            'article': None,
            'part': None,
            'schedule': None
        }

        for key, pattern in self.patterns.items():
            if key in structure:
                match = pattern.search(text)
                if match:
                    structure[key] = f"{key.title()} {match.group(1)}: {match.group(2).strip()}"

        return structure

    def _create_context_prefix(
        self,
        chapter: Optional[str],
        section: Optional[str],
        article: Optional[str]
    ) -> str:
        """Create hierarchical context prefix for chunk"""
        parts = []
        if chapter:
            parts.append(f"[{chapter}]")
        if section:
            parts.append(f"[{section}]")
        if article:
            parts.append(f"[{article}]")

        if parts:
            return " > ".join(parts) + "\n\n"
        return ""

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving structure"""
        # Handle common legal abbreviations
        text = re.sub(r'\b(Sec|Art|Ch|No|Vol|vs|etc|Inc|Ltd|Mr|Mrs|Dr|Jr|Sr)\.', r'\1<DOT>', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Restore dots
        sentences = [s.replace('<DOT>', '.') for s in sentences]

        return [s.strip() for s in sentences if s.strip()]

    def _smart_split(
        self,
        text: str,
        page_number: Optional[int] = None,
        current_chapter: Optional[str] = None,
        current_section: Optional[str] = None,
        current_article: Optional[str] = None
    ) -> List[Chunk]:
        """
        Smart splitting that respects document structure
        Tries to keep related content together
        """
        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk = []
        current_length = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # Check for structure changes
            structure = self._detect_structure(sentence)
            if structure['chapter']:
                current_chapter = structure['chapter']
            if structure['section']:
                current_section = structure['section']
            if structure['article']:
                current_article = structure['article']

            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk with current content
                chunk_content = ' '.join(current_chunk)

                # Add hierarchical context if enabled
                if self.include_hierarchy_context:
                    context = self._create_context_prefix(
                        current_chapter, current_section, current_article
                    )
                    chunk_content = context + chunk_content

                chunks.append(Chunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    chapter=current_chapter,
                    section=current_section,
                    article=current_article,
                    page_number=page_number,
                    chroma_id=str(uuid.uuid4()),
                    metadata={
                        'char_count': len(chunk_content),
                        'sentence_count': len(current_chunk)
                    }
                ))

                # Start new chunk with overlap
                overlap_sentences = []
                overlap_length = 0

                # Add sentences from the end for overlap
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break

                current_chunk = overlap_sentences
                current_length = overlap_length
                chunk_index += 1

            current_chunk.append(sentence)
            current_length += sentence_length

        # Don't forget the last chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)

            if self.include_hierarchy_context:
                context = self._create_context_prefix(
                    current_chapter, current_section, current_article
                )
                chunk_content = context + chunk_content

            chunks.append(Chunk(
                content=chunk_content,
                chunk_index=chunk_index,
                chapter=current_chapter,
                section=current_section,
                article=current_article,
                page_number=page_number,
                chroma_id=str(uuid.uuid4()),
                metadata={
                    'char_count': len(chunk_content),
                    'sentence_count': len(current_chunk)
                }
            ))

        return chunks

    def chunk_document(
        self,
        structured_content: List[Dict[str, Any]],
        document_id: Optional[int] = None
    ) -> List[Chunk]:
        """
        Chunk a document using structured content from PDFProcessor
        Maintains hierarchical context across pages
        """
        all_chunks = []
        global_chunk_index = 0

        current_chapter = None
        current_section = None
        current_article = None

        for page_content in structured_content:
            page_num = page_content.get('page_number')
            text = page_content.get('text', '')

            # Update hierarchy from page metadata
            if page_content.get('chapter'):
                current_chapter = page_content['chapter']
            if page_content.get('section'):
                current_section = page_content['section']
            if page_content.get('article'):
                current_article = page_content['article']

            # Chunk this page's content
            page_chunks = self._smart_split(
                text,
                page_number=page_num,
                current_chapter=current_chapter,
                current_section=current_section,
                current_article=current_article
            )

            # Update global indices
            for chunk in page_chunks:
                chunk.chunk_index = global_chunk_index
                chunk.document_id = document_id
                global_chunk_index += 1

            all_chunks.extend(page_chunks)

        return all_chunks

    def chunk_text(
        self,
        text: str,
        document_id: Optional[int] = None
    ) -> List[Chunk]:
        """
        Simple text chunking without page structure
        Still detects and preserves hierarchy
        """
        chunks = self._smart_split(text)

        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.document_id = document_id

        return chunks

    @staticmethod
    def merge_small_chunks(
        chunks: List[Chunk],
        min_size: int = 200
    ) -> List[Chunk]:
        """Merge chunks that are too small"""
        if not chunks:
            return chunks

        merged = []
        buffer = None

        for chunk in chunks:
            if buffer is None:
                buffer = chunk
            elif len(buffer.content) < min_size:
                # Merge with current chunk
                buffer.content = buffer.content + "\n\n" + chunk.content
                buffer.metadata['merged'] = True
            else:
                merged.append(buffer)
                buffer = chunk

        if buffer:
            merged.append(buffer)

        # Re-index
        for i, chunk in enumerate(merged):
            chunk.chunk_index = i

        return merged


def process_and_chunk_document(
    structured_content: List[Dict[str, Any]],
    document_id: Optional[int] = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Convenience function to process and chunk a document
    Returns list of chunk dictionaries ready for database storage
    """
    chunker = HierarchicalChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks = chunker.chunk_document(structured_content, document_id)
    chunks = chunker.merge_small_chunks(chunks)

    return [chunk.to_dict() for chunk in chunks]
