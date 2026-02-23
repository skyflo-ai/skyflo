#!/bin/bash

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

# Fetch latest version from GitHub
LATEST_VERSION=$(curl -sL --connect-timeout 10 --max-time 30 https://api.github.com/repos/skyflo-ai/skyflo/releases/latest \
    | grep -m 1 '"tag_name":' \
    | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')

if [ -z "$LATEST_VERSION" ]; then
    print_colored "red" "Warning: failed to determine the latest release version."
    LATEST_VERSION="unknown"
fi

print_colored "yellow" "
Skyflo.ai Kubernetes Uninstaller
================================
"

# Version selection
if [ -z "$VERSION" ]; then
    if [ "$LATEST_VERSION" != "unknown" ]; then
        printf "Version to uninstall [default: %s]: " "$LATEST_VERSION"
    else
        printf "Version to uninstall (e.g., v0.5.0): "
    fi
    read -r INPUT_VERSION </dev/tty 2>/dev/null || INPUT_VERSION=""

    if [ -z "$INPUT_VERSION" ]; then
        if [ "$LATEST_VERSION" = "unknown" ]; then
            print_colored "red" "No version specified and latest release could not be resolved."
            print_colored "yellow" "Set VERSION explicitly, e.g.: VERSION=v0.5.0 ./uninstall.sh"
            exit 1
        fi
        VERSION="$LATEST_VERSION"
        print_colored "yellow" "ℹ Using latest release: $VERSION"
    else
        VERSION="$INPUT_VERSION"
        print_colored "yellow" "ℹ Using specified version: $VERSION"
    fi
else
    print_colored "yellow" "ℹ Using pre-configured version: $VERSION"
fi

export VERSION

# Namespace configuration
if [ -z "$NAMESPACE" ]; then
    printf "Target Kubernetes namespace [default: skyflo-ai]: "
    read -r NAMESPACE </dev/tty 2>/dev/null || NAMESPACE=""
    if [ -z "$NAMESPACE" ]; then
        NAMESPACE="skyflo-ai"
        print_colored "yellow" "ℹ Using default namespace: skyflo-ai"
    else
        print_colored "yellow" "ℹ Using namespace: $NAMESPACE"
    fi
else
    print_colored "yellow" "ℹ Using pre-configured namespace: $NAMESPACE"
fi

export NAMESPACE

REPO_BASE="https://raw.githubusercontent.com/skyflo-ai/skyflo/${VERSION}/deployment"

print_colored "yellow" "Removing Skyflo.ai resources from the cluster..."

delete_manifest() {
    local url="$1"
    if ! curl -fsSL "$url" 2>/dev/null | envsubst | kubectl delete --ignore-not-found -f - 2>/dev/null; then
        print_colored "yellow" "Warning: Failed to delete manifest from $url (may not exist)"
    fi
}

delete_manifest "${REPO_BASE}/config/engine-configmap.yaml"
delete_manifest "${REPO_BASE}/config/mcp-configmap.yaml"
delete_manifest "${REPO_BASE}/config/ui-configmap.yaml"
delete_manifest "${REPO_BASE}/install.yaml"

print_colored "green" "✓ Core Skyflo.ai resources removed"

print_colored "yellow" "
Data cleanup (optional)
-----------------------
Deleting PVCs will permanently remove all persisted data, including:
  - PostgreSQL data (users, conversations, configuration)
  - Redis data (cache, sessions)
"
printf "Delete persistent volumes? [y/N]: "
read -r DELETE_PVCS </dev/tty 2>/dev/null || DELETE_PVCS="n"

if [[ "$DELETE_PVCS" =~ ^[Yy]$ ]]; then
    print_colored "yellow" "Deleting persistent volumes..."
    kubectl delete pvc -l app=skyflo-ai-postgres -n "$NAMESPACE"
    kubectl delete pvc -l app=skyflo-ai-redis -n "$NAMESPACE"
    print_colored "green" "✓ Persistent volumes deleted"
else
    print_colored "yellow" "ℹ Persistent volumes retained. Data remains intact."
fi

print_colored "green" "
Skyflo.ai uninstallation complete
"
