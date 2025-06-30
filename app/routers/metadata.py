from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import List, Optional
from app.models import (
    TableMetadata, StoredProcedureMetadata, DatabaseMetadataResponse,
    DatabaseObjectType, MetadataSuggestion, ErrorResponse
)
from app.services.metadata import metadata_service
from app.auth import get_api_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@router.get("/", response_model=DatabaseMetadataResponse)
async def get_database_overview(
    database: Optional[str] = Query(None, description="Database name to query"),
    api_key: str = Depends(get_api_key)
):
    """Get complete database metadata overview"""
    try:
        return await metadata_service.get_database_overview(database)
    except Exception as e:
        logger.error(f"Error getting database overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(
    database: Optional[str] = Query(None, description="Database name to check"),
    api_key: str = Depends(get_api_key)
):
    """Check database connection health"""
    try:
        return await metadata_service.health_check(database)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-types")
async def get_supported_database_types(api_key: str = Depends(get_api_key)):
    """Get list of supported database types"""
    try:
        return {
            "supported_types": await metadata_service.get_supported_database_types()
        }
    except Exception as e:
        logger.error(f"Error getting supported types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table/{table_name}", response_model=TableMetadata)
async def get_table_metadata(
    table_name: str = Path(..., description="Name of the table"),
    schema: Optional[str] = Query(None, description="Schema name"),
    database: Optional[str] = Query(None, description="Database name to query"),
    api_key: str = Depends(get_api_key)
):
    """Get detailed metadata for a specific table"""
    try:
        return await metadata_service.get_table_metadata(table_name, schema, database)
    except Exception as e:
        logger.error(f"Error getting table metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/procedure/{procedure_name}", response_model=StoredProcedureMetadata)
async def get_stored_procedure_metadata(
    procedure_name: str = Path(..., description="Name of the stored procedure"),
    schema: Optional[str] = Query(None, description="Schema name"),
    database: Optional[str] = Query(None, description="Database name to query"),
    api_key: str = Depends(get_api_key)
):
    """Get detailed metadata for a specific stored procedure"""
    try:
        return await metadata_service.get_stored_procedure_metadata(procedure_name, schema, database)
    except Exception as e:
        logger.error(f"Error getting procedure metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_database_objects(
    q: str = Query(..., description="Search term"),
    types: Optional[List[str]] = Query(None, description="Object types to search"),
    schema: Optional[str] = Query(None, description="Schema to search within"),
    database: Optional[str] = Query(None, description="Database name to query"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    api_key: str = Depends(get_api_key)
):
    """Search for database objects matching the search term"""
    try:
        # Convert string types to DatabaseObjectType enum
        object_types = None
        if types:
            object_types = []
            for type_str in types:
                try:
                    object_types.append(DatabaseObjectType(type_str.lower()))
                except ValueError:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid object type: {type_str}. Valid types: table, view, stored_procedure, function"
                    )
        
        results = await metadata_service.search_objects(
            search_term=q,
            object_types=object_types,
            schema=schema,
            database_name=database,
            limit=limit
        )
        
        return {
            "query": q,
            "results": results,
            "total_found": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching database objects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_metadata_cache(
    database: Optional[str] = Query(None, description="Database name to clear cache for"),
    api_key: str = Depends(get_api_key)
):
    """Clear metadata cache for a specific database or all databases"""
    try:
        # This would need to be implemented in the cache manager
        from app.cache import cache
        if database:
            await cache.clear_pattern(f"*{database}*")
        else:
            await cache.clear_pattern("*")
        
        return {
            "message": f"Cache cleared successfully for database: {database or 'all'}",
            "database": database
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")
