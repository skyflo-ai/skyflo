# Unleash Skyflo.ai

This guide will help you deploy Skyflo.ai in minutes, whether you're experimenting locally or deploying in production.

## Prerequisites

### For Local Development
- Docker
- KinD (Kubernetes in Docker)
- kubectl command-line tool
- gettext (for envsubst)
- curl

### For Production
- Access to a Kubernetes cluster (v1.19+)
- kubectl command-line tool
- gettext (for envsubst)
- curl

Skyflo supports multiple LLM providers through environment variables:

1. **API Keys**: Set provider-specific API keys:

```env
OPENAI_API_KEY=sk-...     # For OpenAI models
GROQ_API_KEY=gsk-...      # For Groq models
ANTHROPIC_API_KEY=sk-...  # For Anthropic models
```

2. **Model Selection**: Set `LLM_MODEL` to specify the model:

```env
LLM_MODEL=gpt-4o  # OpenAI (default)
# Or for other providers:
# LLM_MODEL=groq/llama-3-70b-versatile
# LLM_MODEL=anthropic/claude-3-sonnet
```

3. **Self-hosted Models**: For Ollama or other self-hosted models, set:

```env
LLM_HOST=http://your-model-host:port
```

> _We recommend using `gpt-4o` by OpenAI as the LLM provider_

## Installation Options

Skyflo.ai offers two deployment options:

### 1. Production Deployment

For deploying Skyflo.ai in a production environment:

```bash
curl -sL https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.sh -o install.sh && chmod +x install.sh && ./install.sh
```

Optional environment variables for production:
```bash
export JWT_SECRET='your-custom-jwt-secret'  # Auto-generated if not provided
export POSTGRES_DATABASE_URL='your-postgres-url'  # Default: postgres://skyflo:skyflo@skyflo-ai-postgres:5432/skyflo
export REDIS_HOST='your-redis-host:port'  # Default: skyflo-ai-redis:6379
```

#### Production Setup - AWS

1. Apply the following Ingress configuration (adjust the values according to your AWS setup):

```yaml
# skyflo-ai-ingress.yaml

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: skyflo-ai-ingress
  namespace: skyflo-ai
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/subnets: subnet-xxxxx, subnet-yyyyy  # Replace with your subnet IDs
    alb.ingress.kubernetes.io/security-groups: sg-xxxxx  # Replace with your security group ID
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxxxx  # Replace with your SSL cert ARN
    alb.ingress.kubernetes.io/target-type: instance
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80,"HTTPS": 443}]'
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/ssl-redirect: "443"
spec:
  ingressClassName: alb
  rules:
  - host: your-domain.com  # Replace with your domain
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: skyflo-ai-ui
            port:
              number: 80
```

Apply the configuration:
```bash
kubectl apply -f skyflo-ai-ingress.yaml
```

2. After applying the configuration, the AWS Load Balancer Controller will provision an Application Load Balancer. Get the ALB DNS name:
```bash
kubectl get ingress -n skyflo-ai
```

3. Configure your DNS provider to point your domain to the ALB DNS name using a CNAME record.


### 2. Local Development with KinD
Perfect for development, testing, and exploring Skyflo.ai features in a local environment:

1. Create the KinD cluster
```bash
kind create cluster --config deployment/local.kind.yaml 
```
2. Configure secrets and runtime defaults (all variables used by deployment/local.install.yaml, mirroring the logic in deployment/install.sh)

```bash
export NAMESPACE=skyflo-ai
export LLM_MODEL=openai/gpt-4o                # pick any provider/model pair
export OPENAI_API_KEY=sk-your-key             # or GROQ_API_KEY/ANTHROPIC_API_KEY/etc.
export JWT_SECRET=$(openssl rand -base64 32)
export POSTGRES_DATABASE_URL=postgres://skyflo:skyflo@skyflo-ai-postgres:5432/skyflo
export REDIS_URL=redis://skyflo-ai-redis:6379/0
export MCP_SERVER_URL=http://skyflo-ai-mcp:8081
export INTEGRATIONS_SECRET_NAMESPACE=$NAMESPACE
```
> Set any additional provider keys from `deployment/local.install.yaml` if you plan to use them (e.g., `GROQ_API_KEY`, `GEMINI_API_KEY`, `HF_TOKEN`, etc.).

3. Apply the local manifest

```bash
envsubst < deployment/local.install.yaml | kubectl apply -f -
```
4. Port-forward the UI service and open the app

```bash
kubectl port-forward svc/skyflo-ai-ui -n $NAMESPACE 30080:80
```

The Skyflo UI will now be available on your localhost:
> `http://localhost:30080`

Follow `deployment/README.md` for building the Docker images locally and loading them into the KinD cluster via `kind load docker-image`.

## Verifying the Installation

Check the status of your deployment:
```bash
kubectl get pods -n skyflo-ai
```


## Uninstalling

To remove Skyflo.ai and all its components:

```bash
curl -sL https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/uninstall.sh -o uninstall.sh && chmod +x uninstall.sh && ./uninstall.sh
```



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
- If pods are stuck in "Pending" state, check your cluster's resources
- For "ImagePullBackOff", verify your container registry access
- For connection issues, ensure all services are running and properly configured

## Need Help?

Join our [Discord community](https://discord.gg/kCFNavMund) for support and discussions.
