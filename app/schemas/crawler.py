"""
Request and Response Schemas - Pydantic models for API validation
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class CrawlRequest(BaseModel):
    """Schema for crawler request"""

    seed_url: HttpUrl = Field(
        ..., 
        description="Starting URL to crawl (e.g., https://example.com)",
        examples=["https://example.com", "https://python.org", "https://wikipedia.org"]
    )
    max_pages: int = Field(
        default=10,
        ge=1,
        le=500,
        description="Maximum number of pages to crawl",
        examples=[10, 20, 50]
    )
    follow_external_links: bool = Field(
        default=False,
        description="Follow links outside the base domain"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "seed_url": "https://example.com",
                    "max_pages": 10,
                    "follow_external_links": False
                },
                {
                    "seed_url": "https://python.org",
                    "max_pages": 20,
                    "follow_external_links": False
                }
            ]
        }
    }


class ImageData(BaseModel):
    """Schema for image information"""

    url: str = Field(..., description="Image URL")
    alt_text: Optional[str] = Field(None, description="Image alt text")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://example.com/image.jpg",
                    "alt_text": "Example image"
                }
            ]
        }
    }


class PageContent(BaseModel):
    """Schema for extracted page content"""

    url: str = Field(..., description="Page URL")
    title: Optional[str] = Field(None, description="Page title")
    text_content: str = Field(..., description="Extracted text content")
    content_snippet: str = Field(..., description="Short snippet of content")
    images: List[ImageData] = Field(default=[], description="List of images found on page")
    images_count: int = Field(default=0, description="Total number of images")
    crawl_timestamp: str = Field(..., description="ISO format timestamp of crawl")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://example.com/page1",
                    "title": "Example Page",
                    "text_content": "This is the full page content...",
                    "content_snippet": "This is the full page content...",
                    "images": [
                        {
                            "url": "https://example.com/image.jpg",
                            "alt_text": "Example"
                        }
                    ],
                    "images_count": 1,
                    "crawl_timestamp": "2024-01-12T10:30:45Z"
                }
            ]
        }
    }


class CrawlResponse(BaseModel):
    """Schema for successful crawler response"""

    success: bool = Field(default=True, description="Whether crawl was successful")
    base_url: str = Field(..., description="Starting URL")
    total_pages_crawled: int = Field(..., description="Total pages successfully crawled")
    total_pages_requested: int = Field(..., description="Total pages requested to crawl")
    pages: List[PageContent] = Field(default=[], description="List of crawled pages")
    errors: List[str] = Field(default=[], description="List of errors encountered")
    crawl_duration_seconds: float = Field(..., description="Total crawl time in seconds")
    vector_storage: Optional[dict] = Field(None, description="Vector storage statistics if enabled")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "base_url": "https://example.com",
                    "total_pages_crawled": 5,
                    "total_pages_requested": 10,
                    "pages": [],
                    "errors": [],
                    "crawl_duration_seconds": 12.5,
                    "vector_storage": {
                        "stored": 5,
                        "failed": 0,
                        "total": 5,
                        "enabled": True
                    }
                }
            ]
        }
    }


class CrawlErrorResponse(BaseModel):
    """Schema for error response"""

    success: bool = Field(default=False, description="Whether operation succeeded")
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for categorization")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": False,
                    "error": "Invalid URL provided",
                    "error_code": "INVALID_URL"
                }
            ]
        }
    }


class SearchResponse(BaseModel):
    """Schema for semantic search response"""
    
    success: bool = Field(default=True, description="Whether search was successful")
    query: str = Field(..., description="Search query")
    results_count: int = Field(..., description="Number of results returned")
    results: List[dict] = Field(default=[], description="Search results")
    vector_enabled: bool = Field(..., description="Whether vector storage is enabled")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "query": "product information",
                    "results_count": 3,
                    "vector_enabled": True,
                    "results": [
                        {
                            "url": "https://example.com/products",
                            "title": "Our Products",
                            "score": 0.85,
                            "content_snippet": "We offer..."
                        }
                    ]
                }
            ]
        }
    }


class TaskStatus(str, Enum):
    """Enum for task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskResponse(BaseModel):
    """Schema for task status response"""
    
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    seed_url: str = Field(..., description="URL being crawled")
    max_pages: int = Field(..., description="Maximum pages to crawl")
    progress: dict = Field(default={}, description="Task progress information")
    result: Optional[CrawlResponse] = Field(None, description="Crawl result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")


class ContentResponse(BaseModel):
    """Schema for content retrieval response"""
    
    success: bool = Field(default=True, description="Whether retrieval was successful")
    url: str = Field(..., description="Content URL")
    title: Optional[str] = Field(None, description="Content title")
    content: str = Field(..., description="Content text")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
