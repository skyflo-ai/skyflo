# Skyflo.ai Engine Service

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org)


## Overview

The Skyflo.ai Engine Service is the central intelligence layer that connects the frontend UI with the Engine's execution backend and the MCP server. It powers the platform's natural language interaction capabilities by orchestrating a sophisticated multi-agent system built using AutoGen that translates user queries into precise Kubernetes operations through LangGraph-powered workflows.

## Architecture

The Engine Service implements a layered architecture designed for high maintainability and testability:

### Layer Structure

- **Web Layer** (`/src/api/web/`): FastAPI endpoints, WebSocket gateways, and Engine dependencies
- **Service Layer** (`/src/api/services/`): Business logic, orchestration, and role enforcement
- **Workflow Layer** (`/src/api/workflow/`): LangGraph-powered execution engine with recursive automata
- **Repository Layer** (`/src/api/repositories/`): Tortoise ORM access to PostgreSQL
- **Domain Layer** (`/src/api/domain/`): Entity definitions, Pydantic models, and permission logic

### Multi-Agent System

The service orchestrates three specialized AI agents working in concert:

1. **Planner Agent** (`/src/api/workflow/agents/planner.py`):
   - Analyzes natural language queries to determine user intent
   - Selects appropriate Kubernetes operations and tools
   - Generates detailed execution plans with step-by-step actions
   - Creates verification checklists for quality assurance

2. **Executor Agent** (`/src/api/workflow/agents/executor.py`):
   - Implements each step of the execution plan
   - Resolves dynamic parameters from previous steps
   - Manages complex, multi-stage operations
   - Executes tool calls against the Engine component

3. **Verifier Agent** (`/src/api/workflow/agents/verifier.py`):
   - Validates execution results against original user intent
   - Implements error recovery strategies
   - Provides clear explanations of outcomes
   - Ensures operations meet quality standards

4. **Workflow Manager** (`/src/api/workflow/manager.py`):
   - Orchestrates the entire workflow using LangGraph
   - Manages state transitions between agents
   - Handles retry logic and error recovery
   - Generates final user responses

## Features

### Core Capabilities

- **Natural Language Understanding**: Process Kubernetes operations through conversational queries
- **Multi-Agent Orchestration**: Coordinates specialized agents via LangGraph workflows
- **Enterprise Authentication**: JWT-based auth with refresh tokens and secure sessions
- **RBAC & Permissions**: Role-based access control powered by PyCasbin
- **Team & Organization Management**: User organizations with hierarchical permissions
- **Real-time Communications**: WebSocket-based streaming for live updates

### Workflow Engine

- **Recursive Automata**: Self-healing graph state machines for complex operations
- **Dynamic Parameter Resolution**: Context-aware parameter handling from previous steps
- **Intelligent Error Recovery**: Automatic retry and alternative strategy implementation
- **Execution Monitoring**: Live tracking of operation progress and resource status
- **Step Visualization**: Real-time display of execution stages and agent transitions

### Communication Features

- **Chat Management**: Persistent conversations with message threading
- **Real-time Messaging**: WebSocket and Redis pub/sub implementation
- **Terminal Streaming**: Live command output display
- **Token Streaming**: Real-time LLM response generation

## Installation

### Prerequisites

- Python 3.11+ - [pyenv](https://github.com/pyenv/pyenv)
- Docker & Docker Compose (optional)

### Setup

1. Copy the .env.example file to .env.

```bash
# From the project root
cp .env.example .env
```

_Make sure to fill in the env `OPEN_AI_KEY` variable._

2. Install dependencies:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix or MacOS
.venv\Scripts\activate     # On Windows

# Install dependencies with uv
uv pip install -e "."
```

3. Configure the database:

```bash
# Initialize database with migrations
aerich upgrade
```

4. Add a new migration

```bash
aerich migrate

aerich upgrade
```

## Usage

### Docker Deployment

Run the local.docker-compose.yml file:

```bash
# From the project root
docker-compose -f deployment/local.docker-compose.yaml up -d
```

This starts the PostgreSQL and Redis services that are required for the Engine to run.

### Starting the Engine Server

```bash
source .venv/bin/activate && uvicorn api.asgi:app --host 0.0.0.0 --port 8080 --reload
```

The Engine service will be available at http://localhost:8080.


## Component Structure

```
engine/
├── src/
│   └── api/
│       ├── web/            # FastAPI endpoints and WebSocket gateways
│       ├── services/       # Business logic and orchestration
│       ├── workflow/       # LangGraph execution engine
│       │   └── agents/     # Specialized AI agents
│       │       ├── planner.py    # Query analysis and planning
│       │       ├── executor.py   # Plan execution and tool calls
│       │       └── verifier.py   # Result validation and QA
│       ├── repositories/   # Tortoise ORM database access
│       ├── domain/        # Entity models and permissions
│       └── config/        # Configuration management
├── migrations/            # Database migrations
└── pyproject.toml        # Project dependencies
```

## Tech Stack

| Component            | Technology                 |
|----------------------|----------------------------|
| Web Framework        | FastAPI + Uvicorn          |
| ORM                  | Tortoise ORM               |
| Migrations           | Aerich                     |
| Authentication       | FastAPI Users              |
| RBAC                 | PyCasbin                   |
| WebSockets           | FastAPI/Socket.IO          |
| Pub/Sub              | Broadcaster (Redis)        |
| Multi-Agent System   | LangGraph + AutoGen        |
| LLM Integration      | OpenAI + Custom LLM Client |
| Database             | PostgreSQL                 |
| Centralized WS       | Redis                      |

## Community and Support

- [Website](https://skyflo.ai)
- [Discord Community](https://discord.gg/kCFNavMund)
- [Twitter/X Updates](https://x.com/skyflo_ai)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
