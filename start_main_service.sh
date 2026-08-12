#!/usr/bin/env bash
set -euo pipefail

# Resolve the repository directory instead of relying on a fixed Pi username.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

# Wait for the user audio session to become available after boot.
for attempt in $(seq 1 60); do
    if wpctl status >/dev/null 2>&1; then
        exec "${PROJECT_DIR}/start_demo.sh"
    fi
    sleep 2
done

echo "ERROR: PipeWire was not ready after 120 seconds."
exit 1
