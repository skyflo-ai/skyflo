#!/bin/bash

VERSION="v0.4.0"

export VERSION

print_colored() {
    local color=$1
    local message=$2
    if [ -t 1 ] && [ -n "$TERM" ] && [ "$TERM" != "dumb" ]; then
        case $color in
            "green") echo -e "\033[0;32m${message}\033[0m" ;;
            "red") echo -e "\033[0;31m${message}\033[0m" ;;
            "yellow") echo -e "\033[1;33m${message}\033[0m" ;;
        esac
    else
        echo "${message}"
    fi
}

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

ensure_namespace_exists() {
    local namespace="$1"
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        print_colored "yellow" "Creating namespace: $namespace"
        kubectl create namespace "$namespace" || {
            print_colored "red" "❌ Failed to create namespace: $namespace"
            exit 1
        }
        print_colored "green" "✓ Created namespace: $namespace"
    else
        print_colored "green" "✓ Using existing namespace: $namespace"
    fi
}

prompt_llm_configuration() {
    print_colored "yellow" "LLM Configuration:"
    while true; do
        read -p "Enter LLM_MODEL (format: provider/model_name, e.g., openai/gpt-4o, groq/meta-llama/llama-4-scout-17b-16e-instruct, gemini/gemini-2.5-flash-preview-04-17, ollama/llama3.1:8b): " LLM_MODEL
        if [ -z "$LLM_MODEL" ]; then
            print_colored "red" "LLM_MODEL cannot be empty."
        elif [[ ! "$LLM_MODEL" == *"/"* ]]; then
            print_colored "red" "Invalid LLM_MODEL format. Please use provider/model_name."
        else
            break
        fi
    done

    local LLM_PROVIDER_RAW=$(echo "$LLM_MODEL" | cut -d'/' -f1)
    local LLM_PROVIDER_UPPER=$(echo "$LLM_PROVIDER_RAW" | tr '[:lower:]' '[:upper:]')
    local API_KEY_VAR_NAME=""

    case "$LLM_PROVIDER_RAW" in
        "huggingface")
            API_KEY_VAR_NAME="HF_TOKEN"
            ;;
        "bedrock"|"aws")
            print_colored "yellow" "AWS Bedrock requires AWS credentials."
            read -s -p "Enter AWS_ACCESS_KEY_ID: " AWS_ACCESS_KEY_ID
            echo ""
            read -s -p "Enter AWS_SECRET_ACCESS_KEY: " AWS_SECRET_ACCESS_KEY
            echo ""
            read -p "Enter AWS_REGION_NAME (e.g., us-west-2): " AWS_REGION_NAME

            export AWS_ACCESS_KEY_ID
            export AWS_SECRET_ACCESS_KEY
            export AWS_REGION_NAME

            API_KEY_VAR_NAME=""
            ;;
        "databricks")
            API_KEY_VAR_NAME="DATABRICKS_TOKEN"
            ;;
        "clarifai")
            API_KEY_VAR_NAME="CLARIFAI_PAT"
            ;;
        "ibm"|"watsonx")
            API_KEY_VAR_NAME="IBM_API_KEY"
            ;;
        "jina"|"jinaai")
            API_KEY_VAR_NAME="JINAAI_API_KEY"
            ;;
        "perplexity"|"perplexityai")
            API_KEY_VAR_NAME="PERPLEXITYAI_API_KEY"
            ;;
        "fireworks"|"fireworksai")
            API_KEY_VAR_NAME="FIREWORKS_AI_API_KEY"
            ;;
        "together"|"togetherai")
            API_KEY_VAR_NAME="TOGETHERAI_API_KEY"
            ;;
        "nvidia"|"nim")
            API_KEY_VAR_NAME="NVIDIA_NGC_API_KEY"
            ;;
        "alephalpha")
            API_KEY_VAR_NAME="ALEPHALPHA_API_KEY"
            ;;
        "featherless")
            API_KEY_VAR_NAME="FEATHERLESS_AI_API_KEY"
            ;;
        "baseten")
            API_KEY_VAR_NAME="BASETEN_API_KEY"
            ;;
        "sambanova")
            API_KEY_VAR_NAME="SAMBANOVA_API_KEY"
            ;;
        "xai")
            API_KEY_VAR_NAME="XAI_API_KEY"
            ;;
        "volcengine")
            API_KEY_VAR_NAME="VOLCENGINE_API_KEY"
            ;;
        "predibase")
            API_KEY_VAR_NAME="PREDIBASE_API_KEY"
            ;;
        *)
            API_KEY_VAR_NAME="${LLM_PROVIDER_UPPER}_API_KEY"
            ;;
    esac

    if [ -n "$API_KEY_VAR_NAME" ]; then
        print_colored "yellow" "Enter API key for $LLM_PROVIDER_RAW."
        if [[ "$LLM_PROVIDER_RAW" == "openai" || "$LLM_PROVIDER_RAW" == "groq" || "$LLM_PROVIDER_RAW" == "anthropic" || \
              "$LLM_PROVIDER_RAW" == "gemini" || "$LLM_PROVIDER_RAW" == "mistral" || "$LLM_PROVIDER_RAW" == "cohere" ]]; then
            while true; do
                read -s -p "Enter $API_KEY_VAR_NAME: " API_KEY_VALUE
                echo ""
                if [ -z "$API_KEY_VALUE" ]; then
                    print_colored "red" "$API_KEY_VAR_NAME is required for $LLM_PROVIDER_RAW."
                else
                    break
                fi
            done
        else
            read -s -p "Enter $API_KEY_VAR_NAME (optional, press Enter to skip): " API_KEY_VALUE
            echo ""
            if [ -z "$API_KEY_VALUE" ]; then
                API_KEY_VALUE=""
                print_colored "yellow" "ℹ $API_KEY_VAR_NAME is not set (optional for $LLM_PROVIDER_RAW)."
            fi
        fi
        export "$API_KEY_VAR_NAME"="$API_KEY_VALUE"
    fi

    read -p "Enter LLM_HOST (optional, e.g., http://localhost:11434, leave empty if not using a self-hosted model): " LLM_HOST
    if [ -z "$LLM_HOST" ]; then
        LLM_HOST=""
        print_colored "yellow" "ℹ LLM_HOST is not set."
    fi

    export LLM_MODEL
    export LLM_HOST
}

set_runtime_defaults() {
    if [ -z "$JWT_SECRET" ]; then
        JWT_SECRET=$(openssl rand -base64 32)
        print_colored "green" "✓ Generated secure JWT secret"
    fi

    if [ -z "$POSTGRES_DATABASE_URL" ]; then
        POSTGRES_DATABASE_URL="postgres://skyflo:skyflo@skyflo-ai-postgres:5432/skyflo"
        print_colored "yellow" "ℹ Using default Postgres database URL"
    fi

    if [ -z "$REDIS_URL" ]; then
        REDIS_URL="redis://skyflo-ai-redis:6379/0"
        print_colored "yellow" "ℹ Using default Redis host"
    fi

    if [ -z "$MCP_SERVER_URL" ]; then
        MCP_SERVER_URL="http://skyflo-ai-mcp:8888/mcp"
        print_colored "yellow" "ℹ Using default MCP server URL"
    fi

    if [ -z "$INTEGRATIONS_SECRET_NAMESPACE" ]; then
        INTEGRATIONS_SECRET_NAMESPACE="$NAMESPACE"
    fi

    export JWT_SECRET
    export POSTGRES_DATABASE_URL
    export REDIS_URL
    export MCP_SERVER_URL
    export INTEGRATIONS_SECRET_NAMESPACE
}

setup_kind_cluster_if_needed() {
    if kind get clusters | grep -q "skyflo-ai"; then
        print_colored "green" "✓ Found existing skyflo-ai cluster"
    else
        print_colored "yellow" "Creating new skyflo-ai cluster..."
        curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/local.kind.yaml" | kind create cluster --config -
        print_colored "green" "✓ Created KinD cluster"
    fi
}

apply_k8s_from_file() {
    local file_path="$1"
    cat "$file_path" | envsubst | kubectl apply -f - || return 1
    return 0
}

print_colored "green" "
skyflo.ai Installer
================================
"

print_colored "yellow" "Please select your installation type:"
print_colored "yellow" "1) Local development cluster (KinD required)"
print_colored "yellow" "2) Production cluster"
read -p "Enter your choice (1 or 2): " choice

choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')

# Namespace configuration
read -p "Enter Kubernetes namespace (press Enter for default 'skyflo-ai'): " NAMESPACE
if [ -z "$NAMESPACE" ]; then
    NAMESPACE="skyflo-ai"
    print_colored "yellow" "ℹ Using default namespace: skyflo-ai"
fi

export NAMESPACE

ensure_namespace_exists "$NAMESPACE"

case $choice in
    1|"1"|"1)"|"local"|"kind"|"l")
        print_colored "green" "Setting up local development cluster using KinD..."
        check_command "kind"
        check_command "kubectl"
        check_command "envsubst"
        check_command "base64"
        check_command "openssl"
        check_command "curl"

        setup_kind_cluster_if_needed

        TMP_INSTALL_FILE=$(mktemp)
        curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/local.install.yaml" > "$TMP_INSTALL_FILE"

        sed -i '' 's/imagePullPolicy: Never/imagePullPolicy: Always/g' "$TMP_INSTALL_FILE"
        prompt_llm_configuration
        set_runtime_defaults

        print_colored "yellow" "🔄 Setting up local development environment..."

        print_colored "yellow" "🔄 Applying Kubernetes configuration..."
        apply_k8s_from_file "$TMP_INSTALL_FILE" || {
            print_colored "red" "❌ Local installation failed"
            rm -f "$TMP_INSTALL_FILE"
            exit 1
        }

        rm -f "$TMP_INSTALL_FILE"

        print_colored "green" "
✅ Installation Complete!
========================
Your Skyflo.ai instance is being deployed. To check the status, run:
  kubectl get pods -n $NAMESPACE

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
        prompt_llm_configuration
        set_runtime_defaults

        print_colored "yellow" "🔄 Applying Kubernetes configuration..."
        TMP_INSTALL_FILE=$(mktemp)
        curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.yaml" > "$TMP_INSTALL_FILE"

        apply_k8s_from_file "$TMP_INSTALL_FILE" || {
            print_colored "red" "❌ Installation failed"
            rm -f "$TMP_INSTALL_FILE"
            exit 1
        }

        rm -f "$TMP_INSTALL_FILE"

        print_colored "green" "
✅ Installation Complete!
========================
Your Skyflo.ai instance is being deployed. To check the status, run:
  kubectl get pods -n $NAMESPACE

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