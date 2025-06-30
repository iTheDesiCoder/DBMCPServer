@echo off
echo Starting Database MCP Server System (Single Window)...
cd /d "d:\Projects\Advance\DBMCPServer"

if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat

echo.
echo Starting API Server in background...
start /b python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo Waiting for API server to initialize...
timeout /t 5 /nobreak >nul

echo.
echo Starting MCP Server (foreground)...
echo API Server running at: http://localhost:8000
echo MCP Server logs below:
echo.
echo Press Ctrl+C to stop both servers
echo.
python mcp_server.py
