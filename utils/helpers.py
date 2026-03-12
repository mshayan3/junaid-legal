"""
Helper Utilities
"""
from datetime import datetime
from typing import Optional, Any


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_datetime(
    dt: Any,
    format_str: str = "%Y-%m-%d %H:%M"
) -> str:
    """Format datetime object or string"""
    if dt is None:
        return "N/A"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt

    if isinstance(dt, datetime):
        return dt.strftime(format_str)

    return str(dt)


def truncate_text(
    text: str,
    max_length: int = 100,
    suffix: str = "..."
) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove or replace unsafe characters
    safe = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    safe = re.sub(r'\s+', '_', safe)
    return safe


def generate_unique_filename(original: str) -> str:
    """Generate unique filename with timestamp"""
    import uuid
    from pathlib import Path

    path = Path(original)
    stem = sanitize_filename(path.stem)
    suffix = path.suffix

    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"{stem}_{timestamp}_{unique_id}{suffix}"


def validate_pdf_file(file_path: str) -> tuple:
    """
    Validate PDF file
    Returns (is_valid, error_message)
    """
    from pathlib import Path

    path = Path(file_path)

    if not path.exists():
        return False, "File does not exist"

    if not path.suffix.lower() == '.pdf':
        return False, "File is not a PDF"

    if path.stat().st_size == 0:
        return False, "File is empty"

    # Try to open with PyMuPDF
    try:
        import fitz
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()

        if page_count == 0:
            return False, "PDF has no pages"

        return True, None

    except Exception as e:
        return False, f"Invalid PDF: {str(e)}"


def calculate_reading_time(text: str, wpm: int = 200) -> int:
    """Calculate estimated reading time in minutes"""
    word_count = len(text.split())
    return max(1, round(word_count / wpm))


def extract_keywords(text: str, top_n: int = 10) -> list:
    """Extract top keywords from text (simple frequency-based)"""
    import re
    from collections import Counter

    # Remove special characters and lowercase
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

    # Common stop words to exclude
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
        'can', 'had', 'her', 'was', 'one', 'our', 'out', 'has',
        'have', 'been', 'were', 'said', 'each', 'she', 'which',
        'their', 'will', 'other', 'about', 'many', 'then', 'them',
        'these', 'some', 'would', 'into', 'more', 'such', 'shall',
        'any', 'this', 'that', 'with', 'from'
    }

    filtered = [w for w in words if w not in stop_words]
    counter = Counter(filtered)

    return [word for word, count in counter.most_common(top_n)]
