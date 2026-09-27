#!/usr/bin/env bash
# d10_pull_months_pod2.sh <YYYY-MM> [<YYYY-MM> ...] -- archive pull for the named months, run ENTIRELY on pod2 under setsid.
# news2 class fix 2026-09-27; replaces d10_pull_resume_pod2.sh (and the other three pull drivers) for every future pull.
#
# What changed vs d10_pull_resume_pod2.sh and why:
#  * the repair branch (drop those zips, re-fetch once) is no longer entered on "puller exit code 1". Python exits 1 for anything
#    raised before the puller's excepthook exists, so an import error used to be answered by deleting files named in a STALE
#    manifest. Now p9_pull_verdict.py decides from a manifest carrying THIS pass's nonce (P9_RUN_NONCE) and a consistent
#    intended_rc; the driver greps its one anchored line and every other outcome -- including no line at all -- is FAILED;
#  * the month-state line must be one of the known states, anchored; a crashed state device used to fall through to a pull;
#  * the repair device's exit code is checked; the symbol list must exist and be non-empty;
#  * months come from argv (nothing hardcoded); the last log line says whether every month ended VERIFIED.
# Exit: 0 = COMPLETE all_verified=yes; 2 = COMPLETE all_verified=no (named); 1 = FAILED (named, nothing further touched).
# Paths default to pod2's layout; EXP / PY are overridable for d10_pull_driver_selftest.py only.
# Usage (on pod2): setsid nohup bash d10_pull_months_pod2.sh 2026-09 </dev/null >/dev/null 2>&1 &
set -uo pipefail
EXP=${EXP:-/dev/shm/d10_2026-09-25}
PY=${PY:-/workspace/venv/bin/python}
DEV=$EXP/devices
LOG=$EXP/logs/pull_months_pod2.log
RUNID="months-$$-$(date -u +%Y%m%dT%H%M%SZ)"
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$RUNID] $*" >> "$LOG"; }
fail() { say "FAILED $*"; exit 1; }
[ $# -ge 1 ] || { say "FAILED usage: no months given"; exit 1; }
say "START run_id=$RUNID pgid=$(ps -o pgid= -p $$ | tr -d ' ') months=$*"

VERDICT=""
pull_pass() {  # $1 month, $2 pass tag; sets VERDICT to the anchored verdict line or ""
  local M=$1 NONCE="$RUNID-$1-$2" rc=0
  P9_RUN_NONCE="$NONCE" nice -n 10 "$PY" -B "$DEV/p9_pull_monthly_funding_zips.py" "$M" "$EXP/symlists/$M.txt" "$EXP/zips/$M" \
    >> "$EXP/logs/pull_$M.log" 2>&1 || rc=$?
  VERDICT=$("$PY" -B "$DEV/p9_pull_verdict.py" "$rc" "$EXP/zips/$M/MANIFEST_$M.json" "$NONCE" "$M" 2>&1 \
            | grep -E '^P9_VERDICT (OK|MISMATCH|FAILED)( |$)' | head -1)
  say "$M pass=$2 rc=$rc ${VERDICT:-P9_VERDICT <no line from the verdict device>}"
}

for M in "$@"; do
  ST=$("$PY" -B "$DEV/d10_month_state.py" "$EXP/zips/$M" "$M" 2>&1 | head -1)
  case "$ST" in
    "VERIFIED "*|VERIFIED)          say "$M $ST -> not re-fetched"; continue;;
    "VERIFIED_WITH_UNVERIFIED "*)   say "$M $ST -> not re-fetched (a re-fetch cannot produce a .CHECKSUM the venue does not serve; red for consumers)"; continue;;
    ABSENT|"MISMATCH "*|"REHASH_MISMATCH "*|"SET_MISMATCH "*|"NO_ZIPS "*|"NOT_VERIFIED "*) ;;
    *) fail "$M month-state device gave no known state: '${ST:-<nothing>}'";;
  esac
  [ -s "$EXP/symlists/$M.txt" ] || fail "$M symbol list $EXP/symlists/$M.txt missing or empty"
  say "$M START state=$ST symbols=$(wc -l < "$EXP/symlists/$M.txt" | tr -d ' ')"
  t0=$(date +%s)
  pull_pass "$M" p1
  case "$VERDICT" in
    "P9_VERDICT OK"*) ;;
    "P9_VERDICT MISMATCH"*)
      say "$M checksum mismatch stated by this run's manifest -> repairing exactly those and re-fetching ONCE"
      "$PY" -B "$DEV/d10_drop_mismatched.py" "$EXP/zips/$M" "$M" >> "$LOG" 2>&1 || fail "$M repair device exited $? -- not re-fetching"
      pull_pass "$M" p2
      case "$VERDICT" in
        "P9_VERDICT OK"*) ;;
        "P9_VERDICT MISMATCH"*)
          say "$M STILL MISMATCHING after one re-fetch -> naming them, not silently skipped"
          "$PY" -B "$DEV/d10_drop_mismatched.py" "$EXP/zips/$M" "$M" --report-only >> "$LOG" 2>&1 || fail "$M report device exited $?";;
        *) tail -6 "$EXP/logs/pull_$M.log" >> "$LOG"; fail "$M re-fetch did not end in a stated outcome -- stopping";;
      esac;;
    *) tail -6 "$EXP/logs/pull_$M.log" >> "$LOG"; fail "$M pull did not end in a stated outcome -- stopping, nothing deleted";;
  esac
  say "$M DONE in $(( $(date +%s) - t0 ))s  $("$PY" -B "$DEV/d10_month_state.py" "$EXP/zips/$M" "$M" 2>&1 | head -1)"
done

NOTV=""
for M in "$@"; do
  G=$("$PY" -B "$DEV/d10_manifest_gate.py" "$EXP/zips/$M" "$M" 2>&1 | head -1)
  say "final $M: $G"
  case "$G" in "$M VERIFIED "*) ;; *) NOTV="${NOTV:+$NOTV,}$M";; esac
done
if [ -z "$NOTV" ]; then say "COMPLETE all_verified=yes"; exit 0; fi
say "COMPLETE all_verified=no months_not_verified=$NOTV"; exit 2
