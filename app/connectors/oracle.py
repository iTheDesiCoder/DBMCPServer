"""
Oracle Database Connector
Example implementation showing how to add new database types
"""
import cx_Oracle
from typing import List, Dict, Any, Optional
from app.connectors.base import BaseDatabaseConnector, ConnectionError, QueryError
from app.connectors.registry import register_connector
from app.models import (
    TableMetadata, StoredProcedureMetadata, ColumnInfo, 
    ParameterInfo, IndexInfo, RelationshipInfo, DatabaseObjectType
)
import asyncio
import logging

logger = logging.getLogger(__name__)


@register_connector('oracle')
class OracleConnector(BaseDatabaseConnector):
    """Oracle database connector implementation"""
    
    @property
    def driver_name(self) -> str:
        return "cx_Oracle"
    
    @property
    def database_type(self) -> str:
        return "oracle"
    
    def get_default_schema(self) -> str:
        # Oracle often uses the username as the default schema
        return "SYSTEM"  # This should be configurable
    
    async def connect(self) -> None:
        """Establish Oracle connection"""
        try:
            self.logger.info(f"Connecting to Oracle database: {self.config.name}")
            
            # Run the blocking connection in a thread pool
            self.connection = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: cx_Oracle.connect(self.config.connection_string)
            )
            
            self.is_connected = True
            self.logger.info(f"Successfully connected to Oracle: {self.config.name}")
            
        except cx_Oracle.Error as e:
            self.logger.error(f"Failed to connect to Oracle {self.config.name}: {e}")
            raise ConnectionError(f"Oracle connection failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to {self.config.name}: {e}")
            raise ConnectionError(f"Unexpected connection error: {e}")
    
    async def disconnect(self) -> None:
        """Close Oracle connection"""
        if self.connection:
            await asyncio.get_event_loop().run_in_executor(
                None, self.connection.close
            )
            self.is_connected = False
            self.logger.info(f"Disconnected from Oracle: {self.config.name}")
    
    async def test_connection(self) -> bool:
        """Test Oracle connection"""
        if not self.connection:
            return False
        
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, "SELECT 1 FROM DUAL"
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchone
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            return True
        except Exception as e:
            self.logger.error(f"Oracle connection test failed: {e}")
            return False
    
    async def get_schemas(self) -> List[str]:
        """Get list of Oracle schemas"""
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            
            query = """
            SELECT username 
            FROM all_users 
            WHERE username NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DIP', 'ORACLE_OCM', 'DBSNMP', 'APPQOSSYS', 'WMSYS', 'EXFSYS', 'CTXSYS', 'XDB', 'ANONYMOUS', 'XS$NULL', 'GSMADMIN_INTERNAL', 'MDDATA', 'SYSBACKUP', 'SYSDG', 'SYSKM', 'SYSMAN', 'MGMT_VIEW', 'FLOWS_FILES', 'MDSYS', 'ORDSYS', 'ORDDATA', 'ORDPLUGINS', 'OLAPSYS', 'SI_INFORMTN_SCHEMA', 'SPATIAL_CSW_ADMIN_USR', 'SPATIAL_WFS_ADMIN_USR', 'LBACSYS', 'OWBSYS', 'OWBSYS_AUDIT', 'SCOTT', 'PM', 'IX', 'SH', 'OE', 'HR', 'BI', 'DEMO')
            ORDER BY username
            """
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, query
            )
            results = await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchall
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            return [row[0] for row in results]
            
        except Exception as e:
            self.logger.error(f"Error getting Oracle schemas: {e}")
            raise QueryError(f"Failed to get schemas: {e}")
    
    async def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of Oracle tables"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            
            query = """
            SELECT table_name, 'TABLE' as table_type
            FROM all_tables 
            WHERE owner = :schema
            UNION ALL
            SELECT view_name, 'VIEW' as table_type
            FROM all_views 
            WHERE owner = :schema
            ORDER BY table_name
            """
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, query, {'schema': schema.upper()}
            )
            results = await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchall
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            tables = []
            for row in results:
                tables.append({
                    "name": row[0],
                    "type": row[1],
                    "schema": schema
                })
            
            return tables
            
        except Exception as e:
            self.logger.error(f"Error getting Oracle tables: {e}")
            raise QueryError(f"Failed to get tables: {e}")
    
    async def get_table_metadata(self, table_name: str, schema: Optional[str] = None) -> TableMetadata:
        """Get detailed Oracle table metadata"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            
            # Get column information
            query = """
            SELECT 
                column_name,
                data_type,
                nullable,
                data_default,
                data_length,
                data_precision,
                data_scale
            FROM all_tab_columns 
            WHERE owner = :schema AND table_name = :table_name
            ORDER BY column_id
            """
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, query, {'schema': schema.upper(), 'table_name': table_name.upper()}
            )
            column_results = await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchall
            )
            
            columns = []
            for row in column_results:
                column = ColumnInfo(
                    name=row[0],
                    type=row[1],
                    nullable=row[2] == 'Y',
                    default_value=row[3],
                    max_length=row[4],
                    precision=row[5],
                    scale=row[6]
                )
                columns.append(column)
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            return TableMetadata(
                name=table_name,
                schema_name=schema,
                type=DatabaseObjectType.TABLE,
                columns=columns,
                indexes=[],
                relationships=[]
            )
            
        except Exception as e:
            self.logger.error(f"Error getting Oracle table metadata: {e}")
            raise QueryError(f"Failed to get table metadata: {e}")
    
    async def get_stored_procedures(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Oracle stored procedures"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            
            query = """
            SELECT object_name, object_type
            FROM all_objects 
            WHERE owner = :schema 
            AND object_type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE')
            ORDER BY object_name
            """
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, query, {'schema': schema.upper()}
            )
            results = await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchall
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            procedures = []
            for row in results:
                procedures.append({
                    "name": row[0],
                    "type": row[1],
                    "schema": schema
                })
            
            return procedures
            
        except Exception as e:
            self.logger.error(f"Error getting Oracle procedures: {e}")
            raise QueryError(f"Failed to get procedures: {e}")
    
    async def get_stored_procedure_metadata(self, sp_name: str, schema: Optional[str] = None) -> StoredProcedureMetadata:
        """Get Oracle stored procedure metadata"""
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
        """Get Oracle functions"""
        schema = schema or self.get_default_schema()
        
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            
            query = """
            SELECT object_name
            FROM all_objects 
            WHERE owner = :schema 
            AND object_type = 'FUNCTION'
            ORDER BY object_name
            """
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, query, {'schema': schema.upper()}
            )
            results = await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchall
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            functions = []
            for row in results:
                functions.append({
                    "name": row[0],
                    "type": "FUNCTION",
                    "schema": schema
                })
            
            return functions
            
        except Exception as e:
            self.logger.error(f"Error getting Oracle functions: {e}")
            raise QueryError(f"Failed to get functions: {e}")
    
    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute Oracle query"""
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            
            if params:
                await asyncio.get_event_loop().run_in_executor(
                    None, cursor.execute, query, params
                )
            else:
                await asyncio.get_event_loop().run_in_executor(
                    None, cursor.execute, query
                )
            
            results = await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchall
            )
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            # Convert to list of dictionaries
            return [dict(zip(columns, row)) for row in results]
            
        except Exception as e:
            self.logger.error(f"Error executing Oracle query: {e}")
            raise QueryError(f"Query execution failed: {e}")
