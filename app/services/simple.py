"""
Simplified services module for initial testing
"""
from typing import List, Optional
from app.models import MetadataSuggestion, TableMetadata, StoredProcedureMetadata, DatabaseMetadataResponse
import logging

logger = logging.getLogger(__name__)


async def get_metadata_suggestion(query: str, database_name: str = None) -> List[MetadataSuggestion]:
    """Get metadata suggestions based on fuzzy query - simplified version"""
    logger.info(f"Getting metadata suggestions for query: {query}")
    
    # Return empty list for now - this is just to get the server running
    return []


async def get_table_details(table_name: str, schema: str = None, database_name: str = None) -> Optional[TableMetadata]:
    """Get detailed table metadata - simplified version"""
    logger.info(f"Getting table details for: {schema}.{table_name}")
    
    # Return None for now - this is just to get the server running
    return None


async def get_stored_procedure_details(sp_name: str, schema: str = None, database_name: str = None) -> Optional[StoredProcedureMetadata]:
    """Get detailed stored procedure metadata - simplified version"""
    logger.info(f"Getting stored procedure details for: {schema}.{sp_name}")
    
    # Return None for now - this is just to get the server running
    return None


async def get_database_overview(database_name: str = None) -> Optional[DatabaseMetadataResponse]:
    """Get overview of database schemas and objects - simplified version"""
    logger.info(f"Getting database overview for: {database_name}")
    
    # Return None for now - this is just to get the server running
    return None


async def clear_cache_for_database(database_name: str = None):
    """Clear cache for specific database or all databases - simplified version"""
    logger.info(f"Clearing cache for database: {database_name}")
    pass
