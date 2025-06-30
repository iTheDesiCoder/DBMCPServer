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
            description="Search for database objects (tables, procedures, etc.) by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find database objects"
                    }
                },
                "required": ["query"]
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
    """Search database objects"""
    try:
        if not args or "query" not in args:
            return [TextContent(type="text", text="Error: Query parameter is required")]
        
        params = {"query": args["query"]}
        logger.info(f"🔍 Searching database objects with query: {params['query']}")
        
        response = requests.get(f"{API_BASE_URL}/api/v1/metadata/search", params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        formatted_response = format_search_results(data, params["query"])
        logger.info("✅ Search completed successfully")
        
        return [TextContent(type="text", text=formatted_response)]
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
