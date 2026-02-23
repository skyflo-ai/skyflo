# Build stage
FROM node:20-slim AS builder

ARG NEXT_PUBLIC_APP_VERSION=dev
ARG NEXT_PUBLIC_APP_NAME=Skyflo.ai
ARG NEXT_PUBLIC_API_URL=/api/v1
ARG NEXT_PUBLIC_ENABLE_ANALYTICS=false
ARG NEXT_PUBLIC_ENABLE_FEEDBACK=false

RUN apt-get update && apt-get install -y \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install dependencies first (caching)
COPY ui/package.json ui/yarn.lock ./
RUN yarn install --frozen-lockfile

# Copy source files
COPY ui/tsconfig.json ./
COPY ui/next.config.mjs ./
COPY ui/tailwind.config.ts ./
COPY ui/postcss.config.mjs ./
COPY ui/components.json ./
COPY ui/.eslintrc.json ./
COPY ui/src ./src
COPY ui/public ./public

# Build the application
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_APP_VERSION=$NEXT_PUBLIC_APP_VERSION
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_ENABLE_ANALYTICS=$NEXT_PUBLIC_ENABLE_ANALYTICS
ENV NEXT_PUBLIC_ENABLE_FEEDBACK=$NEXT_PUBLIC_ENABLE_FEEDBACK
RUN yarn build

# Production stage
FROM node:20-slim AS runner

WORKDIR /app

# Create app user
RUN groupadd -g 1002 skyflogroup \
    && useradd -u 1002 -g skyflogroup -s /bin/bash -m skyflo \
    && chown -R skyflo:skyflogroup /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy files from builder
COPY --from=builder --chown=skyflo:skyflogroup /app/.next/standalone ./
COPY --from=builder --chown=skyflo:skyflogroup /app/.next/static ./.next/static
COPY --from=builder --chown=skyflo:skyflogroup /app/public ./public

# Expose the UI port
EXPOSE 3000

LABEL org.opencontainers.image.source=https://github.com/skyflo-ai/skyflo
LABEL org.opencontainers.image.description="UI for Skyflo.ai - Open Source AI Agent for Cloud & DevOps"

# Switch to non-root user
USER skyflo

# Start the application
CMD ["node", "server.js"] 