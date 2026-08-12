#!/usr/bin/env bash
set -euo pipefail

# Start the phone-friendly status page from the repository virtual environment.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "ERROR: Python virtual environment not found at ${PYTHON_BIN}"
    exit 1
fi

cd "${PROJECT_DIR}"
exec "${PYTHON_BIN}" "${PROJECT_DIR}/display_server.py"
