#!/usr/bin/env bash
# rungate.sh <arm> <receipt_out> [min_headroom_MiB] [min_shm_MiB]
#
# Team engine run gate, final form (lead 2026-09-25, superseding two earlier versions):
#   * other bt_launch GROUPS <= 2   -- counted by DISTINCT OTHER PGID, never by PID and never by an
#     argv token. fresh's first version counted PIDs (one cell read as five -> the gate could never be
#     satisfied and starved its own queue); fresh's second version grouped by the RUN_CONFIG*.json
#     token in argv and had a FALSE NEGATIVE (lead observed a launcher whose argv carries no such
#     token -> it counts as zero groups -> the gate lets an over-quota cell start). Grouping by PGID is
#     independent of how the command line happens to be written. The config path is a LABEL only.
#   * cgroup headroom (memory.max - anon - shmem) >= 24 GiB
#   * /dev/shm free >= 4 GiB
# Thresholds are FLOORS: a caller may raise them, never lower them, and an attempt to lower is PRINTED.
# Read-only: this inspects the process table and NEVER signals another process.
# All three numbers are printed on every recheck and land in the receipt, so "why was it allowed to
# start" is checkable afterwards rather than asserted.
set -uo pipefail
ARM="${1:?usage: rungate.sh <arm> <receipt_out> [min_headroom_MiB] [min_shm_MiB]}"
OUT="${2:?receipt path required}"

RULE_HEAD_MIN=24576          # 24 GiB, team rule
RULE_SHM_MIN=4096            # 4 GiB, team rule
RULE_OTHER_MAX=2             # other bt_launch groups
REQ_HEAD=${3:-$RULE_HEAD_MIN}
REQ_SHM=${4:-$RULE_SHM_MIN}
HEAD_MIN=$RULE_HEAD_MIN; SHM_MIN=$RULE_SHM_MIN
if [ "${REQ_HEAD:-0}" -gt "$RULE_HEAD_MIN" ] 2>/dev/null; then HEAD_MIN=$REQ_HEAD; fi
if [ "${REQ_SHM:-0}"  -gt "$RULE_SHM_MIN"  ] 2>/dev/null; then SHM_MIN=$REQ_SHM; fi
if [ "${REQ_HEAD:-0}" -lt "$RULE_HEAD_MIN" ] 2>/dev/null; then
  echo "  rungate: caller asked headroom>=${REQ_HEAD}MiB, BELOW the team rule ${RULE_HEAD_MIN}MiB -> using the rule"
fi
if [ "${REQ_SHM:-0}" -lt "$RULE_SHM_MIN" ] 2>/dev/null; then
  echo "  rungate: caller asked shm>=${REQ_SHM}MiB, BELOW the team rule ${RULE_SHM_MIN}MiB -> using the rule"
fi

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
ATTEMPTS=0
TRACE=""
while : ; do
  ATTEMPTS=$((ATTEMPTS+1))
  # count by DISTINCT OTHER PGID; config path is a label only
  OTHERP=$(ps -eo pgid,args | grep "bt_launch\.py" | grep -v grep \
           | awk -v me="$MYPGID" '$1 != me {print $1}' | sort -u)
  NG=$(printf '%s\n' "$OTHERP" | grep -c . || true)
  LBL=$(ps -eo pgid,args | grep "bt_launch\.py" | grep -v grep \
        | awk -v me="$MYPGID" '$1 != me {lbl="(no config path in argv)";
            for(i=1;i<=NF;i++) if ($i ~ /RUN_CONFIG.*\.json$/) {lbl=$i; break} print $1"="lbl}' \
        | sort -u | tr '\n' ' ')
  read -r MX < /sys/fs/cgroup/memory.max
  ANON=$(awk '$1=="anon"{print $2}' /sys/fs/cgroup/memory.stat)
  SHMEM=$(awk '$1=="shmem"{print $2}' /sys/fs/cgroup/memory.stat)
  if [ "$MX" = "max" ]; then HEAD_MIB=-1; else HEAD_MIB=$(( (MX - ANON - SHMEM) / 1048576 )); fi
  SHM_FREE_MIB=$(( $(df -k /dev/shm | tail -1 | awk '{print $4}') / 1024 ))

  STAMP=$(date -u +%H:%M:%SZ)
  echo "  rungate $STAMP arm=$ARM other_groups=$NG/$RULE_OTHER_MAX headroom=${HEAD_MIB}/${HEAD_MIN}MiB shm_free=${SHM_FREE_MIB}/${SHM_MIN}MiB  others: ${LBL:-none}"
  TRACE="${TRACE}${STAMP} other_groups=$NG headroom_MiB=$HEAD_MIB shm_free_MiB=$SHM_FREE_MIB others=[${LBL:-none}]"$'\n'

  OK=1
  [ "$NG" -le "$RULE_OTHER_MAX" ] || OK=0
  [ "$HEAD_MIB" -ge "$HEAD_MIN" ] || OK=0
  [ "$SHM_FREE_MIB" -ge "$SHM_MIN" ] || OK=0
  if [ "$OK" = "1" ]; then break; fi
  sleep 60
done

/workspace/venv/bin/python - "$ARM" "$OUT" "$NG" "$HEAD_MIB" "$SHM_FREE_MIB" "$MYPGID" "$ATTEMPTS" \
  "$HEAD_MIN" "$SHM_MIN" "$LBL" "$TRACE" <<'PY'
import datetime, json, sys
arm, out, ng, head, shm, mypgid, att, hmin, smin, lbl, trace = sys.argv[1:12]
json.dump({"arm": arm, "passed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "my_pgid": int(mypgid), "rechecks": int(att),
           "rule": {"other_bt_launch_groups_max": 2, "headroom_min_MiB": 24576, "shm_free_min_MiB": 4096,
                    "thresholds_are_floors": "a caller may raise them, never lower them; a lowering attempt is printed"},
           "effective_thresholds": {"headroom_min_MiB": int(hmin), "shm_free_min_MiB": int(smin)},
           "measured_at_pass": {"other_bt_launch_groups": int(ng), "headroom_MiB": int(head),
                                "shm_free_MiB": int(shm), "other_groups_labels": lbl.strip() or None},
           "grouping_rule": ("distinct OTHER PGID. NOT PID (one cell reads as five -> self-starvation) and "
                             "NOT an argv RUN_CONFIG*.json token (a launcher without that token reads as "
                             "zero groups -> false negative -> over-quota parallelism). The config path is "
                             "a label only."),
           "read_only": "inspects the process table; never signals another process",
           "recheck_trace": [l for l in trace.splitlines() if l.strip()]},
          open(out, "w"), indent=2)
print(f"  rungate PASS arm={arm} after {att} check(s); receipt {out}")
PY
