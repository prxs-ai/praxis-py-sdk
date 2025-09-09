#!/bin/bash
set -e

# Ensure Poetry is in the path
export PATH="/usr/local/bin:$PATH"

# Install dependencies if not already installed
if ! poetry run python -c "import trio" 2>/dev/null; then
    echo "Installing dependencies..."
    poetry install --with dev
fi

# Run the command passed as arguments
exec poetry run "$@"