# Skyflo MCP Server

MCP server exposing schema-validated infrastructure tools for Kubernetes, Helm, Argo Rollouts, and Jenkins to the [Engine](../engine) over Streamable HTTP transport. Tool annotations drive the approval gate for every mutating operation.

See [docs/architecture.md](../docs/architecture.md) for full system context.

## Architecture

### FastMCP Server

The FastMCP server is the core tool execution layer:

- CLI entrypoint via `main.py` (accepts `--host` and `--port` arguments)
- FastMCP instance created in `config/server.py`, tools registered via `@mcp.tool()` decorators at import time
- All CLI tools (kubectl, helm) executed as async subprocesses via `utils/commands.py`
- Jenkins tools use an async HTTP client (`httpx`) with credentials resolved from Kubernetes Secrets
- MCP tool annotations (`readOnlyHint`, `destructiveHint`) drive the Engine's approval policy
- Built-in Streamable HTTP transport support
- Custom health check endpoint at `GET /health`
- Readiness endpoint at `GET /health/ready` verifies CLI tools (kubectl, helm etc.) are accessible
- Startup check endpoint at `GET /health/startup`

## Tools

### Categories

1. `kubectl` - Kubernetes operations: [tools/kubectl.py](tools/kubectl.py)
2. `helm` - Helm chart management: [tools/helm.py](tools/helm.py)
3. `argo` - Argo Rollouts progressive delivery: [tools/argo.py](tools/argo.py)
4. `jenkins` - Jenkins CI/CD pipelines: [tools/jenkins.py](tools/jenkins.py)

### Annotations

Every tool carries MCP annotations that the Engine uses for its approval gate:

- `readOnlyHint: true` - read-only tools execute without approval (e.g. `k8s_get`, `k8s_logs`)
- `readOnlyHint: false` - mutating tools require explicit approval (e.g. `k8s_apply`, `k8s_scale`)
- `destructiveHint: true` - destructive tools are flagged for extra caution (e.g. `k8s_delete`, `k8s_drain`, `helm_uninstall`, `argo_abort_rollout`)

Each tool also has a `tags` list (e.g. `k8s`, `helm`, `argo`, `jenkins`, `metrics`) and a human-readable `title`.

## Installation

### Prerequisites

- Python 3.11+
- Kubernetes cluster (with kubectl configured)
- Argo Rollouts (optional)
- Helm (optional)

### Setup

1. Install `uv` package manager:

```console
# Install uv for macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or install with pip
pip install uv
```

2. Install dependencies:

```console
# Navigate to the mcp directory
cd mcp

uv sync --extra dev

# To replicate the CI environment:
uv sync --frozen --extra dev
```

3. Start the server:

```console
# Start with HTTP transport
uv run python main.py --host 0.0.0.0 --port 8888
```

The server uses Streamable HTTP transport and provides an MCP interface for the Engine to execute infrastructure tools.

## Development Commands

| Command | Description |
| --- | --- |
| `uv run python main.py` | Start development server |
| `uv run ruff check .` | Run Ruff linter to check for code issues |
| `uv run ruff format .` | Format code with Ruff |
| `uv run pytest tests` | Run tests with pytest |
| `uv run pytest --cov tests` | Run tests with coverage report |
| `uv run mypy --install-types --non-interactive main.py config/ utils/` | Run mypy for type checking |

## Configuration

### FastMCP

This project includes a `fastmcp.json` for MCP client integrations and dependency metadata. It defines the server entrypoint and required Python dependencies without embedding them in code.

### Environment Variables

Defined in `.env.example`:

- `APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION` - application metadata
- `DEBUG` - debug mode toggle
- `LOG_LEVEL` - logging level (default `INFO`)
- `MAX_RETRY_ATTEMPTS`, `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`, `RETRY_EXPONENTIAL_BASE` - retry policy

### Jenkins Credential Resolution

Jenkins tools receive `api_url` and `credentials_ref` as parameters from the Engine (injected via integration metadata). The `credentials_ref` points to a Kubernetes Secret in `namespace/name` format. At runtime, the MCP server:

1. Validates the reference format and characters
2. Calls `kubectl get secret <name> -n <namespace> -o json` with a 5-second timeout
3. Decodes `username` and `api-token` from the Secret's base64-encoded data
4. Creates an authenticated `httpx.AsyncClient` with CSRF crumb support

## Testing

Tests are organized in a structured directory layout that mirrors the source code:

```
tests/
├── tools/                   # Tests for tool implementations
│   ├── test_argo.py        # Argo Rollouts tests
│   ├── test_helm.py        # Helm tests
│   ├── test_jenkins.py     # Jenkins tests
│   └── test_kubectl.py     # Kubernetes tests
└── utils/                  # Tests for utility functions
    └── test_commands.py    # Command execution tests
```

```bash
# Navigate to mcp directory
cd mcp

# Run all tests with default coverage (30%)
./run_tests.sh

# Run tests with custom coverage threshold
./run_tests.sh --coverage 80
```

## Component Structure

```text
mcp/
├── main.py                  # CLI entrypoint (--host, --port)
├── config/
│   └── server.py            # FastMCP instance, health check, tool imports
├── tools/                   # Tool implementations
│   ├── __init__.py          # Package initialization
│   ├── kubectl.py           # Kubernetes tools (22)
│   ├── helm.py              # Helm tools (16)
│   ├── argo.py              # Argo Rollouts tools (13)
│   └── jenkins.py           # Jenkins tools (13)
├── utils/
│   ├── commands.py          # Async subprocess execution
│   └── models.py            # Shared type definitions (ToolOutput)
├── tests/                   # Mirrors source structure
│   ├── tools/               # Tool-level tests
│   └── utils/               # Utility tests
├── __about__.py             # Version information
├── .env.example             # Environment variable template
├── fastmcp.json             # MCP client integration metadata
├── run_tests.sh             # Test runner with coverage threshold
├── pyproject.toml           # Project dependencies and tooling
└── README.md                # Documentation
```

### Best Practices

- **Tool Implementation**
  - Register tools using `@mcp.tool()` with `title`, `tags`, and `annotations`
  - Use Pydantic `Field` descriptions for all parameters
  - Implement proper error handling and validation
  - Follow async/await patterns for command execution
  - Return `ToolOutput` typed dicts with `output` and `error` fields

- **Server Development**
  - Import tool modules in `config/server.py` to trigger decorator registration
  - Use `utils/commands.py` for subprocess execution with consistent error handling
  - Set `readOnlyHint` and `destructiveHint` annotations accurately for each tool

## Community

- [Website](https://skyflo.ai)
- [Discord](https://discord.gg/kCFNavMund)
- [X](https://x.com/skyflo_ai)
- [LinkedIn](https://www.linkedin.com/company/skyflo)
