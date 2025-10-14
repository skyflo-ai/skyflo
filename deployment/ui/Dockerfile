# Build stage
FROM node:20-slim AS builder

RUN apt-get update && apt-get install -y \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install dependencies first (caching)
COPY ui/package.json ui/yarn.lock ./
RUN yarn install --frozen-lockfile

# Copy source files and environment file
COPY ui/tsconfig.json ./
COPY ui/next.config.mjs ./
COPY ui/tailwind.config.ts ./
COPY ui/postcss.config.mjs ./
COPY ui/components.json ./
COPY ui/.eslintrc.json ./
COPY ui/src ./src
COPY ui/public ./public
COPY ui/.env ./.env.production

# Build the application
ENV NEXT_TELEMETRY_DISABLED=1
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

# Copy necessary files from builder
COPY --from=builder --chown=skyflo:skyflogroup /app/.next/standalone ./
COPY --from=builder --chown=skyflo:skyflogroup /app/.next/static ./.next/static
COPY --from=builder --chown=skyflo:skyflogroup /app/public ./public
COPY --from=builder --chown=skyflo:skyflogroup /app/.env.production ./.env

# Expose the UI port
EXPOSE 3000

LABEL org.opencontainers.image.source=https://github.com/skyflo-ai/skyflo
LABEL org.opencontainers.image.description="UI for Skyflo.ai - Open Source AI Agent for Cloud & DevOps"

# Switch to non-root user
USER skyflo

# Start the application
CMD ["node", "server.js"] 