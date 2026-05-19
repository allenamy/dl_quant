#!/bin/bash
# Execute a command on the RunPod pod via direct TCP SSH.
# Usage: ./scripts/runpod_exec.sh "your command"
set -euo pipefail

RUNPOD_HOST="${RUNPOD_HOST:-213.192.2.84}"
RUNPOD_PORT="${RUNPOD_PORT:-40007}"
RUNPOD_USER="${RUNPOD_USER:-root}"
RUNPOD_KEY="${RUNPOD_KEY:-$HOME/.ssh/runpod_ed25519}"

ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
    -i "$RUNPOD_KEY" -p "$RUNPOD_PORT" "${RUNPOD_USER}@${RUNPOD_HOST}" \
    "$1" 2>&1 | grep -vE "^(WARNING:|\*\* WARNING|\*\* This|\*\* The|may be vulnerable|post-quantum|See https://openssh)"
