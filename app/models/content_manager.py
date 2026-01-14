"""
Database Models - SQLAlchemy models for content management
Following 11labs crawler architecture principles
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Index, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class ContentManager(Base):
    """
    Model for managing crawled content with comprehensive metadata
    Following 11labs-style crawler architecture
    """
    
    __tablename__ = "content_manager"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # URL and source information
    url = Column(String(2048), unique=True, nullable=True, index=True)  # Nullable for non-URL sources
    base_url = Column(String(512), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    
    # Source tracking (NEW - for multi-source ingestion)
    source_type = Column(String(50), default='url', index=True)  # url, file, text, batch
    source_identifier = Column(String(512), nullable=True)  # filename or text ID
    file_metadata = Column(JSONB, default=dict)  # filename, size, mime_type, upload_timestamp
    
    # Content metadata
    title = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    content_type = Column(String(100), default='text/html', index=True)  # MIME type
    language = Column(String(10), nullable=True)  # ISO 639-1 language code
    
    # Main content
    text_content = Column(Text, nullable=False)
    content_snippet = Column(Text, nullable=True)  # First 200-500 chars
    raw_html = Column(Text, nullable=True)  # Original HTML for re-processing
    
    # Media and assets
    images = Column(JSONB, default=list)  # Array of image objects with url, alt_text
    images_count = Column(Integer, default=0)
    videos = Column(JSONB, default=list)  # Array of video URLs
    links = Column(JSONB, default=list)  # Extracted links
    
    # SEO and metadata
    meta_tags = Column(JSONB, default=dict)  # All meta tags
    keywords = Column(JSONB, default=list)  # Extracted keywords
    author = Column(String(255), nullable=True)
    
    # Content quality and processing
    word_count = Column(Integer, default=0)
    content_hash = Column(String(64), index=True)  # SHA-256 hash for deduplication
    quality_score = Column(Integer, default=0)  # 0-100 quality rating
    
    # Crawl tracking
    crawl_status = Column(String(50), default='completed', index=True)  # completed, failed, pending, processing
    crawl_timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    crawl_depth = Column(Integer, default=0)  # Depth from seed URL
    
    # HTTP response metadata
    http_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Vector embeddings for semantic search (pgvector)
    embedding = Column(Vector(384), nullable=True)  # 384 dimensions for all-MiniLM-L6-v2
    embedding_model = Column(String(100), nullable=True)
    
    # Processing flags
    is_processed = Column(Boolean, default=False, index=True)
    is_indexed = Column(Boolean, default=False, index=True)
    needs_reprocessing = Column(Boolean, default=False)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Custom metadata (flexible JSON field)
    custom_metadata = Column(JSONB, default=dict)
    
    # Create composite indexes for better query performance
    __table_args__ = (
        Index('idx_url_hash', 'url'),
        Index('idx_base_url', 'base_url'),
        Index('idx_domain', 'domain'),
        Index('idx_content_type', 'content_type'),
        Index('idx_crawl_status', 'crawl_status'),
        Index('idx_crawl_timestamp', 'crawl_timestamp'),
        Index('idx_is_processed', 'is_processed'),
        Index('idx_content_hash', 'content_hash'),
        Index('idx_source_type', 'source_type'),  # NEW
        Index('idx_domain_status', 'domain', 'crawl_status'),  # Composite index
        Index('idx_timestamp_status', 'crawl_timestamp', 'crawl_status'),  # Composite index
    )
    
    def __repr__(self):
        return f"<ContentManager(url='{self.url}', title='{self.title}', status='{self.crawl_status}')>"
    
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'url': self.url,
            'base_url': self.base_url,
            'domain': self.domain,
            'title': self.title,
            'description': self.description,
            'content_type': self.content_type,
            'language': self.language,
            'text_content': self.text_content,
            'content_snippet': self.content_snippet,
            'images': self.images,
            'images_count': self.images_count,
            'videos': self.videos,
            'meta_tags': self.meta_tags,
            'keywords': self.keywords,
            'word_count': self.word_count,
            'quality_score': self.quality_score,
            'crawl_status': self.crawl_status,
            'crawl_timestamp': self.crawl_timestamp.isoformat() if self.crawl_timestamp else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'crawl_depth': self.crawl_depth,
            'http_status_code': self.http_status_code,
            'is_processed': self.is_processed,
            'is_indexed': self.is_indexed,
            'source_type': self.source_type,
            'source_identifier': self.source_identifier,
        }


class ContentChunk(Base):
    """
    Model for storing text chunks with embeddings (One-to-Many with ContentManager)
    Used for RAG (Retrieval Augmented Generation)
    """
    __tablename__ = "content_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), index=True, nullable=False)  # ForeignKey logic handled manually or via simple join
    
    # Chunk metadata
    chunk_index = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=False)
    
    # Chunk content
    chunk_text = Column(Text, nullable=False)
    
    # Vector embedding
    embedding = Column(Vector(384), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_content_chunk', 'content_id', 'chunk_index'),
    )
    
    def __repr__(self):
        return f"<ContentChunk(id={self.id}, content_id={self.content_id}, index={self.chunk_index})>"
