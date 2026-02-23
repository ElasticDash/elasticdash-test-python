#!/bin/bash
# Create and activate a Python virtual environment in the current directory
# Usage: ./venv.sh

set -e

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created at .venv"
fi

# Activate the virtual environment (for bash/zsh)
echo "To activate the virtual environment, run:"
echo "source .venv/bin/activate"
