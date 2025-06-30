import pyodbc
import ibm_db
import ibm_db_dbi
from sqlalchemy import create_engine, text
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from app.models import (
    TableMetadata, StoredProcedureMetadata, ColumnInfo, 
    ParameterInfo, IndexInfo, RelationshipInfo, DatabaseObjectType,
    SchemaOverview, DatabaseMetadataResponse
)
from app.config import DatabaseConfig
from app.cache import cache
import logging

logger = logging.getLogger(__name__)


class DatabaseConnector(ABC):
    """Abstract base class for database connectors"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        
    @abstractmethod
    async def connect(self):
        """Establish database connection"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close database connection"""
        pass
    
    @abstractmethod
    async def get_schemas(self) -> List[str]:
        """Get list of all schemas"""
        pass
    
    @abstractmethod
    async def get_tables(self, schema: str = None) -> List[Dict[str, Any]]:
        """Get list of tables"""
        pass
    
    @abstractmethod
    async def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        """Get detailed table metadata"""
        pass
    
    @abstractmethod
    async def get_stored_procedures(self, schema: str = None) -> List[Dict[str, Any]]:
        """Get list of stored procedures"""
        pass
    
    @abstractmethod
    async def get_stored_procedure_metadata(self, sp_name: str, schema: str = None) -> StoredProcedureMetadata:
        """Get detailed stored procedure metadata"""
        pass


class SQLServerConnector(DatabaseConnector):
    """SQL Server database connector"""
    
    async def connect(self):
        """Establish SQL Server connection"""
        try:
            self.connection = pyodbc.connect(
                self.config.connection_string,
                timeout=self.config.connection_timeout
            )
            logger.info(f"Connected to SQL Server database: {self.config.name}")
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server {self.config.name}: {e}")
            raise
    
    async def disconnect(self):
        """Close SQL Server connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    async def get_schemas(self) -> List[str]:
        """Get list of all schemas"""
        query = """
        SELECT DISTINCT SCHEMA_NAME 
        FROM INFORMATION_SCHEMA.SCHEMATA 
        WHERE SCHEMA_NAME NOT IN ('information_schema', 'sys')
        ORDER BY SCHEMA_NAME
        """
        cursor = self.connection.cursor()
        cursor.execute(query)
        schemas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        # Filter by include_schemas if specified
        if self.config.include_schemas:
            schemas = [s for s in schemas if s in self.config.include_schemas]
            
        return schemas
    
    async def get_tables(self, schema: str = None) -> List[Dict[str, Any]]:
        """Get list of tables"""
        query = """
        SELECT 
            t.TABLE_SCHEMA,
            t.TABLE_NAME,
            t.TABLE_TYPE,
            CASE WHEN t.TABLE_TYPE = 'BASE TABLE' THEN 'table' ELSE 'view' END as object_type
        FROM INFORMATION_SCHEMA.TABLES t
        WHERE t.TABLE_SCHEMA NOT IN ('information_schema', 'sys')
        """
        
        params = []
        if schema:
            query += " AND t.TABLE_SCHEMA = ?"
            params.append(schema)
            
        if self.config.include_schemas:
            placeholders = ','.join(['?' for _ in self.config.include_schemas])
            query += f" AND t.TABLE_SCHEMA IN ({placeholders})"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME"
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        
        tables = []
        for row in cursor.fetchall():
            table_info = {
                'schema': row[0],
                'name': row[1],
                'type': DatabaseObjectType.TABLE if row[3] == 'table' else DatabaseObjectType.VIEW,
                'full_name': f"{row[0]}.{row[1]}"
            }
            
            # Apply exclude filters
            if self._should_exclude_object(table_info['name']):
                continue
                
            tables.append(table_info)
            
        cursor.close()
        return tables
    
    async def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        """Get detailed table metadata"""
        if not schema:
            schema = 'dbo'
            
        # Get columns
        columns_query = """
        SELECT 
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.IS_NULLABLE,
            c.COLUMN_DEFAULT,
            c.CHARACTER_MAXIMUM_LENGTH,
            c.NUMERIC_PRECISION,
            c.NUMERIC_SCALE,
            CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as is_primary_key
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc ON tc.TABLE_NAME = c.TABLE_NAME AND tc.TABLE_SCHEMA = c.TABLE_SCHEMA AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk ON pk.CONSTRAINT_NAME = tc.CONSTRAINT_NAME AND pk.COLUMN_NAME = c.COLUMN_NAME
        WHERE c.TABLE_NAME = ? AND c.TABLE_SCHEMA = ?
        ORDER BY c.ORDINAL_POSITION
        """
        
        cursor = self.connection.cursor()
        cursor.execute(columns_query, (table_name, schema))
        
        columns = []
        for row in cursor.fetchall():
            column = ColumnInfo(
                name=row[0],
                type=row[1],
                nullable=row[2] == 'YES',
                default_value=row[3],
                max_length=row[4],
                precision=row[5],
                scale=row[6],
                primary_key=bool(row[7])
            )
            columns.append(column)
        
        # Get indexes
        indexes_query = """
        SELECT 
            i.name as index_name,
            c.name as column_name,
            i.is_unique,
            i.type_desc
        FROM sys.indexes i
        INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        INNER JOIN sys.tables t ON i.object_id = t.object_id
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE t.name = ? AND s.name = ? AND i.type > 0
        ORDER BY i.name, ic.key_ordinal
        """
        
        cursor.execute(indexes_query, (table_name, schema))
        
        indexes_data = {}
        for row in cursor.fetchall():
            index_name = row[0]
            if index_name not in indexes_data:
                indexes_data[index_name] = {
                    'name': index_name,
                    'columns': [],
                    'unique': row[2],
                    'clustered': row[3] == 'CLUSTERED'
                }
            indexes_data[index_name]['columns'].append(row[1])
          indexes = [IndexInfo(**idx_data) for idx_data in indexes_data.values()]
        
        cursor.close()
        
        return TableMetadata(
            name=table_name,
            schema_name=schema,
            type=DatabaseObjectType.TABLE,
            columns=columns,
            indexes=indexes,
            relationships=[]  # TODO: Implement relationship extraction
        )
    
    async def get_stored_procedures(self, schema: str = None) -> List[Dict[str, Any]]:
        """Get list of stored procedures"""
        query = """
        SELECT 
            s.name as schema_name,
            p.name as procedure_name,
            p.create_date,
            p.modify_date
        FROM sys.procedures p
        INNER JOIN sys.schemas s ON p.schema_id = s.schema_id
        WHERE s.name NOT IN ('information_schema', 'sys')
        """
        
        params = []
        if schema:
            query += " AND s.name = ?"
            params.append(schema)
            
        if self.config.include_schemas:
            placeholders = ','.join(['?' for _ in self.config.include_schemas])
            query += f" AND s.name IN ({placeholders})"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY s.name, p.name"
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        
        procedures = []
        for row in cursor.fetchall():
            proc_info = {
                'schema': row[0],
                'name': row[1],
                'type': DatabaseObjectType.STORED_PROCEDURE,
                'created_date': str(row[2]) if row[2] else None,
                'modified_date': str(row[3]) if row[3] else None,
                'full_name': f"{row[0]}.{row[1]}"
            }
            
            if self._should_exclude_object(proc_info['name']):
                continue
                
            procedures.append(proc_info)
            
        cursor.close()
        return procedures
    
    async def get_stored_procedure_metadata(self, sp_name: str, schema: str = None) -> StoredProcedureMetadata:
        """Get detailed stored procedure metadata"""
        if not schema:
            schema = 'dbo'
            
        # Get parameters
        params_query = """
        SELECT 
            p.name as parameter_name,
            t.name as type_name,
            p.max_length,
            p.precision,
            p.scale,
            p.is_output
        FROM sys.parameters p
        INNER JOIN sys.types t ON p.user_type_id = t.user_type_id
        INNER JOIN sys.procedures pr ON p.object_id = pr.object_id
        INNER JOIN sys.schemas s ON pr.schema_id = s.schema_id
        WHERE pr.name = ? AND s.name = ?
        ORDER BY p.parameter_id
        """
        
        cursor = self.connection.cursor()
        cursor.execute(params_query, (sp_name, schema))
        
        parameters = []
        for row in cursor.fetchall():
            param = ParameterInfo(
                name=row[0],
                type=row[1],
                direction="OUT" if row[5] else "IN"
            )
            parameters.append(param)
          cursor.close()
        
        return StoredProcedureMetadata(
            name=sp_name,
            schema_name=schema,
            parameters=parameters,
            returns=[],  # TODO: Implement return type extraction
            related_tables=[]  # TODO: Implement related table extraction
        )
    
    def _should_exclude_object(self, object_name: str) -> bool:
        """Check if object should be excluded based on config"""
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


class DB2Connector(DatabaseConnector):
    """IBM DB2 database connector"""
    
    async def connect(self):
        """Establish DB2 connection"""
        try:
            self.connection = ibm_db.connect(self.config.connection_string, "", "")
            logger.info(f"Connected to DB2 database: {self.config.name}")
        except Exception as e:
            logger.error(f"Failed to connect to DB2 {self.config.name}: {e}")
            raise
    
    async def disconnect(self):
        """Close DB2 connection"""
        if self.connection:
            ibm_db.close(self.connection)
            self.connection = None
    
    # TODO: Implement DB2-specific methods
    async def get_schemas(self) -> List[str]:
        return []
    
    async def get_tables(self, schema: str = None) -> List[Dict[str, Any]]:
        return []
    
    async def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        pass
    
    async def get_stored_procedures(self, schema: str = None) -> List[Dict[str, Any]]:
        return []
    
    async def get_stored_procedure_metadata(self, sp_name: str, schema: str = None) -> StoredProcedureMetadata:
        pass


class MetadataExtractor:
    """Main metadata extraction service"""
    
    def __init__(self):
        self.connectors: Dict[str, DatabaseConnector] = {}
        
    def add_database(self, config: DatabaseConfig) -> DatabaseConnector:
        """Add a database configuration and create connector"""
        if config.type.lower() == 'sqlserver':
            connector = SQLServerConnector(config)
        elif config.type.lower() == 'db2':
            connector = DB2Connector(config)
        else:
            raise ValueError(f"Unsupported database type: {config.type}")
        
        self.connectors[config.name] = connector
        return connector
    
    async def initialize_connections(self):
        """Initialize all database connections"""
        for name, connector in self.connectors.items():
            try:
                await connector.connect()
            except Exception as e:
                logger.error(f"Failed to initialize connection for {name}: {e}")
    
    async def close_connections(self):
        """Close all database connections"""
        for connector in self.connectors.values():
            try:
                await connector.disconnect()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
    
    async def get_all_objects(self, database_name: str = None) -> List[Dict[str, Any]]:
        """Get all database objects for fuzzy matching"""
        cache_key = f"all_objects:{database_name or 'all'}"
        
        # Try cache first
        cached_result = await cache.get(cache_key)
        if cached_result:
            return cached_result
        
        all_objects = []
        connectors_to_query = []
        
        if database_name and database_name in self.connectors:
            connectors_to_query = [self.connectors[database_name]]
        else:
            connectors_to_query = list(self.connectors.values())
        
        for connector in connectors_to_query:
            try:
                # Get tables and views
                tables = await connector.get_tables()
                all_objects.extend(tables)
                
                # Get stored procedures
                procedures = await connector.get_stored_procedures()
                all_objects.extend(procedures)
                
            except Exception as e:
                logger.error(f"Error getting objects from {connector.config.name}: {e}")
        
        # Cache results
        await cache.set(cache_key, all_objects)
        return all_objects


# Global metadata extractor instance
metadata_extractor = MetadataExtractor()
