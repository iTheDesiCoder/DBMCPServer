from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.routers import metadata
from app.services.metadata import metadata_service
from app.cache import cache
from app.auth import get_current_user
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting MCP Server...")
    
    # Initialize cache
    await cache.initialize()
    
    # Initialize connectors (they register automatically on import)
    from app.connectors import ConnectorRegistry
    supported_types = ConnectorRegistry.list_supported_types()
    logger.info(f"Registered database connectors: {supported_types}")
    
    # Test database connections on startup
    for db_config in settings.databases:
        try:
            health = await metadata_service.health_check(db_config.name)
            logger.info(f"Database {db_config.name} health: {health['status']}")
        except Exception as e:
            logger.error(f"Failed to check database {db_config.name}: {e}")
    
    logger.info("MCP Server startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Server...")
    
    # Close database connections
    await metadata_service.close_all_connections()
    
    # Close cache connection
    await cache.close()
    
    logger.info("MCP Server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Model Context Provider (MCP) Server for Enterprise Databases",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include routers
if settings.security.api_key_enabled or settings.security.oauth_enabled:
    # Apply authentication to all metadata routes
    app.include_router(
        metadata.router,
        dependencies=[Depends(get_current_user)]
    )
else:
    # No authentication required
    app.include_router(metadata.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MCP Server - Model Context Provider for Enterprise Databases",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Application health check"""
    # Check database connections
    db_status = {}
    for db_config in settings.databases:
        try:
            health = await metadata_service.health_check(db_config.name)
            db_status[db_config.name] = health.get("status", "unknown")
        except Exception as e:
            db_status[db_config.name] = "error"
    
    # Check cache
    cache_status = "connected" if cache.enabled and cache.redis_client else "disconnected"
    
    return {
        "status": "healthy",
        "databases": db_status,
        "cache": cache_status,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
