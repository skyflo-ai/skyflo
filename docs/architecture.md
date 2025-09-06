# Architecture

This document outlines the architecture of [skyflo.ai](https://skyflo.ai).

## Components

Skyflo.ai follows a clean architecture with the following components:

1. **Engine** (`/engine`):
Core backend service that turns natural language into safe Cloud Native operations using a  LangGraph workflow.

   - LangGraph-based execution with nodes: `entry` → `model` → `gate` → `final`
   - LLM integration via LiteLLM with controlled auto‑continue and iteration limits
   - Approval policy for WRITE operations with human-in-the-loop safety
   - Manages authentication, conversations, titles, persistence, and rate limiting
   - Communicates with the MCP server for tool discovery and execution
   - Real-time Server-Sent Events (SSE) streaming for tokens, tool progress, and workflow events
   - Uses Redis pub/sub internally for streaming and stop signals; optional Postgres checkpointer for resilience

2. **MCP Server** (`/mcp`):
MCP server that exposes standardized cloud-native tools for the Engine to execute.

   - Built with FastMCP; single entrypoint registers tools and metadata
   - Tool categories: `kubectl`, `argo` (Rollouts), and `helm`
   - Safety checks, validation, and clear parameter docs (Pydantic)
   - Supports HTTP and SSE transports; automatic tool discovery and registration
   - Executes commands securely against cluster resources

3. **Command Center** (`/ui`):
UI command center delivering real-time insights and control for cloud native operations.

   - Next.js 14 application with a responsive Markdown-based chat UI
   - Streams tokens and tool events from the Engine via SSE
   - Server-side API routes (BFF) proxy to the Engine, forwarding cookies/auth headers
   - Displays real-time workflow progress, tool results, and terminal-like outputs
   - Manages conversations, profile/password, and team administration (roles, invitations)

4. **Kubernetes Controller** (`/kubernetes-controller`):
Kubernetes controller orchestrating secure, scalable deployments in cloud native environments.

   - Implements custom resource definitions (CRDs) for the Kubernetes operator
   - Manages deployment and configuration of all Skyflo.ai components within Kubernetes clusters
   - Provides unified deployment through a single `SkyfloAI` custom resource
   - Handles dynamic configuration updates and scaling of components
   - Implements secure RBAC management for cluster interactions
   - Supports namespace isolation and fine-grained access control
   - Manages standard Kubernetes resources (Deployments, Services) for UI and API components
   - Monitors and reports component health through status conditions

## Agent Architecture

Skyflo.ai employs a graph-based workflow powered by [LangGraph](https://github.com/LangChain-AI/langgraph). The workflow is organized into the following phases:

1. **Model Phase (Planning)**:
   - Analyzes the user's natural language to determine intent
   - Performs lightweight discovery when needed to ground the plan
   - Produces structured tool calls for the next phase

2. **Tool Gate (Execution)**:
   - Executes MCP tools (`kubectl`, `argo`, `helm`) with validated parameters
   - Requires explicit approval for any WRITE/mutating operation
   - Resolves dynamic parameters from previous steps and supports recursive operations
   - Streams progress/results back to the model and UI

3. **Verification Phase**:
   - Evaluates outcomes against the original intent and summarizes results
   - Decides whether to auto‑continue, request approval, or stop
   - If issues are detected, routes context back to the model phase for refinement

## Features

- **Natural Language Kubernetes Management**: Perform operations via natural language
- **Tool Execution via MCP**: Standardized tools for `kubectl`, `argo` (Rollouts), and `helm`
- **Human-in-the-Loop Safety**: Explicit approvals required for WRITE operations
- **SSE Streaming**: Live tokens, tool progress, and results
- **Resource Discovery**: Automatic discovery to ground actions
- **Multi-stage Operations**: Complex workflows broken into manageable steps
- **Context-aware Responses**: Maintains conversation history
- **Conversation Persistence**: Saved timelines with title generation
- **Team Administration**: Roles, invitations, and member management
- **Rate Limiting**: Protects services via Redis-backed limiter
- **Optional Checkpointer**: Postgres-backed workflow resilience
- **Progressive Delivery**: Argo Rollouts support
- **Package Management**: Helm install/upgrade/rollback
- **Terminal-style Output**: Live command output visualization

## Technical Stack

- **Backend**: Python 3.11+, FastAPI, LangGraph, LiteLLM, Tortoise ORM, Aerich, Redis, PostgreSQL
- **Frontend**: React, Next.js 14, TypeScript, Tailwind CSS
- **AI/ML**: LangGraph, LLM integration via LiteLLM
- **Infrastructure**: Kubernetes, Argo Rollouts, Helm
- **Communication**: Server-Sent Events (SSE), Redis pub/sub
- **Security**: JWT authentication via fastapi-users, role-based access (admin)
