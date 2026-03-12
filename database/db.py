"""
Database Connection and Management
"""
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from config import SQLITE_DB_PATH
from database.models import (
    Base, User, UserRole, Document, DocumentChunk,
    ChatSession, ChatMessage, QueryLog
)

# Create engine
engine = create_engine(
    f"sqlite:///{SQLITE_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def init_db():
    """Initialize the database tables"""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class DatabaseManager:
    """Database operations manager"""

    # ==================== User Operations ====================

    @staticmethod
    def create_user(
        email: str,
        username: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        full_name: Optional[str] = None
    ) -> Optional[User]:
        """Create a new user"""
        with get_db() as db:
            # Check if user exists
            existing = db.query(User).filter(
                (User.email == email) | (User.username == username)
            ).first()
            if existing:
                return None

            user = User(
                email=email,
                username=username,
                password_hash=password_hash,
                role=role,
                full_name=full_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email"""
        with get_db() as db:
            return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username"""
        with get_db() as db:
            return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID"""
        with get_db() as db:
            return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_user_login(user_id: int):
        """Update user's last login timestamp"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                db.commit()

    @staticmethod
    def get_all_users() -> List[User]:
        """Get all users"""
        with get_db() as db:
            return db.query(User).all()

    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """Update user fields"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            return True

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Delete a user"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db.delete(user)
                db.commit()
                return True
            return False

    @staticmethod
    def set_reset_token(user_id: int, token: str, expiry_hours: int = 24) -> bool:
        """Set password reset token"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.reset_token = token
                user.reset_token_expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
                db.commit()
                return True
            return False

    @staticmethod
    def verify_reset_token(token: str) -> Optional[User]:
        """Verify reset token and return user"""
        with get_db() as db:
            user = db.query(User).filter(
                User.reset_token == token,
                User.reset_token_expiry > datetime.utcnow()
            ).first()
            return user

    @staticmethod
    def clear_reset_token(user_id: int):
        """Clear reset token after use"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.reset_token = None
                user.reset_token_expiry = None
                db.commit()

    # ==================== Document Operations ====================

    @staticmethod
    def create_document(
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: int,
        file_hash: str,
        uploaded_by: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        page_count: Optional[int] = None
    ) -> Document:
        """Create a new document record"""
        with get_db() as db:
            doc = Document(
                filename=filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
                uploaded_by=uploaded_by,
                title=title or original_filename,
                description=description,
                page_count=page_count
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc

    @staticmethod
    def get_document_by_id(doc_id: int) -> Optional[Document]:
        """Get document by ID"""
        with get_db() as db:
            return db.query(Document).filter(Document.id == doc_id).first()

    @staticmethod
    def get_document_by_hash(file_hash: str) -> Optional[Document]:
        """Get document by file hash"""
        with get_db() as db:
            return db.query(Document).filter(Document.file_hash == file_hash).first()

    @staticmethod
    def get_user_documents(user_id: int) -> List[Document]:
        """Get all documents for a user"""
        with get_db() as db:
            return db.query(Document).filter(Document.uploaded_by == user_id).all()

    @staticmethod
    def get_all_documents() -> List[Document]:
        """Get all documents"""
        with get_db() as db:
            return db.query(Document).all()

    @staticmethod
    def update_document_status(
        doc_id: int,
        is_processed: bool,
        chunk_count: int = 0,
        error: Optional[str] = None
    ):
        """Update document processing status"""
        with get_db() as db:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.is_processed = is_processed
                doc.chunk_count = chunk_count
                doc.processing_error = error
                doc.processed_at = datetime.utcnow() if is_processed else None
                db.commit()

    @staticmethod
    def delete_document(doc_id: int) -> bool:
        """Delete a document and its chunks"""
        with get_db() as db:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                db.delete(doc)
                db.commit()
                return True
            return False

    # ==================== Chunk Operations ====================

    @staticmethod
    def create_chunks(doc_id: int, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Create multiple chunks for a document"""
        with get_db() as db:
            chunk_objects = []
            for chunk_data in chunks:
                chunk = DocumentChunk(
                    document_id=doc_id,
                    chunk_index=chunk_data.get('chunk_index', 0),
                    content=chunk_data['content'],
                    chapter=chunk_data.get('chapter'),
                    section=chunk_data.get('section'),
                    article=chunk_data.get('article'),
                    page_number=chunk_data.get('page_number'),
                    chroma_id=chunk_data.get('chroma_id'),
                    char_count=len(chunk_data['content']),
                    chunk_metadata=chunk_data.get('metadata')
                )
                db.add(chunk)
                chunk_objects.append(chunk)
            db.commit()
            return chunk_objects

    @staticmethod
    def get_document_chunks(doc_id: int) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        with get_db() as db:
            return db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc_id
            ).order_by(DocumentChunk.chunk_index).all()

    @staticmethod
    def get_chunk_by_chroma_id(chroma_id: str) -> Optional[DocumentChunk]:
        """Get chunk by ChromaDB ID"""
        with get_db() as db:
            return db.query(DocumentChunk).filter(
                DocumentChunk.chroma_id == chroma_id
            ).first()

    # ==================== Chat Operations ====================

    @staticmethod
    def create_chat_session(user_id: int, title: str = "New Chat") -> ChatSession:
        """Create a new chat session"""
        with get_db() as db:
            session = ChatSession(user_id=user_id, title=title)
            db.add(session)
            db.commit()
            db.refresh(session)
            return session

    @staticmethod
    def get_user_sessions(user_id: int) -> List[ChatSession]:
        """Get all chat sessions for a user"""
        with get_db() as db:
            return db.query(ChatSession).filter(
                ChatSession.user_id == user_id,
                ChatSession.is_active == True
            ).order_by(ChatSession.updated_at.desc()).all()

    @staticmethod
    def get_session_by_id(session_id: int) -> Optional[ChatSession]:
        """Get chat session by ID"""
        with get_db() as db:
            return db.query(ChatSession).filter(
                ChatSession.id == session_id
            ).first()

    @staticmethod
    def update_session_title(session_id: int, title: str):
        """Update chat session title"""
        with get_db() as db:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id
            ).first()
            if session:
                session.title = title
                db.commit()

    @staticmethod
    def delete_session(session_id: int) -> bool:
        """Delete a chat session"""
        with get_db() as db:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id
            ).first()
            if session:
                session.is_active = False  # Soft delete
                db.commit()
                return True
            return False

    @staticmethod
    def add_message(
        session_id: int,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None
    ) -> ChatMessage:
        """Add a message to a chat session"""
        with get_db() as db:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                sources=sources
            )
            db.add(message)

            # Update session timestamp
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id
            ).first()
            if session:
                session.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(message)
            return message

    @staticmethod
    def get_session_messages(session_id: int) -> List[ChatMessage]:
        """Get all messages for a session"""
        with get_db() as db:
            return db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at).all()

    @staticmethod
    def rate_message(message_id: int, rating: int, feedback: Optional[str] = None):
        """Rate a message"""
        with get_db() as db:
            message = db.query(ChatMessage).filter(
                ChatMessage.id == message_id
            ).first()
            if message:
                message.rating = rating
                message.feedback = feedback
                db.commit()

    # ==================== Analytics Operations ====================

    @staticmethod
    def log_query(
        user_id: int,
        query: str,
        session_id: Optional[int] = None,
        retrieval_time_ms: Optional[float] = None,
        generation_time_ms: Optional[float] = None,
        total_time_ms: Optional[float] = None,
        chunks_retrieved: Optional[int] = None,
        avg_similarity_score: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        response_length: Optional[int] = None
    ) -> QueryLog:
        """Log a query for analytics"""
        with get_db() as db:
            log = QueryLog(
                user_id=user_id,
                session_id=session_id,
                query=query,
                retrieval_time_ms=retrieval_time_ms,
                generation_time_ms=generation_time_ms,
                total_time_ms=total_time_ms,
                chunks_retrieved=chunks_retrieved,
                avg_similarity_score=avg_similarity_score,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                response_length=response_length
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log

    @staticmethod
    def get_analytics_summary(days: int = 30) -> Dict[str, Any]:
        """Get analytics summary for the past N days"""
        with get_db() as db:
            cutoff = datetime.utcnow() - timedelta(days=days)

            # Total queries
            total_queries = db.query(func.count(QueryLog.id)).filter(
                QueryLog.created_at >= cutoff
            ).scalar()

            # Total users
            total_users = db.query(func.count(User.id)).scalar()
            active_users = db.query(func.count(func.distinct(QueryLog.user_id))).filter(
                QueryLog.created_at >= cutoff
            ).scalar()

            # Total documents
            total_docs = db.query(func.count(Document.id)).scalar()
            processed_docs = db.query(func.count(Document.id)).filter(
                Document.is_processed == True
            ).scalar()

            # Average response time
            avg_response_time = db.query(func.avg(QueryLog.total_time_ms)).filter(
                QueryLog.created_at >= cutoff,
                QueryLog.total_time_ms.isnot(None)
            ).scalar()

            # Total tokens used
            total_tokens = db.query(func.sum(QueryLog.total_tokens)).filter(
                QueryLog.created_at >= cutoff
            ).scalar()

            # Queries per day
            queries_by_day = db.query(
                func.date(QueryLog.created_at).label('date'),
                func.count(QueryLog.id).label('count')
            ).filter(
                QueryLog.created_at >= cutoff
            ).group_by(func.date(QueryLog.created_at)).all()

            return {
                'total_queries': total_queries or 0,
                'total_users': total_users or 0,
                'active_users': active_users or 0,
                'total_documents': total_docs or 0,
                'processed_documents': processed_docs or 0,
                'avg_response_time_ms': round(avg_response_time or 0, 2),
                'total_tokens_used': total_tokens or 0,
                'queries_by_day': [
                    {'date': str(q.date), 'count': q.count}
                    for q in queries_by_day
                ]
            }

    @staticmethod
    def get_popular_queries(limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common queries"""
        with get_db() as db:
            results = db.query(
                QueryLog.query,
                func.count(QueryLog.id).label('count')
            ).group_by(QueryLog.query).order_by(
                func.count(QueryLog.id).desc()
            ).limit(limit).all()

            return [{'query': r.query, 'count': r.count} for r in results]
