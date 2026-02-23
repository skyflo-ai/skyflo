#!/bin/bash

if [ -z "$VERSION" ]; then
    VERSION=$(curl -sL --connect-timeout 10 --max-time 30 https://api.github.com/repos/skyflo-ai/skyflo/releases/latest \
        | grep -m 1 '"tag_name":' \
        | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
    if [ -z "$VERSION" ]; then
        echo "Error: unable to determine latest release tag."
        echo "Set VERSION manually, e.g.: VERSION=v0.5.0 ./install.sh"
        exit 1
    fi
fi

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
        print_colored "red" "Missing dependency: $1"
        case "$1" in
            "kubectl")
                print_colored "yellow" "Install instructions:"
                print_colored "yellow" "https://kubernetes.io/docs/tasks/tools/"
                ;;
            "envsubst")
                print_colored "yellow" "Install gettext:"
                print_colored "yellow" "  macOS: brew install gettext"
                print_colored "yellow" "  Linux: apt-get install gettext or yum install gettext"
                print_colored "yellow" "  Windows: available via WSL or Git Bash"
                ;;
            "curl")
                print_colored "yellow" "Install curl using your system package manager"
                ;;
        esac
        exit 1
    fi
}

ensure_namespace_exists() {
    local namespace="$1"
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        print_colored "yellow" "Namespace '$namespace' not found. Creating..."
        kubectl create namespace "$namespace" || {
            print_colored "red" "Failed to create namespace '$namespace'"
            exit 1
        }
        print_colored "green" "✓ Namespace '$namespace' created"
    else
        print_colored "green" "✓ Using existing namespace '$namespace'"
    fi
}

prompt_llm_configuration() {
    print_colored "yellow" "LLM configuration"
    print_colored "yellow" "-----------------"
    while true; do
        read -r -p "LLM model identifier (provider/model): " LLM_MODEL </dev/tty
        if [ -z "$LLM_MODEL" ]; then
            print_colored "red" "LLM_MODEL cannot be empty."
        elif [[ ! "$LLM_MODEL" == *"/"* ]]; then
            print_colored "red" "Invalid format. Expected: provider/model (e.g., openai/gpt-4o)"
        else
            break
        fi
    done

    local LLM_PROVIDER_RAW=$(echo "$LLM_MODEL" | cut -d'/' -f1)
    local LLM_PROVIDER_UPPER=$(echo "$LLM_PROVIDER_RAW" | tr '[:lower:]' '[:upper:]')
    local LLM_PROVIDER_SANITIZED=$(echo "$LLM_PROVIDER_UPPER" | sed 's/[^A-Z0-9_]/_/g')
    local API_KEY_VAR_NAME=""

    case "$LLM_PROVIDER_RAW" in
        "huggingface") API_KEY_VAR_NAME="HF_TOKEN" ;;
        "bedrock"|"aws")
            print_colored "yellow" "AWS Bedrock requires AWS credentials."
            read -r -s -p "AWS_ACCESS_KEY_ID: " AWS_ACCESS_KEY_ID </dev/tty
            echo ""
            read -r -s -p "AWS_SECRET_ACCESS_KEY: " AWS_SECRET_ACCESS_KEY </dev/tty
            echo ""
            read -r -p "AWS_REGION_NAME (e.g., us-west-2): " AWS_REGION_NAME </dev/tty
            export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION_NAME
            API_KEY_VAR_NAME=""
            ;;
        "databricks") API_KEY_VAR_NAME="DATABRICKS_TOKEN" ;;
        "clarifai") API_KEY_VAR_NAME="CLARIFAI_PAT" ;;
        "ibm"|"watsonx") API_KEY_VAR_NAME="IBM_API_KEY" ;;
        "jina"|"jinaai") API_KEY_VAR_NAME="JINAAI_API_KEY" ;;
        "perplexity"|"perplexityai") API_KEY_VAR_NAME="PERPLEXITYAI_API_KEY" ;;
        "fireworks"|"fireworksai") API_KEY_VAR_NAME="FIREWORKS_AI_API_KEY" ;;
        "together"|"togetherai") API_KEY_VAR_NAME="TOGETHERAI_API_KEY" ;;
        "nvidia"|"nim") API_KEY_VAR_NAME="NVIDIA_NGC_API_KEY" ;;
        "alephalpha") API_KEY_VAR_NAME="ALEPHALPHA_API_KEY" ;;
        "featherless") API_KEY_VAR_NAME="FEATHERLESS_AI_API_KEY" ;;
        "baseten") API_KEY_VAR_NAME="BASETEN_API_KEY" ;;
        "sambanova") API_KEY_VAR_NAME="SAMBANOVA_API_KEY" ;;
        "xai") API_KEY_VAR_NAME="XAI_API_KEY" ;;
        "volcengine") API_KEY_VAR_NAME="VOLCENGINE_API_KEY" ;;
        "predibase") API_KEY_VAR_NAME="PREDIBASE_API_KEY" ;;
        *) API_KEY_VAR_NAME="${LLM_PROVIDER_SANITIZED}_API_KEY" ;;
    esac

    if [ -n "$API_KEY_VAR_NAME" ]; then
        print_colored "yellow" "Authentication required for provider: $LLM_PROVIDER_RAW"
        if [[ "$LLM_PROVIDER_RAW" == "openai" || "$LLM_PROVIDER_RAW" == "groq" || "$LLM_PROVIDER_RAW" == "anthropic" || \
              "$LLM_PROVIDER_RAW" == "gemini" || "$LLM_PROVIDER_RAW" == "mistral" || "$LLM_PROVIDER_RAW" == "cohere" ]]; then
            while true; do
                read -r -s -p "$API_KEY_VAR_NAME: " API_KEY_VALUE </dev/tty
                echo ""
                if [ -z "$API_KEY_VALUE" ]; then
                    print_colored "red" "$API_KEY_VAR_NAME is required for $LLM_PROVIDER_RAW."
                else
                    break
                fi
            done
        else
            read -r -s -p "$API_KEY_VAR_NAME (optional, press Enter to skip): " API_KEY_VALUE </dev/tty
            echo ""
            if [ -z "$API_KEY_VALUE" ]; then
                API_KEY_VALUE=""
                print_colored "yellow" "ℹ $API_KEY_VAR_NAME not provided. Continuing without it."
            fi
        fi
        export "$API_KEY_VAR_NAME"="$API_KEY_VALUE"
    fi

    read -r -p "Optional self-hosted LLM endpoint (press Enter to skip): " LLM_HOST </dev/tty
    if [ -z "$LLM_HOST" ]; then
        LLM_HOST=""
        print_colored "yellow" "ℹ No LLM_HOST configured."
    fi

    export LLM_MODEL
    export LLM_HOST
}

set_runtime_defaults() {
    if [ -z "$JWT_SECRET" ]; then
        JWT_SECRET=$(openssl rand -base64 32)
        print_colored "green" "✓ JWT secret generated"
    fi

    if [ -z "$REDIS_URL" ]; then
        REDIS_URL="redis://skyflo-ai-redis:6379/0"
        print_colored "yellow" "ℹ Redis: using in-cluster default"
    fi

    if [ -z "$MCP_SERVER_URL" ]; then
        MCP_SERVER_URL="http://skyflo-ai-mcp:8888/mcp"
        print_colored "yellow" "ℹ MCP server: using in-cluster default"
    fi

    if [ -z "$INTEGRATIONS_SECRET_NAMESPACE" ]; then
        INTEGRATIONS_SECRET_NAMESPACE="$NAMESPACE"
    fi

    if [ -z "$POSTGRES_USER" ]; then
        POSTGRES_USER="skyflo"
    fi

    if [ -z "$POSTGRES_PASSWORD" ]; then
        POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=')
        print_colored "green" "✓ Postgres password generated"
    fi

    if [ -z "$POSTGRES_DB" ]; then
        POSTGRES_DB="skyflo"
    fi

    if [ -z "$POSTGRES_PORT" ]; then
        POSTGRES_PORT="5432"
    fi

    if [ -z "$POSTGRES_DATABASE_URL" ]; then
        POSTGRES_DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@skyflo-ai-postgres:${POSTGRES_PORT}/${POSTGRES_DB}"
        print_colored "yellow" "ℹ Postgres: using in-cluster default"
    fi

    export JWT_SECRET
    export POSTGRES_DATABASE_URL
    export REDIS_URL
    export MCP_SERVER_URL
    export INTEGRATIONS_SECRET_NAMESPACE
    export POSTGRES_USER
    export POSTGRES_PASSWORD
    export POSTGRES_DB
    export POSTGRES_PORT
}

apply_k8s_from_file() {
    local file_path="$1"
    envsubst < "$file_path" | kubectl apply -f - || return 1
    return 0
}

print_colored "green" "
Skyflo.ai Kubernetes Installer
Version: ${VERSION}
========================================
"

read -r -p "Target Kubernetes namespace [default: skyflo-ai]: " NAMESPACE </dev/tty
if [ -z "$NAMESPACE" ]; then
    NAMESPACE="skyflo-ai"
    print_colored "yellow" "ℹ No namespace provided. Using 'skyflo-ai'."
fi

export NAMESPACE

print_colored "green" "Validating cluster and prerequisites..."
check_command "kubectl"
check_command "envsubst"
check_command "base64"
check_command "openssl"
check_command "curl"

ensure_namespace_exists "$NAMESPACE"
prompt_llm_configuration
set_runtime_defaults

print_colored "yellow" "Applying Kubernetes manifests..."

TMP_DIR=$(mktemp -d)
REPO_BASE="https://raw.githubusercontent.com/skyflo-ai/skyflo/${VERSION}/deployment"

print_colored "yellow" "Downloading manifests..."
for file in "config/engine-configmap.yaml" "config/mcp-configmap.yaml" "config/ui-configmap.yaml" "install.yaml"; do
    target="${TMP_DIR}/$(basename "$file")"
    if ! curl -fsSL "${REPO_BASE}/${file}" -o "$target"; then
        print_colored "red" "Failed to download ${file}. Check VERSION=${VERSION} exists."
        rm -rf "$TMP_DIR"
        exit 1
    fi
done

print_colored "yellow" "Applying ConfigMaps..."
apply_k8s_from_file "${TMP_DIR}/engine-configmap.yaml" || {
    print_colored "red" "Failed to apply engine ConfigMap. See errors above."
    rm -rf "$TMP_DIR"
    exit 1
}
apply_k8s_from_file "${TMP_DIR}/mcp-configmap.yaml" || {
    print_colored "red" "Failed to apply MCP ConfigMap. See errors above."
    rm -rf "$TMP_DIR"
    exit 1
}
apply_k8s_from_file "${TMP_DIR}/ui-configmap.yaml" || {
    print_colored "red" "Failed to apply UI ConfigMap. See errors above."
    rm -rf "$TMP_DIR"
    exit 1
}
print_colored "green" "✓ ConfigMaps applied"

print_colored "yellow" "Applying core manifests..."
apply_k8s_from_file "${TMP_DIR}/install.yaml" || {
    print_colored "red" "Installation failed. See errors above."
    rm -rf "$TMP_DIR"
    exit 1
}

rm -rf "$TMP_DIR"

print_colored "green" "
Installation successful
=======================
Skyflo.ai has been successfully installed.

Check rollout status:
  kubectl get pods -n $NAMESPACE

Access the UI locally:
  kubectl port-forward -n $NAMESPACE svc/skyflo-ai-ui 3000:80

Production access:
  Configure an Ingress controller.
  Docs: https://github.com/skyflo-ai/skyflo/blob/main/docs/install.md
"
