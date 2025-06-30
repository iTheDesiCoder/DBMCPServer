"""
MySQL Database Connector
Example implementation showing how to add new database types
"""
import aiomysql
from typing import List, Dict, Any, Optional
from app.connectors.base import BaseDatabaseConnector, ConnectionError, QueryError
from app.connectors.registry import register_connector
from app.models import (
    TableMetadata, StoredProcedureMetadata, ColumnInfo, 
    ParameterInfo, IndexInfo, RelationshipInfo, DatabaseObjectType
)
import logging

logger = logging.getLogger(__name__)


@register_connector('mysql')
class MySQLConnector(BaseDatabaseConnector):
    """MySQL database connector implementation"""
    
    @property
    def driver_name(self) -> str:
        return "aiomysql"
    
    @property
    def database_type(self) -> str:
        return "mysql"
    
    def get_default_schema(self) -> str:
        # MySQL uses database name as schema
        return self.config.name
    
    async def connect(self) -> None:
        """Establish MySQL connection"""
        try:
            self.logger.info(f"Connecting to MySQL database: {self.config.name}")
            
            # Parse connection string or use individual parameters
            # This is a simplified example - you'd want more robust connection string parsing
            self.connection = await aiomysql.connect(
                host=self.config.connection_string.split(';')[0].split('=')[1],
                port=3306,
                user='root',  # Would parse from connection string
                password='password',  # Would parse from connection string
                db=self.config.name,
                autocommit=True
            )
            
            self.is_connected = True
            self.logger.info(f"Successfully connected to MySQL: {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MySQL {self.config.name}: {e}")
            raise ConnectionError(f"MySQL connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close MySQL connection"""
        if self.connection:
            self.connection.close()
            self.is_connected = False
            self.logger.info(f"Disconnected from MySQL: {self.config.name}")
    
    async def test_connection(self) -> bool:
        """Test MySQL connection"""
        if not self.connection:
            return False
        
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("SELECT 1")
            await cursor.fetchone()
            await cursor.close()
            return True
        except Exception as e:
            self.logger.error(f"MySQL connection test failed: {e}")
            return False
    
    async def get_schemas(self) -> List[str]:
        """Get list of databases (schemas in MySQL context)"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("SHOW DATABASES")
            results = await cursor.fetchall()
            await cursor.close()
            
            schemas = [row[0] for row in results if row[0] not in ('information_schema', 'mysql', 'performance_schema', 'sys')]
            return schemas
            
        except Exception as e:
            self.logger.error(f"Error getting MySQL schemas: {e}")
            raise QueryError(f"Failed to get schemas: {e}")
    
    async def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of tables in MySQL"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await self.connection.cursor()
            await cursor.execute(f"SHOW TABLES FROM `{schema}`")
            results = await cursor.fetchall()
            await cursor.close()
            
            tables = []
            for row in results:
                tables.append({
                    "name": row[0],
                    "type": "TABLE",
                    "schema": schema
                })
            
            return tables
            
        except Exception as e:
            self.logger.error(f"Error getting MySQL tables: {e}")
            raise QueryError(f"Failed to get tables: {e}")
    
    async def get_table_metadata(self, table_name: str, schema: Optional[str] = None) -> TableMetadata:
        """Get detailed MySQL table metadata"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await self.connection.cursor()
            
            # Get column information
            await cursor.execute(f"DESCRIBE `{schema}`.`{table_name}`")
            column_results = await cursor.fetchall()
            
            columns = []
            for row in column_results:
                column = ColumnInfo(
                    name=row[0],
                    type=row[1],
                    nullable=row[2] == 'YES',
                    primary_key=row[3] == 'PRI',
                    default_value=row[4]
                )
                columns.append(column)
            
            await cursor.close()
            
            return TableMetadata(
                name=table_name,
                schema_name=schema,
                type=DatabaseObjectType.TABLE,
                columns=columns,
                indexes=[],
                relationships=[]
            )
            
        except Exception as e:
            self.logger.error(f"Error getting MySQL table metadata: {e}")
            raise QueryError(f"Failed to get table metadata: {e}")
    
    async def get_stored_procedures(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get MySQL stored procedures"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await self.connection.cursor()
            await cursor.execute(f"SHOW PROCEDURE STATUS WHERE Db = '{schema}'")
            results = await cursor.fetchall()
            await cursor.close()
            
            procedures = []
            for row in results:
                procedures.append({
                    "name": row[1],  # Procedure name
                    "type": "PROCEDURE",
                    "schema": schema
                })
            
            return procedures
            
        except Exception as e:
            self.logger.error(f"Error getting MySQL procedures: {e}")
            raise QueryError(f"Failed to get procedures: {e}")
    
    async def get_stored_procedure_metadata(self, sp_name: str, schema: Optional[str] = None) -> StoredProcedureMetadata:
        """Get MySQL stored procedure metadata"""
        schema = schema or self.get_default_schema()
        
        # This is a simplified implementation
        return StoredProcedureMetadata(
            name=sp_name,
            schema_name=schema,
            type=DatabaseObjectType.STORED_PROCEDURE,
            parameters=[],
            returns=[],
            related_tables=[]
        )
    
    async def get_functions(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get MySQL functions"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await self.connection.cursor()
            await cursor.execute(f"SHOW FUNCTION STATUS WHERE Db = '{schema}'")
            results = await cursor.fetchall()
            await cursor.close()
            
            functions = []
            for row in results:
                functions.append({
                    "name": row[1],  # Function name
                    "type": "FUNCTION",
                    "schema": schema
                })
            
            return functions
            
        except Exception as e:
            self.logger.error(f"Error getting MySQL functions: {e}")
            raise QueryError(f"Failed to get functions: {e}")
    
    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute MySQL query"""
        try:
            cursor = await self.connection.cursor(aiomysql.DictCursor)
            
            if params:
                await cursor.execute(query, params)
            else:
                await cursor.execute(query)
            
            results = await cursor.fetchall()
            await cursor.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"Error executing MySQL query: {e}")
            raise QueryError(f"Query execution failed: {e}")
