#!/bin/bash

# Test runner script for Skyflo project
# Usage: ./run_tests.sh --folder <folder> [--coverage <threshold>]
# Examples:
#   ./run_tests.sh --folder mcp
#   ./run_tests.sh --folder mcp --coverage 50

set -e

# Default values
FOLDER=""
COVERAGE_THRESHOLD=0

# Parse named arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --folder)
            FOLDER="$2"
            shift 2
            ;;
        --coverage)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Usage: $0 --folder <folder> [--coverage <threshold>]"
            echo "Examples:"
            echo "  $0 --folder mcp"
            echo "  $0 --folder mcp --coverage 50"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$FOLDER" ]; then
    echo "❌ Error: Folder name is required"
    echo "Usage: $0 --folder <folder> [--coverage <threshold>]"
    echo "Example: $0 --folder mcp --coverage 50"
    exit 1
fi

echo "🚀 Starting tests for $FOLDER..."

# Validate folder exists
if [ ! -d "$FOLDER" ]; then
    echo "❌ Error: Folder '$FOLDER' does not exist"
    exit 1
fi

# Change to the target directory
cd "$FOLDER"

# Activate virtual environment
echo "📦 Activating virtual environment..."

if [ ! -f test_env/bin/activate ]; then
    echo "❌ Error: Virtual environment not found at test_env/bin/activate"
    echo "Please activate it first"
    exit 1
fi

source test_env/bin/activate

echo "🧪 Running tests with coverage..."
python -m pytest tests/ --cov=. --cov-report=term --cov-fail-under="$COVERAGE_THRESHOLD"

echo "✅ Tests completed successfully!"
