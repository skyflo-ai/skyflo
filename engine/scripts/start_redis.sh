#!/bin/bash
# Script to start Redis using Docker Compose or standalone Docker container

echo "Starting Redis service..."

# Try Docker Compose first
if cd $(dirname "$0")/../../ && [ -f "deployment/docker-compose.yaml" ]; then
    echo "Found Docker Compose configuration. Starting Redis service..."
    docker-compose -f deployment/docker-compose.yaml up -d redis
else
    echo "No Docker Compose configuration found, starting standalone Redis container..."
    # Start a Redis container directly
    docker run --name skyflo-redis -p 6379:6379 -d redis:latest
fi

echo "Waiting for Redis to be ready..."
sleep 3

# Check if Redis is running
if docker ps | grep -q "skyflo-redis" || docker ps | grep -q "redis"; then
    echo "Redis is running successfully."
    echo "You can now start the API server."
else
    echo "Redis service failed to start. Please check Docker logs."
    echo "If you want to disable Redis requirement, set RATE_LIMITING_ENABLED=false in your .env file"
fi 