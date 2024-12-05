#!/bin/bash
# Exit on any error
set -e

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements/requirements.txt
uv pip install -r requirements/requirements-dev.txt
uv pip install -r requirements/requirements-test.txt

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
uv pip install pre-commit
pre-commit install

echo "Setup complete! Activate your virtual environment with:"
echo "source .venv/bin/activate"
