"""
IBM DB2 Database Connector
"""
import ibm_db
import ibm_db_dbi
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


@register_connector('db2')
class DB2Connector(BaseDatabaseConnector):
    """IBM DB2 database connector implementation"""
    
    @property
    def driver_name(self) -> str:
        return "IBM DB2 Driver"
    
    @property
    def database_type(self) -> str:
        return "db2"
    
    def get_default_schema(self) -> str:
        return "DB2INST1"  # Common default, can be overridden
    
    async def connect(self) -> None:
        """Establish DB2 connection"""
        try:
            self.logger.info(f"Connecting to DB2 database: {self.config.name}")
            
            # Run the blocking connection in a thread pool
            connection = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: ibm_db.connect(self.config.connection_string, "", "")
            )
            
            # Create DBI connection wrapper for easier SQL execution
            self.connection = ibm_db_dbi.Connection(connection)
            self._raw_connection = connection
            
            self.is_connected = True
            self.logger.info(f"Successfully connected to DB2: {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to DB2 {self.config.name}: {e}")
            raise ConnectionError(f"DB2 connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close DB2 connection"""
        if self._raw_connection:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, ibm_db.close, self._raw_connection
                )
                self.is_connected = False
                self.logger.info(f"Disconnected from DB2: {self.config.name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {self.config.name}: {e}")
            finally:
                self.connection = None
                self._raw_connection = None
    
    async def test_connection(self) -> bool:
        """Test if the DB2 connection is alive"""
        if not self._raw_connection:
            return False
        
        try:
            stmt = await asyncio.get_event_loop().run_in_executor(
                None, ibm_db.exec_immediate, self._raw_connection, "SELECT 1 FROM SYSIBM.SYSDUMMY1"
            )
            if stmt:
                await asyncio.get_event_loop().run_in_executor(
                    None, ibm_db.free_result, stmt
                )
                return True
            return False
        except Exception as e:
            self.logger.error(f"Connection test failed for {self.config.name}: {e}")
            return False
    
    async def get_schemas(self) -> List[str]:
        """Get list of all schemas in DB2"""
        query = """
        SELECT DISTINCT SCHEMANAME 
        FROM SYSCAT.SCHEMATA 
        WHERE SCHEMANAME NOT LIKE 'SYS%' 
        AND SCHEMANAME NOT IN ('INFORMATION_SCHEMA')
        ORDER BY SCHEMANAME
        """
        
        try:
            results = await self.execute_query(query)
            schemas = [row['SCHEMANAME'] for row in results]
            
            # Filter by include_schemas if specified
            if self.config.include_schemas:
                schemas = [s for s in schemas if s in self.config.include_schemas]
                
            return schemas
        except Exception as e:
            self.logger.error(f"Error getting schemas from {self.config.name}: {e}")
            raise QueryError(f"Failed to get schemas: {e}")
    
    async def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of tables and views from DB2"""
        query = """
        SELECT 
            TABSCHEMA as schema_name,
            TABNAME as name,
            TYPE,
            CASE WHEN TYPE = 'T' THEN 'table' 
                 WHEN TYPE = 'V' THEN 'view' 
                 ELSE 'other' END as object_type
        FROM SYSCAT.TABLES
        WHERE TABSCHEMA NOT LIKE 'SYS%'
        AND TABSCHEMA != 'INFORMATION_SCHEMA'
        """
        
        params = []
        if schema:
            query += " AND TABSCHEMA = ?"
            params.append(schema)
            
        if self.config.include_schemas and not schema:
            placeholders = ','.join(['?' for _ in self.config.include_schemas])
            query += f" AND TABSCHEMA IN ({placeholders})"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY TABSCHEMA, TABNAME"
        
        try:
            results = await self.execute_query(query, params)
            
            tables = []
            for row in results:
                table_info = {
                    'schema': row['schema_name'],
                    'name': row['name'],
                    'type': DatabaseObjectType.TABLE if row['object_type'] == 'table' else DatabaseObjectType.VIEW,
                    'full_name': f"{row['schema_name']}.{row['name']}"
                }
                
                # Apply exclude filters
                if not self.should_exclude_object(table_info['name']):
                    tables.append(table_info)
                    
            return tables
        except Exception as e:
            self.logger.error(f"Error getting tables from {self.config.name}: {e}")
            raise QueryError(f"Failed to get tables: {e}")
    
    async def get_table_metadata(self, table_name: str, schema: Optional[str] = None) -> TableMetadata:
        """Get detailed table metadata from DB2"""
        if not schema:
            schema = self.get_default_schema()
            
        try:
            # Get columns
            columns = await self._get_table_columns(table_name, schema)
            
            # Get indexes
            indexes = await self._get_table_indexes(table_name, schema)
            
            # Get relationships
            relationships = await self._get_table_relationships(table_name, schema)
            
            return TableMetadata(
                name=table_name,
                schema_name=schema,
                type=DatabaseObjectType.TABLE,
                columns=columns,
                indexes=indexes,
                relationships=relationships
            )
        except Exception as e:
            self.logger.error(f"Error getting table metadata for {schema}.{table_name}: {e}")
            raise QueryError(f"Failed to get table metadata: {e}")
    
    async def get_stored_procedures(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of stored procedures from DB2"""
        query = """
        SELECT 
            PROCSCHEMA as schema_name,
            PROCNAME as name,
            CREATE_TIME,
            ALTER_TIME
        FROM SYSCAT.PROCEDURES
        WHERE PROCSCHEMA NOT LIKE 'SYS%'
        AND PROCSCHEMA != 'INFORMATION_SCHEMA'
        """
        
        params = []
        if schema:
            query += " AND PROCSCHEMA = ?"
            params.append(schema)
            
        if self.config.include_schemas and not schema:
            placeholders = ','.join(['?' for _ in self.config.include_schemas])
            query += f" AND PROCSCHEMA IN ({placeholders})"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY PROCSCHEMA, PROCNAME"
        
        try:
            results = await self.execute_query(query, params)
            
            procedures = []
            for row in results:
                proc_info = {
                    'schema': row['schema_name'],
                    'name': row['name'],
                    'type': DatabaseObjectType.STORED_PROCEDURE,
                    'created_date': str(row['CREATE_TIME']) if row['CREATE_TIME'] else None,
                    'modified_date': str(row['ALTER_TIME']) if row['ALTER_TIME'] else None,
                    'full_name': f"{row['schema_name']}.{row['name']}"
                }
                
                if not self.should_exclude_object(proc_info['name']):
                    procedures.append(proc_info)
                    
            return procedures
        except Exception as e:
            self.logger.error(f"Error getting stored procedures from {self.config.name}: {e}")
            raise QueryError(f"Failed to get stored procedures: {e}")
    
    async def get_stored_procedure_metadata(self, sp_name: str, schema: Optional[str] = None) -> StoredProcedureMetadata:
        """Get detailed stored procedure metadata from DB2"""
        if not schema:
            schema = self.get_default_schema()
            
        try:
            # Get parameters
            parameters = await self._get_procedure_parameters(sp_name, schema)
            
            return StoredProcedureMetadata(
                name=sp_name,
                schema_name=schema,
                parameters=parameters,
                returns=[],
                related_tables=[]
            )
        except Exception as e:
            self.logger.error(f"Error getting procedure metadata for {schema}.{sp_name}: {e}")
            raise QueryError(f"Failed to get procedure metadata: {e}")
    
    async def get_functions(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of functions from DB2"""
        query = """
        SELECT 
            FUNCSCHEMA as schema_name,
            FUNCNAME as name,
            CREATE_TIME,
            ALTER_TIME
        FROM SYSCAT.FUNCTIONS
        WHERE FUNCSCHEMA NOT LIKE 'SYS%'
        AND FUNCSCHEMA != 'INFORMATION_SCHEMA'
        AND ORIGIN = 'U'  -- User-defined functions only
        """
        
        params = []
        if schema:
            query += " AND FUNCSCHEMA = ?"
            params.append(schema)
            
        if self.config.include_schemas and not schema:
            placeholders = ','.join(['?' for _ in self.config.include_schemas])
            query += f" AND FUNCSCHEMA IN ({placeholders})"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY FUNCSCHEMA, FUNCNAME"
        
        try:
            results = await self.execute_query(query, params)
            
            functions = []
            for row in results:
                func_info = {
                    'schema': row['schema_name'],
                    'name': row['name'],
                    'type': DatabaseObjectType.FUNCTION,
                    'created_date': str(row['CREATE_TIME']) if row['CREATE_TIME'] else None,
                    'modified_date': str(row['ALTER_TIME']) if row['ALTER_TIME'] else None,
                    'full_name': f"{row['schema_name']}.{row['name']}"
                }
                
                if not self.should_exclude_object(func_info['name']):
                    functions.append(func_info)
                    
            return functions
        except Exception as e:
            self.logger.error(f"Error getting functions from {self.config.name}: {e}")
            raise QueryError(f"Failed to get functions: {e}")
    
    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        if not self.is_connected:
            await self.connect()
        
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
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch all rows
            rows = await asyncio.get_event_loop().run_in_executor(
                None, cursor.fetchall
            )
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"DB2 query error: {e}")
            raise QueryError(f"Query execution failed: {e}")
    
    # Helper methods for detailed metadata extraction
    
    async def _get_table_columns(self, table_name: str, schema: str) -> List[ColumnInfo]:
        """Get column information for a table"""
        query = """
        SELECT 
            COLNAME as column_name,
            TYPENAME as data_type,
            NULLS as is_nullable,
            DEFAULT as column_default,
            LENGTH as character_maximum_length,
            SCALE as numeric_scale,
            CASE WHEN KEYSEQ IS NOT NULL THEN 1 ELSE 0 END as is_primary_key
        FROM SYSCAT.COLUMNS c
        LEFT JOIN SYSCAT.KEYCOLUSE k ON c.TABSCHEMA = k.TABSCHEMA 
                                      AND c.TABNAME = k.TABNAME 
                                      AND c.COLNAME = k.COLNAME
        WHERE c.TABNAME = ? AND c.TABSCHEMA = ?
        ORDER BY c.COLNO
        """
        
        results = await self.execute_query(query, [table_name, schema])
        
        columns = []
        for row in results:
            column = ColumnInfo(
                name=row['column_name'],
                type=row['data_type'],
                nullable=row['is_nullable'] == 'Y',
                default_value=row['column_default'],
                max_length=row['character_maximum_length'],
                precision=None,  # DB2 handles precision differently
                scale=row['numeric_scale'],
                primary_key=bool(row['is_primary_key'])
            )
            columns.append(column)
        
        return columns
    
    async def _get_table_indexes(self, table_name: str, schema: str) -> List[IndexInfo]:
        """Get index information for a table"""
        query = """
        SELECT 
            INDNAME as index_name,
            COLNAMES as columns,
            UNIQUERULE as unique_rule
        FROM SYSCAT.INDEXES
        WHERE TABNAME = ? AND TABSCHEMA = ?
        ORDER BY INDNAME
        """
        
        results = await self.execute_query(query, [table_name, schema])
        
        indexes = []
        for row in results:
            # Parse column names (DB2 stores them as "+COL1+COL2" format)
            column_names = [col.strip('+') for col in row['columns'].split('+') if col.strip('+')]
            
            index = IndexInfo(
                name=row['index_name'],
                columns=column_names,
                unique=row['unique_rule'] == 'U',
                clustered=False  # DB2 clustering is different concept
            )
            indexes.append(index)
        
        return indexes
    
    async def _get_table_relationships(self, table_name: str, schema: str) -> List[RelationshipInfo]:
        """Get relationship information for a table"""
        # TODO: Implement foreign key relationship extraction for DB2
        return []
    
    async def _get_procedure_parameters(self, sp_name: str, schema: str) -> List[ParameterInfo]:
        """Get parameter information for a stored procedure"""
        query = """
        SELECT 
            PARMNAME as parameter_name,
            TYPENAME as type_name,
            ROWTYPE as parameter_mode
        FROM SYSCAT.PROCPARMS
        WHERE PROCNAME = ? AND PROCSCHEMA = ?
        ORDER BY ORDINAL
        """
        
        results = await self.execute_query(query, [sp_name, schema])
        
        parameters = []
        for row in results:
            direction = "IN"
            if row['parameter_mode'] == 'O':
                direction = "OUT"
            elif row['parameter_mode'] == 'B':
                direction = "INOUT"
            
            param = ParameterInfo(
                name=row['parameter_name'] or f"param_{len(parameters)+1}",
                type=row['type_name'],
                direction=direction
            )
            parameters.append(param)
        
        return parameters
