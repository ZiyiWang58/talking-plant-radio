#!/usr/bin/env bash
set -euo pipefail

# Resolve the repository directory instead of relying on a fixed Pi username.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "ERROR: Python virtual environment not found at ${PYTHON_BIN}"
    echo "Create it with: python3 -m venv .venv"
    exit 1
fi

# Use the current default sink unless PIPEWIRE_SINK is explicitly exported.
AUDIO_SINK="${PIPEWIRE_SINK:-@DEFAULT_AUDIO_SINK@}"
AUDIO_VOLUME="${PIPEWIRE_VOLUME:-60%}"

if [[ "${AUDIO_SINK}" != "@DEFAULT_AUDIO_SINK@" ]]; then
    wpctl set-default "${AUDIO_SINK}"
fi
wpctl set-volume "${AUDIO_SINK}" "${AUDIO_VOLUME}"
wpctl set-mute "${AUDIO_SINK}" 0

cd "${PROJECT_DIR}"
exec "${PYTHON_BIN}" "${PROJECT_DIR}/plant_pi_controller_local_playback.py"
