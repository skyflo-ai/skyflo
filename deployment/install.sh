#!/bin/bash

# Version configuration
VERSION="v0.1.1"

# Export VERSION for envsubst
export VERSION

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
            "kind")
                print_colored "yellow" "Install KinD:"
                print_colored "yellow" "- Using Homebrew: brew install kind"
                print_colored "yellow" "- Using Go: go install sigs.k8s.io/kind@latest"
                print_colored "yellow" "- More info: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
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

# Function to check if all deployments are ready
wait_for_pods() {
    local namespace="skyflo-ai"
    local spinner=( "⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏" )
    local spin_idx=0
    local all_ready=false

    print_colored "yellow" "Waiting for all deployments to be ready..."
    echo ""

    while [ "$all_ready" = false ]; do
        # Get deployment statuses
        local deploy_statuses=$(kubectl get deploy -n "$namespace" -o jsonpath='{range .items[*]}{.metadata.name}{":"}{.status.readyReplicas}{":"}{.status.replicas}{"\n"}{end}' 2>/dev/null)
        
        # Clear previous line
        echo -en "\033[1A\033[K"
        
        # Print current status with spinner
        echo -n "${spinner[$spin_idx]} Checking deployment status: "
        
        all_ready=true
        local has_deployments=false
        
        while IFS=: read -r deploy_name ready_replicas total_replicas; do
            if [ -n "$deploy_name" ]; then
                has_deployments=true
                # Handle null ready_replicas by treating it as 0
                ready_replicas=${ready_replicas:-0}
                echo -n "$deploy_name: $ready_replicas/$total_replicas, "
                if [ "$ready_replicas" -eq 0 ]; then
                    all_ready=false
                fi
            fi
        done <<< "$deploy_statuses"

        if [ "$has_deployments" = false ]; then
            all_ready=false
            echo -n "No deployments found yet"
        fi

        echo ""  # New line for next iteration
        
        # Update spinner index
        spin_idx=$(( (spin_idx + 1) % 10 ))
        
        if [ "$all_ready" = false ]; then
            sleep 2
        fi
    done

    echo ""
    print_colored "green" "✓ All deployments have at least one replica ready!"
    echo ""
}

# Welcome message
print_colored "green" "
skyflo.ai Installer
================================
"

# Ask user for installation type
print_colored "yellow" "Please select your installation type:"
print_colored "yellow" "1) Local development cluster (KinD required)"
print_colored "yellow" "2) Production cluster"
read -p "Enter your choice (1 or 2): " choice

# Convert choice to lowercase using tr for better compatibility
choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')

case $choice in  # Modified case statement without bash-specific lowercase conversion
    1|"1"|"1)"|"local"|"kind"|"l")
        print_colored "green" "Setting up local development cluster using KinD..."
        check_command "kind"
        check_command "kubectl"
        check_command "envsubst"
        check_command "base64"
        check_command "openssl"
        check_command "curl"

        # Check if cluster exists, create only if it doesn't
        if kind get clusters | grep -q "skyflo-ai"; then
            print_colored "green" "✓ Found existing skyflo-ai cluster"
        else
            print_colored "yellow" "Creating new skyflo-ai cluster..."
            curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/local.kind.yaml" | kind create cluster --config -
            print_colored "green" "✓ Created KinD cluster"
        fi

        # Download and modify the installation yaml
        TMP_INSTALL_FILE=$(mktemp)
        curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/local.install.yaml" > "$TMP_INSTALL_FILE"


        # Replace image names and pull policies
        sed -i '' 's/imagePullPolicy: Never/imagePullPolicy: Always/g' "$TMP_INSTALL_FILE"
        sed -i '' "s|skyfloai/engine|skyfloaiagent/engine|g" "$TMP_INSTALL_FILE"
        sed -i '' "s|skyfloai/mcp|skyfloaiagent/mcp|g" "$TMP_INSTALL_FILE"
        sed -i '' "s|skyfloai/ui|skyfloaiagent/ui|g" "$TMP_INSTALL_FILE"
        sed -i '' "s|skyfloai/controller|skyfloaiagent/k8s-controller|g" "$TMP_INSTALL_FILE"
        sed -i '' "s|skyfloai/proxy|skyfloaiagent/proxy|g" "$TMP_INSTALL_FILE"

        # Prompt for LLM configuration
        print_colored "yellow" "LLM Configuration:"
        while true; do
            read -p "Enter LLM_MODEL (format: provider/model_name, e.g., openai/gpt-4o, groq/meta-llama/llama-4-scout-17b-16e-instruct, ollama/llama3.1:8b): " LLM_MODEL
            if [ -z "$LLM_MODEL" ]; then
                print_colored "red" "LLM_MODEL cannot be empty."
            elif [[ ! "$LLM_MODEL" == *"/"* ]]; then
                print_colored "red" "Invalid LLM_MODEL format. Please use provider/model_name."
            else
                break
            fi
        done

        LLM_PROVIDER_RAW=$(echo "$LLM_MODEL" | cut -d'/' -f1)
        LLM_PROVIDER_UPPER=$(echo "$LLM_PROVIDER_RAW" | tr '[:lower:]' '[:upper:]')
        API_KEY_VAR_NAME="${LLM_PROVIDER_UPPER}_API_KEY"

        print_colored "yellow" "Enter API key for $LLM_PROVIDER_RAW."
        if [[ "$LLM_PROVIDER_RAW" == "openai" || "$LLM_PROVIDER_RAW" == "groq" || "$LLM_PROVIDER_RAW" == "anthropic" ]]; then
            while true; do
                read -s -p "Enter $API_KEY_VAR_NAME: " API_KEY_VALUE
                echo "" # Newline after secret input
                if [ -z "$API_KEY_VALUE" ]; then
                    print_colored "red" "$API_KEY_VAR_NAME is required for $LLM_PROVIDER_RAW."
                else
                    break
                fi
            done
        else
            read -s -p "Enter $API_KEY_VAR_NAME (optional, press Enter to skip): " API_KEY_VALUE
            echo "" # Newline after secret input
            if [ -z "$API_KEY_VALUE" ]; then
                API_KEY_VALUE=""
                print_colored "yellow" "ℹ $API_KEY_VAR_NAME is not set (optional for $LLM_PROVIDER_RAW)."
            fi
        fi
        # Dynamically create and export the API key variable
        export "$API_KEY_VAR_NAME"="$API_KEY_VALUE"

        read -p "Enter LLM_HOST (optional, e.g., http://localhost:11434, leave empty if not using a self-hosted model): " LLM_HOST
        if [ -z "$LLM_HOST" ]; then
            LLM_HOST=""
            print_colored "yellow" "ℹ LLM_HOST is not set."
        fi
        
        export LLM_MODEL
        export LLM_HOST

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
        export JWT_SECRET
        export POSTGRES_DATABASE_URL
        export REDIS_HOST

        # Build and load local images
        print_colored "yellow" "🔄 Setting up local development environment..."

        # Apply the configuration
        print_colored "yellow" "🔄 Applying Kubernetes configuration..."

        cat "$TMP_INSTALL_FILE" | envsubst | kubectl apply -f - || {
            print_colored "red" "❌ Local installation failed"
            rm -f "$TMP_INSTALL_FILE"
            exit 1
        }

        # Clean up temporary file
        rm -f "$TMP_INSTALL_FILE"

        # Wait for all deployments to be ready
        wait_for_pods

        print_colored "green" "
✅ Installation Complete!
========================
Your Skyflo.ai instance is being deployed. To check the status, run:
  kubectl get pods -n skyflo-ai

Your services are directly accessible through NodePorts:
- UI: http://localhost:30080
- API: http://localhost:30081

For production setup and more information, visit:
  https://github.com/skyflo-ai/skyflo/blob/main/docs/install.md
"
        ;;
    2|"2"|"2)"|"prod"|"production"|"p")
        print_colored "green" "Setting up production cluster..."
        check_command "kubectl"
        check_command "envsubst"
        check_command "base64"
        check_command "openssl"
        check_command "curl"

        # Prompt for LLM configuration
        print_colored "yellow" "LLM Configuration:"
        while true; do
            read -p "Enter LLM_MODEL (format: provider/model_name, e.g., openai/gpt-4o, groq/meta-llama/llama-4-scout-17b-16e-instruct, ollama/llama3.1:8b): " LLM_MODEL
            if [ -z "$LLM_MODEL" ]; then
                print_colored "red" "LLM_MODEL cannot be empty."
            elif [[ ! "$LLM_MODEL" == *"/"* ]]; then
                print_colored "red" "Invalid LLM_MODEL format. Please use provider/model_name."
            else
                break
            fi
        done

        LLM_PROVIDER_RAW=$(echo "$LLM_MODEL" | cut -d'/' -f1)
        LLM_PROVIDER_UPPER=$(echo "$LLM_PROVIDER_RAW" | tr '[:lower:]' '[:upper:]')
        API_KEY_VAR_NAME="${LLM_PROVIDER_UPPER}_API_KEY"

        print_colored "yellow" "Enter API key for $LLM_PROVIDER_RAW."
        if [[ "$LLM_PROVIDER_RAW" == "openai" || "$LLM_PROVIDER_RAW" == "groq" || "$LLM_PROVIDER_RAW" == "anthropic" ]]; then
            while true; do
                read -s -p "Enter $API_KEY_VAR_NAME: " API_KEY_VALUE
                echo "" # Newline after secret input
                if [ -z "$API_KEY_VALUE" ]; then
                    print_colored "red" "$API_KEY_VAR_NAME is required for $LLM_PROVIDER_RAW."
                else
                    break
                fi
            done
        else
            read -s -p "Enter $API_KEY_VAR_NAME (optional, press Enter to skip): " API_KEY_VALUE
            echo "" # Newline after secret input
            if [ -z "$API_KEY_VALUE" ]; then
                API_KEY_VALUE=""
                print_colored "yellow" "ℹ $API_KEY_VAR_NAME is not set (optional for $LLM_PROVIDER_RAW)."
            fi
        fi
        # Dynamically create and export the API key variable
        export "$API_KEY_VAR_NAME"="$API_KEY_VALUE"
        
        read -p "Enter LLM_HOST (optional, e.g., http://localhost:11434, leave empty if not using a self-hosted model): " LLM_HOST
        if [ -z "$LLM_HOST" ]; then
            LLM_HOST=""
            print_colored "yellow" "ℹ LLM_HOST is not set."
        fi

        export LLM_MODEL
        export LLM_HOST

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
        export JWT_SECRET
        export POSTGRES_DATABASE_URL
        export REDIS_HOST

        # Apply the configuration
        print_colored "yellow" "🔄 Applying Kubernetes configuration..."

        # Download and modify the installation yaml
        TMP_INSTALL_FILE=$(mktemp)
        curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.yaml" > "$TMP_INSTALL_FILE"

        cat "$TMP_INSTALL_FILE" | envsubst | kubectl apply -f - || {
            print_colored "red" "❌ Installation failed"
            rm -f "$TMP_INSTALL_FILE"
            exit 1
        }

        # Clean up temporary file
        rm -f "$TMP_INSTALL_FILE"

        # Wait for all deployments to be ready
        wait_for_pods

        print_colored "green" "
✅ Installation Complete!
========================
Your Skyflo.ai instance is being deployed. To check the status, run:
  kubectl get pods -n skyflo-ai

Create your Ingress controller and expose the \"skyflo-ui\" NodePort Service. Refer to our documentation:
  https://github.com/skyflo-ai/skyflo/blob/main/docs/install.md
"
        ;;
    *)
        print_colored "red" "Invalid choice. Please select either:"
        print_colored "yellow" "- 1, local, or kind for local development"
        print_colored "yellow" "- 2, prod, or production for production deployment"
        exit 1
        ;;
esac 