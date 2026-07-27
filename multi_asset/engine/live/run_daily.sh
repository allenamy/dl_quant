#!/bin/bash
# Live shadow — item 5: the daily orchestrator (server-resident cron).
#
# Runs the full chain once per day: pull the latest public archives -> splice the panel tail ->
# fold_4 inference -> emit unit-gross positions -> update the dual-curve paper P&L -> C4 daily report.
# Idempotent (safe to re-run: the tail rebuild is deterministic from the frozen panel; emit/P&L/report
# overwrite). A lock prevents concurrent runs; any step failure is logged to the alarm file and aborts.
#
# Install (server crontab, daily 09:00 UTC — after the T+1 daily archive publishes):
#   (crontab -l 2>/dev/null; echo "0 9 * * * /bin/bash /mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live/run_daily.sh") | crontab -
set -uo pipefail

MA=/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python3
LIVE=$MA/exports/live
LOG=$LIVE/logs
LOCK=$LIVE/run_daily.lock
ALARM=$LOG/ALARM.log
mkdir -p "$LOG" "$LIVE/positions" "$LIVE/pnl" "$LIVE/monitor"

exec 9>"$LOCK"
if ! flock -n 9; then echo "$(date -u +%FT%TZ) another run_daily is in progress; skip" >> "$LOG/run.log"; exit 0; fi

TODAY=$(date -u +%Y%m%d)
RUNLOG=$LOG/run_$TODAY.log
# ★ THE PRODUCER MUST SAY WHY IT PRODUCED NOTHING (0C 2026-07-27).
# On 07-26 this script exited 1 at the very first step. Downstream, `check_factor_health` saw only
# that `monitor/daily_report.json` had stopped moving and reported "STALE: the shadow's own report
# is 28.2h old" — a TRUE alarm pointing at a SYMPTOM, while the actual sentence ("the funding gate
# refused to publish the panel") sat in a log file on another machine that nothing reads.
# ⇒ The absence of a report is now accompanied by the reason, emitted BY THE PRODUCER, next to the
#   report the consumer already fetches. Not by log-scraping: a consumer that greps another
#   machine's log is a criterion written into the data instead of into attribution.
# ⇒ It carries its own timestamp ON PURPOSE. The lock-skip path and a kill -9 both leave this file
#   untouched, so a consumer must compare `finished_utc` against the report it is complaining about
#   and say "no run record newer than the report" when it is older. A stale attribution is worse
#   than none.
RUNSTATE=$LIVE/monitor/last_run.json
write_run_state() {   # $1 status, $2 failed step (or ""), $3 exit code
  local tail_json
  tail_json=$(tail -n 25 "$RUNLOG" 2>/dev/null | "$PY" -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '""')
  cat > "$RUNSTATE" <<EOF
{
 "day": "$TODAY",
 "finished_utc": "$(date -u +%FT%TZ)",
 "status": "$1",
 "failed_step": "$2",
 "exit_code": $3,
 "run_log": "$RUNLOG",
 "log_tail": $tail_json,
 "_why": "written by run_daily.sh so that the ABSENCE of a fresh daily_report.json is accompanied by the reason for it. A consumer must ignore this record when finished_utc is older than the report it is judging."
}
EOF
}
step() { echo "$(date -u +%FT%TZ) [step] $*" | tee -a "$RUNLOG"; }
fail() { echo "$(date -u +%FT%TZ) [ALARM] step '$1' FAILED (exit $2) — see $RUNLOG" | tee -a "$ALARM" >> "$RUNLOG"; write_run_state failed "$1" "$2"; exit "$2"; }
# ★ `_desc` is not cosmetic. It used to read `run() { step "$1"; shift; ... || fail "$1" $?; }` —
# and after the `shift`, `$1` is the COMMAND. So the one line written to ALARM.log to attribute a
# failure named the interpreter: on 2026-07-26 the only alarm the shadow emitted was
#   [ALARM] step '/root/miniconda3/envs/hsy_v5push/bin/python3' FAILED (exit 1)
# for a failure in the ingest step. The attribution line existed, fired, and pointed at nothing —
# which is why the real cause had to be reconstructed by hand from the run log the next day.
run() { local _desc="$1"; step "$_desc"; shift; "$@" >> "$RUNLOG" 2>&1 || fail "$_desc" $?; }

step "=== run_daily start $TODAY ==="
run "ingest (pull + splice tail -> wide_dl_live)"   "$PY" "$MA/engine/live/build_tail.py" --build
run "signal loop (inference -> positions_*.json)"    "$PY" "$MA/engine/live/signal_loop.py" --emit
run "paper P&L (dual-curve A/B)"                       "$PY" "$MA/engine/live/paper_pnl.py"
run "C4 monitor (rolling rank-IC daily report)"       "$PY" "$MA/engine/live/monitor.py"
# challenger dual-track (leg weights) — ADDITIVE and NON-FATAL: a failure here must never
# break the champion pipeline, so it is deliberately not routed through run()/fail().
step "challenger dual-track (king .50 weights; non-fatal)"
"$PY" "$MA/engine/live/challenger.py" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] challenger step failed (non-fatal)" | tee -a "$RUNLOG"

# champion_fixfunding third track (funding settlement-interval fix) — ADDITIVE, NON-FATAL.
# Orthogonal to the challenger track: that one tests WEIGHTS, this one tests the FACTOR FIX.
step "fixfunding third track (corrected funding factor; non-fatal)"
"$PY" "$MA/engine/live/fixfunding_track.py" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] fixfunding step failed (non-fatal)" | tee -a "$RUNLOG"

# pilot-prep daily chain (§9.5): regime -> guards -> v2 shadow log -> metrics -> watchdog ->
# mirrored report. ADDITIVE, NON-FATAL. MOCK ONLY: no account, no credentials, no venue contact.
step "pilot-prep daily (schema v2 log + metrics + watchdog + mirror; non-fatal, MOCK)"
"$PY" "$MA/engine/live/pilot_daily.py" --days_back 1 >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] pilot_daily step failed (non-fatal)" | tee -a "$RUNLOG"

# four-track shadow matrix (2 weight configs x 2 factor versions) — ADDITIVE, NON-FATAL.
# Three frozen comparisons + a pre-registered generalisation test; see exports/live/track_matrix/README.md
step "four-track matrix (weights x factor version; non-fatal)"
"$PY" "$MA/engine/live/track_matrix.py" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] track_matrix step failed (non-fatal)" | tee -a "$RUNLOG"

# acceptance runner — the SINGLE machine-checkable "all green" statement. Non-fatal here (the
# shadow must keep running even if a suite regresses) but its JSON is the only citable source.
step "acceptance runner (single all-green statement)"
# ★ ACCEPT_PY MUST BE PASSED. run_acceptance.sh documents this override and defaults to the SYSTEM
# `python3` without it — which on this box has no numpy, so its first automated run reported four
# suites "failing" that had never executed a line. The caller is the only party that knows which
# interpreter the pipeline actually runs under; it is the caller's job to say so.
ACCEPT_PY="$PY" bash "$MA/engine/live/run_acceptance.sh" --json "$MA/exports/live/acceptance/latest.json" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] acceptance NOT green — see exports/live/acceptance/latest.json" | tee -a "$RUNLOG" "$ALARM"

# panel-caliber manifest (0C): the funding caliber of every panel this FROZEN GENERATION holds,
# asserted against a blessed record and keyed to the checkpoint hashes. Catches a rebuild that
# bypasses build_wide_dl.py's own gate (a copy, a moved fundfix artefact, a hand edit).
# ★ NON-FATAL BY DESIGN, AND THAT IS A CONSIDERED CHOICE, NOT TIMIDITY. The panel the day's live
#   signal is computed from is already hard-gated at build time (build_wide_dl.py -> exit 1). This
#   check's unique coverage is the TRAINING panel and out-of-band rebuilds, neither of which
#   invalidates a signal already computed. Making it fatal would stop the whole shadow for a
#   condition that does not corrupt today's reading — which is exactly the mistake that froze the
#   report for 28 hours on 07-26. It must RING, loudly, into ALARM.log; it must not stop the book.
step "panel-caliber manifest (frozen generation vs blessed caliber; non-fatal, ALARMS)"
"$PY" "$MA/exports/eda/assert_panel_caliber_manifest.py" \
      --json "$MA/exports/live/monitor/panel_caliber_last.json" >> "$RUNLOG" 2>&1
_pcm=$?
if [ $_pcm -ne 0 ]; then
  echo "$(date -u +%FT%TZ) [ALARM] panel-caliber manifest exit=$_pcm ($([ $_pcm -eq 2 ] && echo UNKNOWN || echo FAIL)) — a panel held by the frozen generation no longer carries its blessed funding caliber, or nothing could be verified. See exports/live/monitor/panel_caliber_last.json" | tee -a "$RUNLOG" "$ALARM"
fi

step "=== run_daily done $TODAY ==="
write_run_state ok "" 0
