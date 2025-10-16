#!/bin/bash

# MCP module test runner
# Usage: ./run_tests.sh [--coverage <threshold>]
# Examples:
#   ./run_tests.sh
#   ./run_tests.sh --coverage 80

set -euo pipefail

# Default values
COVERAGE_THRESHOLD=30

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Usage: $0 [--coverage <threshold>]"
            exit 1
            ;;
    esac
done

echo "🐍 Setting up MCP test environment..."

if [ -f ".venv/bin/activate" ]; then
    echo "🔑 Using existing .venv"
    source .venv/bin/activate

    if command -v uv >/dev/null 2>&1; then
        echo "🔄 Syncing dependencies with uv (including dev extras)"
        uv sync --extra dev
    else
        echo "⚠️  'uv' not found. Installing dev deps with pip"
        python3 -m pip install -e ".[dev]"
    fi
else
    echo "📦 Creating .venv and installing dependencies (per README)"
    python3 -m venv .venv
    source .venv/bin/activate

    if command -v uv >/dev/null 2>&1; then
        echo "📥 Installing with uv (including dev extras)"
        uv sync --extra dev
    else
        echo "📥 Installing with pip (uv not found)"
        python3 -m pip install -e .
        python3 -m pip install -e ".[dev]"
    fi
fi

# Run tests with coverage
echo "🧪 Running tests with coverage (threshold: $COVERAGE_THRESHOLD%)..."
python3 -m pytest tests/ --cov=. --cov-report=term --cov-fail-under="$COVERAGE_THRESHOLD"


echo "✅ MCP tests completed successfully!"
