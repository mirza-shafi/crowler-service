# Content Ingestion & Crawler Service

A comprehensive content ingestion and processing microservice built with FastAPI, BeautifulSoup4, and PostgreSQL with pgvector. Similar to platforms like ElevenLabs and Apify, this service provides a unified API for ingesting content from multiple sources (URLs, files, text), processing with intelligent chunking, and enabling semantic search through vector embeddings.

## 🚀 Key Features

### Multi-Source Content Ingestion
- **File Upload Support** - PDF, DOCX, TXT, MD, HTML with automatic format detection
- **Direct Text Input** - Ingest raw text content programmatically
- **URL Crawling** - Recursive web crawling with domain boundary protection
- **Batch Processing** - Upload and process multiple files simultaneously

### Advanced Text Processing
- **Smart Chunking** - Intelligent text splitting optimized for RAG systems
  - 512 token chunks with 100 token overlap
  - Multiple strategies: recursive, paragraph, sentence-based
  - Context preservation at chunk boundaries
- **Vector Embeddings** - Automatic embedding generation using `sentence-transformers`
- **Deduplication** - SHA-256 hash-based content deduplication
- **Metadata Extraction** - Word count, file type, timestamps automatically tracked

### Semantic Search & Retrieval
- **Vector Similarity Search** - Find relevant content using cosine similarity
- **PostgreSQL with pgvector** - Production-ready vector storage
- **Chunk-Level Search** - Search at chunk granularity for precise results
- **Filters** - Filter by source type, base URL, or date range

### Web Crawling Capabilities
- **Recursive Crawling** - Follow links within the same domain automatically
- **Content Extraction** - Extract titles, text content, and image URLs
- **Asynchronous Processing** - Concurrent page fetching with configurable limits
- **Error Handling** - Graceful handling of timeouts, 404s, and network errors
- **Rate Limiting** - Configurable concurrency and retry logic

## 🏗️ Architecture

```
crawler-service/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── ingestion.py       # File/text upload endpoints
│   │   └── crawler.py          # Web crawling endpoints
│   ├── services/
│   │   ├── content_ingestion.py   # Unified ingestion logic
│   │   ├── file_processor.py      # File parsing (PDF, DOCX, etc.)
│   │   ├── text_chunker.py        # Smart chunking algorithms
│   │   ├── vector_db_service.py   # Vector embeddings & search
│   │   ├── crawler.py             # Web crawling logic
│   │   └── task_manager.py        # Background task handling
│   ├── models/
│   │   └── content_manager.py  # Database models
│   ├── schemas/
│   │   ├── ingestion.py        # Ingestion request/response models
│   │   └── crawler.py          # Crawler request/response models
│   ├── core/
│   │   ├── config.py           # Configuration
│   │   └── database.py         # Database connection
│   └── main.py                 # FastAPI application
├── uploads/                    # File upload storage
├── demo_chunking.py            # Interactive chunking demo
├── verify_chunking.py          # Chunking verification script
└── docker-compose.yml          # Docker orchestration
```

## 📋 Requirements

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- FastAPI, Uvicorn
- SQLAlchemy (async)
- httpx (async HTTP)
- BeautifulSoup4 (HTML parsing)
- sentence-transformers (embeddings)
- PyPDF2, python-docx (file processing)

See `requirements.txt` for complete dependencies.

## 📦 Installation

### Docker (Recommended)

```bash
# Clone and navigate to project
cd crawler-service

# Start all services (FastAPI + PostgreSQL)
docker-compose up --build

# The service will be available at http://localhost:8001
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL with pgvector
./setup_pgvector.sh

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python migrate_to_content_manager.py
python migrate_add_ingestion_fields.py
python migrate_add_chunks_table.py

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## 🔌 API Endpoints

### Content Ingestion Endpoints

#### Upload File
```http
POST /api/v1/ingestion/upload/file
Content-Type: multipart/form-data

file: <file>
title: "Optional Title"
```

**Supported Formats:** PDF, DOCX, TXT, MD, HTML

**Response:**
```json
{
  "success": true,
  "content_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_type": "pdf",
  "title": "Document Title",
  "file_path": "uploads/document.pdf",
  "text_preview": "First 200 characters...",
  "word_count": 1250,
  "chunks_created": 5,
  "vector_stored": true,
  "message": "File uploaded and processed successfully"
}
```

#### Upload Text
```http
POST /api/v1/ingestion/upload/text
Content-Type: application/json

{
  "text_content": "Your text content here...",
  "title": "Optional Title",
  "source_identifier": "optional-id",
  "metadata": {}
}
```

#### Batch Upload
```http
POST /api/v1/ingestion/upload/batch
Content-Type: multipart/form-data

files: [<file1>, <file2>, <file3>]
```

**Response:**
```json
{
  "total_files": 3,
  "successful": 2,
  "failed": 1,
  "results": [
    {
      "filename": "doc1.pdf",
      "success": true,
      "content_id": "...",
      "chunks_created": 5
    },
    {
      "filename": "doc2.pdf",
      "success": false,
      "error": "Unsupported file type"
    }
  ]
}
```

#### List Content
```http
GET /api/v1/ingestion/content/list?source_type=pdf&limit=50&offset=0
```

**Response:**
```json
{
  "total": 100,
  "items": [
    {
      "content_id": "550e8400-e29b-41d4-a716-446655440000",
      "source_type": "pdf",
      "title": "Document Title",
      "word_count": 1250,
      "created_at": "2024-01-14T10:30:00Z"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

#### Get Ingestion Statistics
```http
GET /api/v1/ingestion/stats
```

**Response:**
```json
{
  "total_content": 150,
  "by_source_type": {
    "pdf": {"count": 50, "total_words": 125000},
    "url": {"count": 75, "total_words": 200000},
    "text": {"count": 25, "total_words": 50000}
  },
  "total_chunks": 1250,
  "total_words": 375000
}
```

### Web Crawling Endpoints

#### Crawl Website
```http
POST /api/v1/crawler/crawl
Content-Type: application/x-www-form-urlencoded

seed_url=https://example.com
max_pages=50
follow_external_links=false
```

**Response:**
```json
{
  "success": true,
  "base_url": "https://example.com",
  "total_pages_crawled": 25,
  "pages": [
    {
      "url": "https://example.com/page1",
      "title": "Page Title",
      "text_content": "Full content...",
      "images_count": 3,
      "content_id": "uuid-here",
      "chunks_created": 4
    }
  ],
  "crawl_duration_seconds": 15.3
}
```

#### Batch Crawl
```http
POST /api/v1/crawler/crawl/batch
Content-Type: application/json

[
  {"seed_url": "https://example1.com", "max_pages": 20},
  {"seed_url": "https://example2.com", "max_pages": 30}
]
```

#### Semantic Search
```http
POST /api/v1/crawler/search
Content-Type: application/x-www-form-urlencoded

query=What are neural networks?
top_k=5
base_url_filter=https://example.com
```

**Response:**
```json
{
  "query": "What are neural networks?",
  "results": [
    {
      "content_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Neural Networks Guide",
      "chunk_text": "Neural networks are...",
      "similarity_score": 0.89,
      "url": "https://example.com/neural-nets",
      "source_type": "url"
    }
  ],
  "total_results": 5
}
```

#### Get Content by URL
```http
GET /api/v1/crawler/content/{url}
```

#### Vector Database Stats
```http
GET /api/v1/crawler/stats/vector
```

### Health Check
```http
GET /api/v1/crawler/health
```

## 🧠 Smart Chunking System

The service implements intelligent text chunking following 2024 best practices for RAG systems:

### Chunking Configuration
- **Chunk Size:** 512 tokens (~2000 characters)
- **Overlap:** 100 tokens (~400 characters, 20% overlap)
- **Strategy:** Recursive splitting (paragraphs → sentences → words)

### Strategies Available

1. **Recursive (Recommended)** - Splits at natural boundaries
   ```python
   chunks = text_chunker.chunk_text(text, strategy="recursive")
   ```

2. **Paragraph-based** - Best for documents with clear structure
   ```python
   chunks = text_chunker.chunk_text(text, strategy="paragraphs")
   ```

3. **Sentence-based** - Best for FAQ, Q&A, precise fact retrieval
   ```python
   chunks = text_chunker.chunk_text(text, strategy="sentences")
   ```

### Why Chunking?

**Without Chunking:**
- Large documents truncated to 5000 chars → information loss
- Search returns entire document → user reads irrelevant content
- Poor precision in retrieval

**With Chunking:**
- No information loss → all content preserved
- Search returns only relevant chunks → precise results
- Better user experience → less reading required

### Try the Demo!

```bash
python demo_chunking.py
```

This interactive demo shows:
- How documents are split into chunks
- Chunk overlap visualization
- Simulated search results
- Comparison with/without chunking

## 🔧 Configuration

Configure via environment variables in `.env`:

```env
# Application
APP_NAME=Content Ingestion Service
APP_VERSION=2.0.0
DEBUG=False

# Server
HOST=0.0.0.0
PORT=8001

# Database (PostgreSQL with pgvector)
DATABASE_URL=postgresql://user:pass@localhost:5432/crawler_db

# Vector Storage
VECTOR_STORAGE_ENABLED=true
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Chunking Configuration
CHUNK_SIZE=512                  # tokens
CHUNK_OVERLAP=100              # tokens
CHUNKING_STRATEGY=recursive

# Crawler Settings
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=30
DEFAULT_MAX_PAGES=50
MAX_ALLOWED_PAGES=500

# File Upload
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE=10485760       # 10MB
ALLOWED_EXTENSIONS=pdf,docx,txt,md,html

# Content Processing
CONTENT_SNIPPET_LENGTH=200
MAX_CONTENT_LENGTH=100000
```

## 📊 Data Models

### ContentManager Table
Stores all ingested content with unified schema:

```python
{
  "content_id": "UUID",
  "source_type": "url|pdf|docx|txt|md|html|text",
  "source_identifier": "URL or file path",
  "title": "Content title",
  "content_text": "Full text content",
  "content_hash": "SHA-256 hash",
  "word_count": 1250,
  "embedding": "vector(384)",  # pgvector
  "metadata": {},  # JSONB
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### ContentChunk Table
Stores text chunks with embeddings for RAG:

```python
{
  "chunk_id": "UUID",
  "content_id": "UUID (foreign key)",
  "chunk_index": 0,
  "chunk_text": "Chunk content...",
  "start_char": 0,
  "end_char": 2000,
  "token_count": 512,
  "embedding": "vector(384)",
  "metadata": {},
  "created_at": "timestamp"
}
```

## 🛡️ Error Handling

The service handles various error conditions gracefully:

- **File Processing Errors** - Unsupported formats, corrupted files
- **Duplication** - Hash-based detection with informative messages
- **Database Errors** - Connection issues, constraint violations
- **Timeout Errors** - Request timeout handling
- **HTTP Errors** - 404 and other HTTP error tracking
- **Network Errors** - Connection failures and DNS issues
- **Parsing Errors** - Malformed HTML or document structure

All errors return structured responses with clear messages.

## 📈 Performance Characteristics

- **Async Processing** - Uses asyncio for concurrent operations
- **Batch Operations** - Process multiple files efficiently
- **Connection Pooling** - PostgreSQL connection management
- **Vector Indexing** - Fast similarity search with pgvector
- **Chunking Overhead** - Minimal (~100ms for 10,000 words)
- **Typical Performance**:
  - PDF processing: 1-3 seconds
  - URL crawling (50 pages): 10-30 seconds
  - Semantic search: 50-200ms
  - Batch upload (10 files): 10-30 seconds

## 🧪 Testing & Verification

### Verify Chunking
```bash
# Check chunking functionality
python verify_chunking.py
```

### Interactive Demo
```bash
# See chunking in action
python demo_chunking.py
```

### View Content
```bash
# View stored content
python view_content.py
```

### Test Crawler
```bash
# Test crawler functionality
python test_crawler.py
```

## 📝 Example Usage

### Python Example - File Upload

```python
import requests

# Upload a file
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    data = {'title': 'My Document'}
    response = requests.post(
        'http://localhost:8001/api/v1/ingestion/upload/file',
        files=files,
        data=data
    )
    result = response.json()
    print(f"Uploaded: {result['content_id']}")
    print(f"Chunks created: {result['chunks_created']}")
```

### Python Example - Text Ingestion

```python
import requests

# Ingest text
response = requests.post(
    'http://localhost:8001/api/v1/ingestion/upload/text',
    json={
        'text_content': 'Your long text content here...',
        'title': 'Article Title',
        'metadata': {'author': 'John Doe', 'category': 'AI'}
    }
)
result = response.json()
print(f"Content ID: {result['content_id']}")
```

### Python Example - Semantic Search

```python
import requests

# Search for content
response = requests.post(
    'http://localhost:8001/api/v1/crawler/search',
    data={
        'query': 'What are neural networks?',
        'top_k': 5
    }
)
results = response.json()

for item in results['results']:
    print(f"Title: {item['title']}")
    print(f"Score: {item['similarity_score']:.2f}")
    print(f"Text: {item['chunk_text'][:200]}...")
    print()
```

### cURL Examples

```bash
# Upload file
curl -X POST http://localhost:8001/api/v1/ingestion/upload/file \
  -F "file=@document.pdf" \
  -F "title=My Document"

# Ingest text
curl -X POST http://localhost:8001/api/v1/ingestion/upload/text \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "Your content here...",
    "title": "Article Title"
  }'

# Search content
curl -X POST http://localhost:8001/api/v1/crawler/search \
  -d "query=neural networks" \
  -d "top_k=5"

# List content
curl http://localhost:8001/api/v1/ingestion/content/list?source_type=pdf&limit=10

# Get stats
curl http://localhost:8001/api/v1/ingestion/stats
```

## 📚 Documentation

- **Interactive API Docs**: `http://localhost:8001/docs` (Swagger UI)
- **ReDoc Documentation**: `http://localhost:8001/redoc`
- **OpenAPI Schema**: `http://localhost:8001/openapi.json`

## 🔄 Integration with Other Services

The service is designed as a microservice for distributed architectures:

- **RESTful API** - Easy integration with any language/framework
- **Async Operations** - Non-blocking for event-driven architectures
- **Stateless Design** - Horizontal scaling ready
- **Docker Ready** - Containerized deployment
- **Database Backed** - Persistent storage with PostgreSQL
- **Vector Search** - Integrate with RAG systems, chatbots, knowledge bases

## 🚀 Deployment

### Docker Compose (Production)

```yaml
version: '3.8'
services:
  postgres:
    image: ankane/pgvector
    environment:
      POSTGRES_DB: crawler_db
      POSTGRES_USER: crawler_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  crawler-service:
    build: .
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql://crawler_user:secure_password@postgres:5432/crawler_db
      VECTOR_STORAGE_ENABLED: "true"
    depends_on:
      - postgres
    volumes:
      - ./uploads:/app/uploads

volumes:
  pgdata:
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crawler-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crawler
  template:
    metadata:
      labels:
        app: crawler
    spec:
      containers:
      - name: crawler
        image: crawler-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: VECTOR_STORAGE_ENABLED
          value: "true"
```

## 🎯 Use Cases

1. **Knowledge Base Systems** - Ingest documents, enable semantic search
2. **RAG Applications** - Chunk documents for retrieval-augmented generation
3. **Content Management** - Unified storage for multi-source content
4. **Web Scraping** - Automated content collection from websites
5. **Document Processing** - Extract and process PDF, DOCX files
6. **Q&A Systems** - Build question-answering systems with vector search
7. **Research Tools** - Aggregate and search across research papers
8. **Chatbot Knowledge** - Feed content to chatbots with semantic retrieval

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- pgvector for vector similarity search
- sentence-transformers for embeddings
- BeautifulSoup4 for HTML parsing
- PyPDF2 and python-docx for file processing

## 📞 Support

For issues, questions, or suggestions, please open an issue on the repository.

---

**Built with ❤️ for modern content ingestion and retrieval systems**
