#!/bin/bash
# Commit 5 (comment-only follow-up to 4dd7d53): (1) compiled-code identity of live/beta_overlay.py 4dd7d53 vs HEAD
# (+ two negative controls that MUST come out DIFFERENT), (2) every suite that reads source TEXT (census / import / scope /
# scanner suites) re-run on the new commit in the battery's clone (live state copied), same interpreter and env as run_targeted.sh.
set -u
M3=$HOME/cc_tmp/m3_impl_20260923; X=$M3/exec; DEV=$(cd "$(dirname "$0")" && pwd); OUT=$M3/receipts/c5; mkdir -p "$OUT"
git -C "$X" show 4dd7d53:live/beta_overlay.py > "$OUT/beta_overlay_4dd7d53.py"
git -C "$X" show HEAD:live/beta_overlay.py > "$OUT/beta_overlay_HEAD.py"
echo "HEAD=$(git -C "$X" rev-parse --short HEAD)"
/usr/bin/python3 "$DEV/code_identity.py" "$OUT/beta_overlay_4dd7d53.py" "$OUT/beta_overlay_HEAD.py" live/beta_overlay.py; echo "IDENTITY_EXIT=$?"
sed 's/^TARGET_DIAG_REL_TOL = 1e-9$/TARGET_DIAG_REL_TOL = 1e-8/' "$OUT/beta_overlay_HEAD.py" > "$OUT/neg_const.py"
/usr/bin/python3 "$DEV/code_identity.py" "$OUT/beta_overlay_4dd7d53.py" "$OUT/neg_const.py" live/beta_overlay.py; echo "NEG_CONST_EXIT=$? (must be 1)"
sed 's/^Pure functions only: no file,/Pure functions only: no files,/' "$OUT/beta_overlay_HEAD.py" > "$OUT/neg_doc.py"
/usr/bin/python3 "$DEV/code_identity.py" "$OUT/beta_overlay_4dd7d53.py" "$OUT/neg_doc.py" live/beta_overlay.py; echo "NEG_DOC_EXIT=$? (must be 1)"
git -C "$X" diff --stat 4dd7d53 HEAD | tail -1
# tests_acceptance_entrypoints is NOT in this list: run standalone it executes `bash run_acceptance.sh` (the WHOLE battery,
# outside the offline kernel sandbox). The first run of this device included it by mistake (11:20:03Z; stopped with
# TaskStop at ~11:30Z, see IMPL §4.5); it does not read live/beta_overlay.py and is green in the 4dd7d53 battery.
SUITES="live/tests_beta_overlay.py live/tests_rehearsal_anchor.py live/tests_imports.py live/tests_scoped_writes.py live/tests_venue_fills.py live/tests_guard_reach.py live/tests_harvest_ema.py live/tests_external_book.py live/tests_daily_summary.py live/tests_disposition_matrix.py live/tests_k_window.py live/tests_ledger_notary.py live/tests_reject_topup.py live/tests_static_names.py ops/gate_coverage.py ops/guard_reach.py"
for s in $SUITES; do
  log="$OUT/$(echo $s | tr / _).log"
  ( cd "$X/$(dirname $s)" && /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=$HOME LIVE_MODE=DRY_RUN PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 nice -n 10 /usr/bin/python3 "$(basename $s)" ) > "$log" 2>&1
  echo "$s EXIT=$?"
done
