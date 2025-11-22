#!/usr/bin/env bash
set -euo pipefail

# Make sure the script runs from the repository root.
cd "$(dirname "$0")/.."

# Prefer the project virtualenv python, then python3, then python.
python_bin="${PYTHON_BIN:-$(
  if [ -x ".venv/bin/python" ]; then
    printf "%s" ".venv/bin/python"
  else
    command -v python3 2>/dev/null || command -v python 2>/dev/null || true
  fi
)}"
if [ -z "$python_bin" ]; then
  echo "Python interpreter not found. Install python3 (recommended) or set PYTHON_BIN."
  exit 1
fi

mapfile -t python_files < <(git ls-files '*.py')

function run_step() {
  echo
  echo ">>> $1"
  shift
  "$@" || exit 1
}

if [ "${#python_files[@]}" -eq 0 ]; then
  echo ">>> No Python files to lint"
else
  run_step "Running Pylint" "$python_bin" -m pylint "${python_files[@]}"
fi
run_step "Formatting with Black" "$python_bin" -m black .
run_step "Checking import sorting with isort" "$python_bin" -m isort --check-only . --profile black
run_step "Running mypy" "$python_bin" -m mypy src tests
run_step "Running Bandit security scan" "$python_bin" -m bandit -r src tests -s B101
run_step "Upgrading pip" "$python_bin" -m pip install --upgrade pip
run_step "Running pip-audit" "$python_bin" -m pip_audit
run_step "Running pytest with coverage" "$python_bin" -m pytest --cov=. --cov-report=term-missing
