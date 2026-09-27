# mr_stop.sh -- the family's ONE stop predicate, sourced by every dispatcher (mr_master / mr_engine_queue / rc_hybrid) and by the
# consumer mr_prep.sh (fresh2 2026-09-27; class fix of run 3: the STOP came 01:31:59Z, mr_master's check ran BEFORE a 7.5-min slot
# wait, and A0_m3's prep was dispatched 01:39:33Z). The class = "stop checked, then a blocking wait, then a launch". Rules:
#   1. every wait loop in a dispatcher re-evaluates mr_stopped;
#   2. every launch goes through mr_guard ON THE SAME LINE as the fork (no wait can sit between the check and the launch);
#   3. the consumer mr_prep.sh calls mr_guard at entry, so a dispatcher written tomorrow is covered without remembering this file.
# Scope = (MR_MASTER_LOG, MR_LOG_OFFSET): a line-start "<ts> STOP" in the dispatching job's registered log at or after the byte
# offset recorded when that job started (the same line the registry / patrol treat as terminal). Offset-scoped because the machine
# is reused after a STOP (rc_hybrid ran after run 3's STOP in its own log). Unset scope or an unreadable log => stopped (fail closed).
mr_scope_begin() {   # <registered log> -- call once at dispatcher start, before its START line
  export MR_MASTER_LOG=$1 MR_LOG_OFFSET=0
  [ -e "$1" ] && MR_LOG_OFFSET=$(wc -c < "$1" | tr -d ' ')
  export MR_LOG_OFFSET
}
mr_stopped() {       # rc 0 = stopped
  [ -n "${MR_MASTER_LOG:-}" ] && [ -n "${MR_LOG_OFFSET:-}" ] || { echo "mr_stopped: no stop scope declared (MR_MASTER_LOG/MR_LOG_OFFSET unset) => stopped" >&2; return 0; }
  [ -e "$MR_MASTER_LOG" ] || return 1
  local n   # grep -c reads to EOF: no early close => no SIGPIPE status under pipefail; empty count (instrument failure) => stopped
  n=$(tail -c +$((MR_LOG_OFFSET + 1)) "$MR_MASTER_LOG" | grep -cE '^[^ ]+ STOP')
  [ "${n:-x}" != 0 ]
}
mr_guard() {         # <what> -- rc 1 (and a REFUSED_LAUNCH line on stderr) when stopped
  if mr_stopped; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) REFUSED_LAUNCH ($*): STOP in ${MR_MASTER_LOG:-<unset>} after byte ${MR_LOG_OFFSET:-<unset>}" >&2
    return 1
  fi
}
