# Legacy Kubernetes agent deprecation

As of October 2, 2026, the open source Skyflo agent in this repository is deprecated. It is the legacy self-hosted Kubernetes and CI/CD agent, separate from the current Skyflo product.

## Current Skyflo

Skyflo is now the control plane for agentic engineering: a local-first mission operating layer that coordinates coding agents, models, repositories, and tools through governed missions. Explore the current product at [skyflo.ai](https://skyflo.ai).

The current product is not an in-place upgrade of this agent. Do not treat the old Helm charts, container images, installer, or configuration as installation instructions for Skyflo Desktop.

## Existing deployments

Do not use this deprecated agent for new production deployments. The source, deployment assets, and historical instructions remain available for reference and existing operators.

This deprecation notice does not change running installations or delete cluster resources. Review your existing deployment and follow your own change-control process before upgrading, removing, or replacing it. There is no automatic migration from the legacy agent to the current product.

## Repository status

The [legacy project reference](LEGACY.md) preserves the earlier feature, architecture, and installation documentation. The repository documents the legacy project. Its installation and contribution guides should be read in that context. Deprecation does not change the Apache 2.0 license or existing trademark terms.

For questions about the current Skyflo product, use [Contact](https://skyflo.ai/contact).
