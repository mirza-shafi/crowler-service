"""
Database Models - SQLAlchemy models for crawled content
"""

import uuid
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class CrawledContent(Base):
    """Model for storing crawled content"""
    
    __tablename__ = "crawled_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=True)
    text_content = Column(Text, nullable=False)
    content_snippet = Column(Text, nullable=True)
    base_url = Column(String(512), nullable=False, index=True)
    images_count = Column(String, default=0)
    crawl_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Create indexes for better query performance
    __table_args__ = (
        Index('idx_url', 'url'),
        Index('idx_base_url', 'base_url'),
    )
    
    def __repr__(self):
        return f"<CrawledContent(url='{self.url}', title='{self.title}')>"
