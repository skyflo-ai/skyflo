<p align="center">
  <a href="https://skyflo.ai">
    <img src="https://skyflo.ai/assets/hero.png" alt="Skyflo – Self-Hosted AI Agent for Kubernetes and CI/CD" width="1000"/>
  </a>
</p>

<h3 align="center">Self-Hosted AI Agent for Kubernetes & CI/CD</h3>

<p align="center">
  <a href="https://github.com/skyflo-ai/skyflo/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/skyflo-ai/skyflo/ci.yml?branch=main&label=CI" alt="CI Status">
  </a>&nbsp;
  <a href="https://github.com/skyflo-ai/skyflo/releases">
    <img src="https://img.shields.io/github/v/release/skyflo-ai/skyflo" alt="Release">
  </a>&nbsp;
  <a href="https://github.com/skyflo-ai/skyflo/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/skyflo-ai/skyflo" alt="License">
  </a>
</p>

<p align="center">
  <a href="https://skyflo.ai/docs">Docs</a> ·
  <a href="https://skyflo.ai/docs/architecture">Architecture</a> ·
  <a href="https://discord.gg/kCFNavMund">Discord</a>
</p>

---

Infrastructure automation tools fall into two categories.

CLI assistants translate prompts into shell commands.
Autonomous agents execute infrastructure changes without explicit approval.

Neither model guarantees a deterministic execution process or a complete audit trail.

Skyflo is a **self-hosted AI agent for Kubernetes and CI/CD systems**. It runs inside your cluster and executes infrastructure operations through a deterministic control loop:

**Plan → Approve → Execute → Verify**

> Every mutating tool call is approval-gated, typed, and auditable.

Skyflo is not a CLI wrapper, not an autonomous mutation bot, and not a GitOps control plane.

It is an **in-cluster AI control layer** that enforces safe infrastructure changes before anything reaches production.

---

### Quick Start

Install Skyflo inside your Kubernetes cluster.

#### Using `Helm`:

```bash
helm repo add skyflo https://charts.skyflo.ai
helm repo update skyflo
```

Create a `values.yaml` file:

```yaml
engine:
  secrets:
    llmModel: "gemini/gemini-2.5-pro"
    geminiApiKey: "AI-..."
```

See `helm show values skyflo/skyflo` for the full list of configurable values.

```bash
helm install skyflo skyflo/skyflo -n skyflo --create-namespace -f values.yaml
```

#### Using `curl`:

Get started quickly with the interactive installer.

```bash
curl -fsSL https://skyflo.ai/install.sh | bash
```

Bring your own LLM (OpenAI, Anthropic, Gemini, Groq, self-hosted). See the [quick start](https://skyflo.ai/docs/quick-start) guide.

---

### Execution Model

Skyflo enforces a strict loop for every infrastructure change:

1. **Plan**: generate a concrete, replayable plan
2. **Approve**: explicit approval for every mutating tool call
3. **Execute**: run typed tools via MCP (Kubernetes, Helm, Argo Rollouts, Jenkins)
4. **Verify**: validate cluster state against declared intent
5. **Persist**: store tool-level audit history

No blind `kubectl apply`. No silent automation. No untracked changes.

---

### Safety Properties

* Approval gate for every mutating tool call, enforced by the engine
* Typed tool execution with schema-validated inputs
* Persisted audit trail with tool results
* Replayable control loop (plan → approve → execute → verify)
* Runs inside your cluster. No Skyflo telemetry or phone-home
* LLM-agnostic via LiteLLM. No vendor lock-in

---

### Supported Tools

| Tool              | Capabilities                                                                     |
| ----------------- | -------------------------------------------------------------------------------- |
| **Kubernetes**    | discovery, get/describe, logs/exec, diff-first apply, rollout history, rollbacks |
| **Helm**          | template, install/upgrade/rollback, dry-run, diff-first safety                   |
| **Argo Rollouts** | status, pause/resume, promote/cancel, progressive delivery control               |
| **Jenkins**       | jobs/builds/logs, parameters, SCM context, build control                         |

All mutating tool calls require explicit approval.

---

### Demo

<p align="center">
  <img src="assets/demo.gif" alt="Skyflo Demo" width="100%"/>
</p>

Deterministic plans. Explicit approval. Verified execution.

---

### Comparison

| Capability                    | CLI Assistants | Autonomous Agents | GitOps Platforms | **Skyflo** |
| ----------------------------- | -------------: | ----------------: | ---------------: | ---------: |
| Natural language ops          |            Yes |               Yes |          Limited |        Yes |
| Mandatory mutation approval   |       Optional |                No |         PR-based |        Yes |
| Deterministic control loop    |             No |                No |          Partial |        Yes |
| Kubernetes + CI unified       |             No |           Partial |               No |        Yes |
| In-cluster deployment         |        Partial |           Partial |           Varies |        Yes |
| Team RBAC + audit             |             No |           Limited |              Yes |        Yes |
| Real-time execution streaming |             No |                No |               No |        Yes |

---

### System Architecture

| Component                | Description                                                                  |
| ------------------------ | ---------------------------------------------------------------------------- |
| [**Engine**](engine)     | LangGraph workflow: planner, approval gate, verifier, persistence, auth/RBAC |
| [**MCP Server**](mcp)    | Typed tools for Kubernetes, Helm, Argo Rollouts, Jenkins                     |
| [**Command Center**](ui) | Next.js UI with real-time streaming, approvals, team admin                   |

Details: [Architecture](https://skyflo.ai/docs/architecture)

---

### Contributing

Apache 2.0 OSS. High-signal contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

### License

Apache 2.0. See [LICENSE](LICENSE).

---

### Community

<p>
  <a href="https://skyflo.ai/docs">Docs</a> ·
  <a href="https://discord.gg/kCFNavMund">Discord</a> ·
  <a href="https://x.com/skyflo_ai">X</a> ·
  <a href="https://www.linkedin.com/company/skyflo">LinkedIn</a>
</p>