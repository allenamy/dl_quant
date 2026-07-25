#!/bin/bash
# Single machine-checkable acceptance statement for the pilot prerequisite stack.
#
# ★ WHY THIS EXISTS: "all suites green" was being produced by running five commands by hand and
#   reading five outputs. That produced a FALSE all-green claim twice in one day:
#     (a) `python x.py | tail; echo $?` reports TAIL's exit code, not the program's — a mistake I
#         made, caught, wrote down, and then made again on a different script;
#     (b) an "all green" report quoted a full-suite run that PREDATED later edits; only one suite
#         was re-run before reporting.
#   Both are the same class: a claim about the whole, assembled by hand from parts, at a moment
#   that drifts. So the claim becomes one machine action instead of five human ones.
#
# ★ RULE: any statement of the form "the suites are green" must cite THIS script's output.
#   Exit code: 0 only if every suite exited 0. Never pipe this script's invocation.
#
# Usage: bash engine/live/run_acceptance.sh [--json <path>]
set -uo pipefail          # pipefail so a piped stage cannot mask a failure either

MA=/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python3
LOGDIR=$MA/exports/live/acceptance
mkdir -p "$LOGDIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
JSON_OUT=""
[ "${1:-}" = "--json" ] && JSON_OUT="${2:-}"

SUITES=(
  "log_schema_falsify_v2:$MA/exports/eda/log_schema_falsify_v2.py"
  "tests_pilot_log:$MA/engine/live/tests_pilot_log.py"
  "tests_watchdog:$MA/engine/live/tests_watchdog.py"
  "tests_production_signature:$MA/engine/live/tests_production_signature.py"
  "inject_failures:$MA/engine/live/inject_failures.py"
)

overall=0
rows=""
printf '%-32s %-6s %-6s %s\n' "SUITE" "EXIT" "FAILS" "LOG"
printf '%s\n' "--------------------------------------------------------------------------"
for entry in "${SUITES[@]}"; do
  name="${entry%%:*}"; path="${entry#*:}"
  log="$LOGDIR/${STAMP}_${name}.log"
  if [ ! -f "$path" ]; then
    printf '%-32s %-6s %-6s %s\n' "$name" "MISSING" "-" "$path"
    overall=1
    rows="$rows{\"suite\":\"$name\",\"exit\":null,\"missing\":true},"
    continue
  fi
  # exit code captured DIRECTLY from the interpreter — no pipe, no subshell, no tail
  "$PY" "$path" > "$log" 2>&1
  rc=$?
  fails=$(grep -c '^  FAIL' "$log" 2>/dev/null || true)
  printf '%-32s %-6s %-6s %s\n' "$name" "$rc" "$fails" "$log"
  [ "$rc" -ne 0 ] && overall=1
  rows="$rows{\"suite\":\"$name\",\"exit\":$rc,\"fail_lines\":$fails,\"log\":\"$log\"},"
done
printf '%s\n' "--------------------------------------------------------------------------"
if [ "$overall" -eq 0 ]; then
  echo "ACCEPTANCE: ALL GREEN (${#SUITES[@]}/${#SUITES[@]} suites exit 0)"
else
  echo "ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)"
fi
if [ -n "$JSON_OUT" ]; then
  printf '{"stamp":"%s","overall_exit":%d,"all_green":%s,"suites":[%s]}\n' \
    "$STAMP" "$overall" "$([ $overall -eq 0 ] && echo true || echo false)" "${rows%,}" > "$JSON_OUT"
fi
exit $overall
