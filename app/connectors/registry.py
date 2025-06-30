"""
Database Connector Registry
Provides a centralized way to register and retrieve database connectors
"""
from typing import Dict, Type, Optional, List
from app.connectors.base import BaseDatabaseConnector
from app.config import DatabaseConfig
import logging

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for managing database connectors.
    
    This allows for dynamic registration of new connector types and
    provides a factory method to create the appropriate connector
    based on database type.
    """
    
    _connectors: Dict[str, Type[BaseDatabaseConnector]] = {}
    
    @classmethod
    def register(cls, database_type: str, connector_class: Type[BaseDatabaseConnector]) -> None:
        """
        Register a connector class for a specific database type.
        
        Args:
            database_type: The database type identifier (e.g., 'sqlserver', 'postgresql')
            connector_class: The connector class that implements BaseDatabaseConnector
        """
        if not issubclass(connector_class, BaseDatabaseConnector):
            raise ValueError(f"Connector class must inherit from BaseDatabaseConnector")
        
        cls._connectors[database_type.lower()] = connector_class
        logger.info(f"Registered connector for database type: {database_type}")
    
    @classmethod
    def get_connector(cls, config: DatabaseConfig) -> BaseDatabaseConnector:
        """
        Get a connector instance for the specified database configuration.
        
        Args:
            config: Database configuration
            
        Returns:
            Instance of the appropriate connector
            
        Raises:
            ValueError: If no connector is registered for the database type
        """
        db_type = config.type.lower()
        
        if db_type not in cls._connectors:
            available_types = ", ".join(cls._connectors.keys())
            raise ValueError(
                f"No connector registered for database type: {db_type}. "
                f"Available types: {available_types}"
            )
        
        connector_class = cls._connectors[db_type]
        return connector_class(config)
    
    @classmethod
    def list_supported_types(cls) -> List[str]:
        """
        Get a list of all supported database types.
        
        Returns:
            List of supported database type identifiers
        """
        return list(cls._connectors.keys())
    
    @classmethod
    def is_supported(cls, database_type: str) -> bool:
        """
        Check if a database type is supported.
        
        Args:
            database_type: The database type to check
            
        Returns:
            True if the type is supported, False otherwise
        """
        return database_type.lower() in cls._connectors
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered connectors (mainly for testing)"""
        cls._connectors.clear()


# Decorator to simplify connector registration
def register_connector(database_type: str):
    """
    Decorator to register a connector class.
    
    Usage:
        @register_connector('mysql')
        class MySQLConnector(BaseDatabaseConnector):
            ...
    """
    def decorator(connector_class: Type[BaseDatabaseConnector]):
        ConnectorRegistry.register(database_type, connector_class)
        return connector_class
    return decorator
