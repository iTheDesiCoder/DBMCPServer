"""
PostgreSQL Database Connector
"""
import asyncpg
from typing import List, Dict, Any, Optional
from app.connectors.base import BaseDatabaseConnector, ConnectionError, QueryError
from app.connectors.registry import register_connector
from app.models import (
    TableMetadata, StoredProcedureMetadata, ColumnInfo, 
    ParameterInfo, IndexInfo, RelationshipInfo, DatabaseObjectType
)
import logging

logger = logging.getLogger(__name__)


@register_connector('postgresql')
class PostgreSQLConnector(BaseDatabaseConnector):
    """PostgreSQL database connector implementation"""
    
    @property
    def driver_name(self) -> str:
        return "asyncpg"
    
    @property
    def database_type(self) -> str:
        return "postgresql"
    
    def get_default_schema(self) -> str:
        return "public"
    
    async def connect(self) -> None:
        """Establish PostgreSQL connection"""
        try:
            self.logger.info(f"Connecting to PostgreSQL database: {self.config.name}")
            
            # Parse connection string or use asyncpg.connect with parameters
            self.connection = await asyncpg.connect(self.config.connection_string)
            
            self.is_connected = True
            self.logger.info(f"Successfully connected to PostgreSQL: {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL {self.config.name}: {e}")
            raise ConnectionError(f"PostgreSQL connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close PostgreSQL connection"""
        if self.connection:
            try:
                await self.connection.close()
                self.is_connected = False
                self.logger.info(f"Disconnected from PostgreSQL: {self.config.name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {self.config.name}: {e}")
            finally:
                self.connection = None
    
    async def test_connection(self) -> bool:
        """Test if the PostgreSQL connection is alive"""
        if not self.connection:
            return False
        
        try:
            await self.connection.fetchval("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed for {self.config.name}: {e}")
            return False
    
    async def get_schemas(self) -> List[str]:
        """Get list of all schemas in PostgreSQL"""
        query = """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY schema_name
        """
        
        try:
            results = await self.execute_query(query)
            schemas = [row['schema_name'] for row in results]
            
            # Filter by include_schemas if specified
            if self.config.include_schemas:
                schemas = [s for s in schemas if s in self.config.include_schemas]
                
            return schemas
        except Exception as e:
            self.logger.error(f"Error getting schemas from {self.config.name}: {e}")
            raise QueryError(f"Failed to get schemas: {e}")
    
    async def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of tables and views from PostgreSQL"""
        query = """
        SELECT 
            table_schema as schema_name,
            table_name as name,
            table_type,
            CASE WHEN table_type = 'BASE TABLE' THEN 'table' ELSE 'view' END as object_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        """
        
        params = []
        if schema:
            query += " AND table_schema = $1"
            params.append(schema)
            
        if self.config.include_schemas and not schema:
            placeholders = ','.join([f'${i+1}' for i in range(len(self.config.include_schemas))])
            query += f" AND table_schema = ANY(ARRAY[{placeholders}])"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY table_schema, table_name"
        
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
        """Get detailed table metadata from PostgreSQL"""
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
        """Get list of stored procedures/functions from PostgreSQL"""
        query = """
        SELECT 
            routine_schema as schema_name,
            routine_name as name,
            routine_type,
            created
        FROM information_schema.routines
        WHERE routine_schema NOT IN ('information_schema', 'pg_catalog')
        """
        
        params = []
        if schema:
            query += " AND routine_schema = $1"
            params.append(schema)
            
        if self.config.include_schemas and not schema:
            placeholders = ','.join([f'${i+1}' for i in range(len(self.config.include_schemas))])
            query += f" AND routine_schema = ANY(ARRAY[{placeholders}])"
            params.extend(self.config.include_schemas)
        
        query += " ORDER BY routine_schema, routine_name"
        
        try:
            results = await self.execute_query(query, params)
            
            procedures = []
            for row in results:
                proc_info = {
                    'schema': row['schema_name'],
                    'name': row['name'],
                    'type': DatabaseObjectType.FUNCTION if row['routine_type'] == 'FUNCTION' else DatabaseObjectType.STORED_PROCEDURE,
                    'created_date': str(row['created']) if row['created'] else None,
                    'full_name': f"{row['schema_name']}.{row['name']}"
                }
                
                if not self.should_exclude_object(proc_info['name']):
                    procedures.append(proc_info)
                    
            return procedures
        except Exception as e:
            self.logger.error(f"Error getting procedures from {self.config.name}: {e}")
            raise QueryError(f"Failed to get procedures: {e}")
    
    async def get_stored_procedure_metadata(self, sp_name: str, schema: Optional[str] = None) -> StoredProcedureMetadata:
        """Get detailed stored procedure metadata from PostgreSQL"""
        if not schema:
            schema = self.get_default_schema()
            
        try:
            # Get parameters
            parameters = await self._get_procedure_parameters(sp_name, schema)
            
            # Get related tables by parsing function definition
            related_tables = await self._get_procedure_related_tables(sp_name, schema)
            
            return StoredProcedureMetadata(
                name=sp_name,
                schema_name=schema,
                parameters=parameters,
                returns=[],
                related_tables=related_tables
            )
        except Exception as e:
            self.logger.error(f"Error getting procedure metadata for {schema}.{sp_name}: {e}")
            raise QueryError(f"Failed to get procedure metadata: {e}")

    async def _get_procedure_related_tables(self, function_name: str, schema: str) -> List[str]:
        """Get related tables for a PostgreSQL function/procedure by parsing its definition"""
        try:
            # Get function definition from PostgreSQL system catalogs
            definition_query = """
            SELECT pg_get_functiondef(p.oid) as definition
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE p.proname = $1 AND n.nspname = $2
            """
            
            result = await self.execute_query(definition_query, [function_name, schema])
            
            if not result or not result[0].get('definition'):
                return []
            
            definition = result[0]['definition'].upper()
            tables = set()
            
            # Common SQL patterns to find table references
            import re
            
            # Pattern 1: FROM table_name or JOIN table_name
            from_join_pattern = r'\b(?:FROM|JOIN)\s+(?:([a-zA-Z_][a-zA-Z0-9_]*)\.)?\s*([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(from_join_pattern, definition, re.IGNORECASE)
            
            for match in matches:
                schema_part, table_part = match
                if table_part:
                    # Skip common SQL keywords and system objects
                    if table_part.upper() not in ['INFORMATION_SCHEMA', 'PG_CATALOG', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'VALUES', 'DECLARE']:
                        if schema_part:
                            tables.add(f"{schema_part}.{table_part}")
                        else:
                            tables.add(table_part)
            
            # Pattern 2: INSERT INTO table_name, UPDATE table_name
            insert_update_pattern = r'\b(?:INSERT\s+INTO|UPDATE)\s+(?:([a-zA-Z_][a-zA-Z0-9_]*)\.)?\s*([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(insert_update_pattern, definition, re.IGNORECASE)
            
            for match in matches:
                schema_part, table_part = match
                if table_part and table_part.upper() not in ['VALUES', 'SET']:
                    if schema_part:
                        tables.add(f"{schema_part}.{table_part}")
                    else:
                        tables.add(table_part)
            
            # Pattern 3: DELETE FROM table_name
            delete_pattern = r'\bDELETE\s+FROM\s+(?:([a-zA-Z_][a-zA-Z0-9_]*)\.)?\s*([a-zA-Z_][a-zA-Z0-9_]*)'
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
                
                # Check if table exists in PostgreSQL
                try:
                    check_query = """
                    SELECT COUNT(*) as count_result
                    FROM information_schema.tables 
                    WHERE table_schema = $1 AND table_name = $2
                    """
                    check_result = await self.execute_query(check_query, [table_schema.lower(), table_name.lower()])
                    exists = check_result and len(check_result) > 0 and check_result[0].get('count_result', 0) > 0
                    
                    if exists:
                        verified_tables.append(f"{table_schema}.{table_name}")
                except Exception:
                    # If verification fails, include the table anyway
                    verified_tables.append(table)
            
            return sorted(list(set(verified_tables)))
            
        except Exception as e:
            self.logger.warning(f"Error parsing table dependencies for {schema}.{function_name}: {e}")
            return []
    
    async def get_functions(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of functions from PostgreSQL"""
        # In PostgreSQL, functions and procedures are both in routines table
        return await self.get_stored_procedures(schema)
    
    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        if not self.is_connected:
            await self.connect()
        
        try:
            if params:
                rows = await self.connection.fetch(query, *params)
            else:
                rows = await self.connection.fetch(query)
            
            # Convert asyncpg.Record to dictionaries
            results = []
            for row in rows:
                results.append(dict(row))
            
            return results
            
        except Exception as e:
            self.logger.error(f"PostgreSQL query error: {e}")
            raise QueryError(f"Query execution failed: {e}")
    
    # Helper methods for detailed metadata extraction
    
    async def _get_table_columns(self, table_name: str, schema: str) -> List[ColumnInfo]:
        """Get column information for a table"""
        query = """
        SELECT 
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale,
            CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
        FROM information_schema.columns c
        LEFT JOIN (
            SELECT ku.column_name
            FROM information_schema.table_constraints tc
            INNER JOIN information_schema.key_column_usage ku
                ON tc.constraint_name = ku.constraint_name
                AND tc.table_schema = ku.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = $1
                AND tc.table_schema = $2
        ) pk ON c.column_name = pk.column_name
        WHERE c.table_name = $1 AND c.table_schema = $2
        ORDER BY c.ordinal_position
        """
        
        results = await self.execute_query(query, [table_name, schema])
        
        columns = []
        for row in results:
            column = ColumnInfo(
                name=row['column_name'],
                type=row['data_type'],
                nullable=row['is_nullable'] == 'YES',
                default_value=row['column_default'],
                max_length=row['character_maximum_length'],
                precision=row['numeric_precision'],
                scale=row['numeric_scale'],
                primary_key=row['is_primary_key']
            )
            columns.append(column)
        
        return columns
    
    async def _get_table_indexes(self, table_name: str, schema: str) -> List[IndexInfo]:
        """Get index information for a table"""
        query = """
        SELECT 
            i.relname as index_name,
            a.attname as column_name,
            ix.indisunique as is_unique
        FROM pg_class t
        JOIN pg_namespace n ON t.relnamespace = n.oid
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE t.relname = $1 AND n.nspname = $2
        ORDER BY i.relname, a.attnum
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
                    'clustered': False  # PostgreSQL doesn't have clustered indexes
                }
            indexes_data[index_name]['columns'].append(row['column_name'])
        
        return [IndexInfo(**idx_data) for idx_data in indexes_data.values()]
    
    async def _get_table_relationships(self, table_name: str, schema: str) -> List[RelationshipInfo]:
        """Get relationship information for a table"""
        # TODO: Implement foreign key relationship extraction for PostgreSQL
        return []
    
    async def _get_procedure_parameters(self, sp_name: str, schema: str) -> List[ParameterInfo]:
        """Get parameter information for a stored procedure/function"""
        query = """
        SELECT 
            p.parameter_name,
            p.data_type,
            p.parameter_mode
        FROM information_schema.parameters p
        WHERE p.specific_schema = $1 AND p.specific_name = $2
        ORDER BY p.ordinal_position
        """
        
        results = await self.execute_query(query, [schema, sp_name])
        
        parameters = []
        for row in results:
            param = ParameterInfo(
                name=row['parameter_name'] or f"param_{len(parameters)+1}",
                type=row['data_type'],
                direction=row['parameter_mode'] or "IN"
            )
            parameters.append(param)
        
        return parameters
