#!/bin/bash
# Run gate. TEAM RULE (lead 2026-09-25, supersedes "strictly one engine cell at a time"): at most TWO engine cells in
# parallel. Start only if ALL THREE hold:
#   (a) at most TWO other bt_launch GROUPS in the process table (lead ruling 2026-09-25, total cap 3 cells),
#       groups counted by DISTINCT PGID -- one launcher's workers share its PGID. Counting PIDs would read one cell
#       as five; matching a config path in argv misses a launcher whose argv has no such token (pgid 3062350);
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
# Count OTHERS' engine groups by DISTINCT PGID, not by the config path in argv.
# Why the change (lead spotted pgid 3062350 on 2026-09-25): a bt_launch whose argv carries no RUN_CONFIG*.json token
# was counted as ZERO groups by the previous version -- a false negative that would let me start alongside two others.
# Identifying "is someone running an engine" by a STRING PATTERN in argv is a textual instrument for a behavioural
# property. The PGID is the behaviour: one launcher's worker PIDs all share its PGID (verified on pnoise 3049880),
# so distinct other PGIDs == distinct other engine groups regardless of how the command line looks.
# The config path is kept only as a LABEL, printed when present so the receipt names who is running.
OTHERP=$(ps -eo pgid,args | grep "bt_launch\.py" | grep -v grep \
         | awk -v me="$MYPGID" '$1 != me {print $1}' | sort -u)
NG=$(printf '%s\n' "$OTHERP" | grep -c . )
OTHERG=$(ps -eo pgid,args | grep "bt_launch\.py" | grep -v grep \
         | awk -v me="$MYPGID" '$1 != me {lbl="(no config path in argv)"; for(i=1;i<=NF;i++) if ($i ~ /RUN_CONFIG.*\.json$/) {lbl=$i; break} print $1"="lbl}' \
         | sort -u)
echo "  rungate: other_bt_launch_groups=${NG} cgroup_headroom=${H}MiB shm_free=${D}MiB (need groups<=2, headroom>=${HEAD_MIN_MIB}, shm>=${SHM_MIN_MIB})"
[ "$NG" -gt 0 ] && printf '  rungate: other group(s): %s\n' "$(printf '%s ' $OTHERG)"
# lead ruling 2026-09-25: total cap 3 cells => at most 2 OTHER groups. Memory is protected by (b) and (c) below;
# the group cap no longer doubles as a memory guard, which is what starved a third agent under the cap of 2.
MAX_OTHER=2
if [ "$NG" -gt "$MAX_OTHER" ]; then echo "  rungate: WAIT (${NG} other engine groups running, cap is ${MAX_OTHER})"; exit 9; fi
if [ "$H" -lt "$HEAD_MIN_MIB" ]; then echo "  rungate: WAIT (cgroup headroom below ${HEAD_MIN_MIB}MiB)"; exit 9; fi
if [ "$D" -lt "$SHM_MIN_MIB" ]; then echo "  rungate: WAIT (/dev/shm free below ${SHM_MIN_MIB}MiB)"; exit 9; fi
echo "  rungate: OK"
