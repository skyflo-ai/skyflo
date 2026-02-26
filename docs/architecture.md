# Architecture

Skyflo is a self-hosted AI operations agent for Kubernetes and CI/CD automation with native Jenkins support. The [Engine](../engine) runs a LangGraph workflow with an approval gate for every mutating operation, executes typed tools via the [MCP server](../mcp), and streams real-time SSE updates to the [Command Center](../ui).

## Components

### Engine (`/engine`)

Core backend that turns natural language into safe, auditable infrastructure operations using a LangGraph workflow.

- LangGraph execution graph: `entry` → `model` → `gate` → `final` with conditional routing
- Multi-provider LLM support (OpenAI, Groq, Ollama, Gemini, etc.) via LiteLLM with controlled auto-continue and iteration limits
- Annotation-based approval policy using MCP `readOnlyHint` for the approval gate
- JWT authentication with refresh token rotation and cookie-based session management
- Conversation management, automatic title generation, persistence, and rate limiting
- Tool discovery and execution via FastMCP
- Thinking/reasoning model support with streamed reasoning tokens and configurable effort/budget
- Real-time SSE streaming for tokens, thinking content, tool progress, token usage metrics, and workflow events
- Graceful mid-stream workflow stop via Redis flags
- Redis pub/sub for internal streaming; optional Postgres checkpointer for resilience

### MCP Server (`/mcp`)

Model Context Protocol (MCP) server exposing schema-validated infrastructure tools for the Engine.

- Built with FastMCP; 64 tools registered via `@mcp.tool()` decorators with titles, tags, and annotations
- Tool categories: `kubectl` (22), `helm` (16), `argo` Rollouts (13), and `jenkins` CI (13)
- Tool annotations (`readOnlyHint`, `destructiveHint`) drive the Engine's approval policy
- CLI tools (kubectl, helm) run as async subprocesses; Jenkins uses an httpx client with credentials resolved from Kubernetes Secrets
- Streamable HTTP transport for Engine communication; automatic tool discovery
- Pydantic-validated parameters with clear Field descriptions

### Command Center (`/ui`)

Next.js command interface for real-time operations visibility and control.

- Next.js 14 with Radix UI + shadcn/ui primitives and Tailwind CSS
- Streams tokens, thinking/reasoning content, tool events, and token usage metrics from the Engine via SSE
- Collapsible thinking blocks showing the model's reasoning process
- Inline tool approval/deny UI with bulk approval bar
- Server-side API routes (BFF) proxy to the Engine, forwarding cookies/auth headers
- Zustand-backed auth state with automatic refresh token rotation
- Real-time workflow progress, tool results, and terminal-style outputs
- Conversation management, integrations admin, profile/password, and team administration

### Kubernetes Controller (`/kubernetes-controller`)

Go-based Kubernetes operator managing Skyflo component lifecycle via CRD.

- Custom resource definition (`SkyfloAI`) for declarative deployment
- Manages all Skyflo components (Engine, MCP, UI) through a single custom resource
- Dynamic configuration updates and scaling
- RBAC management for cluster interactions
- Namespace isolation and fine-grained access control
- Health monitoring through status conditions

## Execution Workflow

Skyflo uses a graph-based workflow powered by [LangGraph](https://github.com/LangChain-AI/langgraph). The workflow enforces a deterministic loop:

1. **Plan**
   - Analyzes the user's natural language to determine intent
   - Performs lightweight discovery when needed to ground the plan
   - Produces structured tool calls for the next phase

2. **Approve and Execute**
   - Executes MCP tools (`kubectl`, `argo`, `helm`, `jenkins`) with validated parameters
   - Requires explicit approval for every mutating tool call
   - Resolves dynamic parameters from previous steps and supports recursive operations
   - Streams progress and results back to the model and UI

3. **Verify**
   - Evaluates outcomes against the original intent and summarizes results
   - Decides whether to auto-continue, request approval, or stop
   - Routes context back to the model phase for refinement if issues are detected

4. **Persist**
   - Stores tool calls, parameters, and results
   - Supports audit and replay

## Technical Stack

| Layer          | Technologies                                                                           |
|----------------|----------------------------------------------------------------------------------------|
| Backend        | Python 3.11+, FastAPI, LangGraph, LiteLLM, Tortoise ORM, Aerich, Redis, PostgreSQL    |
| MCP            | FastMCP, httpx, Pydantic, Streamable HTTP transport                                    |
| Frontend       | React, Next.js 14, TypeScript, Tailwind CSS, Radix UI + shadcn/ui, Zustand, framer-motion |
| AI/ML          | LangGraph, multi-provider LLM integration via LiteLLM                                 |
| Infrastructure | Kubernetes, Argo Rollouts, Helm                                                       |
| Communication  | Server-Sent Events (SSE), Redis pub/sub                                                |
| Security       | JWT + refresh token rotation via fastapi-users, role-based access, HttpOnly cookies    |
