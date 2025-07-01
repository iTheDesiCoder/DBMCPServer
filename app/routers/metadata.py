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
    query: Optional[str] = Query(None, description="Search term"),
    q: Optional[str] = Query(None, description="Search term (backward compatibility)"),
    types: Optional[List[str]] = Query(None, description="Object types to search (table, view, stored_procedure, function)"),
    schema: Optional[str] = Query(None, description="Schema to search within"),
    database: Optional[str] = Query(None, description="Database name to query"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    api_key: str = Depends(get_api_key)
):
    """Search for database objects matching the search term with smart error handling"""
    try:
        # Validate and convert string types to DatabaseObjectType enum
        object_types = None
        valid_types = ["table", "view", "stored_procedure", "function"]
        
        if types:
            object_types = []
            invalid_types = []
            
            for type_str in types:
                type_str_clean = type_str.lower().strip()
                
                # Handle common aliases
                if type_str_clean in ["proc", "procedure", "sp"]:
                    type_str_clean = "stored_procedure"
                elif type_str_clean in ["func", "fn"]:
                    type_str_clean = "function"
                elif type_str_clean in ["tbl"]:
                    type_str_clean = "table"
                elif type_str_clean in ["vw"]:
                    type_str_clean = "view"
                
                if type_str_clean in valid_types:
                    try:
                        object_types.append(DatabaseObjectType(type_str_clean))
                    except ValueError:
                        invalid_types.append(type_str)
                else:
                    invalid_types.append(type_str)
            
            if invalid_types:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Invalid object types",
                        "invalid_types": invalid_types,
                        "valid_types": valid_types,
                        "aliases": {
                            "stored_procedure": ["proc", "procedure", "sp"],
                            "function": ["func", "fn"],
                            "table": ["tbl"],
                            "view": ["vw"]
                        }
                    }
                )
        
        # Handle both 'query' and 'q' parameters for backward compatibility
        search_query = query or q
        if not search_query or not search_query.strip():
            raise HTTPException(
                status_code=422,
                detail="Search term cannot be empty. Use 'query' or 'q' parameter."
            )
        
        search_term = search_query.strip()
        
        logger.info(f"Searching for '{search_term}' with types: {[t.value for t in object_types] if object_types else 'all'}")
        
        results = await metadata_service.search_objects(
            search_term=search_term,
            object_types=object_types,
            schema=schema,
            database_name=database,
            limit=limit
        )
        
        logger.info(f"Search completed: found {len(results)} results")
        
        # Categorize results for better response
        categorized_results = {
            "tables": [],
            "views": [],
            "stored_procedures": [],
            "functions": []
        }
        
        for result in results:
            result_type = result.get("type", "").lower()
            if result_type == "table":
                categorized_results["tables"].append(result)
            elif result_type == "view":
                categorized_results["views"].append(result)
            elif result_type in ["procedure", "stored_procedure"]:
                categorized_results["stored_procedures"].append(result)
            elif result_type == "function":
                categorized_results["functions"].append(result)
        
        return {
            "query": search_term,
            "results": results,
            "categorized_results": categorized_results,
            "total_found": len(results),
            "counts": {
                "tables": len(categorized_results["tables"]),
                "views": len(categorized_results["views"]),
                "stored_procedures": len(categorized_results["stored_procedures"]),
                "functions": len(categorized_results["functions"])
            },
            "search_info": {
                "searched_types": [t.value for t in object_types] if object_types else valid_types,
                "searched_schema": schema,
                "limit_applied": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching database objects: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Search failed",
                "message": str(e),
                "search_term": search_query if 'search_query' in locals() else None
            }
        )


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
