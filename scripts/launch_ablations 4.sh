#!/usr/bin/env bash
# Launch the 8-configuration ablation sweep on pod. Only run if V4 full
# has cleared the 0.12 primary bar — do NOT chain from postprocess.
#
# Usage (from local): ./scripts/launch_ablations.sh
set -euo pipefail

HOST="213.192.2.108"
PORT="40087"
KEY="$HOME/.ssh/runpod_ed25519"

# Gate: require docs/V4_RESULTS_AUTO.md to show PRIMARY PASS: YES
if ! grep -q 'PRIMARY PASS: YES' docs/V4_RESULTS_AUTO.md 2>/dev/null; then
  echo "❌ docs/V4_RESULTS_AUTO.md does not show PRIMARY PASS: YES."
  echo "   Not launching ablations — V4 full must clear the 0.12 bar first."
  exit 1
fi

echo "✅ Primary pass confirmed. Launching 8-ablation sweep on pod …"

# Make sure pod has the latest branch (scripts may have changed since training started)
ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no root@"$HOST" \
  "cd /workspace/quant_research && git fetch origin siyu_dev_2 && git reset --hard origin/siyu_dev_2 && git log -1 --oneline"

# Kick off the ablation runner
ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no root@"$HOST" \
  "cd /workspace/quant_research && \
   nohup python3 scripts/run_ablations.py > logs/ablations.log 2>&1 & \
   echo ablation_pid=\$!"

echo "Ablation sweep kicked off. Tail logs/ablations.log on pod to track."
