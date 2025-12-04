#!/bin/bash

export VERSION=v0.3.2

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

print_colored "yellow" "Uninstalling Skyflo.ai..."


# Namespace configuration
read -p "Enter the name of your configured kubernetes namespace (press Enter for default 'skyflo-ai'): " NAMESPACE
if [ -z "$NAMESPACE" ]; then
    NAMESPACE="skyflo-ai"
    print_colored "yellow" "ℹ processing the removal of the default namespace: skyflo-ai"
else
    print_colored "yellow" "ℹ processing the removal of the configured namespace: $NAMESPACE"
fi


export NAMESPACE

print_colored "yellow" "ℹ processing the removal of the skyflo.ai deployment"
envsubst < curl -sL "https://raw.githubusercontent.com/skyflo-ai/skyflo/main/deployment/install.yaml"  | kubectl delete -f -

print_colored "yellow" "ℹ processing the removal of the skyflo.ai pvc"
kubectl delete pvc -l app=skyflo-ai-postgres -n $NAMESPACE
kubectl delete pvc -l app=skyflo-ai-redis -n $NAMESPACE

print_colored "green" "ℹ skyflo.ai uninstalled successfully"