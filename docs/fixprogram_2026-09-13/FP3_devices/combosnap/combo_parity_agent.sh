#!/bin/bash
# FP3 item C part 2 (2026-09-17): for every rolling-state snapshot without a parity receipt, replay the producer in a sandbox and compare with the
# archived target (combo_parity_replay.sh). Receipt: state/snap/<A>/PARITY.json (+ PARITY.run.log); the sandbox is removed afterwards. Never touches
# any producer or executor file. launchd agent com.hsy.comboparity, every 300 s; one anchor per run (≈10 s), serialized by a lock dir.
set -u
WS="$HOME/wide_shadow"; SNAP="$WS/state/snap"; DEV="$WS/fea171/combosnap"; LOCK="$SNAP/.parity.lock"
mkdir "$LOCK" 2>/dev/null || exit 0                          # ★ R08: `mkdir` WITHOUT -p is the mutex (fails when the dir exists); -p succeeded on an existing dir and let two agents run the same anchor
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
for d in $(ls -d "$SNAP"/1[0-9]* 2>/dev/null | sort); do
  A=$(basename "$d"); [ -f "$d/COMPLETE" ] || continue; [ -f "$d/PARITY.json" ] && continue
  [ -f "$WS/state/target_live_king/$A.json" ] || continue     # the combo did not run for A (king form traded) ⇒ nothing to replay; left without receipt on purpose
  bash "$DEV/combo_parity_replay.sh" "$A" "$d/PARITY.json" "$HOME/cc_tmp/parity" > "$d/PARITY.run.log" 2>&1; RC=$?
  echo "parity $A rc=$RC $(date -u +%FT%TZ) $(tail -1 "$d/PARITY.run.log" | cut -c1-160)" >> "$SNAP/parity.log"
  rm -rf "$HOME/cc_tmp/parity/$A"
  exit 0
done
