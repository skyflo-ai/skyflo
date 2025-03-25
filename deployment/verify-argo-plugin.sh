#!/bin/bash
set -e

echo "Verifying kubectl installation..."
kubectl version --client

echo "Checking kubectl plugins..."
kubectl plugin list

echo "Verifying kubectl-argo-rollouts plugin..."
if ! kubectl argo rollouts version 2>/dev/null; then
  echo "ERROR: kubectl-argo-rollouts plugin is not correctly installed!"
  exit 1
else
  echo "✅ kubectl-argo-rollouts plugin is correctly installed"
fi

echo "Testing argo rollouts command execution..."
echo "Command: kubectl argo rollouts help"
kubectl argo rollouts help

echo "All verification steps passed successfully! 🎉" 