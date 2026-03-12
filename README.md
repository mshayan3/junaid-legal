# Legal Document Assistant

A professional-grade RAG (Retrieval-Augmented Generation) application built with Streamlit for querying legal documents like the Punjab Service Sales Tax Act.

## Features

### Core Features
- **Interactive Chat Interface**: Natural language Q&A with your legal documents
- **Smart Document Processing**: Hierarchical chunking that preserves chapter/section/article structure
- **Citation Tracking**: Every answer includes sources with exact document locations
- **Multi-Document Support**: Upload and query across multiple PDF documents

### User Management
- **Full Authentication System**: Login, registration, password reset
- **Role-Based Access**: User, Admin, and Super Admin roles
- **User Profiles**: Customizable profiles and preferences

### Document Management
- **Easy Upload**: Drag-and-drop PDF upload
- **Automatic Processing**: Documents are automatically chunked and embedded
- **Document Library**: View, manage, and delete your documents
- **Duplicate Detection**: Prevents uploading the same document twice

### Analytics & Insights
- **Usage Dashboard**: Track queries, response times, and token usage
- **Popular Queries**: See what questions are being asked most
- **Performance Metrics**: Monitor system performance

### Export & Data Management
- **Chat Export**: Export conversations in Markdown, Text, HTML, or JSON
- **Analytics Reports**: Export usage reports
- **Data Control**: Full control over your data with export and delete options

## Tech Stack

- **Frontend**: Streamlit
- **LLM**: OpenAI GPT-4o-mini (configurable)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector Database**: ChromaDB
- **Database**: SQLite with SQLAlchemy ORM
- **PDF Processing**: PyMuPDF

## Installation

### Prerequisites
- Python 3.9 or higher
- OpenAI API key

### Setup Steps

1. **Clone or Download the Project**
   ```bash
   cd "rag implementation"
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env and add your OpenAI API key
   # OPENAI_API_KEY=your-api-key-here
   ```

5. **Run the Application**
   ```bash
   streamlit run app.py
   ```

6. **Access the Application**
   Open your browser and go to `http://localhost:8501`

## Default Admin Credentials

- **Email**: admin@example.com
- **Password**: admin123

**Important**: Change these credentials immediately after first login!

## Project Structure

```
rag implementation/
├── app.py                      # Main Streamlit application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── README.md                  # This file
│
├── auth/                      # Authentication module
│   ├── __init__.py
│   ├── authentication.py      # Auth logic
│   └── utils.py               # Password hashing, validation
│
├── database/                  # Database module
│   ├── __init__.py
│   ├── db.py                  # Database manager
│   ├── models.py              # SQLAlchemy models
│   └── vector_store.py        # ChromaDB operations
│
├── ingestion/                 # Document processing
│   ├── __init__.py
│   ├── pdf_processor.py       # PDF extraction
│   ├── chunker.py             # Hierarchical chunking
│   └── embeddings.py          # Embedding generation
│
├── rag/                       # RAG components
│   ├── __init__.py
│   ├── retriever.py           # Document retrieval
│   ├── chain.py               # RAG chain
│   └── prompts.py             # System prompts
│
├── pages/                     # Streamlit pages
│   ├── 1_💬_Chat.py           # Chat interface
│   ├── 2_📁_Documents.py      # Document management
│   ├── 3_📊_Analytics.py      # Analytics dashboard
│   ├── 4_⚙️_Settings.py       # User settings
│   └── 5_👥_Admin.py          # Admin panel
│
├── components/                # UI components
│   ├── __init__.py
│   ├── chat_ui.py             # Chat components
│   ├── sidebar.py             # Sidebar components
│   └── cards.py               # Card components
│
├── utils/                     # Utilities
│   ├── __init__.py
│   ├── export.py              # Export functionality
│   └── helpers.py             # Helper functions
│
└── data/                      # Data directory (created automatically)
    ├── pdfs/                  # Uploaded PDF storage
    ├── database/              # SQLite database
    ├── chroma_db/             # ChromaDB storage
    └── exports/               # Export files
```

## Configuration Options

Edit `.env` file to customize:

```env
# OpenAI Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini        # or gpt-4o, gpt-4-turbo
EMBEDDING_MODEL=text-embedding-3-small

# Chunking Configuration
CHUNK_SIZE=1000                 # Characters per chunk
CHUNK_OVERLAP=200               # Overlap between chunks

# Retrieval Configuration
TOP_K_RESULTS=5                 # Number of chunks to retrieve
SIMILARITY_THRESHOLD=0.7        # Minimum similarity score

# Admin Credentials
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_PASSWORD=admin123
```

## Usage Guide

### Uploading Documents

1. Go to the **Documents** page
2. Click "Choose PDF files" or drag and drop
3. Select your PDF documents
4. Click "Upload Documents"
5. Wait for processing to complete

### Asking Questions

1. Go to the **Chat** page
2. Select which documents to search (or search all)
3. Type your question in the chat input
4. View the answer with citations
5. Click "Sources" to see the exact document locations

### Managing Users (Admin)

1. Go to the **Admin** page
2. View all users
3. Activate/deactivate users
4. Change user roles (Super Admin only)
5. Delete users (Super Admin only)

## Troubleshooting

### "OpenAI API key is required"
- Make sure you've created a `.env` file with your API key
- Check that the key is correct and has sufficient credits

### "No documents processed"
- Upload documents in the Documents page
- Wait for processing to complete (check for green checkmark)

### "Invalid PDF"
- Ensure the PDF is not corrupted
- Check that the PDF contains selectable text (not scanned images)

### Slow Processing
- Large PDFs may take longer to process
- Check your internet connection for API calls

## Security Notes

1. Change default admin credentials immediately
2. Use strong passwords (8+ chars, mixed case, numbers)
3. Keep your OpenAI API key secure
4. The SQLite database stores password hashes, not plain text
5. Consider using HTTPS in production deployments

## License

This project is provided as-is for educational and professional use.

## Support

For issues or questions, please refer to the documentation or contact the development team.
