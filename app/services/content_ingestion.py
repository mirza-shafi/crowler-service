"""
Content Ingestion Service - Unified service for all content types (URLs, files, text)
"""

import logging
import hashlib
import os
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from fastapi import UploadFile

from ..models.content_manager import ContentManager
from ..services.file_processor import file_processor
from ..services.vector_db_service import vector_db_service
from ..core.config import settings

logger = logging.getLogger(__name__)


class ContentIngestionService:
    """Service for ingesting content from multiple sources"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else "uploads"
        os.makedirs(self.upload_dir, exist_ok=True)
    
    @staticmethod
    def _calculate_content_hash(content: str) -> str:
        """Calculate SHA-256 hash of content for deduplication"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def _calculate_word_count(text: str) -> int:
        """Calculate word count from text"""
        return len(text.split()) if text else 0
    
    async def ingest_file(
        self,
        file: UploadFile,
        db: Session,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ContentManager:
        """
        Ingest a file upload
        
        Args:
            file: Uploaded file
            db: Database session
            title: Optional title for the content
            metadata: Optional additional metadata
            
        Returns:
            ContentManager instance
        """
        temp_file_path = None
        
        try:
            # Detect MIME type
            mime_type = file_processor.detect_mime_type(file.filename)
            
            # Validate file type
            if hasattr(settings, 'ALLOWED_FILE_TYPES'):
                if mime_type not in settings.ALLOWED_FILE_TYPES:
                    raise ValueError(f"Unsupported file type: {mime_type}")
            
            # Save file temporarily
            file_id = str(uuid.uuid4())
            temp_file_path = os.path.join(self.upload_dir, f"{file_id}_{file.filename}")
            
            # Read and save file
            content = await file.read()
            
            # Check file size
            file_size = len(content)
            max_size = getattr(settings, 'MAX_FILE_SIZE_MB', 50) * 1024 * 1024
            if file_size > max_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {max_size} bytes)")
            
            with open(temp_file_path, 'wb') as f:
                f.write(content)
            
            # Extract text from file
            logger.info(f"Processing file: {file.filename} ({mime_type})")
            extracted_data = await file_processor.extract_text(temp_file_path, mime_type)
            
            text_content = extracted_data['text_content']
            word_count = extracted_data['word_count']
            file_metadata = extracted_data.get('metadata', {})
            
            # Use extracted title if not provided
            if not title and 'title' in file_metadata:
                title = file_metadata['title']
            
            # Calculate content hash
            content_hash = self._calculate_content_hash(text_content)
            
            # Generate content snippet
            content_snippet = text_content[:500] if len(text_content) > 500 else text_content
            
            # Prepare file metadata
            file_meta = {
                "filename": file.filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "upload_timestamp": datetime.utcnow().isoformat(),
                **file_metadata
            }
            
            if metadata:
                file_meta.update(metadata)
            
            # Generate embedding if vector storage is enabled
            embedding = None
            embedding_model = None
            if vector_db_service.enabled and vector_db_service.model:
                try:
                    embedding_text = f"{title or ''} {text_content}".strip()
                    embedding = vector_db_service._create_embedding(embedding_text)
                    embedding_model = settings.EMBEDDING_MODEL
                    logger.info(f"Generated embedding for file: {file.filename}")
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {e}")
            
            # Create ContentManager instance
            content_manager = ContentManager(
                url=None,  # No URL for file uploads
                base_url=None,
                domain=None,
                source_type='file',
                source_identifier=file.filename,
                file_metadata=file_meta,
                title=title or file.filename,
                text_content=text_content,
                content_snippet=content_snippet,
                content_type=mime_type,
                word_count=word_count,
                content_hash=content_hash,
                crawl_status='completed',
                is_processed=True,
                is_indexed=True if embedding else False,
                embedding=embedding,
                embedding_model=embedding_model,
            )
            
            # Save to database
            db.add(content_manager)
            db.commit()
            db.refresh(content_manager)
            
            # Store chunks for RAG (if vector DB is enabled)
            if vector_db_service.enabled:
                chunks_count = await vector_db_service.store_content_chunks(
                    content_id=content_manager.id, 
                    text=text_content,
                    metadata={"source": "file", "filename": file.filename}
                )
                logger.info(f"Generated {chunks_count} chunks for file {file.filename}")
            
            logger.info(f"File ingested successfully: {file.filename} (ID: {content_manager.id})")
            
            return content_manager
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error ingesting file {file.filename}: {e}")
            raise
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")
    
    async def ingest_text(
        self,
        text_content: str,
        db: Session,
        title: Optional[str] = None,
        source_identifier: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ContentManager:
        """
        Ingest raw text content
        
        Args:
            text_content: The text content to ingest
            db: Database session
            title: Optional title
            source_identifier: Optional identifier
            metadata: Optional additional metadata
            
        Returns:
            ContentManager instance
        """
        try:
            # Calculate metrics
            word_count = self._calculate_word_count(text_content)
            content_hash = self._calculate_content_hash(text_content)
            content_snippet = text_content[:500] if len(text_content) > 500 else text_content
            
            # Generate unique identifier if not provided
            if not source_identifier:
                source_identifier = f"text-{str(uuid.uuid4())[:8]}"
            
            # Prepare metadata
            text_metadata = {
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                "source": "direct_text_input"
            }
            if metadata:
                text_metadata.update(metadata)
            
            # Generate embedding if vector storage is enabled
            embedding = None
            embedding_model = None
            if vector_db_service.enabled and vector_db_service.model:
                try:
                    # Parent embedding (summary)
                    embedding_text = f"{title or ''} {text_content}".strip()
                    embedding = vector_db_service._create_embedding(embedding_text)
                    embedding_model = settings.EMBEDDING_MODEL
                    logger.info(f"Generated summary embedding for text: {source_identifier}")
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {e}")
            
            # Create ContentManager instance
            content_manager = ContentManager(
                url=None,
                base_url=None,
                domain=None,
                source_type='text',
                source_identifier=source_identifier,
                file_metadata=text_metadata,
                title=title or f"Text: {source_identifier}",
                text_content=text_content,
                content_snippet=content_snippet,
                content_type='text/plain',
                word_count=word_count,
                content_hash=content_hash,
                crawl_status='completed',
                is_processed=True,
                is_indexed=True if embedding else False,
                embedding=embedding,
                embedding_model=embedding_model,
            )
            
            # Save to database
            db.add(content_manager)
            db.commit()
            db.refresh(content_manager)
            
            # Store chunks for RAG
            if vector_db_service.enabled:
                chunks_count = await vector_db_service.store_content_chunks(
                    content_id=content_manager.id, 
                    text=text_content,
                    metadata={"source": "text", "identifier": source_identifier}
                )
                logger.info(f"Generated {chunks_count} chunks for text {source_identifier}")
            
            logger.info(f"Text ingested successfully: {source_identifier} (ID: {content_manager.id})")
            
            return content_manager
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error ingesting text: {e}")
            raise
    
    async def ingest_batch(
        self,
        files: List[UploadFile],
        db: Session
    ) -> Dict:
        """
        Ingest multiple files in batch
        
        Args:
            files: List of uploaded files
            db: Database session
            
        Returns:
            Dict with batch processing results
        """
        results = []
        successful = 0
        failed = 0
        
        for file in files:
            try:
                content = await self.ingest_file(file, db)
                results.append({
                    "success": True,
                    "content_id": str(content.id),
                    "filename": file.filename,
                    "source_type": "file",
                    "mime_type": content.content_type,
                    "word_count": content.word_count,
                    "embedding_generated": content.embedding is not None,
                    "message": "File processed successfully"
                })
                successful += 1
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {e}")
                results.append({
                    "success": False,
                    "content_id": "",
                    "filename": file.filename,
                    "source_type": "file",
                    "mime_type": "",
                    "word_count": 0,
                    "embedding_generated": False,
                    "message": f"Error: {str(e)}"
                })
                failed += 1
        
        return {
            "success": failed == 0,
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "results": results
        }


# Singleton instance
content_ingestion_service = ContentIngestionService()
