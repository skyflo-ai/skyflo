# Skyflo Kubernetes Controller

[![Go Version](https://img.shields.io/badge/Go-1.24.1-blue)](https://golang.org/dl/)

Kubernetes operator that manages the Skyflo platform lifecycle through a single Custom Resource Definition (CRD). It handles deployment, configuration, and scaling of all Skyflo components (Engine, MCP, Command Center) within a Kubernetes cluster.

See [docs/architecture.md](../docs/architecture.md) for full system context.

## Architecture

Built in Go using Kubebuilder and controller-runtime. The controller introduces a single CRD (`SkyfloAI`) to manage the entire Skyflo deployment.

### Custom Resource Definition

- **SkyfloAI** (`skyfloais.skyflo.ai`):
  - **Spec Fields** (Required: ui, engine, mcp):
    - `ui`: Configuration for the Command Center.
      - image (required)
      - replicas
      - resources
      - env variables
    - `engine`: Settings for the Engine component.
      - image (required)
      - replicas
      - resources
      - databaseConfig (PostgreSQL configuration)
      - redisConfig (Redis configuration)
      - env variables
    - `mcp`: Parameters for the MCP server.
      - image (required)
      - replicas
      - resources
      - kubeconfigSecret
      - env variables
    - `imagePullSecrets`: Secrets for pulling images from private registries.
    - `nodeSelector`: Node selection constraints for scheduling pods.
    - `tolerations`: Tolerations for scheduling pods on tainted nodes.
    - `affinity`: Affinity rules for pod scheduling.
  - **Status Fields**:
    - `uiStatus`: Current status of the Command Center.
    - `engineStatus`: Status of the Engine component.
    - `mcpStatus`: Status of the MCP component.
    - `conditions`: Overall conditions and health indicators.

### Controller Manager

- Watches for changes to the `SkyfloAI` custom resource
- Reconciles the desired state by managing Deployments, Services, and other Kubernetes resources
- Metrics endpoint for monitoring (`:8080`)
- Health probes for liveness and readiness (`:8081`)
- Leader election support for high availability

### RBAC

- Configures Role-Based Access Control policies based on the specified access level
- Ensures the MCP component has necessary permissions to interact with cluster resources
- Implements cluster-admin role binding for MCP service account

### Deployment Model

- **Namespace Isolation**: all Skyflo components deployed within the `skyflo-ai` namespace with network policies controlling inter-component communication
- **Standard Kubernetes Resources**:
  - UI Deployment with NodePort service (30080)
  - API Service Deployment with associated service
  - MCP Deployment with NodePort service (30081)
  - StatefulSets for Redis and PostgreSQL with persistent storage
- **Security**:
  - Non-root container execution with specific UIDs
  - Restricted capabilities and privilege escalation controls
  - Network policies for inter-service communication

## Prerequisites

- Docker
- KinD (Kubernetes In Docker)
- kubectl
- Helm (optional)

## Development

Refer to the [deployment guide](../deployment/README.md) for local development setup.

### Code Structure

- **`api/v1/skyfloai_types.go`**: Defines the `SkyfloAI` custom resource schema.
- **`controllers/skyfloai_controller.go`**: Reconciliation logic for managing Skyflo components.
- **`config/`**: Kubernetes manifests for CRDs, RBAC, and sample resources.

## Community

- [Website](https://skyflo.ai)
- [Discord](https://discord.gg/kCFNavMund)
- [X](https://x.com/skyflo_ai)
- [LinkedIn](https://www.linkedin.com/company/skyflo)
