#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in the repository root
d=$(dirname "$0")
cd "$d/.."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

# Activate the virtual environment
# shellcheck disable=SC1091
source .venv/bin/activate

# Install Python dependencies
pip install .

# Install Node dependencies and build CSS
npm install
npm run build:css
