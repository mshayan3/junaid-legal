"""
Configuration settings for the RAG Application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
DB_DIR = DATA_DIR / "database"
CHROMA_DIR = DATA_DIR / "chroma_db"
EXPORTS_DIR = DATA_DIR / "exports"

# Create directories if they don't exist
for dir_path in [DATA_DIR, PDF_DIR, DB_DIR, CHROMA_DIR, EXPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Database settings
SQLITE_DB_PATH = DB_DIR / "app.db"

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Chunking settings
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval settings
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

# Session settings
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

# App settings
APP_NAME = "Legal Document Assistant"
APP_DESCRIPTION = "AI-powered assistant for Punjab Service Sales Tax Act and legal documents"
APP_VERSION = "1.0.0"

# Admin default credentials (change in production!)
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

# Rate limiting
MAX_QUERIES_PER_HOUR = int(os.getenv("MAX_QUERIES_PER_HOUR", "100"))
MAX_DOCUMENTS_PER_USER = int(os.getenv("MAX_DOCUMENTS_PER_USER", "50"))

# Export settings
MAX_EXPORT_MESSAGES = int(os.getenv("MAX_EXPORT_MESSAGES", "1000"))
