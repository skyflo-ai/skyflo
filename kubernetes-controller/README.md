# Skyflo.ai Kubernetes Controller

[![Go Version](https://img.shields.io/badge/Go-1.24.1-blue)](https://golang.org/dl/)

## Overview

The Skyflo.ai Kubernetes Controller is a robust operator designed to facilitate the deployment, configuration, and management of the Skyflo.ai platform within Kubernetes environments. By leveraging a single Custom Resource Definition (CRD), the controller streamlines the orchestration of Skyflo.ai's components, ensuring efficient and secure operations.

## Architecture

The controller is developed in Go and built using the Kubebuilder framework with controller-runtime library, adhering to Kubernetes operator best practices. It introduces a singular CRD to manage the Skyflo.ai deployment, encompassing the UI, Engine, and MCP components.

### Custom Resource Definition (CRD)

- **SkyfloAI** (`skyfloais.skyflo.ai`):
  - **Spec Fields** (Required: ui, engine, mcp):
    - `ui`: Configuration parameters for the Skyflo.ai UI component.
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
    - `mcp`: Parameters governing the MCP component.
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
    - `uiStatus`: Current status of the UI component.
    - `engineStatus`: Status of the Engine component.
    - `mcpStatus`: Status of the MCP component.
    - `conditions`: Overall conditions and health indicators of the Skyflo.ai deployment.

### Controller Components

- **Controller Manager**:
  - Watches for changes to the `SkyfloAI` custom resource.
  - Reconciles the desired state by managing Deployments, Services, and other Kubernetes resources.
  - Provides metrics endpoint for monitoring (`:8080`)
  - Implements health probes for liveness and readiness (`:8081`)
  - Supports leader election for high availability
- **RBAC Management**:
  - Ensures the MCP component has the necessary permissions to interact with cluster resources.
  - Configures Role-Based Access Control (RBAC) policies based on the specified access level.
  - Implements cluster-admin role binding for MCP service account

### Deployment Model

- **Namespace Isolation**:
  - All Skyflo.ai components are deployed within the `skyflo-ai` namespace
  - Network policies controlling inter-component communication
- **Standard Kubernetes Resources**:
  - UI Deployment with NodePort service (30080)
  - API Service Deployment with associated service
  - MCP Deployment with NodePort service (30081)
  - StatefulSets for Redis and PostgreSQL with persistent storage
- **Security Model**:
  - Non-root container execution with specific UIDs
  - Restricted capabilities and privilege escalation controls
  - Secure inter-service communication through network policies

## Features

- **Unified Deployment**:
  - Simplifies the deployment process by managing all Skyflo.ai components through a single custom resource.
  - Integrated database and cache management with PostgreSQL and Redis
- **Dynamic Configuration**:
  - Supports on-the-fly updates to component configurations, scaling, and resource allocations.
  - Environment variable customization for all components
  - Configurable resource requests and limits
- **Secure Cluster Interaction**:
  - Provides configurable access levels for the MCP component through RBAC
  - Network policies controlling pod-to-pod communication
  - Non-root security model with minimal container capabilities
- **Resource Efficiency**:
  - Utilizes standard Kubernetes resources where appropriate
  - Built-in monitoring through metrics endpoint
  - Health checking capabilities for all components
  - Persistent storage for stateful components

## Prerequisites

- Docker
- KinD (Kubernetes In Docker)
- kubectl
- helm (optional, for Helm-based installation)

## Development

Refer to the [Local Development](../deployment/README.md) guide for more information.

### Code Structure

- **`api/v1/skyfloai_types.go`**:
  - Defines the `SkyfloAI` custom resource schema.
- **`controllers/skyfloai_controller.go`**:
  - Implements the reconciliation logic for managing Skyflo.ai components.
- **`config/`**:
  - Contains Kubernetes manifests for CRDs, RBAC, and sample resources.

## Community and Support

- [Website](https://skyflo.ai)
- [Discord Community](https://discord.gg/kCFNavMund)
- [Twitter/X Updates](https://x.com/skyflo_ai)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)




