"""
Database Connectors Package
Auto-registers all available database connectors
"""
from .registry import ConnectorRegistry, register_connector
from .base import BaseDatabaseConnector, DatabaseConnectorError, ConnectionError, QueryError

# Import core connectors (always required)
from .sqlserver import SQLServerConnector

# Import connectors with optional dependencies
try:
    from .postgresql import PostgreSQLConnector
except ImportError as e:
    print(f"PostgreSQL connector not available: {e}")
    PostgreSQLConnector = None

try:
    from .db2 import DB2Connector
except ImportError as e:
    print(f"DB2 connector not available: {e}")
    DB2Connector = None

# Optional connectors (only import if dependencies are available)
try:
    from .mysql import MySQLConnector
except ImportError:
    MySQLConnector = None

try:
    from .oracle import OracleConnector
except ImportError:
    OracleConnector = None

# Export the main components
__all__ = [
    'ConnectorRegistry',
    'register_connector',
    'BaseDatabaseConnector',
    'DatabaseConnectorError',
    'ConnectionError',
    'QueryError',
    'SQLServerConnector'
]

# Add optional connectors to exports if available
if PostgreSQLConnector:
    __all__.append('PostgreSQLConnector')
if DB2Connector:
    __all__.append('DB2Connector')
if MySQLConnector:
    __all__.append('MySQLConnector')
if OracleConnector:
    __all__.append('OracleConnector')
