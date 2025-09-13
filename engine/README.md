# Skyflo.ai Engine Service

The Skyflo.ai Engine is the backend intelligence layer that connects the [UI](../ui) and the [MCP server](../mcp) to turn natural-language requests into **safe Cloud & DevOps operations** across Kubernetes and CI/CD systems, with a human-in-the-loop workflow.

## Architecture

The Engine follows a layered structure under `src/api`:

- `endpoints/`: FastAPI routers for agent chat/approvals/stop, conversations, auth, team, integrations, and health
- `services/`: Business logic (MCP client, tool execution, approvals, rate limiting, titles, persistence)
- `agent/`: LangGraph workflow
- `config/`: Settings, database, and rate-limit configuration
- `models/`: Tortoise ORM models
- `middleware/`: CORS and request logging
- `utils/`: Helpers, sanitization, time utilities

### Execution Model (LangGraph)

The workflow is a compact graph compiled with an optional Postgres checkpointer:

- Nodes: `entry` → `model` → `gate` → `final` with conditional routing
- `model` runs an LLM turn (via LiteLLM) and may produce tool calls
- `gate` executes MCP tools (with approval policy) and feeds results back to the model
- Auto‑continue is applied conservatively based on a “next speaker” decision
- Stop requests are honored mid‑stream via Redis flags

Checkpointer:
- Postgres checkpointer via `langgraph-checkpoint-postgres` when `ENABLE_POSTGRES_CHECKPOINTER=true`
- Falls back to in‑memory if Postgres is unavailable

### Event Streaming (SSE + Redis)

All workflow events stream over SSE from `/api/v1/agent/chat` and `/api/v1/agent/approvals/{call_id}`. Internally, the Engine uses Redis pub/sub channels keyed by a unique run id. Event types include (non‑exhaustive):

- `ready`, `heartbeat`
- `token`, `generation.start`, `generation.complete`
- `tools.pending`, `tool.executing`, `tool.result`, `tool.error`, `tool.approved`, `tool.denied`
- `completed`, `workflow_complete`, `workflow_error`

## Features

- Natural language operations with tool execution via MCP
- SSE streaming for tokens, tool progress, and results
- Auth with fastapi-users (JWT), first user becomes admin
- Team admin endpoints (list/add/update/remove members)
- Conversation CRUD with persisted message timeline and title generation
- Rate limiting via Redis (fastapi-limiter)
- Optional Postgres checkpointer for resilient workflow state
- Integrations admin (CRUD) with secure credential storage (Kubernetes Secret)

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL and Redis
- Docker & Docker Compose (optional, for local services)

### Setup

1) Create `.env` from the example and set required variables.

```bash
# From engine/
cp .env.example .env
```

Minimum to set for local dev:
- `APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`
- `POSTGRES_DATABASE_URL` (e.g. `postgres://postgres:postgres@localhost:5432/skyflo`)
- `REDIS_URL` (e.g. `redis://localhost:6379/0`)
- `JWT_SECRET`
- LLM provider key, e.g. `OPENAI_API_KEY` when `LLM_MODEL=openai/gpt-4o`

2) Install dependencies and the package in editable mode.

```bash
python -m venv .venv
source .venv/bin/activate
uv pip install -e "."
```

3) Apply database migrations (Tortoise + Aerich).

```bash
aerich upgrade
```

To create new migrations during development:

```bash
aerich migrate
aerich upgrade
```

### Optional: Start local PostgreSQL + Redis

```bash
# From project root
docker compose -f deployment/local.docker-compose.yaml up -d
```

### Run the Engine

```bash
source .venv/bin/activate
uvicorn api.asgi:app --host 0.0.0.0 --port 8080 --reload
```

Service will be available at `http://localhost:8080`.

## API

Base path: `/api/v1`

- `GET /health` and `GET /health/database`
- `POST /agent/chat` (SSE): stream tokens/events
- `POST /agent/approvals/{call_id}` (SSE): approve/deny pending tool
- `POST /agent/stop`: stop a specific run
- `POST /conversations`, `GET /conversations`, `GET/PATCH/DELETE /conversations/{id}`
- Auth (`/auth/jwt/*`, `/auth/register/*`, `/auth/verify/*`, `/auth/reset-password/*`, `/auth/users/*`), plus:
  - `GET /auth/is_admin_user`
  - `GET /auth/me`, `PATCH /auth/me`
  - `PATCH /auth/users/me/password`
- Team admin (`/team/*`): members list/add/update/remove (requires admin)
 - Integrations (`/integrations/*`): list/create/update/delete (admin only)

### SSE chat example

```bash
curl -N -H "Content-Type: application/json" \
  -X POST \
  -d '{"messages":[{"role":"user","content":"List pods in default"}]}' \
  http://localhost:8080/api/v1/agent/chat
```

### Approvals example

```bash
curl -N -H "Content-Type: application/json" \
  -X POST \
  -d '{"approve":true, "reason":"safe", "conversation_id":"<conversation-uuid>"}' \
  http://localhost:8080/api/v1/agent/approvals/<call_id>
```

## Configuration

Defined in `src/api/config/settings.py` (Pydantic Settings, `.env` loaded). Key variables:

- App: `APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`, `DEBUG`, `LOG_LEVEL`, `API_V1_STR`
- DB: `POSTGRES_DATABASE_URL`
- Checkpointer: `ENABLE_POSTGRES_CHECKPOINTER` (default true), `CHECKPOINTER_DATABASE_URL`
- Redis & Rate limit: `REDIS_URL`, `RATE_LIMITING_ENABLED`, `RATE_LIMIT_PER_MINUTE`
- Auth: `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- MCP: `MCP_SERVER_URL`
 - Integrations: `INTEGRATIONS_SECRET_NAMESPACE` (default `default`)
- Workflow: `MAX_AUTO_CONTINUE_TURNS`, `LLM_MAX_ITERATIONS`, `LLM_TEMPERATURE`
- LLM: `LLM_MODEL` (e.g. `openai/gpt-4o`), `LLM_HOST` (optional), provider API key envs like `OPENAI_API_KEY`

## Component Structure

```
engine/
├── src/
│   └── api/
│       ├── agent/          # LangGraph workflow (graph, model node, state, prompts)
│       ├── config/         # Settings, DB, rate limiting
│       ├── endpoints/      # FastAPI routers (agent, auth, conversations, team, integrations, health)
│       ├── middleware/     # CORS, logging
│       ├── models/         # Tortoise ORM models (User, Conversation, Message, Integration)
│       ├── schemas/        # Pydantic schemas (team)
│       ├── services/       # MCP client, tool executor, approvals, limiter, persistence, titles
│       └── utils/          # Helpers, sanitization, time
├── migrations/              # Aerich migrations
└── pyproject.toml          # Project dependencies and tooling
```

## Tech Stack

| Component            | Technology                       |
|----------------------|----------------------------------|
| Web Framework        | FastAPI + Uvicorn                |
| ORM                  | Tortoise ORM                     |
| Migrations           | Aerich                           |
| Authentication       | fastapi-users (+ tortoise)       |
| Streaming            | SSE + Redis (pub/sub)            |
| Rate limiting        | fastapi-limiter + Redis          |
| AI Agent             | LangGraph                        |
| LLM Integration      | LiteLLM                          |
| Database             | PostgreSQL                       |

## Community and Support

- Website: https://skyflo.ai
- Discord: https://discord.gg/kCFNavMund
- X/Twitter: https://x.com/skyflo_ai
- GitHub Discussions: https://github.com/skyflo-ai/skyflo/discussions
