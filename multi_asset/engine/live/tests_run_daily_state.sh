#!/bin/bash
# Red/green battery for run_daily.sh's failure-attribution and run-state record (0C 2026-07-27).
#
# > created 2026-07-27 | Session: 0C | 状态: permanent | 作废条件: run_daily.sh 退役
#
# It tests the REAL function text: the preamble of run_daily.sh (everything before the first step)
# is extracted and sourced, so these cases cannot pass against a copy that has drifted from the
# script that actually runs.
#
# THE DISCRIMINATING CASE IS R2. Before 2026-07-27 `run()` shifted its arguments and then passed
# `$1` to `fail()`, so the single line written to ALARM.log named the INTERPRETER, not the step:
#     [ALARM] step '/root/miniconda3/envs/hsy_v5push/bin/python3' FAILED (exit 1)
# The attribution line existed and fired; it just pointed at nothing. R2 asserts the alarm names the
# STEP and does NOT name the command — it goes red again the moment someone reintroduces the shift.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# A path may be passed in so the battery can be pointed at a DELIBERATELY BROKEN copy and observed
# going red. "It passes" is not evidence until "it fails when it should" has been watched happen.
# To reproduce the control, revert `run()` to its pre-2026-07-27 form with a LITERAL replacement:
#   python3 -c 'p="run_daily.sh"; s=open(p).read(); \
#     new=r"""run() { local _desc="$1"; step "$_desc"; shift; "$@" >> "$RUNLOG" 2>&1 || fail "$_desc" $?; }"""; \
#     old=r"""run() { step "$1"; shift; "$@" >> "$RUNLOG" 2>&1 || fail "$1" $?; }"""; \
#     assert s.count(new)==1; open("/tmp/old.sh","w").write(s.replace(new,old,1))'
#   bash tests_run_daily_state.sh /tmp/old.sh
# Observed 2026-07-27: R1 and R2 both FAIL, R2 with `step 'bash'` — the same shape as the real
# 07-26 alarm (`step '/root/.../python3'`).
# ⚠ Do NOT do this with sed: `&` in a sed replacement means "the whole match", so `2>&1` is silently
#   corrupted and the battery goes red for a reason that has nothing to do with the case under test.
#   That happened on the first attempt here — a red for the wrong reason is as misleading as a green
#   for the wrong reason, and harder to notice because red feels like success when you want red.
SRC="${1:-$HERE/run_daily.sh}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
fails=0
ok()   { echo "  ok    $1"; }
bad()  { echo "  FAIL  $1"; echo "        $2"; fails=$((fails+1)); }

# ── extract the preamble (everything before the first pipeline step) and neutralise the lock ──────
awk '/^step "=== run_daily start/{exit} {print}' "$SRC" > "$T/preamble.sh"
grep -q 'write_run_state' "$T/preamble.sh" || { echo "extraction failed: no write_run_state"; exit 1; }
# point the paths at the sandbox; keep the FUNCTION BODIES untouched
sed -i.bak -e "s#^MA=.*#MA=$T/ma#" -e "s#^LIVE=.*#LIVE=$T/live#" \
           -e "s#^exec 9.*#:#" -e "s#^if ! flock.*#:#" "$T/preamble.sh"
bash -n "$T/preamble.sh" || { echo "extracted preamble does not parse"; exit 1; }
mkdir -p "$T/live/monitor" "$T/ma"
# shellcheck disable=SC1090
source "$T/preamble.sh"
PY=$(command -v python3)

# ── G1: a successful step writes no failure record ────────────────────────────────────────────────
rm -f "$RUNSTATE"
( run "a step that works" true ) >/dev/null 2>&1
if [ ! -f "$RUNSTATE" ]; then ok "G1 a successful step leaves no run-state record"
else bad "G1 a successful step leaves no run-state record" "record appeared: $(cat "$RUNSTATE")"; fi
# red-when: would go red if run() wrote a record unconditionally, which would make "failed" and
# "ok" indistinguishable at the moment of writing.

# ── R1: a failing step writes a failure record with the right exit code ───────────────────────────
rm -f "$RUNSTATE" "$ALARM"
( run "ingest (pull + splice tail -> wide_dl_live)" bash -c 'echo boom >&2; exit 7' ) >/dev/null 2>&1
rc_seen=$?
if [ -f "$RUNSTATE" ]; then
  got=$("$PY" - "$RUNSTATE" <<'EOF'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"{d['status']}|{d['failed_step']}|{d['exit_code']}|{'boom' in d['log_tail']}")
EOF
)
  [ "$got" = "failed|ingest (pull + splice tail -> wide_dl_live)|7|True" ] \
    && ok "R1 a failing step records status/step/exit-code/log-tail" \
    || bad "R1 a failing step records status/step/exit-code/log-tail" "got: $got"
else bad "R1 a failing step records status/step/exit-code/log-tail" "no record written"; fi
# red-when: would go red if the record were written without the step name, with a hardcoded exit
# code, or if the tail were dropped — each of which turns the attribution back into a guess.

# ── R2 ★ THE DISCRIMINATING CASE: the alarm must name the STEP, not the command ───────────────────
line=$(grep '\[ALARM\]' "$ALARM" 2>/dev/null | tail -1)
if [[ "$line" == *"step 'ingest (pull + splice tail -> wide_dl_live)'"* ]] && [[ "$line" != *"$PY"* ]] \
   && [[ "$line" != *"step 'bash'"* ]]; then
  ok "R2 the ALARM line names the STEP and not the command"
else
  bad "R2 the ALARM line names the STEP and not the command" "line: $line"
fi
# red-when: reintroducing `shift` before `fail "$1"` — the exact 07-26 defect — makes this red.

# ── G2: the ok record is valid JSON and says ok ───────────────────────────────────────────────────
rm -f "$RUNSTATE"
write_run_state ok "" 0
got=$("$PY" - "$RUNSTATE" <<'EOF'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"{d['status']}|{d['exit_code']}|{bool(d['finished_utc'])}|{bool(d['_why'])}")
EOF
)
[ "$got" = "ok|0|True|True" ] && ok "G2 the success record is valid JSON carrying its own timestamp" \
  || bad "G2 the success record is valid JSON carrying its own timestamp" "got: $got"
# red-when: would go red if the heredoc emitted invalid JSON (an unescaped quote in the log tail is
# the realistic way that happens — which is why the tail is JSON-encoded by python, not by echo).

# ── R3: a log tail containing quotes/backslashes must not corrupt the JSON ────────────────────────
rm -f "$RUNSTATE"
printf '%s\n' 'he said "hi" \ and \n stopped' >> "$RUNLOG"
write_run_state failed "a step" 3
"$PY" -c 'import json,sys; json.load(open(sys.argv[1]))' "$RUNSTATE" 2>/dev/null \
  && ok "R3 quotes and backslashes in the log tail keep the record parseable" \
  || bad "R3 quotes and backslashes in the log tail keep the record parseable" "record is not JSON"
# red-when: would go red if the tail were interpolated raw — the classic way a status file becomes
# unreadable precisely on the days something went wrong.

echo
[ $fails -eq 0 ] && echo "run_daily state battery: all cases behaved as specified" \
                 || echo "run_daily state battery: $fails FAILED"
exit $([ $fails -eq 0 ] && echo 0 || echo 1)
