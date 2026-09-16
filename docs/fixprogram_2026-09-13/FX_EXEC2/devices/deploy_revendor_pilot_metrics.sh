#!/bin/bash
# DEPLOY STEP (not to be run before the review package is accepted) — re-vendor `pilot_metrics.py` into the research
# repo in the SAME non-anchor window as the executor deploy, and check the drift gate on both sides of the copy.
#
# ★★★ WHY THIS IS A DEPLOY STEP AND NOT A CLEANUP. LED-01 1/3 re-froze `live/pilot_metrics.py` (the collapse key
#     became (symbol, trade_id)). That breaks the invariant `manifest[pilot_metrics.py] == metrics_freeze sha` unless
#     BOTH pins move, and it makes the research repo's vendored copy stale. The direction for this one file is
#     **production -> research** (docs/VENDORED_MAP.md §"pilot_metrics.py 的特殊裁定"): the executor's copy is the
#     upstream. Copying the other way would overwrite the freshly frozen bytes and break the freeze chain — which is
#     why VENDORED_MAP makes `direction` a field and not a comment.
#   ⇒ Re-vendor EARLY and the RUNNING tree's drift gate goes red. Re-vendor LATE and the NEW tree's gate goes red.
#     There is no ordering that avoids a red gate except doing both in one window, executor first.
#
# ★★ THE EXPECTED RED, BEFORE THIS RUNS, IS DOCUMENTED AND MUST NOT BE "FIXED" LOCALLY. Measured 2026-09-16:
#     ops/check_upstream_drift.py rc=1, and live/tests_drift_gate.py rc=1 with exactly ONE red cell
#     ("it states its DENOMINATOR"). The gate's own message says it: "the RESEARCH side fell behind this repo's file
#     — do NOT 'fix' the local copy, it is the upstream for this file".
#
# Order at deploy:
#   1. executor: ops/safe_commit.sh with the stacked tree (outside an anchor window)
#   2. THIS script, same window
#   3. re-run both gates; both must be green
#
# Usage: deploy_revendor_pilot_metrics.sh <executor_tree> [--apply]
#        without --apply it only REPORTS what it would do and what the gates say now.
set -u
TREE="$1"; APPLY="${2:-}"
RESEARCH=/Users/haosiyu/Desktop/quant_research
SRC="$TREE/live/pilot_metrics.py"
DST="$RESEARCH/multi_asset/engine/live/pilot_metrics.py"
WANT=cd508c3f6a2727cca83666f0fab831a9249ff9279323ac96d0bef3e5dd1cacd6

say() { echo "[$(date -u '+%H:%M:%SZ')] $*"; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }

[ -r "$SRC" ] || { say "REFUSED: cannot read $SRC"; exit 2; }
[ -r "$DST" ] || { say "REFUSED: cannot read $DST"; exit 2; }

S=$(sha "$SRC"); D=$(sha "$DST")
say "executor copy (upstream for this file): $S"
say "research  copy (vendored)             : $D"
say "expected after re-vendor              : $WANT"

# ★ the three pins must already agree with each other on the executor side, or the copy would propagate a
#   disagreement rather than resolve one
M=$(grep -E '^[0-9a-f]{64}[[:space:]]+pilot_metrics\.py' "$TREE/ops/UPSTREAM_MANIFEST.sha256" | awk '{print $1}')
F=$(/usr/bin/python3 -c "import json;print(json.load(open('$TREE/config/metrics_freeze.json'))['pilot_metrics_sha256'])")
say "UPSTREAM_MANIFEST pin                 : $M"
say "config/metrics_freeze pin             : $F"
[ "$S" = "$WANT" ] || { say "REFUSED: the executor copy is not the expected re-frozen bytes"; exit 2; }
[ "$M" = "$WANT" ] || { say "REFUSED: UPSTREAM_MANIFEST does not pin the expected bytes"; exit 2; }
[ "$F" = "$WANT" ] || { say "REFUSED: metrics_freeze does not pin the expected bytes (the LED-01 1/3 invariant)"; exit 2; }

say "--- drift gate BEFORE (expected: rc 1, research side behind) ---"
( cd "$TREE" && /usr/bin/python3 -B ops/check_upstream_drift.py ); say "check_upstream_drift rc=$?"
( cd "$TREE" && /usr/bin/python3 -B live/tests_drift_gate.py > /tmp/tdg_before.$$ 2>&1 ); say "tests_drift_gate rc=$?"
grep -E '^  FAIL' /tmp/tdg_before.$$ | head -3; rm -f /tmp/tdg_before.$$

if [ "$APPLY" != "--apply" ]; then
  say "REPORT ONLY (pass --apply to perform the copy). Nothing was written."
  exit 0
fi

cp -p "$DST" "$DST.bak_$(date -u '+%Y%m%dT%H%M%SZ')"
cp -p "$SRC" "$DST"
say "copied; research copy is now $(sha "$DST")"
[ "$(sha "$DST")" = "$WANT" ] || { say "FAILED: the copy did not land as the expected bytes"; exit 3; }

say "--- drift gate AFTER (both must be green) ---"
( cd "$TREE" && /usr/bin/python3 -B ops/check_upstream_drift.py ); RC1=$?; say "check_upstream_drift rc=$RC1"
( cd "$TREE" && /usr/bin/python3 -B live/tests_drift_gate.py ); RC2=$?; say "tests_drift_gate rc=$RC2"
say "commit the research side with an explicit pathspec: git -C $RESEARCH add multi_asset/engine/live/pilot_metrics.py"
[ "$RC1" = 0 ] && [ "$RC2" = 0 ] || { say "FAILED: a gate is still red after the re-vendor"; exit 4; }
say "DONE — both gates green"
