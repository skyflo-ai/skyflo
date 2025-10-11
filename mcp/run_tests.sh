#!/bin/bash

# MCP module test runner
# Usage: ./run_tests.sh [--coverage <threshold>]
# Examples:
#   ./run_tests.sh
#   ./run_tests.sh --coverage 80

set -e

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

# Check if virtual environment exists, create if not
if [ ! -f "test_env/bin/activate" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv test_env
fi

# Activate virtual environment
source test_env/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -e ".[dev]" > /dev/null 2>&1

# Run tests with coverage
echo "🧪 Running tests with coverage (threshold: $COVERAGE_THRESHOLD%)..."
python3 -m pytest tests/ --cov=. --cov-report=term --cov-fail-under="$COVERAGE_THRESHOLD"


echo "✅ MCP tests completed successfully!"
