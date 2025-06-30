# Database MCP Server

A FastAPI-based MCP (Model Context Protocol) server that exposes database metadata for AI tools like GitHub Copilot, Claude, and other AI assistants.

## 🌟 Features

- **Multi-Database Support**: SQL Server, PostgreSQL, DB2, MySQL, Oracle
- **MCP Protocol**: Native integration with AI tools via Model Context Protocol
- **REST API**: FastAPI with automatic OpenAPI documentation
- **Modular Architecture**: Easy to extend with new database connectors
- **Real-time Metadata**: Live database schema information for AI tools

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Database
Edit `config.yaml` with your database connection details:
```yaml
databases:
  - name: "main_sql"
    type: "sqlserver"
    connection_string: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=server;DATABASE=db;UID=user;PWD=pass"
```

### 3. Start Servers
```bash
# Windows - starts both API and MCP servers
start_mcp.bat

# Linux/Mac - manual start
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
python mcp_server.py
```

### 4. Access API
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔧 MCP Integration

### VS Code + GitHub Copilot
Add to your VS Code `settings.json`:
```json
{
  "mcp.servers": {
    "database": {
      "command": "python",
      "args": ["d:\\path\\to\\mcp_server.py"],
      "cwd": "d:\\path\\to\\DBMCPServer"
    }
  }
}
```

### Usage with AI Tools
Once configured, you can ask AI assistants:
- "What database tables do I have?" → Uses `MyDB_get_database_overview`
- "Show me the schema for Users table" → Uses `MyDB_get_table_schema`
- "Search for tables containing 'order'" → Uses `MyDB_search_database_objects`
- "Check my database health" → Uses `MyDB_check_database_health`

## 🛠️ MCP Tools Available

Your MCP server provides these tools to AI assistants:

| Tool Name | Description |
|-----------|-------------|
| `MyDB_get_database_overview` | Get complete database metadata overview |
| `MyDB_search_database_objects` | Search for tables, procedures, etc. |
| `MyDB_get_table_schema` | Get detailed schema for a specific table |
| `MyDB_check_database_health` | Check database connectivity status |

## 📁 Project Structure

```
DBMCPServer/
├── app/                    # Core FastAPI application
│   ├── connectors/         # Database connector implementations
│   ├── routers/           # API endpoint definitions
│   ├── services/          # Business logic layer
│   └── main.py           # FastAPI app entry point
├── config.yaml           # Database configuration
├── config.example.yaml   # Configuration template
├── mcp_server.py         # MCP protocol server
├── requirements.txt      # Python dependencies
├── start_mcp.bat        # Windows startup script
└── README.md            # This file
```

## 🔌 API Endpoints

- `GET /health` - Server health and database status
- `GET /api/v1/metadata/` - List all tables and schemas
- `GET /api/v1/metadata/table/{name}` - Get table schema details
- `GET /api/v1/metadata/search?q={query}` - Search database objects

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
