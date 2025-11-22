#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in the repository root
d=$(dirname "$0")
cd "$d/.."

# Prefer python3 but fall back to python to create the virtualenv.
python_bin="${PYTHON_BIN:-$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)}"
if [ -z "$python_bin" ]; then
  echo "Python interpreter not found. Install python3 (recommended) or set PYTHON_BIN."
  exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  "$python_bin" -m venv .venv
fi

# Activate the virtual environment
# shellcheck disable=SC1091
source .venv/bin/activate

# Install Python dependencies, including development extras needed for the CI suite
pip install .[dev]

# Install Node dependencies and build CSS
npm install
npm run build:css
