# Skyflo Deployment

## Local Development with KinD

## Prerequisites

- Docker
- KinD
- kubectl

## Configuration Defaults

Non-sensitive defaults are provided via per-service ConfigMaps (Engine, MCP, and UI).
Sensitive values (API keys, JWT secret, database URLs) are runtime-only and are
expected to be supplied during installation via `install.sh`. This is a
temporary model until a secure UI-based installer provisions Kubernetes Secrets.

## Setup KinD Cluster

```bash
kind create cluster --name skyflo-ai --config deployment/local.kind.yaml
```

## Build the Docker Images

```bash
# Build the Engine image
docker buildx build -f deployment/engine/Dockerfile -t skyfloaiagent/engine:latest .

# Build the MCP image
docker buildx build -f deployment/mcp/Dockerfile -t skyfloaiagent/mcp:latest .

# Build the UI image
docker buildx build -f deployment/ui/Dockerfile -t skyfloaiagent/ui:latest .

# Build the Kubernetes Controller image
docker buildx build -f deployment/kubernetes-controller/Dockerfile -t skyfloaiagent/controller:latest .

# Build the Proxy image
docker buildx build -f deployment/ui/proxy.Dockerfile -t skyfloaiagent/proxy:latest .
```

## Load the built images into the KinD cluster
```bash
kind load docker-image --name skyflo-ai skyfloaiagent/ui:latest

kind load docker-image --name skyflo-ai skyfloaiagent/engine:latest

kind load docker-image --name skyflo-ai skyfloaiagent/mcp:latest

kind load docker-image --name skyflo-ai skyfloaiagent/controller:latest

kind load docker-image --name skyflo-ai skyfloaiagent/proxy:latest
```

## Install the Controller and Resources

```bash
k delete -f local.install.yaml
k apply -f local.install.yaml
```

## How to test

The Nginx deployment contains an incorrect image tag. This is a good basic test to see if the Sky AI agent catches the error and fixes it.

```bash
k apply -f local.test-deploy.yaml

k delete -f local.test-deploy.yaml
```