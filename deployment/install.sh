#!/bin/bash

# Function to print colored output
print_colored() {
    local color=$1
    local message=$2
    # Check if the terminal supports colors
    if [ -t 1 ] && [ -n "$TERM" ] && [ "$TERM" != "dumb" ]; then
        case $color in
            "green") echo -e "\033[0;32m${message}\033[0m" ;;
            "red") echo -e "\033[0;31m${message}\033[0m" ;;
            "yellow") echo -e "\033[1;33m${message}\033[0m" ;;
        esac
    else
        # Fallback to plain text if colors aren't supported
        echo "${message}"
    fi
}

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_colored "red" "Error: $1 is required but not installed."
        case "$1" in
            "kubectl")
                print_colored "yellow" "Install kubectl: https://kubernetes.io/docs/tasks/tools/"
                ;;
            "envsubst")
                print_colored "yellow" "Install gettext:"
                print_colored "yellow" "- macOS: brew install gettext"
                print_colored "yellow" "- Linux: apt-get install gettext or yum install gettext"
                print_colored "yellow" "- Windows: Available through WSL or Git Bash"
                ;;
            "curl")
                print_colored "yellow" "Install curl:"
                print_colored "yellow" "- macOS: brew install curl"
                print_colored "yellow" "- Linux: apt-get install curl or yum install curl"
                print_colored "yellow" "- Windows: Available through WSL or Git Bash"
                ;;
        esac
        exit 1
    fi
}

# Check required commands
check_command "kubectl"
check_command "envsubst"
check_command "base64"
check_command "openssl"
check_command "curl"

# Welcome message
print_colored "green" "
skyflo.ai Installer
================================
"

# Validate OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    print_colored "red" "Error: OPENAI_API_KEY environment variable is required."
    print_colored "yellow" "Please run the installer with your OpenAI API key:"
    echo "OPENAI_API_KEY='your-key-here' ./install.sh"
    exit 1
fi

# Generate secure JWT secret if not provided
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(openssl rand -base64 32)
    print_colored "green" "✓ Generated secure JWT secret"
fi

if [ -z "$POSTGRES_DATABASE_URL" ]; then
    POSTGRES_DATABASE_URL="postgres://skyflo:skyflo@skyflo-ai-postgres:5432/skyflo"
    print_colored "yellow" "ℹ Using default Postgres database URL"
fi

if [ -z "$REDIS_HOST" ]; then
    REDIS_HOST="skyflo-ai-redis:6379"
    print_colored "yellow" "ℹ Using default Redis host"
fi

# Export variables for envsubst
export OPENAI_API_KEY
export JWT_SECRET
export POSTGRES_DATABASE_URL
export REDIS_HOST

# Apply the configuration
print_colored "yellow" "🔄 Applying Kubernetes configuration..."

curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.yaml" | \
    envsubst | \
    kubectl apply -f - || {
        print_colored "red" "❌ Installation failed"
        exit 1
    }

print_colored "green" "
✅ Installation Complete!
========================
Your Skyflo.ai instance is being deployed. To check the status, run:
  kubectl get pods -n skyflo-ai

To access the UI locally:
  kubectl port-forward -n skyflo-ai svc/skyflo-ai-ui 3000:3000

To access the API locally:
  kubectl port-forward -n skyflo-ai svc/skyflo-ai-engine 8080:8080

For production setup and more information, visit:
  https://github.com/skyflo-ai/skyflo/blob/main/docs/install.md
" 