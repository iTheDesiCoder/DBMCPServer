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
- **Detailed Table Metadata**: Columns, indexes, relationships, constraints
- **Stored Procedure Info**: Parameters, return types, dependencies
- **Smart Search**: Find database objects with fuzzy matching
- **Health Monitoring**: Real-time connection status

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Tools      │    │   MCP Server    │    │   Enterprise    │
│ (Copilot, etc.) │◄──►│   (FastAPI)     │◄──►│   Databases     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼───┐ ┌───▼───┐ ┌───▼────┐
            │   SQL     │ │  DB2  │ │ PostgreSQL│
            │ Server    │ │       │ │  MySQL   │
            │Connector  │ │Connector│ │ Oracle │
            └───────────┘ └───────┘ └─────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Redis Cache   │
                       │   + Monitoring  │
                       └─────────────────┘
```

## � Quick Start

### Option 1: Standard Installation

1. **Clone and Setup**:
```bash
git clone <repository-url>
cd DBMCPServer
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

2. **Install Dependencies**:
```bash
pip install -r requirements.txt

# Optional: Install additional database drivers
pip install aiomysql cx-Oracle  # MySQL and Oracle
```

3. **Configure Database Connections**:
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your database details
```

4. **Start the Server**:
```bash
python run_dev.py
# Or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Docker Deployment

```bash
# Copy configuration
cp config.example.yaml config.yaml
cp .env.example .env

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f mcp-server
```

## 📝 Configuration

### Database Configuration (`config.yaml`)

```yaml
databases:
  - name: "production_db"
    type: "sqlserver"  # sqlserver, postgresql, db2, mysql, oracle
    connection_string: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=MyDB;UID=user;PWD=pass"
    include_schemas: ["dbo", "sales"]  # Optional: limit to specific schemas
    exclude_objects: ["temp_*", "sys_*"]  # Optional: exclude objects by pattern
    max_connections: 10
    connection_timeout: 30

  - name: "analytics_postgres"
    type: "postgresql"  
    connection_string: "postgresql://user:pass@localhost:5432/analytics"
    include_schemas: ["public", "analytics"]
```

### Security & API Configuration

```yaml
security:
  api_key_enabled: true
  api_key: "your-secret-key-here"
  column_masking_rules:
    "ssn": "XXX-XX-****"
    "credit_card": "****-****-****-****"

cache:
  enabled: true
  redis_url: "redis://localhost:6379"
  ttl_seconds: 3600
```

## 🔧 API Endpoints

### Core Metadata APIs
- `GET /api/v1/metadata/` - Complete database overview
- `GET /api/v1/metadata/supported-types` - List supported database types  
- `GET /api/v1/metadata/table/{table_name}` - Detailed table metadata
- `GET /api/v1/metadata/procedure/{procedure_name}` - Stored procedure metadata
- `GET /api/v1/metadata/search?q={query}` - Search database objects

### Management APIs  
- `GET /api/v1/metadata/health` - Health check with connection status
- `POST /api/v1/metadata/cache/clear` - Clear metadata cache
- `GET /docs` - Interactive API documentation (Swagger UI)

### Example Requests

```bash
# Get database overview
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/metadata/

# Search for tables containing "user"
curl -H "X-API-Key: your-api-key" "http://localhost:8000/api/v1/metadata/search?q=user&types=table"

# Get detailed table metadata
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/metadata/table/Users?schema=dbo
```

## 🔌 Adding New Database Connectors

The modular architecture makes adding new database types incredibly simple:

### 1. Create Your Connector

```python
# app/connectors/your_database.py
from app.connectors.base import BaseDatabaseConnector
from app.connectors.registry import register_connector

@register_connector('your_db_type')
class YourDatabaseConnector(BaseDatabaseConnector):
    
    @property
    def driver_name(self) -> str:
        return "your-driver-name"
    
    @property  
    def database_type(self) -> str:
        return "your_db_type"
    
    async def connect(self) -> None:
        # Implement connection logic
        self.connection = await your_db_library.connect(self.config.connection_string)
        self.is_connected = True
    
    async def get_schemas(self) -> List[str]:
        # Implement schema discovery
        return await self.connection.fetch("SHOW SCHEMAS")
    
    # ... implement other required methods
```

### 2. Add Driver Dependencies

```bash
# Add to requirements-optional.txt
your-database-driver>=1.0.0

# Install
pip install your-database-driver
```

### 3. Update Configuration

```yaml
databases:
  - name: "my_new_db"
    type: "your_db_type"  # matches the @register_connector parameter
    connection_string: "your://connection/string"
```

That's it! Your connector is automatically registered and available.

## 🧪 Testing

### Run Connector Tests
```bash
python test_connectors.py
```

### Run Full Test Suite  
```bash
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html  # With coverage
```

### Manual API Testing
```bash
# Start server
python run_dev.py

# Visit interactive docs
open http://localhost:8000/docs
```

## 📚 Documentation

- **[Connector Architecture Guide](CONNECTOR_ARCHITECTURE.md)** - Detailed guide for adding database support
- **[API Documentation](http://localhost:8000/docs)** - Interactive Swagger UI when server is running  
- **[Getting Started Guide](GETTING_STARTED.md)** - Step-by-step setup instructions

## 🚢 Production Deployment

### Environment Variables
```bash
# .env file
DATABASE_URL=postgresql://user:pass@db:5432/mydb
REDIS_URL=redis://redis:6379
API_KEY=your-production-api-key
```

### Docker Production Setup
```bash
# Build production image
docker build -t mcp-server:latest .

# Run with production config
docker run -d \
  --name mcp-server \
  -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e REDIS_URL=$REDIS_URL \
  -e API_KEY=$API_KEY \
  mcp-server:latest
```

### Performance Tuning
- **Connection Pooling**: Adjust `max_connections` per database
- **Cache TTL**: Set appropriate cache timeouts for your use case
- **Redis Configuration**: Use Redis Cluster for high availability
- **Load Balancing**: Run multiple instances behind a load balancer

## 🛡️ Security Best Practices

1. **Change Default API Keys**: Never use default keys in production
2. **Use Environment Variables**: Keep secrets out of config files  
3. **Enable HTTPS**: Always use TLS in production
4. **Restrict CORS**: Configure specific origins, not wildcards
5. **Database Permissions**: Use read-only database accounts
6. **Network Security**: Deploy in private networks when possible
7. **Monitoring**: Set up alerts for failed connections/authentication

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-connector`  
3. **Add** your database connector following the architecture guide
4. **Test** your changes: `python test_connectors.py`
5. **Submit** a pull request with a clear description

### Areas We Need Help With:
- Additional database connectors (MongoDB, Cassandra, etc.)
- Performance optimizations  
- Security enhancements
- Documentation improvements
- Test coverage expansion

## 📊 Supported Database Types

| Database | Status | Driver | Notes |
|----------|--------|--------|-------|
| SQL Server | ✅ Production | pyodbc | Full support |
| PostgreSQL | ✅ Production | asyncpg | Async support |  
| IBM DB2 | ✅ Production | ibm_db | Enterprise features |
| MySQL | 🚧 Beta | aiomysql | Optional install |
| Oracle | 🚧 Beta | cx_Oracle | Optional install |
| MongoDB | 📋 Planned | pymongo | NoSQL support |
| Cassandra | 📋 Planned | cassandra-driver | NoSQL support |

Legend: ✅ Ready, 🚧 In Development, 📋 Planned

## 📈 Roadmap

### Short Term (Next 2-4 weeks)
- [ ] Complete MySQL and Oracle connector testing
- [ ] Add comprehensive error handling and retry logic
- [ ] Implement advanced caching strategies
- [ ] Add metrics and monitoring endpoints  

### Medium Term (1-3 months)
- [ ] NoSQL database support (MongoDB, Cassandra)
- [ ] GraphQL API alongside REST
- [ ] Advanced security features (JWT, RBAC)
- [ ] Performance dashboard and analytics

### Long Term (3-6 months)  
- [ ] Cloud database support (BigQuery, Redshift, Snowflake)
- [ ] Real-time schema change notifications
- [ ] AI-powered query optimization suggestions
- [ ] Multi-tenant architecture

## 🐛 Troubleshooting

### Common Issues

**Connection Failures**:
```bash
# Check database connectivity
python -c "from app.services.metadata import metadata_service; import asyncio; asyncio.run(metadata_service.health_check())"

# Verify ODBC drivers
python -c "import pyodbc; print(pyodbc.drivers())"
```

**Import Errors**:
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

**Performance Issues**:
- Increase connection pool sizes in config
- Reduce cache TTL for faster updates  
- Enable Redis clustering for scale
- Check database index performance

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)  
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI team for the excellent async web framework
- Database driver maintainers for reliable connectivity
- Open source community for inspiration and contributions

---

**Built with ❤️ for the enterprise AI development community**
# Edit .env with your configuration
```

3. Update `config.yaml` with your database connections

4. Start the services:
```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your databases in `config.yaml`

3. Start Redis server

4. Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## ⚙️ Configuration

### Database Configuration (`config.yaml`)

```yaml
databases:
  - name: "main_sql"
    type: "sqlserver"
    connection_string: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=YourDB;UID=user;PWD=pass"
    include_schemas: ["dbo", "reporting"]
    exclude_objects: ["audit_log", "temp_*"]
    
  - name: "mainframe_db2"
    type: "db2"
    connection_string: "DATABASE=SAMPLE;HOSTNAME=localhost;PORT=50000;PROTOCOL=TCPIP;UID=user;PWD=pass"
    include_schemas: ["SCHEMA1"]
```

### Security Configuration

```yaml
security:
  api_key_enabled: true
  oauth_enabled: false
  allowed_origins: ["*"]
  column_masking_rules:
    ssn: "XXX-XX-****"
    credit_card: "****-****-****-****"

api_key: "your-secret-api-key"
```

## 🔌 API Endpoints

### Get Metadata Suggestions

Resolves a fuzzy query string to the most relevant database objects.

```http
GET /metadata/suggest?q=getClientInvoices
```

**Response:**
```json
{
  "type": "stored_procedure",
  "name": "sp_GetClientInvoices",
  "schema": "dbo",
  "score": 0.95,
  "params": [
    { "name": "@ClientId", "type": "INT", "direction": "IN" },
    { "name": "@FromDate", "type": "DATE", "direction": "IN" }
  ],
  "returns": [
    { "name": "InvoiceId", "type": "INT" },
    { "name": "Amount", "type": "DECIMAL(10,2)" }
  ],
  "related_tables": ["Invoices", "Clients"]
}
```

### Get Table Metadata

Returns detailed schema information for a specific table.

```http
GET /metadata/table/Clients?schema=dbo
```

### Get Stored Procedure Metadata

Returns parameter and return type information for stored procedures.

```http
GET /metadata/sp/sp_GetClientInvoices?schema=dbo
```

### Get Schema Overview

Returns overview of all database schemas and objects.

```http
GET /metadata/schema
```

## 🔐 Authentication

### API Key Authentication

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-api-key" \
     http://localhost:8000/metadata/suggest?q=client
```

### Bearer Token Authentication

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer your-token" \
     http://localhost:8000/metadata/suggest?q=client
```

## 🧠 AI Integration Flow

1. Developer writes partial code:
   ```typescript
   const invoices = getClientInvoices(clientId);
   ```

2. GitHub Copilot extension triggers:
   ```http
   GET /metadata/suggest?q=getClientInvoices
   ```

3. MCP Server returns metadata to complete the function call with correct parameters and types.

## 🧪 Testing

Run tests with pytest:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest tests/
```

## 📊 Monitoring

### Health Checks

- Application health: `GET /health`
- Metadata service health: `GET /metadata/health`

### Cache Management

Clear cache for specific database:
```http
POST /metadata/cache/clear?database=main_sql
```

## 🐳 Deployment

### Docker

```bash
docker build -t mcp-server .
docker run -p 8000:8000 mcp-server
```

### Kubernetes

See `k8s/` directory for Kubernetes deployment manifests (TODO).

### Environment Variables

Key environment variables:
- `DEBUG`: Enable debug mode
- `API_KEY`: API key for authentication
- `REDIS_URL`: Redis connection URL
- `LOG_LEVEL`: Logging level

## 🔧 Development

### Project Structure

```
mcp-server/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── auth.py              # Authentication middleware
│   ├── models/              # Pydantic models
│   ├── routers/             # API route handlers
│   │   └── metadata.py      # Metadata endpoints
│   ├── services/            # Business logic
│   │   ├── extractor.py     # Database connectors
│   │   ├── fuzzy_match.py   # Fuzzy matching logic
│   │   └── __init__.py      # Service functions
│   └── cache/               # Cache management
├── tests/                   # Test suite
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container definition
└── docker-compose.yml      # Development environment
```

### Adding New Database Types

1. Create a new connector class inheriting from `DatabaseConnector`
2. Implement the required abstract methods
3. Register the connector type in `MetadataExtractor.add_database()`

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

[Add your license information here]

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the logs for debugging information

## 🗺️ Roadmap

- [ ] PostgreSQL connector
- [ ] Oracle connector
- [ ] GraphQL API support
- [ ] VS Code extension
- [ ] Web UI for metadata exploration
- [ ] Advanced relationship detection
- [ ] Query performance analytics
