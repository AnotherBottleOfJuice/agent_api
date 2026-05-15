# Agent API

`fastapi` `mcp` `llm` `agent` `async` `openai-compatible`

A production-ready HTTP API for autonomous agents that integrate Large Language Models with Model Context Protocol (MCP) servers. Built with FastAPI and async Python.

## Features

**Core Capabilities**
- Autonomous agent execution with integrated LLM support
- Multi-MCP server integration (Streamable HTTP transport)
- Persistent chat history and state management
- Multi-user support with token-based authentication
- Data isolation between users
- OpenAPI/Swagger documentation at `/docs`

**Agent Features**
- OpenAI-compatible `/v1/chat/completions` endpoint
- Tool calling and execution from connected MCP servers
- Built-in arithmetic MCP server (multiplication, division)
- Configurable LLM endpoints (BASE_URL, API_KEY, MODEL)
- Safety guards: tool call limits, iteration limits
- Seamless tool integration between agent cycles

**Database & Storage**
- SQLite backend for chat history and configurations
- Async-friendly database layer (aiosqlite)
- User-scoped data storage

## Quick Start

### Installation

```bash
pip install -e .
```

### Configuration

Create a `.env` file like:

```bash
# Server configuration
SECRET_KEY=abacaba
APP_PORT=8000
APP_HOST=127.0.0.1

# Default MCP server
DEFAULT_MCP_NAME=Default-MCP
DEFAULT_MCP_URL=http://127.0.0.1:8010/mcp
DEFAULT_MCP_HOST=127.0.0.1
DEFAULT_MCP_PORT=8010
DEFAULT_MCP_TOKEN=abacaba
```

### Running the Server

```bash
python -m uvicorn agent_api.app:app
```

The API will be available at `http://localhost:8000/docs`

## API Usage

### Authentication

All requests require a `User-Token` header:

```bash
curl -H "User-Token: your-user-token" http://localhost:8000/...
```

### Create a User (Admin Only)

```bash
curl -X POST http://localhost:8000/admin/add_user \
  -H "Admin-Key: your-secret-key"
```

### Example: Chat with Agent

```bash
# Create a chat
POST /chats
Body: {"name": "My Chat"}
Headers: {"User-Token": "user-token"}

# Add LLM configuration
POST /llm-configs
Body: {
  "name": "OpenAI GPT-4",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "model": "gpt-4"
}

# Add message and get response
POST /chats/{chat_id}/messages
Body: {
  "content": "Calculate 15 * 2 and then divide by 3"
}
```

## Architecture

```
api_agent/
├── app.py              # FastAPI application
├── api_types.py        # Pydantic models
├── api_exceptions.py   # Custom exceptions
├── generate.py         # Agent logic and LLM integration
└── mcp_utils.py        # MCP client utilities

database/
└── handler.py          # SQLite database handler

simple_mcp/
└── main.py             # Built-in MCP server (arithmetic tools)
```

## Key Requirements Met

- Multi-user authentication with header-based tokens  
- User data isolation and privacy  
- LLM configuration management  
- MCP server integration (Streamable HTTP)  
- Chat history persistence  
- Tool call safety limits (max 2 consecutive, 10 total)  
- OpenAPI schema generation  
- Async/await throughout for performance

## Technologies

- **Framework**: FastAPI 0.95+
- **ASGI Server**: Uvicorn 0.21+
- **MCP Client**: mcp
- **Database**: SQLite with aiosqlite
- **Validation**: Pydantic
- **Config**: python-dotenv

## Security Notes

- API tokens should be managed securely via environment variables
- User data is completely isolated per user token
- No hardcoded secrets in the codebase
- Use `.env` files (excluded from version control) for sensitive data

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Deployment

Suitable for deployment on cloud platforms (Yandex Cloud, AWS, DigitalOcean, etc.) using:
- Docker containerization
- HTTPS with reverse proxy (nginx)
- Environment-based configuration
- Process management (systemd, supervisor, or Docker)

## License

MIT
