# Skyflo Deployment

This directory contains Docker configurations for deploying Skyflo components.

## Prerequisites

- Docker
- KinD
- kubectl

## Setup KinD Cluster

```bash
kind create cluster --name skyfloai --config kind.yml
```

## Build the Docker Images

```bash
# Build the Kubernetes Controller image
docker buildx build -f deployment/controller.Dockerfile -t skyfloai/controller:latest .

# Build the UI image
docker buildx build -f deployment/ui.Dockerfile -t skyfloai/ui:latest .

# Build the API image
docker buildx build -f deployment/engine.Dockerfile -t skyfloai/engine:latest .

# Build the Engine image
docker buildx build -f deployment/mcp.Dockerfile -t skyfloai/mcp:latest .
```

## Load the built images into the KinD cluster
```bash
kind load docker-image --name skyfloai skyfloai/ui:latest skyfloai/engine:latest skyfloai/mcp:latest skyfloai/controller:latest
```

## Install the Controller and Resources

```bash
k apply -f install.yaml
```
