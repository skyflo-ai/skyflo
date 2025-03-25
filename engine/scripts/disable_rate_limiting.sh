#!/bin/bash
# Script to disable rate limiting in the API by updating .env

ENV_FILE=$(dirname "$0")/../.env

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Check if RATE_LIMITING_ENABLED already exists in .env
if grep -q "RATE_LIMITING_ENABLED" "$ENV_FILE"; then
    # Replace the existing line
    sed -i '' 's/RATE_LIMITING_ENABLED=.*/RATE_LIMITING_ENABLED=false/' "$ENV_FILE"
    echo "Updated RATE_LIMITING_ENABLED to false in .env file"
else
    # Add the setting at the end of the file
    echo -e "\n# Rate Limiting\nRATE_LIMITING_ENABLED=false" >> "$ENV_FILE"
    echo "Added RATE_LIMITING_ENABLED=false to .env file"
fi

echo "Rate limiting has been disabled. You can run the API server without Redis now." 