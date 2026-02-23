# Use official Python image
FROM python:3.11-slim

ARG TARGETARCH
ARG APP_VERSION=dev
ARG KUBECTL_VERSION=v1.35.0
ARG ARGO_ROLLOUTS_VERSION=v1.8.3
ARG HELM_VERSION=v4.1.0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    netcat-openbsd \
    bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -fsSL -o kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/$TARGETARCH/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install kubectl argo rollouts plugin
RUN curl -fsSL -o kubectl-argo-rollouts-linux-$TARGETARCH "https://github.com/argoproj/argo-rollouts/releases/download/${ARGO_ROLLOUTS_VERSION}/kubectl-argo-rollouts-linux-$TARGETARCH" \
    && chmod +x kubectl-argo-rollouts-linux-$TARGETARCH \
    && mv kubectl-argo-rollouts-linux-$TARGETARCH /usr/local/bin/kubectl-argo-rollouts \
    && ln -s /usr/local/bin/kubectl-argo-rollouts /usr/local/bin/kubectl-argo

# Install Helm
RUN curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${TARGETARCH}.tar.gz" -o /tmp/helm.tar.gz \
    && tar xzf /tmp/helm.tar.gz -C /tmp \
    && mv /tmp/linux-${TARGETARCH}/helm /usr/local/bin/helm \
    && rm -rf /tmp/helm.tar.gz /tmp/linux-${TARGETARCH}

# Create app user and directory
RUN groupadd -g 1002 skyflogroup \
    && useradd -u 1002 -g skyflogroup -s /bin/bash -m skyflo \
    && mkdir -p /app \
    && chown -R skyflo:skyflogroup /app

# Set up application
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.28 /uv /usr/local/bin/uv

# Copy files needed for installation
COPY mcp/pyproject.toml mcp/.python-version mcp/uv.lock mcp/README.md ./
COPY mcp/__about__.py ./

# Install dependencies using uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev

# Now copy all remaining application files
COPY mcp/main.py ./
COPY mcp/config ./config
COPY mcp/tools ./tools
COPY mcp/utils ./utils

# Copy and set up entrypoint script
COPY deployment/mcp/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set final permissions
RUN chown -R skyflo:skyflogroup /app && \
    chmod -R 755 /app

# Update PATH and PYTHONPATH for skyflo user
ENV APP_VERSION=$APP_VERSION \
    PATH="/app/.venv/bin:/usr/local/bin:/home/skyflo/.local/bin:${PATH}" \
    PYTHONPATH="/app"

# Expose the API port
EXPOSE 8888

LABEL org.opencontainers.image.source=https://github.com/skyflo-ai/skyflo
LABEL org.opencontainers.image.description="Skyflo.ai MCP Server - Open Source AI Agent for Cloud & DevOps"

# Switch to non-root user
USER skyflo

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]