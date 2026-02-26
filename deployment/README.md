# Skyflo Deployment

Deployment assets for Skyflo: Dockerfiles, Kubernetes manifests, ConfigMaps, Nginx reverse proxy, and installer scripts for production and local development.

## Directory Structure

```text
deployment/
├── install.sh                     # Interactive Kubernetes installer (fetches latest release)
├── uninstall.sh                   # Kubernetes uninstaller
├── install.yaml                   # Production Kubernetes manifests (uses ${VERSION}, ${NAMESPACE})
├── local.install.yaml             # Local manifests (imagePullPolicy: Never, NodePort services)
├── local.docker-compose.yaml      # Docker Compose for local PostgreSQL + Redis
├── local.kind.yaml                # KinD cluster config (control plane + worker, port mappings)
├── local.test-deploy.yaml         # Test deployment (intentionally broken nginx image)
├── config/
│   ├── engine-configmap.yaml      # Engine env vars (app metadata, JWT, LLM, rate limiting)
│   ├── mcp-configmap.yaml         # MCP env vars (app metadata, retry policy)
│   └── ui-configmap.yaml          # UI env vars (API URLs, feature flags)
├── engine/
│   ├── Dockerfile                 # Python 3.11-slim, uv deps, non-root user, port 8080
│   └── entrypoint.sh              # Aerich migrations + Uvicorn startup
├── mcp/
│   ├── Dockerfile                 # Python 3.11-slim, kubectl + Helm + Argo plugin, port 8888
│   └── entrypoint.sh              # FastMCP server startup
├── ui/
│   ├── Dockerfile                 # Multi-stage Node.js 20 build, Next.js standalone, port 3000
│   ├── proxy.Dockerfile           # Nginx 1.25-alpine reverse proxy, port 80
│   └── nginx.conf                 # Routes /api/v1/ to Engine, / to UI
└── kubernetes-controller/
    └── Dockerfile                 # Multi-stage Go build, distroless nonroot runtime
```

## Production Installation

### Prerequisites

- A running Kubernetes cluster
- `kubectl` configured and pointed at the target cluster
- `curl`, `envsubst` (from `gettext`), `openssl`

### Install

The installer fetches the latest release from GitHub, prompts for LLM provider and API keys, generates secrets (JWT, database passwords), and applies the manifests:

```bash
curl -sL https://skyflo.ai/install.sh | bash
```

Or with a pinned version:

```bash
VERSION=<version> curl -sL https://skyflo.ai/install.sh | bash
```

### Uninstall

```bash
curl -sL https://skyflo.ai/uninstall.sh | bash
```

The uninstaller removes all Skyflo resources and optionally deletes persistent volumes.

## Local Development

### Option A: Docker Compose (databases only)

Start PostgreSQL and Redis locally for Engine and MCP development:

```bash
docker compose -f deployment/local.docker-compose.yaml up -d
```

This starts:
- **PostgreSQL 15** on `localhost:5432` (user/pass/db: `skyflo`)
- **Redis 7** on `localhost:6379` (append-only persistence)

Both services include health checks and persistent volumes.

### Option B: Full local Kubernetes (KinD)

#### 1. Create the KinD cluster

```bash
kind create cluster --name skyflo-ai --config deployment/local.kind.yaml
```

#### 2. Build all Docker images

```bash
docker buildx build -f deployment/engine/Dockerfile -t skyfloaiagent/engine:latest .
docker buildx build -f deployment/mcp/Dockerfile -t skyfloaiagent/mcp:latest .
docker buildx build -f deployment/ui/Dockerfile -t skyfloaiagent/ui:latest .
docker buildx build -f deployment/kubernetes-controller/Dockerfile -t skyfloaiagent/controller:latest .
docker buildx build -f deployment/ui/proxy.Dockerfile -t skyfloaiagent/proxy:latest .
```

#### 3. Load images into the KinD cluster

```bash
kind load docker-image --name skyflo-ai \
  skyfloaiagent/engine:latest \
  skyfloaiagent/mcp:latest \
  skyfloaiagent/ui:latest \
  skyfloaiagent/controller:latest \
  skyfloaiagent/proxy:latest
```

#### 4. Configure secrets and runtime defaults

Set all variables used by `deployment/local.install.yaml`:

```bash
export NAMESPACE=skyflo-ai
export LLM_MODEL=gemini/gemini-2.5-pro
export GEMINI_API_KEY=AI...
export JWT_SECRET=$(openssl rand -base64 32)
export POSTGRES_DATABASE_URL=postgres://skyflo:skyflo@skyflo-ai-postgres:5432/skyflo
export REDIS_URL=redis://skyflo-ai-redis:6379/0
export MCP_SERVER_URL=http://skyflo-ai-mcp:8888/mcp
export INTEGRATIONS_SECRET_NAMESPACE=$NAMESPACE
```

> Set any additional provider keys if needed (e.g., `GROQ_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, etc.).

#### 5. Apply the local manifests

```bash
envsubst < deployment/local.install.yaml | kubectl apply -f -
```

#### 6. Access the UI

```bash
kubectl port-forward svc/skyflo-ai-ui -n $NAMESPACE 3000:80
```

Then open `http://localhost:3000`.

#### 7. Test with a sample deployment

The test manifest deploys an nginx pod with an intentionally incorrect image tag. Useful for verifying the agent detects and resolves the error:

```bash
kubectl apply -f deployment/local.test-deploy.yaml

# Clean up
kubectl delete -f deployment/local.test-deploy.yaml
```

## Service Architecture

### Images and Ports

| Service    | Image                         | Port | Description |
|------------|-------------------------------|------|-------------|
| Engine     | `skyfloaiagent/engine`        | 8080 | FastAPI backend (Uvicorn) |
| MCP        | `skyfloaiagent/mcp`           | 8888 | FastMCP tool server (kubectl, Helm, Argo, Jenkins) |
| UI         | `skyfloaiagent/ui`            | 3000 | Next.js frontend |
| Proxy      | `skyfloaiagent/proxy`         | 80   | Nginx reverse proxy |
| Controller | `skyfloaiagent/controller`    | 8081 | Kubernetes operator (Go) |
| PostgreSQL | `postgres:15.15-alpine`       | 5432 | Primary database |
| Redis      | `redis:7.4.7-alpine`          | 6379 | Pub/sub, rate limiting, stop signals |

### Nginx Proxy

The proxy sidecar runs alongside the UI deployment and routes traffic:

- `GET /health` - proxy health check
- `/api/v1/*` - forwarded to the Engine service (`skyflo-ai-engine:8080`)
- `/*` - forwarded to the UI service (`skyflo-ai-ui:3000`)

SSE streaming is supported with buffering disabled and 3600s timeouts.

### Init Containers

The Engine deployment includes init containers that wait for PostgreSQL and Redis to become healthy before starting (300s timeout each).

## Configuration

### ConfigMaps (non-sensitive)

Per-service ConfigMaps in `config/` provide non-sensitive environment variables:

- **engine-configmap.yaml**: `APP_NAME`, `APP_VERSION`, `LOG_LEVEL`, `RATE_LIMITING_ENABLED`, `RATE_LIMIT_PER_MINUTE`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`, `LLM_MAX_ITERATIONS`, `MAX_AUTO_CONTINUE_TURNS`, `ENABLE_POSTGRES_CHECKPOINTER`
- **mcp-configmap.yaml**: `APP_NAME`, `APP_VERSION`, `LOG_LEVEL`, `MAX_RETRY_ATTEMPTS`, `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`, `RETRY_EXPONENTIAL_BASE`
- **ui-configmap.yaml**: `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_APP_VERSION`, `API_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_ENABLE_ANALYTICS`, `NEXT_PUBLIC_ENABLE_FEEDBACK`

### Secrets (sensitive)

Sensitive values are injected at install time by `install.sh` via `${VARIABLE}` placeholders in `install.yaml`:

- LLM API keys (OpenAI, Anthropic, Azure, Gemini, Groq, etc.)
- `JWT_SECRET`
- `POSTGRES_DATABASE_URL`, `CHECKPOINTER_DATABASE_URL`
- PostgreSQL credentials

## Security

- All application containers run as non-root user (`skyflo`, UID 1002)
- All capabilities dropped, `allowPrivilegeEscalation: false`
- **NetworkPolicy**: MCP ingress restricted to Engine pods only (all egress allowed)
- Controller uses distroless nonroot runtime image
- Sensitive values stored in Kubernetes Secrets (not ConfigMaps)

## Resource Limits

| Service    | CPU request | CPU limit | Memory request | Memory limit |
|------------|-------------|-----------|----------------|--------------|
| Engine     | 200m        | 1         | 512Mi          | 1Gi          |
| MCP        | 200m        | 1         | 512Mi          | 1Gi          |
| UI         | 100m        | 500m      | 256Mi          | 512Mi        |
| Proxy      | 100m        | 200m      | 128Mi          | 256Mi        |
| Controller | 100m        | 500m      | 64Mi           | 128Mi        |
| PostgreSQL | 200m        | 1         | 512Mi          | 1Gi          |
| Redis      | 100m        | 500m      | 256Mi          | 512Mi        |

## Persistent Storage

| StatefulSet | Volume         | Size | Mount Path                        |
|-------------|----------------|------|-----------------------------------|
| PostgreSQL  | `postgres-data`| 5Gi  | `/var/lib/postgresql/data`        |
| Redis       | `redis-data`   | 1Gi  | `/data`                           |
