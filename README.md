# Agent API

`fastapi` `mcp` `llm` `docker` `openai-compatible`

HTTP API for agent-style LLM workflows with MCP server integration.

> **Note:** `abacaba` in this README is a demo/test token placeholder. Replace it with your own secure values in real environments.

## Repository contents

- `agent_api/` — main FastAPI API (users, LLM configs, MCP configs, completions)
- `simple_mcp/` — example MCP server with `multiply` and `divide` tools
- `docker-compose.yaml` — runs both services together

## Quick start (Docker, recommended)

### Option 1: prebuilt images (same approach as deployment)

```bash
# 1) Network
sudo docker network create mcp_network || true

# 2) Simple MCP
sudo docker run -d --name juice_simple_mcp \
  --network mcp_network \
  -p 8015:8000 \
  -e SIMPLE_MCP_NAME=Simple-MCP \
  -e SIMPLE_MCP_TOKEN=abacaba \
  ghcr.io/anotherbottleofjuice/agent_api/simple-mcp:latest

# 3) Agent API
sudo docker run -d --name juice_agent_api \
  --network mcp_network \
  -p 4015:8000 \
  -e SECRET_KEY=abacaba \
  -e DEFAULT_MCP_NAME=Simple-MCP \
  -e DEFAULT_MCP_URL=http://juice_simple_mcp:8000/mcp \
  -e DEFAULT_MCP_TOKEN=abacaba \
  ghcr.io/anotherbottleofjuice/agent_api/agent-api:latest
```

Swagger UI: `http://localhost:4015/docs`

### Option 2: local build with Docker Compose

```bash
docker compose up --build
```

Default ports:

- Agent API: `http://localhost:4015`
- Simple MCP: `http://localhost:8015`

## Local run without Docker

> Important: `agent_api` and `simple_mcp` currently use the same package name in metadata, so it is safer to run them in separate virtual environments.

### Agent API

```bash
cd agent_api
pip install -e .
uvicorn agent_api.app:app --host 0.0.0.0 --port 8000
```

Environment variables:

```bash
SECRET_KEY=abacaba
DEFAULT_MCP_NAME=Simple-MCP
DEFAULT_MCP_URL=http://127.0.0.1:8010/mcp
DEFAULT_MCP_TOKEN=abacaba
```

### Simple MCP

```bash
cd simple_mcp
pip install -e .
uvicorn simple_mcp.main:app --host 0.0.0.0 --port 8010
```

Environment variables:

```bash
SIMPLE_MCP_NAME=Simple-MCP
SIMPLE_MCP_TOKEN=abacaba
```

## Authentication

### Agent API

- `User-Token` header is required for most endpoints.
- `POST /admin/add_user` requires header `key` with the value of `SECRET_KEY`.

### Simple MCP

- `Authorization` header is required.
- Supported formats:
  - `Authorization: Bearer <token>`
  - `Authorization: <token>`

## Main Agent API endpoints

- `POST /admin/add_user` — create user and default MCP config
- `POST /v1/chat/llm/` — add LLM config
- `GET /v1/chat/llm/` — list user LLM configs
- `POST /v1/chat/mcp` — add MCP config
- `GET /v1/chat/mcp` — list user MCP configs
- `POST /v1/chat/completions` — create completion
- `PUT /v1/chat/completions/{completion_id}` — continue/update completion
- `GET /v1/chat/completions` — list completions
- `GET /v1/chat/completions/{completion_id}` — get completion
- `DELETE /v1/chat/completions/{completion_id}` — delete completion

## API usage example

### 1) Create a user

```bash
curl -X POST http://localhost:4015/admin/add_user \
  -H "key: abacaba"
```

Save `user_token` from the response.

### 2) Add an LLM config

```bash
curl -X POST http://localhost:4015/v1/chat/llm/ \
  -H "Content-Type: application/json" \
  -H "User-Token: <user_token>" \
  -d '{
    "config_name": "OpenAI",
    "model": "gpt-4.1-mini",
    "api_key": "<api_key>",
    "base_url": "https://api.openai.com/v1"
  }'
```

### 3) Create a completion

```bash
curl -X POST http://localhost:4015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "User-Token: <user_token>" \
  -d '{
    "completion": {
      "messages": [
        {"role": "user", "content": "Multiply 10 and then divide the result"}
      ]
    },
    "llm_config_id": 1,
    "mcp_ids": [1]
  }'
```

## Technologies

- FastAPI
- Uvicorn
- MCP SDK
- OpenAI-compatible API clients
- SQLite (via the `database` package)

## License

MIT
