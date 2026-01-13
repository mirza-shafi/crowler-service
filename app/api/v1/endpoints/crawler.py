"""
Crawler Endpoints - FastAPI routes for crawling operations
"""

import logging
from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, status, Form, Depends

from ....schemas.crawler import CrawlRequest, CrawlResponse, CrawlErrorResponse, SearchResponse
from ....services.crawler import crawler_service
from ....services.vector_db_service import vector_db_service
from ....services.database_service import database_service
from ....core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawler")


@router.get("/health", status_code=200)
async def health_check():
    """
    Health check endpoint

    Returns:
        Status of the crawler service
    """
    return {"status": "healthy", "service": "crawler-microservice"}


@router.post(
    "/crawl",
    response_model=CrawlResponse,
    status_code=200,
    responses={
        400: {"model": CrawlErrorResponse, "description": "Invalid input"},
        500: {"model": CrawlErrorResponse, "description": "Internal server error"},
    },
)
async def crawl(
    seed_url: Annotated[str, Form(description="Starting URL to crawl (e.g., https://example.com)", examples=["https://example.com"])],
    max_pages: Annotated[int, Form(description="Maximum number of pages to crawl (1-500)", ge=1, le=500)] = 10,
    follow_external_links: Annotated[bool, Form(description="Follow links outside the base domain")] = False,
    db = Depends(get_db),
) -> CrawlResponse:
    """
    Crawl and scrape a website

    ## Description
    Crawls a website starting from a seed URL, following internal links
    within the same domain. Extracts page titles, content, and image URLs.

    ## Parameters
    - **seed_url**: The starting URL to begin crawling
    - **max_pages**: Maximum number of pages to crawl (1-500, default: 10)
    - **follow_external_links**: Whether to follow links outside the base domain (default: false)

    ## Returns
    A structured response containing:
    - All crawled pages with their content and images
    - Total pages crawled and requested
    - Any errors encountered during crawling
    - Total crawl duration in seconds
    """
    try:
        logger.info(f"Crawl request: {seed_url} (max_pages={max_pages})")

        # Perform the crawl
        result = await crawler_service.crawl(
            seed_url=seed_url,
            max_pages=max_pages,
            follow_external_links=follow_external_links,
        )

        # Store crawled content in database
        if result.pages:
            logger.info("Storing crawled content in database...")
            db_stats = database_service.store_pages_batch(db, result.pages, seed_url)
            logger.info(f"Database storage: {db_stats}")
        
        logger.info(f"Crawl completed successfully: {result.total_pages_crawled} pages")
        return result

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during crawl: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during crawling",
        )


@router.post("/crawl/batch", response_model=dict, status_code=200)
async def crawl_batch(requests: list[CrawlRequest]) -> dict:
    """
    Batch crawl multiple websites

    ## Description
    Crawl multiple websites sequentially. Each crawl is performed
    independently with its own domain boundary.

    ## Parameters
    - **requests**: List of CrawlRequest objects

    ## Returns
    Dictionary containing results for each URL with crawl status
    """
    if not requests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one crawl request is required",
        )

    if len(requests) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 URLs per batch request",
        )

    results = {}

    try:
        for idx, request in enumerate(requests):
            try:
                logger.info(
                    f"Batch crawl {idx + 1}/{len(requests)}: {request.seed_url}"
                )

                result = await crawler_service.crawl(
                    seed_url=str(request.seed_url),
                    max_pages=request.max_pages,
                    follow_external_links=request.follow_external_links,
                )

                results[str(request.seed_url)] = {
                    "success": True,
                    "data": result.model_dump(),
                }
            except Exception as e:
                logger.error(f"Error crawling {request.seed_url}: {str(e)}")
                results[str(request.seed_url)] = {
                    "success": False,
                    "error": str(e),
                }

        return {"batch_results": results}

    except Exception as e:
        logger.error(f"Unexpected error during batch crawl: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during batch crawling",
        )


@router.post("/search", response_model=SearchResponse, status_code=200)
async def search_content(
    query: Annotated[str, Form(description="Search query text")],
    top_k: Annotated[int, Form(description="Number of results to return (1-100)", ge=1, le=100)] = 5,
    base_url_filter: Annotated[Optional[str], Form(description="Filter by base URL (optional)")] = None,
) -> SearchResponse:
    """
    Semantic search across crawled content using pgvector
    
    ## Description
    Search for relevant content from previously crawled pages using vector similarity.
    Requires vector storage to be enabled and configured with PostgreSQL.
    
    ## Parameters
    - **query**: Search query text (natural language)
    - **top_k**: Number of results to return (default: 5)
    - **base_url_filter**: Optional filter to search within specific base URL
    
    ## Returns
    List of most relevant pages with similarity scores (0-1, higher is better)
    """
    try:
        if not vector_db_service.enabled:
            return SearchResponse(
                success=False,
                query=query,
                results_count=0,
                results=[],
                vector_enabled=False
            )
        
        # Perform vector search
        results = await vector_db_service.search_similar(
            query=query,
            top_k=top_k,
            base_url_filter=base_url_filter
        )
        
        logger.info(f"Search completed: {len(results)} results for query '{query}'")
        
        return SearchResponse(
            success=True,
            query=query,
            results_count=len(results),
            results=results,
            vector_enabled=True
        )
        
    except Exception as e:
        logger.error(f"Error during search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during search"
        )


@router.get("/vector/stats", response_model=dict, status_code=200)
async def get_vector_stats():
    """
    Get vector database statistics
    
    ## Description
    Returns information about the vector database including
    total pages stored, unique base URLs, and embedding configuration.
    
    ## Returns
    Dictionary with vector database statistics
    """
    try:
        stats = await vector_db_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting vector stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving stats"
        )


@router.get("/content/{url:path}", response_model=dict, status_code=200)
async def get_content_by_url(url: str):
    """
    Get crawled content by URL
    
    ## Description
    Retrieve previously crawled content for a specific URL.
    
    ## Parameters
    - **url**: The full URL to retrieve
    
    ## Returns
    Content data if found, or 404 if not found
    """
    try:
        if not vector_db_service.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector storage is not enabled"
            )
        
        content = await vector_db_service.get_content_by_url(url)
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found for this URL"
            )
        
        return content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving content"
        )
