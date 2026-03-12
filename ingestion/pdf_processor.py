"""
PDF Processing Module
Extracts text and structure from PDF documents
"""
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import fitz  # PyMuPDF


class PDFProcessor:
    """Process PDF documents and extract structured content"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = None
        self._text_cache = {}

    def __enter__(self):
        self.doc = fitz.open(self.file_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        return Path(file_path).stat().st_size

    @property
    def page_count(self) -> int:
        """Get number of pages"""
        if self.doc:
            return len(self.doc)
        return 0

    def get_metadata(self) -> Dict[str, Any]:
        """Extract PDF metadata"""
        if not self.doc:
            return {}

        metadata = self.doc.metadata
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'keywords': metadata.get('keywords', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'page_count': self.page_count
        }

    def extract_page_text(self, page_num: int) -> str:
        """Extract text from a specific page"""
        if page_num in self._text_cache:
            return self._text_cache[page_num]

        if not self.doc or page_num >= len(self.doc):
            return ""

        page = self.doc[page_num]
        text = page.get_text("text")
        self._text_cache[page_num] = text
        return text

    def extract_all_text(self) -> str:
        """Extract all text from the document"""
        if not self.doc:
            return ""

        all_text = []
        for page_num in range(len(self.doc)):
            text = self.extract_page_text(page_num)
            all_text.append(f"[Page {page_num + 1}]\n{text}")

        return "\n\n".join(all_text)

    def extract_toc(self) -> List[Dict[str, Any]]:
        """Extract table of contents if available"""
        if not self.doc:
            return []

        toc = self.doc.get_toc()
        return [
            {
                'level': item[0],
                'title': item[1],
                'page': item[2]
            }
            for item in toc
        ]

    def extract_structured_content(self) -> List[Dict[str, Any]]:
        """
        Extract content with structure detection for legal documents
        Identifies chapters, sections, articles, etc.
        """
        if not self.doc:
            return []

        structured_content = []
        current_chapter = None
        current_section = None
        current_article = None

        # Patterns for legal document structure
        patterns = {
            'chapter': re.compile(
                r'^(?:CHAPTER|Chapter)\s+([IVXLCDM\d]+)[:\.\s]*(.*)$',
                re.MULTILINE
            ),
            'section': re.compile(
                r'^(?:SECTION|Section|SEC\.?|Sec\.?)\s+(\d+[\.\d]*)[:\.\s]*(.*)$',
                re.MULTILINE
            ),
            'article': re.compile(
                r'^(?:ARTICLE|Article|ART\.?|Art\.?)\s+(\d+[\.\d]*)[:\.\s]*(.*)$',
                re.MULTILINE
            ),
            'part': re.compile(
                r'^(?:PART|Part)\s+([IVXLCDM\d]+)[:\.\s]*(.*)$',
                re.MULTILINE
            ),
            'schedule': re.compile(
                r'^(?:SCHEDULE|Schedule)\s+([IVXLCDM\d]+)[:\.\s]*(.*)$',
                re.MULTILINE
            ),
            'rule': re.compile(
                r'^(?:RULE|Rule)\s+(\d+[\.\d]*)[:\.\s]*(.*)$',
                re.MULTILINE
            ),
            'clause': re.compile(
                r'^\((\d+)\)\s+(.*)$',
                re.MULTILINE
            ),
            'sub_clause': re.compile(
                r'^\(([a-z])\)\s+(.*)$',
                re.MULTILINE
            )
        }

        for page_num in range(len(self.doc)):
            text = self.extract_page_text(page_num)
            page_number = page_num + 1

            # Detect chapter
            chapter_match = patterns['chapter'].search(text)
            if chapter_match:
                current_chapter = f"Chapter {chapter_match.group(1)}: {chapter_match.group(2).strip()}"
                current_section = None
                current_article = None

            # Detect section
            section_matches = patterns['section'].findall(text)
            for match in section_matches:
                current_section = f"Section {match[0]}: {match[1].strip()}"
                current_article = None

            # Detect article
            article_matches = patterns['article'].findall(text)
            for match in article_matches:
                current_article = f"Article {match[0]}: {match[1].strip()}"

            # Store the content with structure
            structured_content.append({
                'page_number': page_number,
                'text': text,
                'chapter': current_chapter,
                'section': current_section,
                'article': current_article,
                'metadata': {
                    'has_chapter': chapter_match is not None,
                    'section_count': len(section_matches),
                    'article_count': len(article_matches)
                }
            })

        return structured_content

    def extract_tables(self) -> List[Dict[str, Any]]:
        """Extract tables from the document"""
        if not self.doc:
            return []

        tables = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]

            # Find tables using PyMuPDF's table detection
            try:
                page_tables = page.find_tables()
                for idx, table in enumerate(page_tables):
                    table_data = table.extract()
                    if table_data:
                        tables.append({
                            'page': page_num + 1,
                            'table_index': idx,
                            'data': table_data,
                            'rows': len(table_data),
                            'cols': len(table_data[0]) if table_data else 0
                        })
            except Exception:
                # Table detection might not be available in all versions
                pass

        return tables

    @staticmethod
    def process_file(file_path: str) -> Dict[str, Any]:
        """
        Complete processing of a PDF file
        Returns all extracted information
        """
        result = {
            'success': False,
            'error': None,
            'file_hash': None,
            'file_size': None,
            'metadata': {},
            'page_count': 0,
            'toc': [],
            'structured_content': [],
            'full_text': '',
            'tables': []
        }

        try:
            result['file_hash'] = PDFProcessor.calculate_file_hash(file_path)
            result['file_size'] = PDFProcessor.get_file_size(file_path)

            with PDFProcessor(file_path) as processor:
                result['metadata'] = processor.get_metadata()
                result['page_count'] = processor.page_count
                result['toc'] = processor.extract_toc()
                result['structured_content'] = processor.extract_structured_content()
                result['full_text'] = processor.extract_all_text()
                result['tables'] = processor.extract_tables()
                result['success'] = True

        except Exception as e:
            result['error'] = str(e)

        return result
