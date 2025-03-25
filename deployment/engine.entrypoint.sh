#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! nc -z $POSTGRES_HOST 5432; do
  sleep 1
done
echo "Database is ready!"

# Initialize Aerich if not already initialized
if [ ! -d "migrations" ]; then
  echo "Initializing Aerich..."
  aerich init -t src.api.repositories.database.TORTOISE_ORM_CONFIG
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
exec uvicorn api.asgi:app --host 0.0.0.0 --port 8080 --workers ${ENGINE_SERVER_WORKERS:-2}