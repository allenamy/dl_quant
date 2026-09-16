#!/bin/bash
# FX-W6C full-battery driver, 2026-09-16. Implements the lead's battery rule in full:
#   · start ONLY between N+65min and N+3h15m of a 4h anchor (00/04/08/12/16/20Z)
#   · hold /Users/haosiyu/cc_tmp/BATTERY.lock (name, PID, tree sha, start time); WAIT if it exists
#   · assert no .env and that the mode is DRY_RUN
#   · record the request weight of the public GETs the DRY run_anchor makes
#   · restore state/ afterwards (untracked residue removed, tracked files checked)
# It binds the result to the tree AT LAUNCH and reads the summary line and rc at the end.
set -u
C=/Users/haosiyu/cc_tmp/fx_w6c
LOCK=/Users/haosiyu/cc_tmp/BATTERY.lock
OUTDIR=/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FX_W6C/receipts
TAG=${1:-final}

# ── window ────────────────────────────────────────────────────────────────────────────────
HH=$((10#$(date -u +%H))); MM=$((10#$(date -u +%M)))
MIN_SINCE=$(( (HH % 4) * 60 + MM ))
if [ "$MIN_SINCE" -lt 65 ] || [ "$MIN_SINCE" -gt 195 ]; then
  echo "REFUSE: $(date -u +%H:%M)Z is N+${MIN_SINCE}min — the window is N+65min..N+3h15m"; exit 3
fi
# ── lock ──────────────────────────────────────────────────────────────────────────────────
if [ -e "$LOCK" ]; then
  echo "REFUSE: $LOCK is held:"; cat "$LOCK"; exit 4
fi
TREE=$(git -C $C rev-parse HEAD^{tree})
HEAD_SHA=$(git -C $C rev-parse HEAD)
{ echo "name=FX-W6C"; echo "pid=$$"; echo "tree=$TREE"; echo "head=$HEAD_SHA";
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "clone=$C"; } > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
# ── preconditions ─────────────────────────────────────────────────────────────────────────
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$OUTDIR/battery_${TAG}_${TS}.log
META=$OUTDIR/battery_${TAG}_${TS}.meta
{
  echo "START $(date -u +%Y-%m-%dT%H:%M:%SZ)  (N+${MIN_SINCE}min)"
  echo "head_at_start      $HEAD_SHA"
  echo "tree_at_start      $TREE"
  echo "env_file_present   $( [ -e $C/.env ] && echo YES || echo no )"
  echo "LIVE_MODE_env      ${LIVE_MODE:-<unset, defaults to DRY_RUN>}"
  echo "tracked_changes_outside_state_at_start $(git -C $C status --porcelain -- . ':!state' | wc -l | tr -d ' ')"
  echo "untracked_under_state_at_start $(git -C $C status --porcelain -- state | wc -l | tr -d ' ')"
  echo "interpreter        $(/usr/bin/python3 -V 2>&1) (run_acceptance.sh pins /usr/bin/python3)"
} > "$META"
if [ -e "$C/.env" ]; then echo "REFUSE: $C/.env exists" | tee -a "$META"; exit 5; fi
if [ "${LIVE_MODE:-DRY_RUN}" != "DRY_RUN" ]; then echo "REFUSE: LIVE_MODE=${LIVE_MODE}" | tee -a "$META"; exit 6; fi
# ── run ───────────────────────────────────────────────────────────────────────────────────
(cd "$C" && env -u LIVE_MODE bash run_acceptance.sh > "$LOG" 2>&1); BRC=$?
# ── after ─────────────────────────────────────────────────────────────────────────────────
{
  echo "END   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "battery_rc $BRC"
  echo "head_at_end        $(git -C $C rev-parse HEAD)"
  echo "tree_at_end        $(git -C $C rev-parse HEAD^{tree})"
  echo "tracked_changes_outside_state_at_end $(git -C $C status --porcelain -- . ':!state' | wc -l | tr -d ' ')"
  echo "summary_line: $(grep -E 'ACCEPTANCE' "$LOG" | tail -1)"
  echo "n_suite_rows: $(grep -cE '^tests_|^[a-z_]+ +[01] ' "$LOG" || true)"
  echo "--- public venue requests this run made (the ruling's 'record request weight') ---"
  grep -niE 'weight|fapi\.binance|/fapi/' "$LOG" | head -20 || echo "(no weight/fapi line in the log)"
  echo "--- state residue after the run ---"
  git -C $C status --porcelain -- state | head -20
} >> "$META"
cat "$META"
