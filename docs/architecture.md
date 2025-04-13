# Architecture

This document outlines the architecture of [skyflo.ai](https://skyflo.ai).

## Components

Skyflo.ai follows a clean architecture with the following components:

1. **Engine** (`/engine`):
Core engine powering the multi-agent system of Skyflo.ai for automating cloud native operations.

   - Hosts the multi-agent system including the following agents built using [AutoGen by Microsoft](https://github.com/microsoft/autogen):
     - The Planner
     - The Executor
     - The Verifier
   - True graph-based execution workflow built for reliability and scalability.
   - Manages user authentication and conversations
   - Communicates with the MCP server for tool discovery and execution
   - Implements WebSocket-based real-time communication between the engine and the command center

2. **MCP Server** (`/mcp`):
MCP server orchestrating secure integration and execution of cloud native tools.

   - Provides the MCP server for different cloud native tool definitions and handles their execution
   - Implements tool definitions for `kubectl`, `argo`, and `helm`.
   - Ensures secure access to cluster resources.
   - Uses subprocess and shell commands for tool call execution.

3. **Command Center** (`/ui`):
UI command center delivering real-time insights and control for cloud native operations.

   - The command center for all your cloud native operations.
   - Manages user authentication and conversations
   - Displays real-time workflow progress visualization
   - Implements responsive Markdown-based chat UI
   - Shows operation status and terminal outputs in real-time
   - Settings dashboard for managing team members and permissions

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

## Multi-Agent Architecture

Skyflo.ai uses a state-of-the-art multi-agent architecture powered by [AutoGen](https://github.com/microsoft/autogen) and [LangGraph](https://github.com/LangChain-AI/langgraph):

1. **Planner Agent**:
   - Analyzes natural language queries to determine user intent
   - Follows a two-step process:

      1. Discovery: Before creating a plan, the planner agent will understand the user's intent and run a discovery phase to find the resources that are relevant to the user's intent.
      2. Plan creation: Once the discovery phase is complete, the planner agent will create a plan for the executor agent to execute.
   - Identifies required Kubernetes operations and resources
   - Generates detailed execution plans with step-by-step actions
   - Optimizes tool selection based on capabilities and dependencies

2. **Executor Agent**:
   - Executes each step of the execution plan by calling the MCP server
   - Handles complex, multi-stage operations by resolving dynamic parameters from previous steps
   - Waits for user confirmation before executing any WRITE operation on the Kubernetes cluster
   - Implements validation for parameter types and values
   - Executes recursive operations on multiple resources
   - Processes and formats command outputs for user readability

3. **Verifier Agent**:
   - Evaluates execution results against original user intent
   - Confirms successful implementation of requested changes
   - Provides clear explanations of what was accomplished
   - Calls the Planner agent to create a new plan if any issues are detected during the execution phase

## Features

- **Natural Language Kubernetes Management**: Interact with Kubernetes using natural language
- **Resource Discovery**: Automatic discovery of cluster resources
- **Cluster Health Monitoring**: Get insights into cluster performance and resource utilization
- **Real-time Q&A**: Get immediate answers about your Kubernetes infrastructure
- **Secure by Design**: Zero-trust, least-privileged architecture
- **Real-time Operation Status**: Live updates during execution with WebSockets
- **Multi-stage Operations**: Complex workflows broken down into manageable steps
- **Context-aware Responses**: Maintains conversation context for follow-up questions
- **Progressive Delivery Support**: Integration with Argo Rollouts for advanced deployment patterns
- **Package Management**: Helm chart installation, upgrades, and rollbacks
- **Terminal Output**: Live display of command outputs
- **Conversation Persistence**: Save and continue conversations later

## Technical Stack

- **Backend**: Python 3.11+, FastAPI, LangGraph, Redis, PostgreSQL
- **Frontend**: React, Next.js, TypeScript, TailwindCSS, Socket.IO
- **AI/ML**: AutoGen, LangGraph, LLM integration
- **Infrastructure**: Kubernetes, Argo, Helm
- **Communication**: WebSockets, Redis pub/sub
- **Security**: JWT authentication, RBAC permissions, PyCasbin
