#!/bin/bash
# FP3 item C part 2 (2026-09-17): per-anchor snapshot of the producer's ROLLING state, so that any anchor can be replayed later in a sandbox and compared
# with the archived target_live/<A>.json (production whole-book parity). The three rolling files (state/aux.json, state/rolling.npz,
# state/leg_returns_live.json) are rewritten by the king pipeline every anchor and were never archived; combo_stage reads exactly these plus
# per-anchor files that ARE archived (state/weights/<A-4h>.npz, fea171/state_H_*_<A-4h>.npz, target_live/<A>.json). Copies are taken only AFTER
# combo_live_status.json reports anchor A (i.e. after the combo run), into state/snap/<A>/ with sha256 sidecars; never touches any producer file.
# Runs as a launchd agent (com.hsy.combosnap) polling every 60 s; idempotent (a complete snapshot dir is never rewritten). Retention: 21 days.
set -u
WS="$HOME/wide_shadow"; SNAP="$WS/state/snap"; mkdir -p "$SNAP"
A=$("$WS/venv/bin/python" -c "import json;print(json.load(open('$WS/state/combo_live_status.json')).get('anchor_ts') or 0)" 2>/dev/null || echo 0)
[ "$A" -gt 0 ] || exit 0
D="$SNAP/$A"; [ -f "$D/COMPLETE" ] && exit 0
AA=$("$WS/venv/bin/python" -c "import json;print(json.load(open('$WS/state/aux.json'))['prev_rec']['anchor_ts'])" 2>/dev/null || echo 0)
[ "$AA" = "$A" ] || exit 0                                   # rolling state is not (or no longer) the one combo read for A ⇒ do not snapshot a wrong state
mkdir -p "$D.tmp" || exit 1
for f in aux.json rolling.npz leg_returns_live.json combo_live_status.json; do cp "$WS/state/$f" "$D.tmp/$f" || exit 1; done
( cd "$D.tmp" && shasum -a 256 aux.json rolling.npz leg_returns_live.json combo_live_status.json > SHA256SUMS ) || exit 1
AA2=$("$WS/venv/bin/python" -c "import json;print(json.load(open('$D.tmp/aux.json'))['prev_rec']['anchor_ts'])" 2>/dev/null || echo 0)
[ "$AA2" = "$A" ] || { rm -rf "$D.tmp"; exit 0; }             # the writer moved on while we copied ⇒ discard (next anchor's snapshot will be its own)
date -u +%FT%TZ > "$D.tmp/COMPLETE" && mv "$D.tmp" "$D" || exit 1
find "$SNAP" -maxdepth 1 -mindepth 1 -type d -mtime +21 -exec rm -rf {} + 2>/dev/null
echo "snap $A $(date -u +%FT%TZ)" >> "$SNAP/snap.log"
