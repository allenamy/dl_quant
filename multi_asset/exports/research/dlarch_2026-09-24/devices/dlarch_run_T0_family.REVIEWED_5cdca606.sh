#!/usr/bin/env bash
# dlarch_run_T0_family.sh — T0 x 8 seeds x 23 folds, strictly SEQUENTIAL (never two on the GPU at once).
# PREREG docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md revision 9 (lead: S before L; the 8 T0 seeds are also
# fresh's "model sampling family"). Seeds are pinned by DECISION_RULE ... 038e8e78f revision 1.
# After EACH seed it prints the artifact path + sha256 so fresh can reference a family member immediately,
# and it re-checks the GPU is not being used by anyone else before starting the next seed.
set -uo pipefail
EXP=/workspace/dlarch_2026-09-24
D=$EXP
SEEDS="42 2027 7 11 23 101 3 5"
LOG=$EXP/T0_family.log
say(){ echo "$(date -u +%H:%M:%SZ) $*" | tee -a "$LOG"; }
# MEMORY GATE. 2026-09-25 04:3xZ: an OOM kill (cgroup memory.events oom_kill) took out BOTH this driver
# and a concurrent combo run at fold 8/23. The ceiling is memory.max 56.8 GiB minus ~26.5 GiB pinned by
# /dev/shm, so a transient spike from several agents at once is enough. Wait for headroom rather than be
# killed: being killed loses the in-flight fold and, worse, leaves a half-written artifact behind.
MEM_NEED_GIB=8
memfree_gib(){ awk 'NR==FNR{m=$1;next}{printf "%.2f", (m-$1)/1073741824}' /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current; }
mem_wait(){
  for i in $(seq 1 240); do
    F=$(memfree_gib)
    awk -v f="$F" -v n="$MEM_NEED_GIB" 'BEGIN{exit !(f+0>=n+0)}' && { [ "$i" -gt 1 ] && say "  memory ok: ${F} GiB free"; return 0; }
    [ "$i" -eq 1 ] && say "  memory gate: only ${F} GiB free, need ${MEM_NEED_GIB} -- waiting"
    sleep 30
  done
  say "  memory gate: still short after 2 h, proceeding anyway and recording it"; return 0
}

say "=== T0 FAMILY START (8 seeds x 23 folds, sequential) ==="
for S in $SEEDS; do
  # yield to anyone else holding the GPU (news2 / fresh have priority)
  for i in $(seq 1 240); do
    OTHER=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | wc -l)
    [ "$OTHER" -eq 0 ] && break
    [ "$i" -eq 1 ] && say "seed $S: GPU busy ($OTHER proc), yielding"
    sleep 30
  done
  mem_wait
  say "seed $S: start  gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader)  mem_free=$(memfree_gib) GiB  oom_kill_so_far=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)"
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 5 /workspace/venv/bin/python -B "$D/dlarch_train_f10.py" \
      --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --seed "$S" --folds all \
      > "$EXP/logs_T0_s$S.log" 2>&1
  RC=$?
  if [ $RC -ne 0 ]; then
    say "seed $S: FAILED rc=$RC  oom_kill_now=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)  mem_free=$(memfree_gib) GiB"
    tail -5 "$EXP/logs_T0_s$S.log" | tee -a "$LOG"
    # rc 137 = SIGKILL (OOM): the per-fold resume makes a retry cheap and lossless, so retry ONCE.
    if [ $RC -eq 137 ]; then
      say "seed $S: rc=137 looks like SIGKILL/OOM -- waiting for headroom and retrying ONCE (per-fold resume keeps finished folds)"
      MEM_NEED_GIB=12 mem_wait
      env -i PATH=/usr/bin:/bin HOME=/root nice -n 5 /workspace/venv/bin/python -B "$D/dlarch_train_f10.py" \
          --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --seed "$S" --folds all \
          >> "$EXP/logs_T0_s$S.log" 2>&1
      RC=$?
      say "seed $S: retry rc=$RC"
    fi
    [ $RC -ne 0 ] && { say "seed $S: giving up, stopping the family run"; exit $RC; }
  fi
  OOF=$EXP/T3/T0/f10_s$S/F10_OOF.npz
  TR=$EXP/T3/T0/f10_s$S/TRAIN_RECEIPT.json
  say "seed $S: DONE  oof=$OOF  oof_sha256=$(sha256sum "$OOF" | cut -d' ' -f1)  receipt_sha256=$(sha256sum "$TR" | cut -d' ' -f1)  folds=$(/workspace/venv/bin/python -c "import json;print(len(json.load(open('$TR'))['folds']))")"
done
say "=== T0 FAMILY ALL DONE ==="
