"""
Database Service - Handles PostgreSQL operations with pgvector for embeddings
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sentence_transformers import SentenceTransformer

from ..core.config import settings
from ..models.content_manager import Base, ContentManager, ContentChunk
from ..services.text_chunker import text_chunker
from ..schemas.crawler import PageContent

logger = logging.getLogger(__name__)


class VectorDatabaseService:
    """Service for storing and searching crawled content with embeddings in PostgreSQL"""
    
    def __init__(self):
        self.enabled = settings.VECTOR_STORAGE_ENABLED and settings.DATABASE_URL
        self.engine = None
        self.async_session_maker = None
        self.model: Optional[SentenceTransformer] = None
        
        if self.enabled:
            try:
                self._initialize()
                logger.info("Vector database service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize vector database: {e}")
                self.enabled = False
    
    def _initialize(self):
        """Initialize database connection and embedding model"""
        # Convert postgres:// to postgresql:// and add asyncpg driver
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Create async engine
        self.engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        # Create session maker
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Load embedding model
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    async def initialize_database(self):
        """Create tables and enable pgvector extension"""
        if not self.enabled:
            return False
        
        try:
            async with self.engine.begin() as conn:
                # Enable pgvector extension
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                logger.info("pgvector extension enabled")
                
                # Create tables
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created")
            
            return True
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    def _create_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        NOTE: For RAG, strictly prefer using store_content_chunks which handles splitting
        """
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        # Truncate text if too long (legacy support for single-vector docs)
        # Increased limit, but ideally should be used only for short texts
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    async def store_content_chunks(self, content_id: str, text: str, metadata: Dict = None) -> int:
        """
        Split text into chunks, generate embeddings, and store them
        
        Args:
            content_id: UUID of the parent ContentManager record
            text: Full text content
            metadata: Optional metadata to attach to chunks
            
        Returns:
            int: Number of chunks stored
        """
        if not self.enabled:
            return 0
            
        try:
            # 1. Split into chunks
            chunks = text_chunker.chunk_text(text, strategy="recursive")
            if not chunks:
                return 0
                
            logger.info(f"Splitting content {content_id} into {len(chunks)} chunks")
            
            async with self.async_session_maker() as session:
                # 2. Process each chunk
                for chunk in chunks:
                    # Generate embedding
                    embedding = self._create_embedding(chunk.text)
                    
                    # Create Chunk record
                    chunk_record = ContentChunk(
                        content_id=content_id,
                        chunk_index=chunk.chunk_index,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                        token_count=chunk.token_count,
                        chunk_text=chunk.text,
                        embedding=embedding
                    )
                    session.add(chunk_record)
                
                await session.commit()
                logger.info(f"Stored {len(chunks)} chunks for content {content_id}")
                return len(chunks)
                
        except Exception as e:
            logger.error(f"Error storing chunks for {content_id}: {e}")
            return 0

    async def store_page(self, page: PageContent, base_url: str) -> bool:
        """
        Store a single crawled page with embedding (AND chunks)
        """
        if not self.enabled:
            logger.debug("Vector storage not enabled, skipping")
            return False
        
        try:
            # Generate embedding for the full doc (summary/legacy)
            text_for_embedding = f"{page.title or ''} {page.text_content}".strip()
            embedding = self._create_embedding(text_for_embedding) if text_for_embedding else None
            
            async with self.async_session_maker() as session:
                # Check if URL already exists
                result = await session.execute(
                    select(ContentManager).where(ContentManager.url == page.url)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing record
                    existing.title = page.title
                    existing.text_content = page.text_content
                    existing.content_snippet = page.content_snippet or page.text_content[:200]
                    existing.base_url = base_url
                    existing.images_count = page.images_count
                    existing.crawl_timestamp = datetime.fromisoformat(page.crawl_timestamp.replace('Z', '+00:00'))
                    existing.embedding = embedding
                    content_id = existing.id
                    
                    # Delete old chunks for this content
                    await session.execute(
                        text("DELETE FROM content_chunks WHERE content_id = :cid"),
                        {"cid": existing.id}
                    )
                    logger.info(f"Updated existing page: {page.url}")
                else:
                    # Create new record
                    content = ContentManager(
                        url=page.url,
                        title=page.title,
                        text_content=page.text_content,
                        content_snippet=page.content_snippet or page.text_content[:200],
                        base_url=base_url,
                        images_count=page.images_count,
                        crawl_timestamp=datetime.fromisoformat(page.crawl_timestamp.replace('Z', '+00:00')),
                        embedding=embedding
                    )
                    session.add(content)
                    await session.flush() # flush to get ID
                    content_id = content.id
                    logger.info(f"Stored new page: {page.url}")
                
                await session.commit()
            
            # Now store chunks (in a separate transaction/session is fine, or same)
            # We already committed the parent, now let's store chunks
            if page.text_content:
                await self.store_content_chunks(content_id, page.text_content)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing page in database: {e}")
            return False
    
    async def store_pages_batch(self, pages: List[PageContent], base_url: str) -> Dict[str, Any]:
        """Store multiple pages with embeddings in batch"""
        if not self.enabled:
            return {"stored": 0, "failed": 0, "total": len(pages), "enabled": False}
        
        stored_count = 0
        failed_count = 0
        
        for page in pages:
            success = await self.store_page(page, base_url)
            if success:
                stored_count += 1
            else:
                failed_count += 1
        
        return {
            "stored": stored_count,
            "failed": failed_count,
            "total": len(pages),
            "enabled": True
        }
    
    async def search_similar(
        self,
        query: str,
        top_k: int = 5,
        base_url_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity
        This now searches CHUNKS but returns parent document info + chunk text
        """
        if not self.enabled:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._create_embedding(query)
            
            async with self.async_session_maker() as session:
                # Query chunks directly
                # We join with ContentManager to get metadata (title, url)
                query_stmt = select(
                    ContentChunk,
                    ContentManager,
                    ContentChunk.embedding.cosine_distance(query_embedding).label('distance')
                ).join(
                    ContentManager, ContentChunk.content_id == ContentManager.id
                )
                
                # Add base_url filter if provided
                if base_url_filter:
                    query_stmt = query_stmt.where(ContentManager.base_url == base_url_filter)
                
                # Order by distance (similarity)
                query_stmt = query_stmt.order_by('distance').limit(top_k)
                
                result = await session.execute(query_stmt)
                rows = result.all()
                
                # Format results
                results = []
                seen_docs = set()
                
                for chunk, content, distance in rows:
                    if distance is None: continue
                    
                    similarity_score = 1 - distance
                    
                    # Construct result result
                    results.append({
                        "id": str(content.id),
                        "chunk_id": str(chunk.id),
                        "score": float(similarity_score),
                        "url": content.url,
                        "title": content.title,
                        # Return the matched CHUNK text, not the whole doc snippet
                        "content_snippet": chunk.chunk_text, 
                        "base_url": content.base_url,
                        "crawl_timestamp": content.crawl_timestamp.isoformat() if content.crawl_timestamp else None,
                        "chunk_index": chunk.chunk_index
                    })
                
                return results
        
        except Exception as e:
            logger.error(f"Error searching database: {e}")
            return []
    
    async def get_content_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get crawled content by URL"""
        if not self.enabled:
            return None
        
        try:
            async with self.async_session_maker() as session:
                result = await session.execute(
                    select(ContentManager).where(ContentManager.url == url)
                )
                content = result.scalar_one_or_none()
                
                if content:
                    return {
                        "id": content.id,
                        "url": content.url,
                        "title": content.title,
                        "text_content": content.text_content,
                        "content_snippet": content.content_snippet,
                        "base_url": content.base_url,
                        "images_count": content.images_count,
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting content by URL: {e}")
            return None
    
    async def delete_by_base_url(self, base_url: str) -> int:
        """Delete all content associated with a base URL"""
        if not self.enabled:
            return 0
        try:
            async with self.async_session_maker() as session:
                # Cascading delete of chunks needs to be handled if not configured in DB
                # Generally safer to select IDs then delete chunks, then delete parents
                
                # Find contents
                result = await session.execute(
                    select(ContentManager.id).where(ContentManager.base_url == base_url)
                )
                content_ids = result.scalars().all()
                
                if not content_ids:
                    return 0

                # Delete chunks
                await session.execute(
                    text("DELETE FROM content_chunks WHERE content_id = ANY(:ids)"),
                    {"ids": content_ids}
                )
                
                # Delete parents
                await session.execute(
                    text("DELETE FROM content_manager WHERE id = ANY(:ids)"),
                    {"ids": content_ids}
                )
                
                await session.commit()
                logger.info(f"Deleted {len(content_ids)} records for base_url: {base_url}")
                return len(content_ids)
        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            return 0
            
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            async with self.async_session_maker() as session:
                # Count total docs
                result = await session.execute(select(ContentManager))
                total_docs = len(result.scalars().all())
                
                # Count total chunks
                result = await session.execute(text("SELECT COUNT(*) FROM content_chunks"))
                total_chunks = result.scalar()
                
                return {
                    "enabled": True,
                    "total_documents": total_docs,
                    "total_chunks": total_chunks,
                    "embedding_model": settings.EMBEDDING_MODEL,
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")


# Singleton instance
vector_db_service = VectorDatabaseService()
