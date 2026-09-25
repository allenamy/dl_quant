#!/bin/bash
# Run gate. TEAM RULE (lead 2026-09-25, supersedes "strictly one engine cell at a time"): at most TWO engine cells in
# parallel. Start only if ALL THREE hold:
#   (a) at most ONE other bt_launch GROUP in the process table, groups identified by the config path in argv
#       (not by PID count -- one launcher spawns several worker PIDs sharing one config path);
#   (b) cgroup headroom  memory.max - anon - shmem  >= 24 GiB
#       (the engine's own gate is 22 GiB; 2 GiB of slack so a second cell does not start and then idle inside the
#        engine holding a slot);
#   (c) /dev/shm free >= 4 GiB.
# Otherwise yield. Recheck every 60s by the caller. The process table is READ ONLY -- never signal another agent's run;
# name-based killing is forbidden on this shared host.
# WHY the rule changed: strict exclusion was set right after the 04:33Z oom_kill when /dev/shm was pinned at 26.5 GiB
# with 1.4-2.0 GiB free. With 35 GiB cgroup headroom and 9 GiB shm free, strict exclusion only starves the queue.
# All three numbers are printed on every check so the receipt shows what the decision was made on.
# The team rule's thresholds are a FLOOR a caller cannot lower. The previous signature took a single "need MiB"
# argument and the running queue still passes 3000 -- read naively that would set the headroom bar to 3 GiB and
# silently weaken the rule. So an argument may only RAISE a threshold, never lower it, and a lowering attempt is
# printed. This is the same shape as a caller-supplied default quietly overriding a policy.
RULE_HEAD_MIN=24576
RULE_SHM_MIN=4096
REQ_HEAD=${1:-$RULE_HEAD_MIN}
REQ_SHM=${2:-$RULE_SHM_MIN}
HEAD_MIN_MIB=$RULE_HEAD_MIN; SHM_MIN_MIB=$RULE_SHM_MIN
[ "$REQ_HEAD" -gt "$RULE_HEAD_MIN" ] 2>/dev/null && HEAD_MIN_MIB=$REQ_HEAD
[ "$REQ_SHM" -gt "$RULE_SHM_MIN" ] 2>/dev/null && SHM_MIN_MIB=$REQ_SHM
if [ "${REQ_HEAD:-0}" -lt "$RULE_HEAD_MIN" ] 2>/dev/null; then
  echo "  rungate: caller asked for headroom>=${REQ_HEAD}MiB, below the team rule ${RULE_HEAD_MIN}MiB -> using the rule"
fi
M=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo 0)
A=$(grep "^anon " /sys/fs/cgroup/memory.stat 2>/dev/null | awk '{print $2}')
S=$(grep "^shmem " /sys/fs/cgroup/memory.stat 2>/dev/null | awk '{print $2}')
case "$M" in ''|max) M=0 ;; esac
H=$(( (M - A - S) / 1024 / 1024 ))
D=$(df -BM /dev/shm | tail -1 | awk '{print $4}' | tr -d M)
MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
# group OTHERS' bt_launch by the config path in argv; count distinct groups
OTHERG=$(ps -eo pgid,args | grep "bt_launch\.py" | grep -v grep \
         | awk -v me="$MYPGID" '$1 != me {for(i=1;i<=NF;i++) if ($i ~ /RUN_CONFIG.*\.json$/) {print $i; break}}' \
         | sort -u)
NG=$(printf '%s\n' "$OTHERG" | grep -c . )
echo "  rungate: other_bt_launch_groups=${NG} cgroup_headroom=${H}MiB shm_free=${D}MiB (need groups<=1, headroom>=${HEAD_MIN_MIB}, shm>=${SHM_MIN_MIB})"
[ "$NG" -gt 0 ] && printf '  rungate: other group(s): %s\n' "$(printf '%s ' $OTHERG)"
if [ "$NG" -gt 1 ]; then echo "  rungate: WAIT (two or more other engine cells already running)"; exit 9; fi
if [ "$H" -lt "$HEAD_MIN_MIB" ]; then echo "  rungate: WAIT (cgroup headroom below ${HEAD_MIN_MIB}MiB)"; exit 9; fi
if [ "$D" -lt "$SHM_MIN_MIB" ]; then echo "  rungate: WAIT (/dev/shm free below ${SHM_MIN_MIB}MiB)"; exit 9; fi
echo "  rungate: OK"
