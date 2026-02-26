# Installing Skyflo on Kubernetes

Deploy Skyflo to any Kubernetes cluster with a single command. The interactive installer provisions all resources, configures your LLM provider, and generates secrets automatically.

```bash
curl -sL https://skyflo.ai/install.sh | bash
```

You will be prompted for:

1. **Target namespace** (default: `skyflo-ai`)
2. **LLM model** in `provider/model` format (e.g. `openai/gpt-4o`, `anthropic/claude-sonnet-4-6`)
3. **Provider API key**
4. **Self-hosted LLM endpoint** (if applicable)

Secrets, database credentials, and internal service URLs are generated automatically.

## Verify

```bash
kubectl get pods -n skyflo-ai
```

All pods should reach `Running` status. The Engine waits for PostgreSQL and Redis to become healthy before starting.

## Ingress

Expose Skyflo through an Ingress resource. The manifest below is cloud-agnostic. Add provider-specific annotations for your environment.

1. Create the Ingress manifest:

```yaml
# skyflo-ai-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: skyflo-ai-ingress
  namespace: skyflo-ai
  annotations:
    # Add cloud-specific annotations below
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - your-domain.com
    secretName: skyflo-ai-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: skyflo-ai-ui
            port:
              number: 80
```

<details>
<summary>AWS ALB</summary>

```yaml
metadata:
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/subnets: subnet-xxxxx, subnet-yyyyy
    alb.ingress.kubernetes.io/security-groups: sg-xxxxx
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxxxx
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80,"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
spec:
  ingressClassName: alb
```

</details>

<details>
<summary>GCP Cloud Load Balancer</summary>

```yaml
metadata:
  annotations:
    kubernetes.io/ingress.class: gce
    networking.gke.io/managed-certificates: skyflo-ai-cert
    kubernetes.io/ingress.global-static-ip-name: skyflo-ai-ip
spec:
  ingressClassName: gce
```

</details>

<details>
<summary>Azure Application Gateway</summary>

```yaml
metadata:
  annotations:
    kubernetes.io/ingress.class: azure/application-gateway
    appgw.ingress.kubernetes.io/ssl-redirect: "true"
    appgw.ingress.kubernetes.io/backend-protocol: "http"
spec:
  ingressClassName: azure-application-gateway
```

</details>

2. Apply:

```bash
kubectl apply -f skyflo-ai-ingress.yaml
```

3. Retrieve the external address:

```bash
kubectl get ingress -n skyflo-ai
```

4. Point your domain to the load balancer address via DNS (CNAME for hostname, A record for IP).

---

## Reference

### Prerequisites

The installer validates these automatically.

- Kubernetes cluster (v1.19+)
- kubectl
- gettext (for `envsubst`)
- curl
- openssl

### Version Pinning

```bash
VERSION=v0.5.0 bash <(curl -sL https://skyflo.ai/install.sh)
```

### Deployed Resources

| Resource | Description |
|----------|-------------|
| Engine Deployment | FastAPI backend with LangGraph agent (port 8080) |
| MCP Deployment | FastMCP tool server with kubectl, Helm, Argo, Jenkins (port 8888) |
| UI Deployment | Next.js frontend with Nginx proxy sidecar (port 80) |
| Controller Deployment | Kubernetes operator for SkyfloAI CRD (Go) |
| PostgreSQL StatefulSet | Primary database with 5Gi persistent volume |
| Redis StatefulSet | Pub/sub, rate limiting, stop signals with 1Gi volume |
| ConfigMaps | Non-sensitive configuration for Engine, MCP, and UI |
| Secrets | JWT secret, database URLs, LLM API keys |
| NetworkPolicy | Restricts MCP ingress to Engine pods only |
| RBAC | ServiceAccounts, ClusterRole, ClusterRoleBinding |
| CRD | `skyfloais.skyflo.ai` custom resource definition |

### Generated Values

The following are created automatically unless pre-set as environment variables:

| Variable | Default |
|----------|---------|
| `JWT_SECRET` | Random 32-byte base64 |
| `POSTGRES_PASSWORD` | Random URL-safe string |
| `POSTGRES_DATABASE_URL` | In-cluster PostgreSQL |
| `REDIS_URL` | `redis://skyflo-ai-redis:6379/0` |
| `MCP_SERVER_URL` | `http://skyflo-ai-mcp:8888/mcp` |

### LLM Configuration

The installer configures your LLM provider interactively. Use the reference below to pre-set values as environment variables or to modify the configuration after installation.

#### Supported Models

Set `LLM_MODEL` using `provider/model` format:

```env
LLM_MODEL=gemini/gemini-2.5-pro       # Gemini (recommended)
LLM_MODEL=moonshot/kimi-k2.5          # Moonshot
LLM_MODEL=deepseek/deepseek-reasoner  # Deepseek
LLM_MODEL=groq/openai/gpt-oss-120b    # Groq
LLM_MODEL=anthropic/claude-sonnet-4-6 # Anthropic
LLM_MODEL=openai/gpt-5.3-codex        # OpenAI
LLM_MODEL=ollama/llama3.1:8b          # Ollama (self-hosted)
```

Skyflo connects to LLM providers through LiteLLM. See the full [list of supported models](https://models.litellm.ai/).

#### API Keys

```env
ANTHROPIC_API_KEY=sk-...    # Anthropic
MOONSHOT_API_KEY=sk-...     # Moonshot
DEEPSEEK_API_KEY=sk-...     # Deepseek
GROQ_API_KEY=gsk-...        # Groq
GEMINI_API_KEY=AI-...       # Gemini
OPENAI_API_KEY=sk-...       # OpenAI
```

Additional providers: AWS Bedrock, HuggingFace, Databricks, Fireworks AI, Together AI, NVIDIA NIM, Perplexity, xAI, and others.

#### Self-hosted Models

For Ollama or other self-hosted endpoints:

```env
LLM_HOST=http://your-model-host:port
```

#### Reasoning Models

Skyflo auto-detects reasoning capabilities using LiteLLM's model registry. Models with native reasoning support (OpenAI o-series, Anthropic Claude with extended thinking, DeepSeek-R1) are enabled automatically at `high` effort. The reasoning process streams to the UI in collapsible thinking blocks.

Setting `LLM_REASONING_EFFORT` to `high` yields the best results with Skyflo.

To override defaults, set these environment variables on the Engine:

```env
LLM_REASONING_EFFORT=high              # low, medium, high
LLM_THINKING_BUDGET_TOKENS=10000       # Anthropic-specific
LLM_MAX_TOKENS=16384                   # Max tokens when thinking is enabled
```

### Building from Source

See [deployment/README.md](../deployment/README.md).

## Uninstalling

```bash
curl -sL https://skyflo.ai/uninstall.sh | bash
```

Pin a specific version:

```bash
VERSION=<version> bash <(curl -sL https://skyflo.ai/uninstall.sh)
```

The uninstaller prompts for the target namespace and whether to delete persistent volume claims. Confirming deletion permanently removes all PostgreSQL and Redis data.

## Troubleshooting

1. Check pod status:

```bash
kubectl get pods -n skyflo-ai
kubectl describe pod <pod-name> -n skyflo-ai
```

2. View logs:

```bash
kubectl logs <pod-name> -n skyflo-ai
```

3. Common issues:
- Pods stuck in `Pending`: insufficient cluster resources
- `ImagePullBackOff`: verify container registry access and image tags
- Engine not starting: confirm PostgreSQL and Redis pods are healthy
- Connection failures: verify services with `kubectl get svc -n skyflo-ai`

## Community

- [Discord](https://discord.gg/kCFNavMund)
- [Website](https://skyflo.ai)
