#!/bin/bash
# Build a throwaway FULL copy of the live repo (minus .git) and lay the staged files over it.
# Never touches ~/dl_quant_live. Usage: bash build_scratch.sh [scratch_dir]
set -uo pipefail
STG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="${LIVE_REPO:-$HOME/dl_quant_live}"
SCR="${1:-/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/live_scratch}"
mkdir -p "$SCR"
rsync -a --delete --exclude .git --exclude __pycache__ --exclude state/pycache_void "$LIVE/" "$SCR/"
[ $? -ne 0 ] && { echo "rsync failed"; exit 1; }
for f in scheduler/anchor_loop.py live/per_name_stop.py live/external_book.py live/tests_external_book.py \
         live/tests_imports.py live/tests_entrypoint_wiring.py live/tests_anchor_skip_visible.py ops/gate_coverage.py run_acceptance.sh config/book.json; do
  cp "$STG/live_repo/$f" "$SCR/$f" || exit 1
done
echo "scratch tree: $SCR"
echo "staged files laid over: 10"
(cd "$SCR" && shasum -a 256 scheduler/anchor_loop.py live/external_book.py config/book.json | sed 's/^/  /')
