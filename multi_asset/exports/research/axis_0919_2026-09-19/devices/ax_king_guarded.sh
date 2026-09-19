#!/bin/bash
# ax_king_guarded.sh (axis_0919): run the king feature builder (chain stage s15) ALONE (RUNBOOK 修订 9: peaks at 50-58 GB, container memory.max 61 GB).
# Precondition checked immediately before launch, and recorded: memory.max, free -g, cgroup anon bytes, and the top RSS processes. Refuses (rc 5) when
# anon > AX_KING_MAX_ANON_GB (default 6) — i.e. when anything sizeable is running, ours or another stream's. A sampler logs cgroup anon/current every 10 s
# for the whole run (peak evidence). usage: AXR=... AX_NEW_DAYS=... AX_IDX_END=... AX_HI_S=... bash ax_king_guarded.sh
set -o pipefail
R=${AXR:?}; L=$R/logs/king_guard.log; MAXA=${AX_KING_MAX_ANON_GB:-6}
anon_gb(){ awk '/^anon /{printf "%.2f", $2/1024/1024/1024}' /sys/fs/cgroup/memory.stat; }
{ echo "[$(date -u +%FT%TZ)] king guard: memory.max=$(cat /sys/fs/cgroup/memory.max) anon_GB=$(anon_gb) limit_anon_GB=$MAXA"
  free -g; grep -E "oom" /sys/fs/cgroup/memory.events; ps -eo pid,pgid,rss,etime,cmd --sort=-rss | head -8 | cut -c1-150; } >> $L
A=$(anon_gb); if awk -v a=$A -v m=$MAXA 'BEGIN{exit !(a>m)}'; then echo "[$(date -u +%FT%TZ)] KING_REFUSED anon ${A} GB > ${MAXA} GB (not alone)" | tee -a $L; exit 5; fi
( while true; do echo "$(date -u +%FT%TZ) anon_GB=$(anon_gb) current_GB=$(awk '{printf "%.2f", $1/1024/1024/1024}' /sys/fs/cgroup/memory.current)"; sleep 10; done ) >> $R/logs/king_mem_sampler.log 2>&1 &
SP=$!
STAGES=s15 RUN_KING=1 bash /workspace/axis_0919/devices/ax_chain.sh; rc=$?
kill $SP 2>/dev/null
{ echo "[$(date -u +%FT%TZ)] king done rc=$rc"; grep -E "oom" /sys/fs/cgroup/memory.events; } >> $L
exit $rc
