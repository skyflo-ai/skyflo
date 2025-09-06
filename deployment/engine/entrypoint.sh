#!/bin/bash
set -e

# Wait for 30 seconds for the database to be ready
sleep 30

# Initialize Aerich if not already initialized
if [ ! -d "migrations" ]; then
  echo "Initializing Aerich..."
  aerich init -t src.api.config.database.TORTOISE_ORM_CONFIG
fi

# Create initial migration if none exists
if [ ! "$(ls -A migrations/models 2>/dev/null)" ]; then
  echo "Creating initial migration..."
  aerich init-db
else
  # Apply any pending migrations
  echo "Applying pending migrations..."
  aerich upgrade
fi

# Start the API service with Uvicorn
echo "Starting Engine service..."
exec uvicorn src.api.asgi:app --host 0.0.0.0 --port 8080