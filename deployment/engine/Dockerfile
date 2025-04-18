# Use official Python image
FROM python:3.11-slim

ARG TARGETARCH

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    ca-certificates \
    netcat-openbsd \
    bash \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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
RUN mkdir -p src/api

# Copy dependency-related files and source code needed for installation
COPY engine/pyproject.toml engine/.python-version engine/uv.lock engine/README.md ./
COPY engine/src/api/__about__.py ./src/api/

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip install uvicorn[standard]

# Now copy all remaining application files
COPY engine/src ./src
COPY engine/.env ./.env
COPY engine/migrations ./migrations
COPY engine/aerich.ini ./aerich.ini
COPY engine/alembic.ini ./alembic.ini

# Copy and set up entrypoint script
COPY deployment/engine/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set final permissions
RUN chown -R skyflo:skyflogroup /app && \
    chmod -R 755 /app

# Update PATH and PYTHONPATH for skyflo user
ENV PATH="/app/venv/bin:/usr/local/bin:/home/skyflo/.local/bin:${PATH}" \
    PYTHONPATH="/app/src"

# Expose the API port
EXPOSE 8080

LABEL org.opencontainers.image.source=https://github.com/skyflo-ai/skyflo
LABEL org.opencontainers.image.description="Skyflo.ai Engine Service - Open Source AI Agent for Cloud Native"

# Switch to non-root user
USER skyflo

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]