# Agent API

`fastapi` `mcp` `llm` `docker` `openai-compatible`

HTTP API для агентных LLM-сценариев с поддержкой MCP-серверов.

## Что в репозитории

- `agent_api/` — основной FastAPI API (управление пользователями, LLM-конфигами, MCP-конфигами, completions)
- `simple_mcp/` — пример MCP-сервера с инструментами `multiply` и `divide`
- `docker-compose.yaml` — запуск двух сервисов

## Быстрый старт (Docker, рекомендуется)

### Вариант 1: готовые образы (как в деплое)

```bash
# 1) Сеть
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

Swagger: `http://localhost:4015/docs`

### Вариант 2: локальная сборка через docker compose

```bash
docker compose up --build
```

По умолчанию сервисы поднимаются на:

- Agent API: `http://localhost:4015`
- Simple MCP: `http://localhost:8015`

## Локальный запуск без Docker

> Важно: `agent_api` и `simple_mcp` сейчас публикуются с одинаковым именем пакета, поэтому удобнее запускать их в разных виртуальных окружениях.

### Agent API

```bash
cd agent_api
pip install -e .
uvicorn agent_api.app:app --host 0.0.0.0 --port 8000
```

Переменные окружения:

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

Переменные окружения:

```bash
SIMPLE_MCP_NAME=Simple-MCP
SIMPLE_MCP_TOKEN=abacaba
```

## Аутентификация

### Agent API

- Для большинства endpoint’ов обязателен заголовок `User-Token`.
- Для создания пользователя (`/admin/add_user`) нужен заголовок `key` со значением `SECRET_KEY`.

### Simple MCP

- Требуется заголовок `Authorization`.
- Допустимы форматы:
  - `Authorization: Bearer <token>`
  - `Authorization: <token>`

## Основные endpoint’ы Agent API

- `POST /admin/add_user` — создать пользователя и дефолтный MCP-конфиг
- `POST /v1/chat/llm/` — добавить LLM-конфиг
- `GET /v1/chat/llm/` — получить LLM-конфиги пользователя
- `POST /v1/chat/mcp` — добавить MCP-конфиг
- `GET /v1/chat/mcp` — получить MCP-конфиги пользователя
- `POST /v1/chat/completions` — создать completion
- `PUT /v1/chat/completions/{completion_id}` — продолжить/обновить completion
- `GET /v1/chat/completions` — список completion’ов
- `GET /v1/chat/completions/{completion_id}` — получить completion
- `DELETE /v1/chat/completions/{completion_id}` — удалить completion

## Пример использования API

### 1) Создать пользователя

```bash
curl -X POST http://localhost:4015/admin/add_user \
  -H "key: abacaba"
```

Из ответа сохранить `user_token`.

### 2) Добавить LLM-конфиг

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

### 3) Создать completion

```bash
curl -X POST http://localhost:4015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "User-Token: <user_token>" \
  -d '{
    "completion": {
      "messages": [
        {"role": "user", "content": "Умножь 10 и потом раздели результат"}
      ]
    },
    "llm_config_id": 1,
    "mcp_ids": [1]
  }'
```

## Технологии

- FastAPI
- Uvicorn
- MCP SDK
- OpenAI-compatible API clients
- SQLite (через `database` пакет)

## Лицензия

MIT
