"""
Database Metadata Service
High-level service for extracting database metadata using the connector architecture
"""
from typing import List, Dict, Any, Optional, Union
from app.connectors import ConnectorRegistry, BaseDatabaseConnector
from app.config import DatabaseConfig, settings
from app.models import (
    TableMetadata, StoredProcedureMetadata, ColumnInfo, 
    ParameterInfo, IndexInfo, RelationshipInfo, DatabaseObjectType,
    SchemaOverview, DatabaseMetadataResponse
)
from app.cache import cache_result
import logging

logger = logging.getLogger(__name__)


def get_database_config(database_name: Optional[str] = None) -> DatabaseConfig:
    """Get database configuration by name or return the first one"""
    if not settings.databases:
        raise ValueError("No databases configured")
    
    if database_name:
        for db_config in settings.databases:
            if db_config.name == database_name:
                return db_config
        raise ValueError(f"Database '{database_name}' not found in configuration")
    
    return settings.databases[0]


class DatabaseMetadataService:
    """
    High-level service for database metadata extraction.
    
    This service abstracts the database-specific implementation details
    and provides a consistent interface for metadata extraction across
    different database types.
    """
    
    def __init__(self):
        self._connectors: Dict[str, BaseDatabaseConnector] = {}
    
    async def get_connector(self, database_name: Optional[str] = None) -> BaseDatabaseConnector:
        """
        Get or create a connector for the specified database.
        
        Args:
            database_name: Name of the database configuration to use
            
        Returns:
            Database connector instance
        """
        config = get_database_config(database_name)
        connector_key = config.name
        
        if connector_key not in self._connectors:
            self._connectors[connector_key] = ConnectorRegistry.get_connector(config)
        
        connector = self._connectors[connector_key]
        
        # Ensure connection is established
        if not connector.is_connected:
            await connector.connect()
        
        return connector
    
    @cache_result(ttl=300)  # Cache for 5 minutes
    async def get_database_overview(self, database_name: Optional[str] = None) -> DatabaseMetadataResponse:
        """
        Get a complete overview of the database metadata.
        
        Args:
            database_name: Name of the database configuration to use
            
        Returns:
            Complete database metadata response
        """
        connector = await self.get_connector(database_name)
        
        try:
            # Get schemas
            schemas = await connector.get_schemas()
            schema_overviews = []
            
            for schema in schemas:
                if not connector.should_include_schema(schema):
                    continue
                    
                # Get tables for this schema
                tables = await connector.get_tables(schema)
                table_list = [
                    {
                        "name": table["name"],
                        "type": table.get("type", "TABLE"),
                        "schema": schema
                    }
                    for table in tables
                    if not connector.should_exclude_object(table["name"])
                ]
                
                # Get stored procedures for this schema
                try:
                    procedures = await connector.get_stored_procedures(schema)
                    procedure_list = [
                        {
                            "name": proc["name"],
                            "type": "PROCEDURE",
                            "schema": schema
                        }
                        for proc in procedures
                        if not connector.should_exclude_object(proc["name"])
                    ]
                except NotImplementedError:
                    procedure_list = []
                
                # Get functions for this schema
                try:
                    functions = await connector.get_functions(schema)
                    function_list = [
                        {
                            "name": func["name"],
                            "type": "FUNCTION",
                            "schema": schema
                        }
                        for func in functions
                        if not connector.should_exclude_object(func["name"])
                    ]
                except NotImplementedError:
                    function_list = []
                
                schema_overview = SchemaOverview(
                    schema_name=schema,
                    table_count=len(table_list),
                    procedure_count=len(procedure_list),
                    function_count=len(function_list),
                    tables=table_list,
                    procedures=procedure_list,
                    functions=function_list
                )
                schema_overviews.append(schema_overview)
            
            total_tables = sum(s.table_count for s in schema_overviews)
            total_procedures = sum(s.procedure_count for s in schema_overviews)
            total_functions = sum(s.function_count for s in schema_overviews)
            
            return DatabaseMetadataResponse(
                database_name=connector.config.name,
                database_type=connector.database_type,
                schemas=schema_overviews,
                total_schemas=len(schema_overviews),
                total_tables=total_tables,
                total_procedures=total_procedures,
                total_functions=total_functions,
                total_objects=total_tables + total_procedures + total_functions
            )
            
        except Exception as e:
            logger.error(f"Error getting database overview: {e}")
            raise
    
    @cache_result(ttl=600)  # Cache for 10 minutes
    async def get_table_metadata(
        self, 
        table_name: str, 
        schema: Optional[str] = None,
        database_name: Optional[str] = None
    ) -> TableMetadata:
        """
        Get detailed metadata for a specific table.
        
        Args:
            table_name: Name of the table
            schema: Schema name (uses default if not provided)
            database_name: Name of the database configuration to use
            
        Returns:
            Detailed table metadata
        """
        connector = await self.get_connector(database_name)
        
        try:
            return await connector.get_table_metadata(table_name, schema)
        except Exception as e:
            logger.error(f"Error getting table metadata for {table_name}: {e}")
            raise
    
    @cache_result(ttl=600)  # Cache for 10 minutes
    async def get_stored_procedure_metadata(
        self, 
        procedure_name: str, 
        schema: Optional[str] = None,
        database_name: Optional[str] = None
    ) -> StoredProcedureMetadata:
        """
        Get detailed metadata for a specific stored procedure.
        
        Args:
            procedure_name: Name of the stored procedure
            schema: Schema name (uses default if not provided)
            database_name: Name of the database configuration to use
            
        Returns:
            Detailed stored procedure metadata
        """
        connector = await self.get_connector(database_name)
        
        try:
            return await connector.get_stored_procedure_metadata(procedure_name, schema)
        except Exception as e:
            logger.error(f"Error getting procedure metadata for {procedure_name}: {e}")
            raise
    
    async def search_objects(
        self,
        search_term: str,
        object_types: Optional[List[DatabaseObjectType]] = None,
        schema: Optional[str] = None,
        database_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for database objects matching the search term.
        
        Args:
            search_term: Term to search for
            object_types: Types of objects to include in search
            schema: Schema to search within (optional)
            database_name: Name of the database configuration to use
            limit: Maximum number of results to return
            
        Returns:
            List of matching database objects
        """
        connector = await self.get_connector(database_name)
        results = []
        
        if not object_types:
            object_types = [DatabaseObjectType.TABLE, DatabaseObjectType.VIEW, 
                          DatabaseObjectType.STORED_PROCEDURE, DatabaseObjectType.FUNCTION]
        
        try:
            # Search tables and views
            if DatabaseObjectType.TABLE in object_types or DatabaseObjectType.VIEW in object_types:
                schemas_to_search = [schema] if schema else await connector.get_schemas()
                
                for schema_name in schemas_to_search:
                    if not connector.should_include_schema(schema_name):
                        continue
                        
                    tables = await connector.get_tables(schema_name)
                    for table in tables:
                        if (search_term.lower() in table["name"].lower() and 
                            not connector.should_exclude_object(table["name"])):
                            
                            table_type = table.get("type", "TABLE")
                            if ((table_type == "TABLE" and DatabaseObjectType.TABLE in object_types) or
                                (table_type == "VIEW" and DatabaseObjectType.VIEW in object_types)):
                                
                                results.append({
                                    "name": table["name"],
                                    "schema": schema_name,
                                    "type": table_type,
                                    "description": table.get("description", "")
                                })
                                
                                if len(results) >= limit:
                                    break
                    
                    if len(results) >= limit:
                        break
            
            # Search stored procedures
            if DatabaseObjectType.STORED_PROCEDURE in object_types and len(results) < limit:
                schemas_to_search = [schema] if schema else await connector.get_schemas()
                
                for schema_name in schemas_to_search:
                    if not connector.should_include_schema(schema_name):
                        continue
                    
                    try:
                        procedures = await connector.get_stored_procedures(schema_name)
                        for procedure in procedures:
                            if (search_term.lower() in procedure["name"].lower() and 
                                not connector.should_exclude_object(procedure["name"])):
                                
                                results.append({
                                    "name": procedure["name"],
                                    "schema": schema_name,
                                    "type": "PROCEDURE",
                                    "description": procedure.get("description", "")
                                })
                                
                                if len(results) >= limit:
                                    break
                        
                        if len(results) >= limit:
                            break
                    except NotImplementedError:
                        continue
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching database objects: {e}")
            raise
    
    async def health_check(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a health check on the database connection.
        
        Args:
            database_name: Name of the database configuration to check
            
        Returns:
            Health check results
        """
        try:
            connector = await self.get_connector(database_name)
            return await connector.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "is_connected": False
            }
    
    async def get_supported_database_types(self) -> List[str]:
        """
        Get a list of all supported database types.
        
        Returns:
            List of supported database type identifiers
        """
        return ConnectorRegistry.list_supported_types()
    
    async def close_all_connections(self):
        """Close all active database connections"""
        for connector in self._connectors.values():
            try:
                await connector.disconnect()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        self._connectors.clear()


# Global service instance
metadata_service = DatabaseMetadataService()
