"""
Database Service - Store crawled content to PostgreSQL
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.crawled_content import CrawledContent
from ..schemas.crawler import PageContent
from .crawler import logger as crawler_logger

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for storing crawled data to PostgreSQL database"""
    
    @staticmethod
    def store_page(db: Session, page: PageContent, base_url: str) -> bool:
        """Store a single crawled page in the database"""
        try:
            crawled_content = CrawledContent(
                url=page.url,
                title=page.title,
                text_content=page.text_content,
                content_snippet=page.content_snippet,
                base_url=base_url,
                images_count=len(page.images) if page.images else 0,
            )
            db.add(crawled_content)
            db.commit()
            db.refresh(crawled_content)
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing page {page.url}: {e}")
            return False
    
    @staticmethod
    def store_pages_batch(db: Session, pages: List[PageContent], base_url: str) -> dict:
        """Store multiple crawled pages in a batch"""
        stored = 0
        failed = 0
        
        try:
            for page in pages:
                try:
                    crawled_content = CrawledContent(
                        url=page.url,
                        title=page.title,
                        text_content=page.text_content,
                        content_snippet=page.content_snippet,
                        base_url=base_url,
                        images_count=len(page.images) if page.images else 0,
                    )
                    db.add(crawled_content)
                    stored += 1
                except Exception as e:
                    logger.error(f"Error preparing page {page.url}: {e}")
                    failed += 1
            
            # Commit all at once
            if stored > 0:
                db.commit()
                logger.info(f"Batch storage completed: {stored} stored, {failed} failed")
            
            return {
                "stored": stored,
                "failed": failed,
                "total": len(pages)
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing batch: {e}")
            return {
                "stored": 0,
                "failed": len(pages),
                "total": len(pages)
            }


# Singleton instance
database_service = DatabaseService()
