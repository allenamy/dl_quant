#!/bin/bash
# e3_ext_mutants.sh <ledger_worktree> <label> — run tests_disposition_matrix on COPIES of the real events.jsonl with one line corrupted.
# The real copy is restored after every mutant and its sha256 compared before/after (no mutant survives).
set -uo pipefail
L="$1"; LABEL="$2"; W=/Users/haosiyu/cc_tmp/fx_exec_work
EV="$L/state/live/watchdog/events.jsonl"; ORIG="$W/e3_events_orig_copy.jsonl"
cp "$EV" "$ORIG"; SHA0=$(shasum -a 256 "$ORIG" | cut -d' ' -f1)
echo "# e3 mutants label=$LABEL tree=$L head=$(git -C "$L" rev-parse HEAD) suite_sha=$(shasum -a 256 "$L/live/tests_disposition_matrix.py" | cut -d' ' -f1) events_sha=$SHA0 start=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mut() {   # mut <name> <python expression producing the new line text from `lines` (list) and index i>
  local NAME="$1" IDX="$2" EXPR="$3"
  /usr/bin/python3 - "$ORIG" "$EV" "$IDX" "$EXPR" <<'PY'
import sys
src, dst, idx, expr = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
lines = open(src, encoding="utf-8").read().split("\n")
lines[idx] = eval(expr, {"line": lines[idx], "json": __import__("json")})
open(dst, "w", encoding="utf-8").write("\n".join(lines))
PY
  local LOG="$W/e3_mut_${LABEL}_${NAME}.log"
  "$W/run1.sh" "$L" live/tests_disposition_matrix.py "$LOG"; local RC=$?
  cp "$ORIG" "$EV"; local SHA1=$(shasum -a 256 "$EV" | cut -d' ' -f1)
  local TB=$(grep -c "^Traceback" "$LOG"); local NF=$(grep -c "^  FAIL\|^FAIL" "$LOG")
  local LAST=$(grep -v "^#" "$LOG" | grep -v "^\s*$" | tail -1 | cut -c1-160)
  echo "MUTANT $NAME line=$((IDX+1)) rc=$RC tracebacks=$TB fail_lines=$NF restored_sha_equal=$([ "$SHA1" = "$SHA0" ] && echo yes || echo NO) last=[$LAST]"
}
mut array_nonflatten 3 '"[]"'
mut array_flatten 0 '"[]"'
mut scalar_nonflatten 3 '"5"'
mut null_nonflatten 3 '"null"'
mut jsondecode_nonflatten 3 'line[:-7]'
mut badts_nonflatten 3 'json.dumps(dict(json.loads(line), ts="not-a-time"))'
mut actions_int_nonflatten 3 'json.dumps(dict(json.loads(line), actions=5))'
mut orders_int_flatten 0 'json.dumps(dict(json.loads(line), actions=[dict(a, orders=7) if a.get("action")=="flatten_all" else a for a in json.loads(line)["actions"]]))'
mut exec_list_flatten 0 'json.dumps(dict(json.loads(line), actions=[dict(a, orders=[dict(o, _exec=[1]) for o in a["orders"]]) if a.get("action")=="flatten_all" else a for a in json.loads(line)["actions"]]))'
mut action_str_nonflatten 3 'json.dumps(dict(json.loads(line), actions=json.loads(line)["actions"] + ["garbage"]))'
echo "# end=$(date -u +%Y-%m-%dT%H:%M:%SZ) final_events_sha=$(shasum -a 256 "$EV" | cut -d' ' -f1)"
