# Skyflo Engine

The Engine is Skyflo's orchestration backend. It connects the [Command Center](../ui) and the [MCP server](../mcp), turning natural language into typed, auditable Kubernetes and CI/CD operations. Every mutating tool call requires explicit approval, enforced by the engine, not a UI toggle.

See the [architecture overview](https://skyflo.ai/docs/architecture) for full system context.

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
- Continuation between `model` and `gate` is driven by conditional edges based on pending tool calls and approval state
- Stop requests are honored mid-stream via Redis flags

Checkpointer:
- Postgres checkpointer via `langgraph-checkpoint-postgres` when `ENABLE_POSTGRES_CHECKPOINTER=true`
- Falls back to in-memory if Postgres is unavailable

### Event Streaming (SSE + Redis)

All workflow events stream over SSE from `/api/v1/agent/chat` and `/api/v1/agent/approvals/{call_id}`. Internally, the Engine uses Redis pub/sub channels keyed by a unique run id. Event types include (non-exhaustive):

- `ready`, `heartbeat`
- `thinking`, `thinking.complete`
- `token`, `generation.start`, `generation.complete`
- `tools.pending`, `tool.executing`, `tool.awaiting_approval`, `tool.result`, `tool.error`, `tool.approved`, `tool.denied`
- `token.usage`, `ttft`
- `completed`, `workflow_complete`, `workflow_error`, `workflow.error`

## Features

- Natural language operations with typed tool execution via MCP
- SSE streaming for tokens, thinking/reasoning content, tool progress, and results
- Thinking/reasoning model support with configurable effort and budget (Anthropic, OpenAI, DeepSeek, etc.)
- Multi-provider LLM support (OpenAI, Groq, Ollama, Gemini, etc.) via LiteLLM
- Approval gate for every mutating tool call, derived from MCP annotations (`readOnlyHint`, `destructiveHint`)
- Auth with fastapi-users (JWT), first user becomes admin
- Refresh token rotation with cookie-based session management
- Team admin endpoints (list/add/update/remove members)
- Conversation CRUD with persisted message timeline and automatic title generation
- Token usage tracking with TTFT and TTR metrics per conversation
- Rate limiting via Redis (fastapi-limiter)
- Graceful mid-stream workflow stop via Redis flags
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
- LLM provider key, e.g. `GEMINI_API_KEY` when `LLM_MODEL=gemini/gemini-2.5-pro`

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

### Optional: Start Local PostgreSQL + Redis

```bash
# From project root
docker compose -f deployment/local.docker-compose.yaml up -d
```

### Run the Engine

```bash
# Using uv (recommended, respects uv.lock for reproducible builds)
uv run uvicorn src.api.asgi:app --host 0.0.0.0 --port 8080 --reload
```

Service will be available at `http://localhost:8080`.

## Development Commands

**Note:** Development commands require [Hatch](https://hatch.pypa.io/). Install via `pip install hatch` or `pipx install hatch`.

| Command | Description |
| ------- | ----------- |
| `uv run uvicorn src.api.asgi:app --host 0.0.0.0 --port 8080 --reload` | Start development server with hot reload |
| `hatch run lint` | Run Ruff linter to check for code issues |
| `hatch run type-check` | Run mypy for type checking |
| `hatch run format` | Format code with Ruff |
| `hatch run test` | Run tests with pytest |
| `hatch run test-cov` | Run tests with coverage report |

## API

Base path: `/api/v1`

- `GET /health` and `GET /health/database`
- `POST /agent/chat` (SSE): stream tokens/events
- `POST /agent/approvals/{call_id}` (SSE): approve/deny pending tool
- `POST /agent/stop`: stop a specific run
- `GET /agent/tools`: list available MCP tools with metadata (name, title, tags, annotations)
- `POST /conversations`, `GET /conversations`, `GET/PATCH/DELETE /conversations/{id}`
- Auth (`/auth/jwt/*`, `/auth/register/*`, `/auth/verify/*`, `/auth/reset-password/*`, `/auth/users/*`), plus:
  - `GET /auth/is_admin_user`
  - `GET /auth/me`, `PATCH /auth/me`
  - `PATCH /auth/users/me/password`
  - `POST /auth/refresh/issue`, `POST /auth/refresh` (refresh token rotation)
  - `POST /auth/logout` (revoke refresh token, clear cookies)
- Team admin (`/team/*`): members list/add/update/remove (requires admin)
- Integrations (`/integrations/*`): list (authenticated), create/update/delete (admin only)

### SSE Chat Example

```bash
curl -N -H "Content-Type: application/json" \
  -X POST \
  -d '{"messages":[{"role":"user","content":"List pods in default"}]}' \
  http://localhost:8080/api/v1/agent/chat
```

### Approvals Example

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
- Workflow: `LLM_MAX_ITERATIONS`, `LLM_CONTEXT_WINDOW_MESSAGES` (max messages kept in the LLM context window per turn; default 40, increase for long-running troubleshooting sessions where older tool results need to remain in context)
- LLM: `LLM_MODEL` (e.g. `gemini/gemini-2.5-pro`), `LLM_HOST` (optional), provider API key envs like `GEMINI_API_KEY`
- Thinking/Reasoning: `LLM_REASONING_EFFORT` (`low`, `medium`, `high`), `LLM_THINKING_BUDGET_TOKENS` (Anthropic-specific), `LLM_MAX_TOKENS` (optional override when thinking is enabled)

## Component Structure

```text
engine/
├── src/
│   └── api/
│       ├── agent/          # LangGraph workflow (graph, model node, state, prompts, stop)
│       ├── config/         # Settings, DB, rate limiting
│       ├── endpoints/      # FastAPI routers (agent, auth, conversations, team, integrations, health)
│       ├── integrations/   # Provider-specific helpers (Jenkins)
│       ├── middleware/     # CORS, logging
│       ├── models/         # Tortoise ORM models (User, Conversation, Message, Integration, RefreshToken)
│       ├── schemas/        # Pydantic schemas (team)
│       ├── services/       # MCP client, tool executor, approvals, limiter, persistence, titles, checkpointer, stop, tools cache
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
| Rate Limiting        | fastapi-limiter + Redis          |
| AI Agent             | LangGraph                        |
| LLM Integration      | LiteLLM                          |
| MCP Communication    | FastMCP                          |
| Database             | PostgreSQL                       |

## Community

- [Docs](https://skyflo.ai/docs)
- [Discord](https://discord.gg/kCFNavMund)
- [X](https://x.com/skyflo_ai)
- [LinkedIn](https://www.linkedin.com/company/skyflo)
