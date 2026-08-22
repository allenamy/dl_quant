#!/bin/bash
# Build a throwaway FULL copy of the live repo (minus .git) and lay the staged files over it.
# Never touches ~/dl_quant_live. Usage: bash build_scratch.sh [scratch_dir] [--external]
#   --external : flip the scratch copy's config to book_source=external + per_name_stop.active_profile=wide
#                (the operator's L0/L1 switch) so the battery can be proven green in BOTH disk states.
set -uo pipefail
STG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="${LIVE_REPO:-$HOME/dl_quant_live}"
SCR="${1:-/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/live_scratch}"
mkdir -p "$SCR"
rsync -a --delete --exclude .git --exclude __pycache__ --exclude state/pycache_void "$LIVE/" "$SCR/"
[ $? -ne 0 ] && { echo "rsync failed"; exit 1; }
for f in scheduler/anchor_loop.py live/per_name_stop.py live/external_book.py live/tests_external_book.py \
         live/tests_imports.py live/tests_entrypoint_wiring.py live/tests_anchor_skip_visible.py live/tests_signal_and_loop.py live/tests_guard_calibers.py ops/gate_coverage.py run_acceptance.sh config/book.json; do
  cp "$STG/live_repo/$f" "$SCR/$f" || exit 1
done
if [ "${2:-}" = "--external" ]; then
  /usr/bin/python3 - "$SCR/config/book.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["book_source"] = "external"
d.setdefault("per_name_stop", {})["active_profile"] = "wide"
json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
print("  config flipped: book_source=external, per_name_stop.active_profile=wide")
PY
fi
echo "scratch tree: $SCR"
echo "staged files laid over: 12"
(cd "$SCR" && shasum -a 256 scheduler/anchor_loop.py live/external_book.py config/book.json | sed 's/^/  /')
