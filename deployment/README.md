# Skyflo Deployment

## Local Development with KinD

## Prerequisites

- Docker
- KinD
- kubectl

## Setup KinD Cluster

```bash
kind create cluster --name skyfloai --config local.kind.yml
```

## Build the Docker Images

```bash
# Build the Engine image
docker buildx build -f deployment/engine/Dockerfile -t skyfloai/engine:latest .

# Build the MCP image
docker buildx build -f deployment/mcp/Dockerfile -t skyfloai/mcp:latest .

# Build the UI image
docker buildx build -f deployment/ui/Dockerfile -t skyfloai/ui:latest .

# Build the Kubernetes Controller image
docker buildx build -f deployment/kubernetes-controller/Dockerfile -t skyfloai/controller:latest .

# Build the Proxy image
docker buildx build -f deployment/proxy/Dockerfile -t skyfloai/proxy:latest .
```

## Load the built images into the KinD cluster
```bash
kind load docker-image --name skyfloai skyfloai/ui:latest

kind load docker-image --name skyfloai skyfloai/engine:latest

kind load docker-image --name skyfloai skyfloai/mcp:latest

kind load docker-image --name skyfloai skyfloai/controller:latest

kind load docker-image --name skyfloai skyfloai/proxy:latest
```

## Install the Controller and Resources

```bash
k apply -f local.install.yaml
```

## How to test

The Nginx deployment contains an incorrect image tag. This is a good basic test to see if the Sky AI agent catches the error and fixes it.

```bash
k apply -f local.test-deploy.yaml

k delete -f local.test-deploy.yaml
```