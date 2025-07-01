# Database MCP Server

A powerful FastAPI-based MCP (Model Context Protocol) server that exposes comprehensive database metadata for AI tools like GitHub Copilot, Claude, and other AI assistants. Features intelligent stored procedure analysis with automatic table dependency detection.

## 🌟 Key Features

### 🔌 **Multi-Database Support**
- **SQL Server** ✅ (Full support with dependency analysis)
- **PostgreSQL** ✅ (Full support with dependency analysis)  
- **IBM DB2** ⚠️ (Basic support)
- **MySQL** ⚠️ (Basic support)
- **Oracle** ⚠️ (Basic support)

### 🧠 **Intelligent Analysis**
- **Stored Procedure Intelligence**: Automatically identifies tables used within stored procedures
- **Smart Search**: Detects object types from naming patterns (`sp_`, `fn_`, `vw_`, etc.)
- **Dependency Mapping**: Shows which procedures use specific tables
- **Error Recovery**: Graceful handling of partial failures

### 🚀 **MCP Protocol Integration**
- Native integration with AI tools via Model Context Protocol
- Real-time database schema information for AI assistants
- Contextual metadata for better AI code generation

### 📊 **Rich REST API**
- FastAPI with automatic OpenAPI documentation
- Real-time metadata extraction
- Smart search with categorization
- Health monitoring and diagnostics

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Database
Edit `config.yaml` with your database connection details:

```yaml
# Database connections
databases:
  - name: "main_sql"
    type: "sqlserver"
    connection_string: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=RAKESH;DATABASE=master;UID=sa;PWD=admin123"
    include_schemas: ["dbo"]  # Optional: limit to specific schemas
    exclude_objects: ["temp_*", "sys_*"]  # Optional: exclude objects by pattern

# Security settings
security:
  api_key_enabled: true
  oauth_enabled: false
  allowed_origins: ["*"]

# API Key (change in production!)
api_key: "your-secret-api-key-change-me"
```

### 3. Start Servers
```bash
# Windows - starts both API and MCP servers
start_mcp.bat

# Or start manually:
# Terminal 1: API Server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: MCP Server  
python mcp_server.py
```

### 4. Access API
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **API Key**: Use `your-secret-api-key-change-me` in Authorization header

## 🔧 MCP Integration

### VS Code + GitHub Copilot
Add to your VS Code `settings.json`:
```json
{
  "mcp.servers": {
    "database": {
      "command": "python",
      "args": ["d:\\Projects\\Advance\\DBMCPServer\\mcp_server.py"],
      "cwd": "d:\\Projects\\Advance\\DBMCPServer"
    }
  }
}
```

### Claude Desktop
Add to your Claude configuration:
```json
{
  "mcpServers": {
    "database": {
      "command": "python",
      "args": ["d:\\Projects\\Advance\\DBMCPServer\\mcp_server.py"],
      "cwd": "d:\\Projects\\Advance\\DBMCPServer"
    }
  }
}
```

## 🛠️ MCP Tools Available

| Tool Name | Description | New Features |
|-----------|-------------|--------------|
| `MyDB_get_database_overview` | Complete database metadata overview | Schema categorization |
| `MyDB_search_database_objects` | Smart search for DB objects | Type detection, relevance sorting |
| `MyDB_get_table_schema` | Detailed table schema information | Relationships, indexes |
| `MyDB_get_stored_procedure_details` | **NEW!** Procedure details with table dependencies | **🔗 Related tables analysis** |
| `MyDB_analyze_table_dependencies` | **NEW!** Find procedures using a table | **🔍 Reverse dependency lookup** |
| `MyDB_check_database_health` | Database connectivity status | Multi-database monitoring |

## � Usage Examples

### With AI Assistants
```
🤖 "What tables does the sp_GetUserOrders procedure use?"
→ Shows: Users, Orders, OrderDetails tables with full analysis

🤖 "Which stored procedures modify the Users table?"  
→ Lists all procedures that INSERT/UPDATE/DELETE from Users

🤖 "Search for procedures related to orders"
→ Smart detection finds sp_, usp_, procedures containing 'order'

🤖 "Show me the complete schema for the Orders table"
→ Columns, indexes, relationships, dependent procedures
```

### API Examples
```bash
# Search with smart type detection
curl -H "X-API-Key: your-secret-api-key-change-me" \
  "http://localhost:8000/api/v1/metadata/search?q=sp_GetUsers"

# Get procedure with table dependencies  
curl -H "X-API-Key: your-secret-api-key-change-me" \
  "http://localhost:8000/api/v1/metadata/procedure/sp_GetUserOrders"

# Response includes:
{
  "name": "sp_GetUserOrders",
  "parameters": [...],
  "related_tables": ["dbo.Users", "dbo.Orders", "dbo.OrderDetails"]
}
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Assistant  │    │   MCP Server    │    │   FastAPI App   │
│  (Claude/Copilot)│◄──►│  mcp_server.py  │◄──►│   app/main.py   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │ Database Layer  │
                                               │ - SQL Server    │
                                               │ - PostgreSQL    │
                                               │ - DB2/MySQL/Oracle│
                                               └─────────────────┘
```

## 📁 Project Structure

```
DBMCPServer/
├── app/                          # Core FastAPI application
│   ├── connectors/               # Database connector implementations
│   │   ├── base.py              # Abstract base connector
│   │   ├── sqlserver.py         # SQL Server with dependency analysis
│   │   ├── postgresql.py        # PostgreSQL with dependency analysis
│   │   ├── db2.py               # IBM DB2 connector
│   │   ├── mysql.py             # MySQL connector
│   │   └── oracle.py            # Oracle connector
│   ├── routers/                 # API endpoint definitions
│   │   └── metadata.py          # Metadata API endpoints
│   ├── services/                # Business logic layer
│   │   └── metadata.py          # Core metadata service
│   ├── models/                  # Pydantic data models
│   ├── cache/                   # Caching layer
│   ├── auth.py                  # API authentication
│   ├── config.py                # Configuration management
│   └── main.py                  # FastAPI app entry point
├── config.yaml                  # Database configuration
├── config.example.yaml          # Configuration template
├── mcp_server.py                # MCP protocol server
├── requirements.txt             # Python dependencies
├── start_mcp.bat                # Windows startup script
├── LICENSE                      # MIT License
└── README.md                    # This file
```

## � Smart Features

### Intelligent Object Type Detection
The server automatically detects object types from naming patterns:

- `sp_GetUsers`, `usp_UpdateUser` → **Stored Procedures**
- `fn_CalculateTotal`, `ufn_GetAge` → **Functions**  
- `vw_ActiveUsers`, `UserView` → **Views**
- `tbl_Customers`, `Users` → **Tables**

### Stored Procedure Dependency Analysis  
**NEW FEATURE!** Automatically parses stored procedure definitions to identify:

- **Tables accessed** (SELECT, FROM, JOIN)
- **Tables modified** (INSERT, UPDATE, DELETE)
- **Cross-schema references**
- **Verified table existence**

Example output:
```markdown
## 🔗 Related Tables:
- **dbo.Users**
- **dbo.Orders** 
- **dbo.OrderDetails**

Total Tables Referenced: 3
```

### Error Handling & Recovery
- **Graceful degradation**: If one schema fails, others continue
- **Detailed error messages**: Clear troubleshooting information
- **Partial success reporting**: Shows what worked vs what failed

## 🔧 API Endpoints

### Core Metadata APIs
- `GET /api/v1/metadata/` - Complete database overview
- `GET /api/v1/metadata/supported-types` - List supported database types  
- `GET /api/v1/metadata/table/{table_name}` - Detailed table metadata
- `GET /api/v1/metadata/procedure/{procedure_name}` - **NEW!** Stored procedure with dependencies
- `GET /api/v1/metadata/search?q={query}` - Smart search with type detection

### Management APIs  
- `GET /api/v1/metadata/health` - Health check with connection status
- `POST /api/v1/metadata/cache/clear` - Clear metadata cache
- `GET /docs` - Interactive API documentation (Swagger UI)

### Search API Features
```bash
# Smart search with automatic type detection
GET /api/v1/metadata/search?q=sp_GetUsers
# → Automatically searches stored procedures

# Explicit type filtering  
GET /api/v1/metadata/search?q=user&types=table,view
# → Only searches tables and views

# Schema-specific search
GET /api/v1/metadata/search?q=order&schema=sales&types=stored_procedure
# → Search procedures in sales schema only
```

## 🔒 Security & Configuration

### API Authentication
```yaml
security:
  api_key_enabled: true          # Enable API key auth
  oauth_enabled: false           # OAuth support (future)
  allowed_origins: ["*"]         # CORS origins

api_key: "your-secret-api-key-change-me"  # Change in production!
```

### Database Security
```yaml
databases:
  - name: "production_db"
    include_schemas: ["app", "reports"]     # Limit access
    exclude_objects: ["temp_*", "backup_*"] # Hide sensitive objects
    max_connections: 10                     # Connection pooling
    connection_timeout: 30                  # Timeout settings
```

## 🚦 Health Monitoring

The health endpoint provides comprehensive status information:

```json
{
  "status": "healthy",
  "databases": {
    "main_sql": "connected",
    "analytics_postgres": "connected"
  },
  "cache": "connected",
  "version": "1.0.0",
  "uptime": "2h 34m",
  "total_queries": 1247
}
```

## 🐛 Troubleshooting

### Common Issues

**1. 422 Unprocessable Content Error**
- **Cause**: Invalid search parameters
- **Fix**: Check parameter names (`q` not `query`)

**2. Database Connection Failed**
- **Cause**: Wrong connection string or credentials
- **Fix**: Verify `config.yaml` settings and network connectivity

**3. Empty `related_tables` in Procedures**
- **Cause**: Procedure definition not accessible or parsing failed
- **Fix**: Check database permissions for reading procedure definitions

**4. MCP Server Not Responding**
- **Cause**: Port conflicts or API server not running
- **Fix**: Ensure API server (port 8000) is running first

### Enable Debug Logging
```python
# Add to mcp_server.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance & Scalability

### Caching Strategy
- **Metadata Cache**: 5-10 minute TTL for database schemas
- **Connection Pooling**: Efficient database connection management
- **Lazy Loading**: Connects to databases only when needed

### Optimization Tips
```yaml
# config.yaml optimizations
databases:
  - name: "prod_db"
    include_schemas: ["core"]      # Limit scope
    exclude_objects: ["temp_*"]    # Skip temporary objects
    max_connections: 5             # Tune for your workload
```

## 🤝 Contributing

### Adding New Database Support
1. Create connector in `app/connectors/new_db.py`
2. Extend `BaseDatabaseConnector`
3. Implement dependency analysis methods
4. Register with `@register_connector` decorator

### Example Connector Structure
```python
@register_connector('newdb')
class NewDBConnector(BaseDatabaseConnector):
    async def get_stored_procedure_metadata(self, sp_name, schema):
        # Get basic metadata
        metadata = await super().get_stored_procedure_metadata(sp_name, schema)
        
        # Add dependency analysis
        metadata.related_tables = await self._parse_procedure_dependencies(sp_name, schema)
        
        return metadata
```

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Built with FastAPI and asyncio for high performance
- MCP Protocol for seamless AI integration  
- Supports multiple database systems with unified interface
- Intelligent SQL parsing for dependency analysis

---

**Ready to supercharge your AI-assisted database development!** 🚀

## 🏗️ Architecture

The server uses a modular connector architecture:

1. **FastAPI Server** - Provides REST API for database metadata
2. **MCP Server** - Exposes database tools via Model Context Protocol
3. **Database Connectors** - Modular, pluggable database adapters
4. **AI Integration** - Seamless integration with Copilot, Claude, etc.

## 🔧 Configuration

### Database Configuration
```yaml
# config.yaml
databases:
  - name: "production_db"
    type: "sqlserver"
    connection_string: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=server;DATABASE=db;UID=user;PWD=pass"
    include_schemas: ["dbo", "reporting"]
    exclude_objects: ["audit_*", "temp_*"]
```

### Environment Variables
```bash
# .env (optional)
DATABASE_URL=your_connection_string
API_KEY=your_api_key
```

## 🧪 Testing

### Test API Server
```bash
# Check health
curl http://localhost:8000/health

# List tables
curl http://localhost:8000/api/v1/metadata/

# Get table schema
curl http://localhost:8000/api/v1/metadata/table/Users
```

### Test MCP Integration
1. Start both servers with `start_mcp.bat`
2. Configure VS Code settings
3. Ask Copilot: "What MyDB tools are available?"

## 🚀 Extending the Server

### Adding New Database Connectors
1. Create new connector in `app/connectors/`
2. Inherit from `BaseDatabaseConnector`
3. Register with `@register_connector("newdb")` decorator
4. Implement required methods

### Adding New MCP Tools
1. Add tool definition in `list_tools()` function
2. Add handler in `call_tool()` function
3. Implement the tool logic

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: See inline code documentation
- **API Docs**: http://localhost:8000/docs when server is running

## ✨ Key Features

### 🔌 **Modular Connector Architecture**
- **Extensible Design**: Easy-to-add support for new database types
- **Auto-Registration**: Connectors register automatically using decorators
- **Type Safety**: Full type hints and validation throughout

### 🗄️ **Multi-Database Support**
- **SQL Server** - Full production support with pyodbc
- **PostgreSQL** - Async support with asyncpg  
- **IBM DB2** - Enterprise-grade DB2 integration
- **MySQL** - Optional support with aiomysql
- **Oracle** - Optional support with cx_Oracle
- **Extensible**: Add new database types in minutes

### 🚀 **Performance & Scalability**
- **Async/Await**: Non-blocking database operations
- **Connection Pooling**: Efficient connection management
- **Redis Caching**: Configurable TTL for metadata caching
- **Background Tasks**: Health checks and maintenance

### 🔒 **Enterprise Security**
- **API Key Authentication**: Secure endpoint access
- **OAuth Support**: Enterprise SSO integration ready
- **Column Masking**: Automatic PII/sensitive data masking
- **Schema Filtering**: Include/exclude specific schemas and objects

### 📊 **Rich Metadata APIs**
- **Complete Database Overview**: Schemas, tables, procedures, functions
