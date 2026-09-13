#!/bin/bash
# e3_ext_mutants2.sh <ledger_worktree> <label> — the two mutants that need more than one line of the event log:
#   jsondecode_flatten_ledger_deleted : line 1 (FLATTEN-20260801T201827Z) made non-JSON AND that batch's 105 protective_flatten rows
#                                       deleted from the 20260801 orders copy — both sides of one batch gone (the silence case)
#   failed_cid_attempt_idx_flatten    : line 15 (FLATTEN-20260912T124737Z, client ids): order[0] attempt_idx "x" and listed in `failed`
#                                       by its client id — the reader's key path is skipped, the reconciliation's is not (backstop case)
# Every mutated file is restored from a copy and its sha256 compared.
set -uo pipefail
L="$1"; LABEL="$2"; W=/Users/haosiyu/cc_tmp/fx_exec_work
EV="$L/state/live/watchdog/events.jsonl"; OR="$L/state/live/pilot_log/20260801/orders.jsonl"
cp "$EV" "$W/e3m2_events_orig.jsonl"; cp "$OR" "$W/e3m2_orders0801_orig.jsonl"
SE=$(shasum -a 256 "$EV" | cut -d' ' -f1); SO=$(shasum -a 256 "$OR" | cut -d' ' -f1)
echo "# e3 mutants2 label=$LABEL tree=$L head=$(git -C "$L" rev-parse HEAD) suite_sha=$(shasum -a 256 "$L/live/tests_disposition_matrix.py" | cut -d' ' -f1) events_sha=$SE orders0801_sha=$SO start=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
run() {
  local NAME="$1"; local LOG="$W/e3_mut_${LABEL}_${NAME}.log"
  "$W/run1.sh" "$L" live/tests_disposition_matrix.py "$LOG"; local RC=$?
  cp "$W/e3m2_events_orig.jsonl" "$EV"; cp "$W/e3m2_orders0801_orig.jsonl" "$OR"
  local R1=$(shasum -a 256 "$EV" | cut -d' ' -f1); local R2=$(shasum -a 256 "$OR" | cut -d' ' -f1)
  local TB=$(grep -c "^Traceback" "$LOG"); local NF=$(grep -c "^  FAIL" "$LOG")
  local LAST=$(grep -v "^#" "$LOG" | grep -v "^\s*$" | tail -1 | cut -c1-120)
  local NAMED=$(grep -o "events.jsonl line [0-9]*" "$LOG" | sort -u | tr '\n' ' ')
  echo "MUTANT $NAME rc=$RC tracebacks=$TB fail_lines=$NF named=[$NAMED] restored_equal=$([ "$R1" = "$SE" ] && [ "$R2" = "$SO" ] && echo yes || echo NO) last=[$LAST]"
}
/usr/bin/python3 - "$EV" "$OR" <<'PY'
import sys, json
ev, orp = sys.argv[1], sys.argv[2]
lines = open(ev, encoding="utf-8").read().split("\n")
lines[0] = lines[0][:-7]
open(ev, "w", encoding="utf-8").write("\n".join(lines))
keep = [l for l in open(orp, encoding="utf-8") if not (l.strip() and json.loads(l).get("rebalance_id") == "FLATTEN-20260801T201827Z")]
open(orp, "w", encoding="utf-8").write("".join(keep))
PY
run jsondecode_flatten_ledger_deleted
/usr/bin/python3 - "$EV" <<'PY'
import sys, json
ev = sys.argv[1]
lines = open(ev, encoding="utf-8").read().split("\n")
rec = json.loads(lines[14]); assert rec["ts"] == "2026-09-12T12:47:37Z"
for a in rec["actions"]:
    if a.get("action") == "flatten_all":
        o = a["orders"][0]; assert o.get("client_id")
        o["attempt_idx"] = "x"
        a["failed"] = list(a.get("failed") or []) + [{"order": {"client_id": o["client_id"], "symbol": o["symbol"], "side": o["side"]}, "err": "mutant"}]
        break
lines[14] = json.dumps(rec)
open(ev, "w", encoding="utf-8").write("\n".join(lines))
PY
run failed_cid_attempt_idx_flatten
echo "# end=$(date -u +%Y-%m-%dT%H:%M:%SZ) final_events_sha=$(shasum -a 256 "$EV" | cut -d' ' -f1) final_orders0801_sha=$(shasum -a 256 "$OR" | cut -d' ' -f1)"
