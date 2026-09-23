#!/bin/bash
# FP3 item C part 2 (2026-09-17): per-anchor snapshot of the producer's ROLLING state, so that any anchor can be replayed later in a sandbox and compared
# with the archived target_live/<A>.json (production whole-book parity). The three rolling files (state/aux.json, state/rolling.npz,
# state/leg_returns_live.json) and their generation.json commit marker are rewritten by the king pipeline every anchor and were never archived; combo_stage reads exactly these plus
# per-anchor files that ARE archived (state/weights/<A-4h>.npz, fea171/state_H_*_<A-4h>.npz, target_live/<A>.json). Copies are taken only AFTER
# combo_live_status.json reports anchor A (i.e. after the combo run), into state/snap/<A>/ with sha256 sidecars; never touches any producer file.
# Runs as a launchd agent (com.hsy.combosnap) polling every 60 s; idempotent (a complete snapshot dir is never rewritten). Retention: 21 days.
# NC release (DESIGN_producer_new_contract §A7 addendum, lead 2026-09-23): the files copied are exactly the ones the producer's generation.json
# commits (combosnap/generation_files.py), plus generation.json and combo_live_status.json — 3 state files for the old producer, 5 for the new one.
set -u
WS="${WIDE_SHADOW_HOME:-$HOME/wide_shadow}"; CHECK="$WS/fea171/combosnap/check_snapshot_generation.py"; SNAP="$WS/state/snap"; mkdir -p "$SNAP"
A=$("$WS/venv/bin/python" -c "import json;print((lambda d: d.get('anchor') if d.get('step') == 'done' and d.get('ok') else 0)(json.load(open('$WS/state/combo_live_status.json'))) or 0)" 2>/dev/null || echo 0)
[ "$A" -gt 0 ] || exit 0
D="$SNAP/$A"
if [ -f "$D/COMPLETE" ]; then
  # Legacy history is unavailable, but the periodic job has nothing to repair.
  # A dangling marker is an existing invalid marker, not a legacy omission.
  if [ ! -e "$D/generation.json" ] && [ ! -L "$D/generation.json" ]; then
    echo "UNAVAILABLE_LEGACY_SNAPSHOT anchor=$A (unchanged; no parity certification)"
    exit 0
  fi
  "$WS/venv/bin/python" "$CHECK" "$D" "$A" || exit 3
  exit 0
fi
"$WS/venv/bin/python" "$CHECK" "$WS/state" "$A" || exit 3
AA=$("$WS/venv/bin/python" -c "import json;print(json.load(open('$WS/state/aux.json'))['prev_rec']['anchor_ts'])" 2>/dev/null || echo 0)
[ "$AA" = "$A" ] || exit 0                                   # rolling state is not (or no longer) the one combo read for A ⇒ do not snapshot a wrong state
GF=$("$WS/venv/bin/python" "$WS/fea171/combosnap/generation_files.py" "$WS/state/generation.json") || exit 3   # the signed state files, e.g. aux.json leg_returns_live.json rolling.npz [boundary_raw.npz members_hist.npz]
FILES="$GF generation.json"
mkdir -p "$D.tmp" || exit 1
PRE=$(cd "$WS/state" && shasum -a 256 $FILES)                                    # source bytes BEFORE the copy
for f in $FILES combo_live_status.json; do cp "$WS/state/$f" "$D.tmp/$f" || { rm -rf "$D.tmp"; exit 1; }; done
POST=$(cd "$WS/state" && shasum -a 256 $FILES)                                   # … and AFTER: a file being rewritten is never snapshotted
[ "$PRE" = "$POST" ] || { rm -rf "$D.tmp"; exit 0; }
GF2=$("$WS/venv/bin/python" "$WS/fea171/combosnap/generation_files.py" "$D.tmp/generation.json") || { rm -rf "$D.tmp"; exit 3; }
[ "$GF2" = "$GF" ] || { rm -rf "$D.tmp"; exit 0; }            # the marker's file set changed between reading it and copying ⇒ the writer moved on
( cd "$D.tmp" && shasum -a 256 $FILES combo_live_status.json > SHA256SUMS ) || exit 1
( cd "$D.tmp" && echo "$PRE" | shasum -a 256 -c --quiet - ) || { rm -rf "$D.tmp"; exit 0; }                        # the copies are the source bytes
AA2=$("$WS/venv/bin/python" -c "import json;print(json.load(open('$D.tmp/aux.json'))['prev_rec']['anchor_ts'])" 2>/dev/null || echo 0)
[ "$AA2" = "$A" ] || { rm -rf "$D.tmp"; exit 0; }             # the writer moved on while we copied ⇒ discard (next anchor's snapshot will be its own)
"$WS/venv/bin/python" "$CHECK" "$D.tmp" "$A" || { rm -rf "$D.tmp"; exit 3; }  # signed bytes, strict integer axis ending at A
date -u +%FT%TZ > "$D.tmp/COMPLETE" && mv "$D.tmp" "$D" || exit 1
find "$SNAP" -maxdepth 1 -mindepth 1 -type d -mtime +21 -exec rm -rf {} + 2>/dev/null
echo "snap $A $(date -u +%FT%TZ)" >> "$SNAP/snap.log"
