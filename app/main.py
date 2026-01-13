"""
Crawler Microservice - Main Application Entry Point

Uses clean layered architecture:
- api/          - HTTP layer (controllers/endpoints)
- core/         - Cross-cutting concerns (config, utilities)
- models/       - ORM and data models
- schemas/      - Pydantic schemas for request/response validation
- services/     - Business logic layer
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.v1 import api_router
from .services.vector_db_service import vector_db_service
from .core.database import init_db

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Crawler Microservice API",
    description="""
    A high-performance web crawler and scraper microservice built with FastAPI.
    
    ## Features
    
    * **Web Crawling** - Recursively crawl websites following internal links
    * **Domain Boundary** - Automatically stay within the same base domain
    * **Content Extraction** - Extract text content, titles, and images
    * **Async Processing** - Concurrent page fetching using asyncio
    * **Error Handling** - Graceful handling of timeouts and HTTP errors
    * **Batch Operations** - Crawl multiple domains in a single request
    * **Structured Output** - JSON-formatted crawl results with metadata
    
    ## Architecture
    
    The service follows a clean layered architecture:
    - **API Layer**: FastAPI endpoints with request/response validation
    - **Service Layer**: Business logic for crawling and scraping
    - **Core Layer**: Configuration and utilities
    
    ## Performance
    
    - Asynchronous HTTP requests for efficient concurrent fetching
    - Configurable concurrency limits to avoid overwhelming servers
    - Timeout handling to prevent hanging requests
    - Automatic retry logic with configurable delays
    
    ## Usage
    
    1. **Basic Crawl**: Send a POST request to `/api/v1/crawler/crawl`
    2. **Batch Crawl**: Send multiple URLs to `/api/v1/crawler/crawl/batch`
    3. **Health Check**: GET `/api/v1/crawler/health` to verify service status
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Startup event - run initialization tasks"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Max concurrent requests: {settings.MAX_CONCURRENT_REQUESTS}")
    logger.info(f"Request timeout: {settings.REQUEST_TIMEOUT}s")
    
    # Initialize database tables
    try:
        init_db()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    
    # Initialize vector database if enabled
    if vector_db_service.enabled:
        logger.info("Initializing vector database with pgvector...")
        success = await vector_db_service.initialize_database()
        if success:
            logger.info("Vector database initialized successfully")
        else:
            logger.warning("Vector database initialization failed")
    else:
        logger.info("Vector storage is disabled")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event - cleanup resources"""
    logger.info(f"Shutting down {settings.APP_NAME}")
    
    # Close database connections
    if vector_db_service.enabled:
        await vector_db_service.close()
        logger.info("Vector database connections closed")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint - service information"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/crawler/health",
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/status", tags=["status"])
async def status():
    """Service status endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "config": {
            "max_concurrent_requests": settings.MAX_CONCURRENT_REQUESTS,
            "request_timeout": settings.REQUEST_TIMEOUT,
            "default_max_pages": settings.DEFAULT_MAX_PAGES,
            "max_allowed_pages": settings.MAX_ALLOWED_PAGES,
        },
    }
