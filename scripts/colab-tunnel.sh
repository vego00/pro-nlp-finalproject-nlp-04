#!/usr/bin/env bash
# Run from the same WSL environment as FastAPI. No installation or downloads.
set -euo pipefail

if [[ $# -eq 0 ]]; then
    echo "Usage: bash scripts/colab-tunnel.sh [-p SSH_PORT] [-i KEY_PATH] USER@SSH_HOST" >&2
    exit 2
fi

exec ssh -N -T \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -L 127.0.0.1:11435:127.0.0.1:11434 \
    "$@"
