"""
SQLAlchemy Database Models
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Float, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class User(Base):
    """User model for authentication and tracking"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="uploaded_by_user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


class Document(Base):
    """Document model for tracking uploaded PDFs"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    file_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash

    # Metadata
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)

    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_error = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)

    # Ownership
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    uploaded_by_user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.original_filename}>"


class DocumentChunk(Base):
    """Chunk model for tracking document segments"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    # Chunk content and metadata
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    # Hierarchical structure
    chapter = Column(String(255), nullable=True)
    section = Column(String(255), nullable=True)
    article = Column(String(255), nullable=True)
    page_number = Column(Integer, nullable=True)

    # Vector store reference
    chroma_id = Column(String(100), nullable=True, index=True)

    # Extra data
    char_count = Column(Integer, nullable=False)
    chunk_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk {self.document_id}:{self.chunk_index}>"


class ChatSession(Base):
    """Chat session model for organizing conversations"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session info
    title = Column(String(255), default="New Chat", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession {self.id}: {self.title}>"


class ChatMessage(Base):
    """Chat message model for storing conversation history"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)

    # Message content
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    # Citations/Sources
    sources = Column(JSON, nullable=True)  # List of source chunks

    # Feedback
    rating = Column(Integer, nullable=True)  # 1-5 rating
    feedback = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage {self.id}: {self.role}>"


class QueryLog(Base):
    """Query log for analytics"""
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)

    # Query details
    query = Column(Text, nullable=False)
    response_length = Column(Integer, nullable=True)

    # Performance metrics
    retrieval_time_ms = Column(Float, nullable=True)
    generation_time_ms = Column(Float, nullable=True)
    total_time_ms = Column(Float, nullable=True)

    # Retrieval info
    chunks_retrieved = Column(Integer, nullable=True)
    avg_similarity_score = Column(Float, nullable=True)

    # Token usage
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="query_logs")

    def __repr__(self):
        return f"<QueryLog {self.id}>"
