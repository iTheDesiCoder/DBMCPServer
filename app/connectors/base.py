"""
Base Database Connector Interface
Defines the contract that all database connectors must implement
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from app.models import (
    TableMetadata, StoredProcedureMetadata, ColumnInfo, 
    ParameterInfo, IndexInfo, RelationshipInfo, DatabaseObjectType
)
from app.config import DatabaseConfig
import logging

logger = logging.getLogger(__name__)


class DatabaseConnectorError(Exception):
    """Base exception for database connector errors"""
    pass


class ConnectionError(DatabaseConnectorError):
    """Raised when database connection fails"""
    pass


class QueryError(DatabaseConnectorError):
    """Raised when database query fails"""
    pass


class BaseDatabaseConnector(ABC):
    """
    Abstract base class for all database connectors.
    
    This defines the interface that all database-specific connectors must implement.
    It provides common functionality and ensures consistent behavior across different
    database types.
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        self._connection_pool = None
        self.is_connected = False
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
    @property
    @abstractmethod
    def driver_name(self) -> str:
        """Return the name of the database driver"""
        pass
    
    @property
    @abstractmethod
    def database_type(self) -> str:
        """Return the type of database (e.g., 'sqlserver', 'postgresql')"""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish database connection.
        Should set self.is_connected = True on success.
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close database connection.
        Should set self.is_connected = False.
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection is alive and working"""
        pass
    
    @abstractmethod
    async def get_schemas(self) -> List[str]:
        """Get list of all schemas in the database"""
        pass
    
    @abstractmethod
    async def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of tables and views.
        
        Args:
            schema: Optional schema name to filter tables
            
        Returns:
            List of dictionaries containing table information
        """
        pass
    
    @abstractmethod
    async def get_table_metadata(self, table_name: str, schema: Optional[str] = None) -> TableMetadata:
        """
        Get detailed metadata for a specific table.
        
        Args:
            table_name: Name of the table
            schema: Schema name (uses default if not provided)
            
        Returns:
            TableMetadata object with complete table information
        """
        pass
    
    @abstractmethod
    async def get_stored_procedures(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of stored procedures.
        
        Args:
            schema: Optional schema name to filter procedures
            
        Returns:
            List of dictionaries containing stored procedure information
        """
        pass
    
    @abstractmethod
    async def get_stored_procedure_metadata(self, sp_name: str, schema: Optional[str] = None) -> StoredProcedureMetadata:
        """
        Get detailed metadata for a specific stored procedure.
        
        Args:
            sp_name: Name of the stored procedure
            schema: Schema name (uses default if not provided)
            
        Returns:
            StoredProcedureMetadata object with complete procedure information
        """
        pass
    
    @abstractmethod
    async def get_functions(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of functions.
        
        Args:
            schema: Optional schema name to filter functions
            
        Returns:
            List of dictionaries containing function information
        """
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            List of dictionaries representing query results
        """
        pass
    
    # Common utility methods that can be overridden if needed
    
    def should_include_schema(self, schema_name: str) -> bool:
        """Check if schema should be included based on configuration"""
        if not self.config.include_schemas:
            return True
        return schema_name in self.config.include_schemas
    
    def should_exclude_object(self, object_name: str) -> bool:
        """Check if object should be excluded based on configuration"""
        if not self.config.exclude_objects:
            return False
            
        for pattern in self.config.exclude_objects:
            if pattern.endswith('*'):
                if object_name.startswith(pattern[:-1]):
                    return True
            elif pattern.startswith('*'):
                if object_name.endswith(pattern[1:]):
                    return True
            elif pattern == object_name:
                return True
        return False
    
    def get_default_schema(self) -> str:
        """Get the default schema for this database type"""
        return "dbo"  # Override in subclasses if different
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager:
        """
        Get a database connection from the pool.
        This is a context manager that ensures connections are properly returned to the pool.
        """
        if not self.is_connected:
            await self.connect()
        
        try:
            yield self.connection
        except Exception as e:
            self.logger.error(f"Error using database connection: {e}")
            raise
        finally:
            # Connection cleanup handled by subclass if needed
            pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the database connection.
        
        Returns:
            Dictionary with health check results
        """
        try:
            is_connected = await self.test_connection()
            return {
                "database": self.config.name,
                "type": self.database_type,
                "driver": self.driver_name,
                "status": "healthy" if is_connected else "unhealthy",
                "connection_string": self._mask_connection_string(),
                "is_connected": is_connected
            }
        except Exception as e:
            return {
                "database": self.config.name,
                "type": self.database_type,
                "driver": self.driver_name,
                "status": "error",
                "error": str(e),
                "is_connected": False
            }
    
    def _mask_connection_string(self) -> str:
        """Mask sensitive information in connection string for logging"""
        conn_str = self.config.connection_string
        # Simple masking - replace password with ***
        import re
        masked = re.sub(r'(PWD?=)[^;]+', r'\1***', conn_str, flags=re.IGNORECASE)
        masked = re.sub(r'(PASSWORD=)[^;]+', r'\1***', masked, flags=re.IGNORECASE)
        return masked
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.name}, type={self.database_type})"
    
    def __repr__(self) -> str:
        return self.__str__()
