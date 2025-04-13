# Use official Python image
FROM python:3.11-slim

ARG TARGETARCH

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
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/$TARGETARCH/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install kubectl argo rollouts plugin
RUN curl -LO "https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-$TARGETARCH" \
    && chmod +x kubectl-argo-rollouts-linux-$TARGETARCH \
    && mv kubectl-argo-rollouts-linux-$TARGETARCH /usr/local/bin/kubectl-argo-rollouts \
    && ln -s /usr/local/bin/kubectl-argo-rollouts /usr/local/bin/kubectl-argo

# Install Helm
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \
    && chmod 700 get_helm.sh \
    && ./get_helm.sh \
    && rm get_helm.sh

# Create app user and directory
RUN groupadd -g 1002 skyflogroup \
    && useradd -u 1002 -g skyflogroup -s /bin/bash -m skyflo \
    && mkdir -p /app \
    && chown -R skyflo:skyflogroup /app

# Set up application
WORKDIR /app

# Create and activate virtual environment early
ENV VIRTUAL_ENV="/app/venv"
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create the source directory structure first
RUN mkdir -p src/mcp_server

# Copy dependency-related files and source code needed for installation
COPY mcp/pyproject.toml mcp/.python-version mcp/uv.lock mcp/README.md ./
COPY mcp/src/mcp_server/__about__.py ./src/mcp_server/

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip install uvicorn[standard]

# Now copy all remaining application files
COPY mcp/src ./src
COPY mcp/.env ./.env

# Copy and set up entrypoint script
COPY deployment/mcp/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set final permissions
RUN chown -R skyflo:skyflogroup /app && \
    chmod -R 755 /app

# Update PATH and PYTHONPATH for skyflo user
ENV PATH="/app/venv/bin:/usr/local/bin:/home/skyflo/.local/bin:${PATH}" \
    PYTHONPATH="/app/src"

# Expose the API port
EXPOSE 8081

LABEL org.opencontainers.image.source=https://github.com/skyflo-ai/skyflo
LABEL org.opencontainers.image.description="Skyflo.ai MCP Server - Open Source AI Agent for Cloud Native"

# Switch to non-root user
USER skyflo

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]