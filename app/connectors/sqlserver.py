"""
Microsoft SQL Server Database Connector
"""
import pyodbc
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


@register_connector('sqlserver')
class SQLServerConnector(BaseDatabaseConnector):
    """Microsoft SQL Server database connector implementation"""
    
    @property
    def driver_name(self) -> str:
        return "SQL Server ODBC Driver"
    
    @property
    def database_type(self) -> str:
        return "sqlserver"
    
    async def connect(self) -> None:
        """Establish SQL Server connection"""
        try:
            self.logger.info(f"Connecting to SQL Server database: {self.config.name}")
            
            # Run the blocking connection in a thread pool
            self.connection = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: pyodbc.connect(
                    self.config.connection_string,
                    timeout=self.config.connection_timeout
                )
            )
            
            self.is_connected = True
            self.logger.info(f"Successfully connected to SQL Server: {self.config.name}")
            
        except pyodbc.Error as e:
            self.logger.error(f"Failed to connect to SQL Server {self.config.name}: {e}")
            raise ConnectionError(f"SQL Server connection failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to {self.config.name}: {e}")
            raise ConnectionError(f"Unexpected connection error: {e}")
    
    async def disconnect(self) -> None:
        """Close SQL Server connection"""
        if self.connection:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.connection.close
                )
                self.is_connected = False
                self.logger.info(f"Disconnected from SQL Server: {self.config.name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {self.config.name}: {e}")
            finally:
                self.connection = None
    
    async def test_connection(self) -> bool:
        """Test if the SQL Server connection is alive"""
        if not self.connection:
            return False
        
        try:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, self.connection.cursor
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, "SELECT 1"
            )
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed for {self.config.name}: {e}")
            return False
    
    async def get_schemas(self) -> List[str]:
        """Get list of all schemas in SQL Server"""
        query = """
        SELECT DISTINCT SCHEMA_NAME 
        FROM INFORMATION_SCHEMA.SCHEMATA 
        WHERE SCHEMA_NAME NOT IN ('information_schema', 'sys', 'guest', 'INFORMATION_SCHEMA')
        ORDER BY SCHEMA_NAME
        """
        
        try:
            results = await self.execute_query(query)
            schemas = [row['SCHEMA_NAME'] for row in results]
            
            # Filter by include_schemas if specified
            if self.config.include_schemas:
                schemas = [s for s in schemas if s in self.config.include_schemas]
                
            return schemas
        except Exception as e:
            self.logger.error(f"Error getting schemas from {self.config.name}: {e}")
            raise QueryError(f"Failed to get schemas: {e}")
    
    async def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of tables and views from SQL Server"""
        query = """
        SELECT 
            t.TABLE_SCHEMA as schema_name,
            t.TABLE_NAME as name,
            t.TABLE_TYPE,
            CASE WHEN t.TABLE_TYPE = 'BASE TABLE' THEN 'table' ELSE 'view' END as object_type
        FROM INFORMATION_SCHEMA.TABLES t
        WHERE t.TABLE_SCHEMA NOT IN ('information_schema', 'sys', 'guest')
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
        
        try:
            results = await self.execute_query(query, params)
            
            tables = []
            for row in results:
                table_info = {
                    'schema': row['schema_name'],
                    'name': row['name'],
                    'type': DatabaseObjectType.TABLE.value if row['object_type'] == 'table' else DatabaseObjectType.VIEW.value,
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
        """Get detailed table metadata from SQL Server"""
        if not schema:
            schema = self.get_default_schema()
            
        try:
            # Get columns
            columns = await self._get_table_columns(table_name, schema)
            
            # Get indexes
            indexes = await self._get_table_indexes(table_name, schema)
            
            # Get relationships (basic implementation)
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
        """Get list of stored procedures from SQL Server"""
        query = """
        SELECT 
            s.name as schema_name,
            p.name as name,
            p.create_date,
            p.modify_date
        FROM sys.procedures p
        INNER JOIN sys.schemas s ON p.schema_id = s.schema_id
        WHERE s.name NOT IN ('information_schema', 'sys', 'guest')
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
        
        try:
            results = await self.execute_query(query, params)
            
            procedures = []
            for row in results:
                proc_info = {
                    'schema': row['schema_name'],
                    'name': row['name'],
                    'type': DatabaseObjectType.STORED_PROCEDURE.value,
                    'created_date': str(row['create_date']) if row['create_date'] else None,
                    'modified_date': str(row['modify_date']) if row['modify_date'] else None,
                    'full_name': f"{row['schema_name']}.{row['name']}"
                }
                
                if not self.should_exclude_object(proc_info['name']):
                    procedures.append(proc_info)
                    
            return procedures
        except Exception as e:
            self.logger.error(f"Error getting stored procedures from {self.config.name}: {e}")
            raise QueryError(f"Failed to get stored procedures: {e}")
    
    async def get_stored_procedure_metadata(self, sp_name: str, schema: Optional[str] = None) -> StoredProcedureMetadata:
        """Get detailed stored procedure metadata from SQL Server"""
        if not schema:
            schema = self.get_default_schema()
            
        try:
            # Get parameters
            parameters = await self._get_procedure_parameters(sp_name, schema)
            
            # Get return columns (if available)
            returns = await self._get_procedure_return_columns(sp_name, schema)
            
            # Get related tables (basic implementation)
            related_tables = await self._get_procedure_related_tables(sp_name, schema)
            
            return StoredProcedureMetadata(
                name=sp_name,
                schema_name=schema,
                parameters=parameters,
                returns=returns,
                related_tables=related_tables
            )
        except Exception as e:
            self.logger.error(f"Error getting procedure metadata for {schema}.{sp_name}: {e}")
            raise QueryError(f"Failed to get procedure metadata: {e}")
    
    async def get_functions(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of functions from SQL Server"""
        query = """
        SELECT 
            s.name as schema_name,
            o.name as name,
            o.create_date,
            o.modify_date,
            o.type_desc
        FROM sys.objects o
        INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
        WHERE o.type IN ('FN', 'IF', 'TF')  -- Scalar, Inline Table, Table-valued functions
        AND s.name NOT IN ('information_schema', 'sys', 'guest')
        """
        
        params = []
        if schema:
            query += " AND s.name = ?"
            params.append(schema)
            
        if self.config.include_schemas:
            placeholders = ','.join(['?' for _ in self.config.include_schemas])
            query += f" AND s.name IN ({placeholders})"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY s.name, o.name"
        
        try:
            results = await self.execute_query(query, params)
            
            functions = []
            for row in results:
                func_info = {
                    'schema': row['schema_name'],
                    'name': row['name'],
                    'type': DatabaseObjectType.FUNCTION.value,
                    'function_type': row['type_desc'],
                    'created_date': str(row['create_date']) if row['create_date'] else None,
                    'modified_date': str(row['modify_date']) if row['modify_date'] else None,
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
            columns = [column[0] for column in cursor.description] if cursor.description else []
            
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
            
        except pyodbc.Error as e:
            self.logger.error(f"SQL Server query error: {e}")
            raise QueryError(f"Query execution failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error executing query: {e}")
            raise QueryError(f"Unexpected query error: {e}")
    
    # Helper methods for detailed metadata extraction
    
    async def _get_table_columns(self, table_name: str, schema: str) -> List[ColumnInfo]:
        """Get column information for a table"""
        query = """
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
        LEFT JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
            ON tc.TABLE_NAME = c.TABLE_NAME 
            AND tc.TABLE_SCHEMA = c.TABLE_SCHEMA 
            AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk 
            ON pk.CONSTRAINT_NAME = tc.CONSTRAINT_NAME 
            AND pk.COLUMN_NAME = c.COLUMN_NAME
        WHERE c.TABLE_NAME = ? AND c.TABLE_SCHEMA = ?
        ORDER BY c.ORDINAL_POSITION
        """
        
        results = await self.execute_query(query, [table_name, schema])
        
        columns = []
        for row in results:
            column = ColumnInfo(
                name=row['COLUMN_NAME'],
                type=row['DATA_TYPE'],
                nullable=row['IS_NULLABLE'] == 'YES',
                default_value=row['COLUMN_DEFAULT'],
                max_length=row['CHARACTER_MAXIMUM_LENGTH'],
                precision=row['NUMERIC_PRECISION'],
                scale=row['NUMERIC_SCALE'],
                primary_key=bool(row['is_primary_key'])
            )
            columns.append(column)
        
        return columns
    
    async def _get_table_indexes(self, table_name: str, schema: str) -> List[IndexInfo]:
        """Get index information for a table"""
        query = """
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
        
        results = await self.execute_query(query, [table_name, schema])
        
        indexes_data = {}
        for row in results:
            index_name = row['index_name']
            if index_name not in indexes_data:
                indexes_data[index_name] = {
                    'name': index_name,
                    'columns': [],
                    'unique': row['is_unique'],
                    'clustered': row['type_desc'] == 'CLUSTERED'
                }
            indexes_data[index_name]['columns'].append(row['column_name'])
        
        return [IndexInfo(**idx_data) for idx_data in indexes_data.values()]
    
    async def _get_table_relationships(self, table_name: str, schema: str) -> List[RelationshipInfo]:
        """Get relationship information for a table (simplified)"""
        # TODO: Implement foreign key relationship extraction
        return []
    
    async def _get_procedure_parameters(self, sp_name: str, schema: str) -> List[ParameterInfo]:
        """Get parameter information for a stored procedure"""
        query = """
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
        
        results = await self.execute_query(query, [sp_name, schema])
        
        parameters = []
        for row in results:
            param = ParameterInfo(
                name=row['parameter_name'],
                type=row['type_name'],
                direction="OUT" if row['is_output'] else "IN"
            )
            parameters.append(param)
        
        return parameters
    
    async def _get_procedure_return_columns(self, sp_name: str, schema: str) -> List[ColumnInfo]:
        """Get return column information for a stored procedure (simplified)"""
        # TODO: Implement return column extraction using sp_describe_first_result_set
        return []
    
    async def _get_procedure_related_tables(self, sp_name: str, schema: str) -> List[str]:
        """Get related tables for a stored procedure by parsing its definition"""
        return await self._parse_procedure_table_dependencies(sp_name, schema)
    
    async def _parse_procedure_table_dependencies(self, sp_name: str, schema: str) -> List[str]:
        """
        Parse stored procedure definition to extract table dependencies
        """
        try:
            # Get procedure definition
            definition_query = """
            SELECT 
                m.definition
            FROM sys.sql_modules m
            INNER JOIN sys.procedures p ON m.object_id = p.object_id
            INNER JOIN sys.schemas s ON p.schema_id = s.schema_id
            WHERE p.name = ? AND s.name = ?
            """
            
            definition_result = await self.execute_query(definition_query, [sp_name, schema])
            
            if not definition_result or not definition_result[0].get('definition'):
                return []
            
            definition = definition_result[0]['definition'].upper()
            tables = set()
            
            # Common SQL patterns to find table references
            import re
            
            # Pattern 1: FROM table_name or JOIN table_name
            from_join_pattern = r'\b(?:FROM|JOIN)\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?)'
            matches = re.findall(from_join_pattern, definition, re.IGNORECASE)
            
            for match in matches:
                schema_part, table_part = match
                if table_part:
                    # Skip common SQL keywords and system objects
                    if table_part.upper() not in ['INFORMATION_SCHEMA', 'SYS', 'MASTER', 'MSDB', 'TEMPDB', 'SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                        if schema_part:
                            tables.add(f"{schema_part}.{table_part}")
                        else:
                            tables.add(table_part)
            
            # Pattern 2: INSERT INTO table_name, UPDATE table_name
            insert_update_pattern = r'\b(?:INSERT\s+INTO|UPDATE)\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?)'
            matches = re.findall(insert_update_pattern, definition, re.IGNORECASE)
            
            for match in matches:
                schema_part, table_part = match
                if table_part and table_part.upper() not in ['VALUES', 'SET']:
                    if schema_part:
                        tables.add(f"{schema_part}.{table_part}")
                    else:
                        tables.add(table_part)
            
            # Pattern 3: DELETE FROM table_name
            delete_pattern = r'\bDELETE\s+FROM\s+(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?\.)?(?:\[?([a-zA-Z_][a-zA-Z0-9_]*)\]?)'
            matches = re.findall(delete_pattern, definition, re.IGNORECASE)
            
            for match in matches:
                schema_part, table_part = match
                if table_part:
                    if schema_part:
                        tables.add(f"{schema_part}.{table_part}")
                    else:
                        tables.add(table_part)
            
            # Verify tables exist in database to filter out false positives
            verified_tables = []
            for table in tables:
                if '.' in table:
                    table_schema, table_name = table.split('.', 1)
                else:
                    table_schema, table_name = schema, table
                
                # Check if table exists
                try:
                    check_query = """
                    SELECT COUNT(*) as count_result
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                    """
                    check_result = await self.execute_query(check_query, [table_schema, table_name])
                    exists = check_result and len(check_result) > 0 and check_result[0].get('count_result', 0) > 0
                    
                    if exists:
                        verified_tables.append(f"{table_schema}.{table_name}")
                except Exception:
                    # If verification fails, include the table anyway
                    verified_tables.append(table)
            
            return sorted(list(set(verified_tables)))
            
        except Exception as e:
            self.logger.warning(f"Error parsing table dependencies for {schema}.{sp_name}: {e}")
            return []
