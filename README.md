# Skyflo.ai - AI Agent for Cloud Native

<p align="center">
  <img src="./assets/readme.png" alt="Skyflo.ai" width="1000"/>
</p>

<div align="center">

  [![Website](https://img.shields.io/badge/Website-Visit-blue.svg)](https://skyflo.ai)
  [![Discord](https://img.shields.io/badge/Discord-Join-blue.svg)](https://discord.gg/kCFNavMund)
  [![Twitter/X Follow](https://img.shields.io/twitter/follow/skyflo_ai?style=social)](https://x.com/skyflo_ai)
  [![YouTube Channel](https://img.shields.io/badge/YouTube-Subscribe-red.svg)](https://www.youtube.com/@SkyfloAI)

</div>

Skyflo.ai is your AI co-pilot for Cloud & DevOps that unifies Kubernetes operations and CI/CD systems (starting with Jenkins) through natural language with a safety-first, human-in-the-loop design.

## How to Install

Skyflo.ai offers flexible deployment options, accommodating both production and local Kubernetes environments:

```bash
curl -sL https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.sh -o install.sh && chmod +x install.sh && ./install.sh
```

Skyflo can be configured to use different LLM providers (like OpenAI, Anthropic, Gemini, Groq, etc.), or even use a self-hosted model.

For more details, see the [Installation Guide](docs/install.md).

## Supported Tools

Skyflo.ai executes Cloud & DevOps operations through standardized tools and integrations:

* **Kubernetes**: Resource discovery; get/describe; logs/exec; **safe apply/diff** flows.
* **Argo Rollouts**: Inspect status; pause/resume; promote/cancel; analyze progressive delivery.
* **Helm**: Search, install/upgrade/rollback with dry-run and diff-first safety.
* **Jenkins (new)**: Jobs, builds, logs, SCM, identity—**secure auth & CSRF handling**, integration-aware tool filtering, and automatic parameter injection from configured credentials.

Write/mutating operations require explicit approval from the user.

## Architecture

Read more about the architecture of Skyflo.ai in the [Architecture](docs/architecture.md) documentation.

## Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details on getting started.

## Code of Conduct

We have a [Code of Conduct](CODE_OF_CONDUCT.md) that we ask all contributors to follow.

## Community

- [Discord](https://discord.gg/kCFNavMund)
- [Twitter/X](https://x.com/skyflo_ai)
- [YouTube](https://www.youtube.com/@SkyfloAI)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
