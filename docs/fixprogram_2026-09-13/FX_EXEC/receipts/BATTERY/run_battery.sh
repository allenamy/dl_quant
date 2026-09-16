#!/bin/bash
# FX-EXEC full acceptance battery on the final head, under the shared lock and inside the window.
#
# WHY EVERY GUARD IS HERE (lead's battery rule + INCIDENT_battery_outside_window_20260916T0316Z):
#   run_acceptance.sh contains tests_entrypoint_wiring, which runs a DRY_RUN run_anchor and makes
#   UNAUTHENTICATED PUBLIC market-data GETs from this Mac's IP — the same IP the live executor
#   uses. So: only inside N+65min..N+3h15m of an anchor, only one worker at a time via
#   /Users/haosiyu/cc_tmp/BATTERY.lock, only with no .env and DRY_RUN asserted, request weight
#   recorded, and state/ restored afterwards.
# ★ I tripped this rule once already by running a SUITE that shells out to the runner. The window
#   and lock checks below are therefore hard failures, not warnings.
set -uo pipefail
TREE=/Users/haosiyu/cc_tmp/fx_exec
LOCK=/Users/haosiyu/cc_tmp/BATTERY.lock
W=/Users/haosiyu/cc_tmp/fx_exec_work/new02
OUT="$W/BATTERY_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
LOG="$OUT/battery.log"

fail () { echo "REFUSING: $*" | tee -a "$LOG"; exit 2; }

# ── 1. the window ───────────────────────────────────────────────────────────────────────────────
NOW=$(date -u +%s)
# seconds since the most recent 4-hourly anchor (00/04/08/12/16/20Z)
SINCE=$(( NOW % 14400 ))
echo "# now=$(date -u +%Y-%m-%dT%H:%M:%SZ) seconds_since_anchor=$SINCE" | tee -a "$LOG"
[ "$SINCE" -ge 3900 ] || fail "only $SINCE s past the anchor; the window opens at N+65min (3900 s)"
[ "$SINCE" -le 11700 ] || fail "$SINCE s past the anchor; the window closed at N+3h15m (11700 s)"

# ── 2. the lock (one worker at a time; three executor clones share it) ───────────────────────────
for _i in $(seq 1 120); do
  if ( set -o noclobber; : > "$LOCK" ) 2>/dev/null; then
    { echo "owner=FX-EXEC"; echo "pid=$$"; echo "tree=$TREE";
      echo "head=$(git -C "$TREE" rev-parse HEAD)"; echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ)"; } > "$LOCK"
    break
  fi
  echo "# lock held by: $(tr '\n' ' ' < "$LOCK" 2>/dev/null) — waiting ($_i/120)" | tee -a "$LOG"
  sleep 15
done
grep -q "pid=$$" "$LOCK" 2>/dev/null || fail "could not take $LOCK after 30 min"
trap 'rm -f "$LOCK"; echo "# lock released $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"' EXIT
cat "$LOCK" | sed 's/^/# lock: /' | tee -a "$LOG"


# ── 2b. THE INTERPRETER, RECORDED — before AND after (KB-73) ─────────────────────────────────────
# ★★★ A GREEN BATTERY CERTIFIES "THE PIN IS WRITTEN IN THE FILE", NOT "THE PIN WAS USED".
#     run_acceptance.sh:28 is `PY="${ACCEPT_PY:-/usr/bin/python3}"` — an OVERRIDABLE DEFAULT — and
#     the guard that is supposed to certify it (tests_acceptance_entrypoints.py:55) asserts a
#     SUBSTRING OF THE SOURCE TEXT: `"ACCEPT_PY:-/usr/bin/python3" in open(ROOT_SH).read()`. Point
#     ACCEPT_PY at 3.14 and that cell still prints OK while tests_inference_parity / tests_panel_build
#     go red for want of torch. And none of the 38,177 artefacts under state/acceptance records a
#     Python version, so no past run can be compared with this one either.
# ⇒ Until the guard asserts the EFFECTIVE interpreter, the only thing that makes this run's numbers
#   comparable is this block. It is part of the receipt, not a convenience. Recorded twice so a
#   mid-run change of environment cannot hide between them.
record_interpreter () {   # $1 = label
  local label="$1" out="$OUT/interpreter_$1.txt"
  {
    echo "# interpreter record [$label]  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [ -n "${ACCEPT_PY+x}" ]; then echo "ACCEPT_PY=IS_SET value=${ACCEPT_PY}"; else echo "ACCEPT_PY=UNSET"; fi
    local _py; _py="${ACCEPT_PY:-/usr/bin/python3}"
    echo "resolved_PY=$_py"
    echo "resolved_PY_realpath=$(command -v "$_py" 2>/dev/null || echo NOT_ON_PATH)"
    echo "resolved_PY_abs=$(/usr/bin/python3 -c "import os,sys;print(os.path.realpath('$_py'))" 2>/dev/null || echo UNRESOLVED)"
    echo "sys.version=$("$_py" -c 'import sys;print(sys.version.replace(chr(10)," "))' 2>&1)"
    echo "sys.executable=$("$_py" -c 'import sys;print(sys.executable)' 2>&1)"
    echo "torch=$("$_py" -c 'import torch;print(torch.__version__)' 2>/dev/null || echo 'NO TORCH IN THIS INTERPRETER (named, not inferred)')"
    echo "numpy=$("$_py" -c 'import numpy;print(numpy.__version__)' 2>/dev/null || echo 'no numpy')"
    echo "# and what the runner itself would resolve, read from the file rather than assumed:"
    grep -n 'ACCEPT_PY' "$TREE/run_acceptance.sh" | sed 's/^/#   /'
  } > "$out"
  cat "$out" | sed 's/^/  /' | tee -a "$LOG"
}
record_interpreter before

# ── 3. no credentials, DRY_RUN ──────────────────────────────────────────────────────────────────
[ -e "$TREE/.env" ] && fail ".env exists in the clone — this battery must never run with credentials"
[ -z "${BINANCE_API_KEY:-}" ] || fail "BINANCE_API_KEY is set in the environment"
[ -z "${BINANCE_API_SECRET:-}" ] || fail "BINANCE_API_SECRET is set in the environment"
case "${LIVE_MODE:-DRY_RUN}" in
  DRY_RUN) : ;;
  *) fail "LIVE_MODE=${LIVE_MODE} — only DRY_RUN is allowed here" ;;
esac
export LIVE_MODE=DRY_RUN
{ echo "# .env absent · BINANCE_API_KEY unset · BINANCE_API_SECRET unset · LIVE_MODE=DRY_RUN"
  echo "# head=$(git -C "$TREE" rev-parse HEAD)"
  echo "# source dirty (live ops scheduler signal run_acceptance.sh)=$(git -C "$TREE" status --porcelain --untracked-files=no -- live ops scheduler signal run_acceptance.sh | wc -l | tr -d ' ')"
} | tee -a "$LOG"

# ── 4. state snapshot, so the restore afterwards is provable and NOT `git clean -- state` ────────
git -C "$TREE" status --porcelain -- state > "$OUT/state_before.txt"
ls -1 "$TREE/state/acceptance" 2>/dev/null | wc -l | sed 's/^/acceptance_logs_before=/' | tee -a "$LOG"

# ── 5. run ──────────────────────────────────────────────────────────────────────────────────────
echo "# battery start $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
( cd "$TREE" && bash run_acceptance.sh ) >> "$LOG" 2>&1
RC=$?
echo "# battery end $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$RC" | tee -a "$LOG"

record_interpreter after

# ── 6. request weight, recorded rather than assumed ──────────────────────────────────────────────
{ echo "## request-weight lines seen during this run"
  grep -rhiE 'used[-_ ]?weight|X-MBX-USED-WEIGHT|request_weight' "$LOG" "$TREE/state/acceptance" 2>/dev/null | sort -u | head -40
  echo "## (empty above = the runner printed none; the DRY_RUN run_anchor still made public GETs —"
  echo "##  their count is not recoverable from these logs, which is itself the finding)"
} > "$OUT/request_weight.txt"

# ── 7. summary lines, per suite ─────────────────────────────────────────────────────────────────
{ echo "## per-suite verdicts"; grep -E '^(OK|FAIL|RED|GREEN|ALL GREEN|ACCEPTANCE)' "$LOG" | head -200; } > "$OUT/summary.txt"
cp -R "$TREE/state/acceptance" "$OUT/acceptance_logs" 2>/dev/null || true

# ── 8. restore state: this run's artefacts only, then tracked files back to HEAD ─────────────────
find "$TREE/state/acceptance" -name "$(date -u +%Y%m%d)T*" -delete 2>/dev/null || true
rm -rf "$TREE/state/pilot_log/$(date -u +%Y%m%d)" 2>/dev/null || true
git -C "$TREE" checkout -- state
{ echo "## state restored"; echo "tracked state dirty after: $(git -C "$TREE" status --porcelain -- state | grep -c '^ M')";
  echo "## NOT run: git clean -- state (it would delete pre-existing untracked REAL-state copies the suites read)"; } | tee -a "$LOG"
echo "BATTERY_RC=$RC"
exit $RC
