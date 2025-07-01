#!/usr/bin/env python3
"""
Working MCP Server for Database Metadata
Uses correct imports for current MCP library
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
import requests
import logging

# MCP imports - using the working pattern
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Create the server
app = Server("database-metadata")

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="MyDB_get_database_overview",
            description="Get complete database metadata overview including tables, schemas, and procedures",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Database name (optional, uses default if not specified)"
                    }
                }
            }
        ),
        Tool(
            name="MyDB_search_database_objects", 
            description="Search for database objects (tables, procedures, etc.) by name with smart type detection",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find database objects (use 'sp_' for procedures, 'fn_' for functions, 'vw_' for views)"
                    },
                    "types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific object types to search (table, view, stored_procedure, function)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="MyDB_get_stored_procedure_details",
            description="Get detailed information about a specific stored procedure including parameters and related tables",
            inputSchema={
                "type": "object",
                "properties": {
                    "procedure_name": {
                        "type": "string",
                        "description": "Name of the stored procedure to get details for"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Schema name (optional)"
                    }
                },
                "required": ["procedure_name"]
            }
        ),
        Tool(
            name="MyDB_analyze_table_dependencies",
            description="Analyze which stored procedures use a specific table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to analyze dependencies for"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Schema name (optional)"
                    }
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="MyDB_get_table_schema",
            description="Get detailed schema information for a specific table",
            inputSchema={
                "type": "object", 
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to get schema for"
                    }
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="MyDB_check_database_health",
            description="Check the health and connectivity of the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string", 
                        "description": "Database name to check (optional)"
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        logger.info(f"🔧 Tool called: {name} with args: {arguments}")
        
        if name == "MyDB_get_database_overview":
            return await get_database_overview(arguments)
        elif name == "MyDB_search_database_objects":
            return await search_database_objects(arguments)
        elif name == "MyDB_get_table_schema":
            return await get_table_schema(arguments)
        elif name == "MyDB_get_stored_procedure_details":
            return await get_stored_procedure_details(arguments)
        elif name == "MyDB_analyze_table_dependencies":
            return await analyze_table_dependencies(arguments)
        elif name == "MyDB_check_database_health":
            return await check_database_health(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def get_database_overview(args: Dict[str, Any]) -> List[TextContent]:
    """Get database overview"""
    try:
        params = {}
        if args and "database" in args:
            params["database"] = args["database"]
        
        logger.info(f"📊 Getting database overview with params: {params}")
        response = requests.get(f"{API_BASE_URL}/api/v1/metadata/", params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        formatted_response = format_database_overview(data)
        logger.info("✅ Database overview retrieved successfully")
        
        return [TextContent(type="text", text=formatted_response)]
    except Exception as e:
        error_msg = f"Error getting database overview: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

async def search_database_objects(args: Dict[str, Any]) -> List[TextContent]:
    """Search database objects with smart type detection"""
    try:
        if not args or "query" not in args:
            return [TextContent(type="text", text="Error: Query parameter is required")]
        
        search_query = args["query"].strip()
        
        # Smart object type detection based on query patterns
        suggested_types = detect_object_types(search_query)
        
        # API expects 'q' parameter, not 'query'
        params = {
            "q": search_query,
            "limit": 100  # Get more results for better analysis
        }
        
        # Add detected types if we have strong indicators, or use provided types
        search_types = args.get("types", [])
        if search_types:
            # User provided specific types
            params["types"] = search_types
            logger.info(f"Using user-specified types: {search_types}")
        elif suggested_types:
            # Use smart detection
            params["types"] = suggested_types
            logger.info(f"Using detected types: {suggested_types}")
        
        logger.info(f"🔍 Searching database objects with query: '{search_query}', suggested types: {suggested_types}")
        
        response = requests.get(f"{API_BASE_URL}/api/v1/metadata/search", params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        formatted_response = format_smart_search_results(data, search_query, suggested_types)
        logger.info("✅ Search completed successfully")
        
        return [TextContent(type="text", text=formatted_response)]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            error_msg = f"🚫 Invalid search parameters. Please check your query: '{search_query}'"
            logger.error(f"422 Error - {error_msg}: {e.response.text}")
        else:
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error searching database objects: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

async def get_table_schema(args: Dict[str, Any]) -> List[TextContent]:
    """Get table schema"""
    try:
        if not args or "table_name" not in args:
            return [TextContent(type="text", text="Error: table_name parameter is required")]
        
        table_name = args["table_name"]
        logger.info(f"📋 Getting schema for table: {table_name}")
        
        response = requests.get(f"{API_BASE_URL}/api/v1/metadata/table/{table_name}", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        formatted_response = format_table_schema(data)
        logger.info("✅ Table schema retrieved successfully")
        
        return [TextContent(type="text", text=formatted_response)]
    except Exception as e:
        error_msg = f"Error getting table schema: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

async def check_database_health(args: Dict[str, Any]) -> List[TextContent]:
    """Check database health"""
    try:
        params = {}
        if args and "database" in args:
            params["database"] = args["database"]
        
        logger.info("🏥 Checking database health")
        response = requests.get(f"{API_BASE_URL}/health", params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        formatted_response = format_health_check(data)
        logger.info("✅ Health check completed successfully")
        
        return [TextContent(type="text", text=formatted_response)]
    except Exception as e:
        error_msg = f"Error checking database health: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

async def get_stored_procedure_details(args: Dict[str, Any]) -> List[TextContent]:
    """Get detailed stored procedure information"""
    try:
        if not args or "procedure_name" not in args:
            return [TextContent(type="text", text="Error: procedure_name parameter is required")]
        
        procedure_name = args["procedure_name"]
        schema = args.get("schema")
        
        logger.info(f"⚙️ Getting details for stored procedure: {procedure_name}")
        
        # Build URL for procedure metadata
        url = f"{API_BASE_URL}/api/v1/metadata/procedure/{procedure_name}"
        params = {}
        if schema:
            params["schema"] = schema
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        formatted_response = format_stored_procedure_details(data)
        logger.info("✅ Stored procedure details retrieved successfully")
        
        return [TextContent(type="text", text=formatted_response)]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            error_msg = f"🚫 Stored procedure '{procedure_name}' not found"
        else:
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error getting stored procedure details: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

async def analyze_table_dependencies(args: Dict[str, Any]) -> List[TextContent]:
    """Analyze which stored procedures use a specific table"""
    try:
        if not args or "table_name" not in args:
            return [TextContent(type="text", text="Error: table_name parameter is required")]
        
        table_name = args["table_name"]
        schema = args.get("schema")
        
        logger.info(f"🔍 Analyzing table dependencies for: {table_name}")
        
        # Search for stored procedures that might reference this table
        search_params = {
            "q": table_name,
            "types": ["stored_procedure"],
            "limit": 50
        }
        
        if schema:
            search_params["schema"] = schema
        
        response = requests.get(
            f"{API_BASE_URL}/api/v1/metadata/search",
            params=search_params,
            timeout=15
        )
        response.raise_for_status()
        
        search_data = response.json()
        procedures = search_data.get('results', [])
        
        # Get detailed information for each procedure to check table dependencies
        dependencies = []
        for proc in procedures:
            proc_name = proc['name']
            proc_schema = proc.get('schema', schema)
            
            try:
                # Get procedure details including related tables
                detail_response = requests.get(
                    f"{API_BASE_URL}/api/v1/metadata/procedure/{proc_name}",
                    params={"schema": proc_schema} if proc_schema else {},
                    timeout=10
                )
                
                if detail_response.status_code == 200:
                    proc_data = detail_response.json()
                    related_tables = proc_data.get('related_tables', [])
                    
                    # Check if our target table is in the related tables
                    full_table_name = f"{schema}.{table_name}" if schema else table_name
                    
                    table_found = False
                    for related_table in related_tables:
                        if (table_name.lower() in related_table.lower() or 
                            full_table_name.lower() == related_table.lower()):
                            table_found = True
                            break
                    
                    if table_found:
                        dependencies.append({
                            'procedure_name': proc_name,
                            'procedure_schema': proc_schema,
                            'related_tables': related_tables,
                            'parameters': proc_data.get('parameters', [])
                        })
                        
            except Exception as e:
                logger.warning(f"Could not get details for procedure {proc_name}: {e}")
                continue
        
        # Format the response
        formatted_response = format_table_dependency_analysis(table_name, schema, dependencies)
        logger.info("✅ Table dependency analysis completed")
        
        return [TextContent(type="text", text=formatted_response)]
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error analyzing table dependencies: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

def format_database_overview(data: Dict[str, Any]) -> str:
    """Format database overview response"""
    output = []
    output.append(f"# 📊 Database Overview: {data.get('database_name', 'Unknown')}")
    output.append(f"**Type**: {data.get('database_type', 'Unknown')}")
    output.append("")
    
    schemas = data.get('schemas', [])
    if schemas:
        for schema in schemas:
            output.append(f"## 📁 Schema: {schema.get('schema_name', 'Unknown')}")
            output.append(f"- 📋 Tables: {schema.get('table_count', 0)}")
            output.append(f"- ⚙️ Procedures: {schema.get('procedure_count', 0)}")
            output.append(f"- 🔧 Functions: {schema.get('function_count', 0)}")
            output.append("")
            
            tables = schema.get('tables', [])
            if tables:
                output.append("### 📋 Tables:")
                for table in tables[:10]:  # Limit to first 10 tables
                    output.append(f"- **{table.get('name', 'Unknown')}** ({table.get('type', 'table')})")
                if len(tables) > 10:
                    output.append(f"- ... and {len(tables) - 10} more tables")
                output.append("")
    else:
        output.append("No schema information available.")
    
    return "\n".join(output)

def format_search_results(data: Dict[str, Any], query: str) -> str:
    """Format search results"""
    results = data.get('results', [])
    
    if not results:
        return f"🔍 No database objects found matching '{query}'"
    
    output = [f"🔍 Search Results for '{query}' ({len(results)} found)"]
    output.append("")
    
    for result in results[:20]:  # Limit to first 20 results
        output.append(f"## 📋 {result.get('name', 'Unknown')}")
        output.append(f"- **Type**: {result.get('type', 'Unknown')}")
        output.append(f"- **Schema**: {result.get('schema', 'Unknown')}")
        if result.get('description'):
            output.append(f"- **Description**: {result['description']}")
        output.append("")
    
    if len(results) > 20:
        output.append(f"... and {len(results) - 20} more results")
    
    return "\n".join(output)

def format_table_schema(data: Dict[str, Any]) -> str:
    """Format table schema response"""
    output = []
    output.append(f"# 📋 Table Schema: {data.get('table_name', 'Unknown')}")
    output.append(f"**Schema**: {data.get('schema_name', 'Unknown')}")
    output.append("")
    
    columns = data.get('columns', [])
    if columns:
        output.append("## 📊 Columns:")
        output.append("| Column | Type | Nullable | Key | Default |")
        output.append("|--------|------|----------|-----|---------|")
        
        for col in columns:
            key_info = ""
            if col.get('primary_key'):
                key_info = "🔑 PK"
            elif col.get('foreign_key'):
                key_info = "🔗 FK"
            
            nullable = "✅" if col.get('nullable') else "❌"
            output.append(f"| {col.get('name', '')} | {col.get('type', '')} | {nullable} | {key_info} | {col.get('default_value', '')} |")
        
        output.append("")
        output.append(f"**Total Columns**: {len(columns)}")
    else:
        output.append("No column information available.")
    
    return "\n".join(output)

def format_health_check(data: Dict[str, Any]) -> str:
    """Format health check response"""
    output = []
    output.append("# 🏥 Database Health Check")
    
    status = data.get('status', 'Unknown')
    status_icon = "✅" if status == "healthy" else "❌"
    output.append(f"**Overall Status**: {status_icon} {status}")
    output.append("")
    
    databases = data.get('databases', {})
    if databases:
        output.append("## 🗄️ Database Connections:")
        for db_name, db_status in databases.items():
            db_icon = "✅" if db_status in ["connected", "healthy"] else "❌"
            output.append(f"- {db_icon} **{db_name}**: {db_status}")
        output.append("")
    
    cache_status = data.get('cache', 'unknown')
    cache_icon = "✅" if cache_status == "connected" else "❌"
    output.append(f"**Cache**: {cache_icon} {cache_status}")
    
    version = data.get('version', 'Unknown')
    output.append(f"**Version**: {version}")
    
    return "\n".join(output)

def format_stored_procedure_details(data: Dict[str, Any]) -> str:
    """Format stored procedure details response"""
    output = []
    output.append(f"# ⚙️ Stored Procedure: {data.get('procedure_name', 'Unknown')}")
    output.append(f"**Schema**: {data.get('schema_name', 'Unknown')}")
    output.append("")
    
    # Description
    if data.get('description'):
        output.append(f"**Description**: {data['description']}")
        output.append("")
    
    # Parameters
    parameters = data.get('parameters', [])
    if parameters:
        output.append("## 📝 Parameters:")
        output.append("| Parameter | Type | Direction | Default | Nullable |")
        output.append("|-----------|------|-----------|---------|----------|")
        
        for param in parameters:
            direction = param.get('direction', 'IN')
            default = param.get('default_value', '')
            nullable = "✅" if param.get('nullable') else "❌"
            
            output.append(f"| {param.get('name', '')} | {param.get('type', '')} | {direction} | {default} | {nullable} |")
        
        output.append("")
        output.append(f"**Total Parameters**: {len(parameters)}")
    else:
        output.append("**Parameters**: None")
    
    output.append("")
    
    # Return type (if available)
    if data.get('return_type'):
        output.append(f"**Return Type**: {data['return_type']}")
    
    # Related tables (NEW FEATURE!)
    related_tables = data.get('related_tables', [])
    if related_tables:
        output.append("")
        output.append("## 🔗 Related Tables:")
        for table in related_tables:
            output.append(f"- **{table}**")
        output.append("")
        output.append(f"**Total Tables Referenced**: {len(related_tables)}")
    else:
        output.append("")
        output.append("**Related Tables**: None detected")
    
    # Definition (if available and not too long)
    definition = data.get('definition', '')
    if definition and len(definition) < 2000:
        output.append("")
        output.append("## 📋 Definition:")
        output.append("```sql")
        output.append(definition)
        output.append("```")
    elif definition:
        output.append("")
        output.append("## 📋 Definition:")
        output.append("*(Definition too long to display fully)*")
        output.append("```sql")
        output.append(definition[:500] + "...")
        output.append("```")
    
    return "\n".join(output)

def detect_object_types(query: str) -> List[str]:
    """
    Smart detection of database object types based on query patterns
    """
    query_lower = query.lower().strip()
    types = []
    
    # Stored procedure indicators
    proc_indicators = ['proc', 'procedure', 'sp_', 'usp_', 'stored', 'exec', 'execute']
    if any(indicator in query_lower for indicator in proc_indicators):
        types.append('stored_procedure')
    
    # Function indicators
    func_indicators = ['func', 'function', 'fn_', 'ufn_']
    if any(indicator in query_lower for indicator in func_indicators):
        types.append('function')
    
    # View indicators
    view_indicators = ['view', 'vw_', 'v_']
    if any(indicator in query_lower for indicator in view_indicators):
        types.append('view')
    
    # Table indicators (less specific, so lower priority)
    table_indicators = ['table', 'tbl_', 't_']
    if any(indicator in query_lower for indicator in table_indicators):
        types.append('table')
    
    # If no specific indicators, include all common types
    if not types:
        types = ['table', 'view', 'stored_procedure', 'function']
    
    return types

def format_smart_search_results(data: Dict[str, Any], query: str, suggested_types: List[str]) -> str:
    """Format search results with smart categorization"""
    results = data.get('results', [])
    
    if not results:
        return f"🔍 No database objects found matching '{query}'"
    
    # Categorize results by type
    categorized = {
        'table': [],
        'view': [],
        'stored_procedure': [],
        'function': []
    }
    
    for result in results:
        obj_type = result.get('type', '').lower()
        if obj_type == 'procedure':
            obj_type = 'stored_procedure'
        
        if obj_type in categorized:
            categorized[obj_type].append(result)
    
    output = [f"🔍 Search Results for '{query}' ({len(results)} found)"]
    
    if suggested_types:
        output.append(f"🎯 **Detected likely types**: {', '.join(suggested_types)}")
    
    output.append("")
    
    # Display results by category
    type_icons = {
        'table': '📋',
        'view': '👁️',
        'stored_procedure': '⚙️',
        'function': '🔧'
    }
    
    type_names = {
        'table': 'Tables',
        'view': 'Views', 
        'stored_procedure': 'Stored Procedures',
        'function': 'Functions'
    }
    
    for obj_type, objects in categorized.items():
        if objects:
            output.append(f"## {type_icons[obj_type]} {type_names[obj_type]} ({len(objects)})")
            
            for obj in objects[:10]:  # Limit per category
                output.append(f"### 📝 {obj.get('name', 'Unknown')}")
                output.append(f"- **Schema**: {obj.get('schema', 'Unknown')}")
                if obj.get('description'):
                    output.append(f"- **Description**: {obj['description']}")
                output.append("")
            
            if len(objects) > 10:
                output.append(f"... and {len(objects) - 10} more {type_names[obj_type].lower()}")
                output.append("")
    
    # Add search tips
    output.append("---")
    output.append("💡 **Search Tips:**")
    output.append("- Use 'sp_' or 'proc' to find stored procedures")
    output.append("- Use 'fn_' or 'func' to find functions") 
    output.append("- Use 'vw_' or 'view' to find views")
    output.append("- Use table names directly for tables")
    
    return "\n".join(output)

def format_table_dependency_analysis(table_name: str, schema: Optional[str], dependencies: List[Dict[str, Any]]) -> str:
    """Format table dependency analysis results"""
    output = []
    full_table_name = f"{schema}.{table_name}" if schema else table_name
    
    output.append(f"# 🔍 Table Dependency Analysis: {full_table_name}")
    output.append("")
    
    if not dependencies:
        output.append("🔍 **No stored procedures found that reference this table.**")
        output.append("")
        output.append("This could mean:")
        output.append("- The table is not used by any stored procedures")
        output.append("- The table name might be referenced differently in procedures")
        output.append("- The procedures might be in different schemas")
        return "\n".join(output)
    
    output.append(f"📊 **Found {len(dependencies)} stored procedure(s) that reference this table:**")
    output.append("")
    
    for i, dep in enumerate(dependencies, 1):
        proc_name = dep['procedure_name']
        proc_schema = dep['procedure_schema']
        related_tables = dep['related_tables']
        parameters = dep['parameters']
        
        output.append(f"## {i}. ⚙️ {proc_name}")
        output.append(f"**Schema**: {proc_schema}")
        
        if parameters:
            output.append(f"**Parameters**: {len(parameters)} parameter(s)")
            for param in parameters[:3]:  # Show first 3 parameters
                direction = param.get('direction', 'IN')
                output.append(f"- `{param.get('name', '')}` ({param.get('type', '')}) - {direction}")
            if len(parameters) > 3:
                output.append(f"- ... and {len(parameters) - 3} more parameters")
        
        if related_tables:
            output.append(f"**All Referenced Tables** ({len(related_tables)}):")
            for table in related_tables:
                if table_name.lower() in table.lower():
                    output.append(f"- 🎯 **{table}** ← Target table")
                else:
                    output.append(f"- {table}")
        
        output.append("")
    
    # Summary
    output.append("---")
    output.append("## 📈 Summary")
    all_related_tables = set()
    for dep in dependencies:
        all_related_tables.update(dep.get('related_tables', []))
    
    output.append(f"- **Procedures analyzing**: {len(dependencies)}")
    output.append(f"- **Total unique tables involved**: {len(all_related_tables)}")
    output.append(f"- **Target table**: {full_table_name}")
    
    return "\n".join(output)

async def main():
    """Main entry point"""
    logger.info("🚀 Starting MCP Database Server...")
    logger.info("📡 Connecting to FastAPI server at http://localhost:8000")
    
    # Test FastAPI connection first
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            logger.info("✅ FastAPI server is accessible and healthy")
            data = response.json()
            logger.info(f"📊 Connected to: {data.get('databases', {})}")
        else:
            logger.warning(f"⚠️ FastAPI server returned status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Cannot connect to FastAPI server: {e}")
        logger.error("💡 Make sure FastAPI server is running:")
        logger.error("   - Run: start_api.bat")
        logger.error("   - Or: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    logger.info("🎯 MCP Database Server ready for AI assistant connections")
    logger.info("🛠️ Available tools: MyDB_get_database_overview, MyDB_search_database_objects, MyDB_get_table_schema, MyDB_check_database_health")
    
    # Run the MCP server
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
