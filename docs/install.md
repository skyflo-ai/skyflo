# Unleash Skyflo.ai

Welcome to the future of cloud orchestration. This guide will help you deploy Skyflo.ai in minutes, whether you're experimenting locally or deploying in production.

## What You'll Need

- Kubernetes cluster (v1.19+)
- kubectl command-line tool
- An OpenAI API key

## Zero-to-Cloud Deployment

Transform your infrastructure with a single command:

```bash
curl -sL https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.sh | OPENAI_API_KEY='your-openai-api-key' bash
```

### Experience the Interface

#### Development Mode

Quick access for local innovation:

```bash
# UI access
kubectl port-forward -n skyflo-ai svc/skyflo-ai-ui 3000:3000

# API access
kubectl port-forward -n skyflo-ai svc/skyflo-ai-engine 8080:8080
```

Navigate to `http://localhost:3000` and dive in.

#### Production Setup - AWS

1. Apply the following Ingress configuration (adjust the values according to your AWS setup):

```yaml
# skyflo-ingress.yaml

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: skyflo-ingress
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
              number: 3000
      - path: /api/*
        pathType: ImplementationSpecific
        backend:
          service:
            name: skyflo-ai-engine
            port:
              number: 8080
```

Apply the configuration:

```bash
kubectl apply -f skyflo-ingress.yaml
```

2. After applying the configuration, the AWS Load Balancer Controller will provision an Application Load Balancer. You can get the ALB DNS name using:

```bash
kubectl get ingress -n skyflo-ai
```

3. Configure your DNS provider to point your domain to the ALB DNS name using a CNAME record.

## Clean Slate

```bash
kubectl delete namespace skyflo-ai
```

## Local Sandbox with KinD

Want to explore Skyflo.ai in your development environment? Our KinD setup gives you a full-featured playground in minutes. Check out [deployment/README.md](../deployment/README.md) for the streamlined process of spinning up clusters, building images, and deploying components locally.

## Join the Movement

We're building something different. Connect with fellow innovators through our [GitHub Issues](https://github.com/skyflo-ai/skyflo/issues).
