# Skyflo.ai - AI Agent for Cloud & DevOps

<p align="center">
  <img src="./assets/readme.png" alt="Skyflo.ai" width="1000"/>
</p>

Skyflo.ai is your AI co-pilot for Cloud & DevOps that unifies Kubernetes operations and CI/CD systems (starting with Jenkins) through natural language with a safety-first, human-in-the-loop design.

## ⚡ Quick Start

Install Skyflo.ai in your Kubernetes cluster using a single command:

```bash
curl -sL https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.sh -o install.sh && chmod +x install.sh && ./install.sh
```

Skyflo can be configured to use different LLM providers (like OpenAI, Anthropic, Gemini, Groq, etc.), or even use a self-hosted model.

See the [Installation Guide](https://github.com/skyflo-ai/skyflo/blob/main/docs/install.md) for details.

## 🚀 Key Features

- **Unified AI Copilot**: One agent for K8s, Jenkins, Helm, and Argo Rollouts
- **Human-in-the-loop Design**: Approval required for any mutating operation
- **Plan → Execute → Verify**: Iterative loop where the agent keeps going untill the task is done 
- **Real-time Streaming**: Everything that the agent does is streamed to the UI in real time
- **MCP-based tool execution**: Standardized tools for safe, consistent actions
- **Built for Teams**: Manage teams, integrations, rate limiting and much more

## 🛠️ Supported Tools

Skyflo.ai executes Cloud & DevOps operations through standardized tools and integrations:

* **Kubernetes**: Resource discovery; get/describe; logs/exec; **safe apply/diff** flows.
* **Argo Rollouts**: Inspect status; pause/resume; promote/cancel; analyze progressive delivery.
* **Helm**: Search, install/upgrade/rollback with dry-run and diff-first safety.
* **Jenkins (new)**: Jobs, builds, logs, SCM, identity—**secure auth & CSRF handling**, integration-aware tool filtering, and automatic parameter injection from configured credentials.

Write/mutating operations require explicit approval from the user.

## 🎯 Who is Skyflo.ai for?

Skyflo.ai is purpose-built for:

- **DevOps Engineers**
- **Cloud Architects**
- **IT Managers**
- **SRE Teams**
- **Security Professionals**

## 🏗️ Architecture

Read more about the architecture of Skyflo.ai in the [Architecture](docs/architecture.md) documentation.

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details on getting started.

## 📜 Code of Conduct

We have a [Code of Conduct](CODE_OF_CONDUCT.md) that we ask all contributors to follow.

## 🌐 Community

- [Discord](https://discord.gg/kCFNavMund)
- [Twitter/X](https://x.com/skyflo_ai)
- [YouTube](https://www.youtube.com/@SkyfloAI)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)

## 📄 License

Skyflo.ai is open source and licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).