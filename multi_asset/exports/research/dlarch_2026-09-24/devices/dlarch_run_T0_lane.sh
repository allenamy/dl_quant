#!/usr/bin/env bash
# dlarch_run_T0_lane.sh -- ONE lane of the T0 family run. Two lanes may run concurrently on one GPU
# (lead ruling 2026-09-25: 2-way parallel for the remaining T0 seeds, not 3-way).
#
# WORK STEALING, not a fixed split: both lanes pull from a shared seed list and claim a seed by
# `mkdir` of a claim directory, which is ATOMIC on the filesystem. Two benefits over assigning
# "lane A does 11,23; lane B does 101,3,5":
#   * self-balancing -- a lane that finishes early takes the next seed instead of idling
#     (a fixed split of 4 remaining seeds as 1+3 would leave one lane idle for ~1 hour)
#   * two lanes CANNOT start the same seed, so no two processes ever write one f10_s<seed> dir
#
# DETERMINISM PRECONDITION (receipt dlarch_gpu_parallel_determinism_2026-09-25.log): bitwise
# reproducibility under 2-way load was MEASURED, not configured -- the trainer sets only
# manual_seed, with no cudnn.deterministic and no use_deterministic_algorithms. Every version below
# is therefore pinned into each seed's receipt, and if ANY of them changes the probe must be re-run
# before parallel training continues.
#
# PROCESS COUNTING (lead ruling; my pgrep -f attempts were wrong twice): GPU users come from
# `nvidia-smi --query-compute-apps`, trainer processes from `ps -eo pid,pgid,args` filtered to the
# interpreter invocation. `pgrep -f` is never used: it self-matches inside an ssh command and it
# missed a launcher whose argv put --env-whitelist before --arm.
#
# usage: DLARCH_LANE=A bash dlarch_run_T0_lane.sh "23 101 3 5"
set -uo pipefail
EXP=/workspace/dlarch_2026-09-24
LANE="${DLARCH_LANE:-X}"
SEEDS="${1:?usage: dlarch_run_T0_lane.sh \"<seed list>\"}"
CLAIMS=$EXP/lane_claims
LOG=$EXP/T0_lane_$LANE.log
PY=/workspace/venv/bin/python
MAX_OTHER_GPU=1          # tolerate ONE other GPU process (the sibling lane); yield above that
mkdir -p "$CLAIMS"

say(){ echo "$(date -u +%H:%M:%SZ) [lane $LANE] $*" | tee -a "$LOG"; }

# how many processes are on the GPU, and how many of those are trainers of mine
gpu_procs(){ nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -c . ; }
my_trainers(){ ps -eo pid,args | awk '$2 ~ /\/python$/ && /dlarch_train_f10\.py/' | grep -c . ; }

mem_avail_gib(){
  awk 'NR==FNR{m=$1;next}/^anon /{a=$2}/^shmem /{s=$2}END{printf "%.2f",(m-a-s)/1073741824}' \
    /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.stat
}

env_json(){
  env -i PATH=/usr/bin:/bin HOME=/root "$PY" -B -c '
import json,sys,torch,subprocess
drv=subprocess.run(["nvidia-smi","--query-gpu=driver_version","--format=csv,noheader"],
                   capture_output=True,text=True).stdout.strip()
print(json.dumps({"python":sys.version.split()[0],"sys_prefix":sys.prefix,
  "torch":torch.__version__,"cuda":torch.version.cuda,"cudnn":torch.backends.cudnn.version(),
  "gpu":torch.cuda.get_device_name(0),"capability":list(torch.cuda.get_device_capability(0)),
  "driver":drv,"tf32_matmul":torch.backends.cuda.matmul.allow_tf32,
  "tf32_cudnn":torch.backends.cudnn.allow_tf32,
  "cudnn_deterministic":torch.backends.cudnn.deterministic,
  "cudnn_benchmark":torch.backends.cudnn.benchmark,
  "NOTE":"bitwise reproducibility under 2-way GPU load is MEASURED, not configured; "
         "if any field above changes, re-run probe_crosslevel.sh before continuing parallel training"},
  indent=1))'
}

say "=== LANE START  candidate seeds: $SEEDS ==="
say "env: $(env_json | tr -d '\n' | cut -c1-200)"

for S in $SEEDS; do
  # ---- atomic claim: mkdir succeeds for exactly one lane ----
  if ! mkdir "$CLAIMS/$S" 2>/dev/null; then
    say "seed $S already claimed by another lane, skipping"
    continue
  fi
  echo "$LANE $(date -u +%FT%TZ)" > "$CLAIMS/$S/owner"

  # ---- yield: at most MAX_OTHER_GPU foreign/sibling GPU processes ----
  for i in $(seq 1 240); do
    G=$(gpu_procs); M=$(mem_avail_gib)
    if [ "$G" -le "$MAX_OTHER_GPU" ]; then
      [ "$i" -gt 1 ] && say "seed $S: gpu clear now (procs=$G, avail=${M} GiB)"
      break
    fi
    [ "$i" -eq 1 ] && say "seed $S: $G GPU procs > $MAX_OTHER_GPU, yielding (avail ${M} GiB)"
    sleep 30
  done

  say "seed $S: start  gpu_procs=$(gpu_procs) my_trainers=$(my_trainers) avail=$(mem_avail_gib) GiB oom_kill=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)"
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 5 "$PY" -B "$EXP/dlarch_train_f10.py" \
      --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --seed "$S" --folds all \
      > "$EXP/logs_T0_lane${LANE}_s$S.log" 2>&1
  RC=$?
  say "seed $S: rc=$RC  oom_kill=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)"
  if [ $RC -ne 0 ]; then
    tail -4 "$EXP/logs_T0_lane${LANE}_s$S.log" | tee -a "$LOG"
    if [ $RC -eq 137 ]; then
      say "seed $S: rc=137 (SIGKILL/OOM) -- per-fold resume makes one retry cheap; retrying once"
      sleep 60
      env -i PATH=/usr/bin:/bin HOME=/root nice -n 5 "$PY" -B "$EXP/dlarch_train_f10.py" \
          --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --seed "$S" --folds all \
          >> "$EXP/logs_T0_lane${LANE}_s$S.log" 2>&1
      RC=$?; say "seed $S: retry rc=$RC"
    fi
    [ $RC -ne 0 ] && { say "seed $S: giving up; releasing the claim so the other lane may retry"; rmdir "$CLAIMS/$S" 2>/dev/null; continue; }
  fi

  OOF=$EXP/T3/T0/f10_s$S/F10_OOF.npz
  TR=$EXP/T3/T0/f10_s$S/TRAIN_RECEIPT.json
  NF=$("$PY" -c "import json;print(len(json.load(open('$TR'))['folds']))" 2>/dev/null || echo "?")
  # env pinned NEXT TO the artifact, per lead
  env_json > "$EXP/T3/T0/f10_s$S/ENVIRONMENT.json"
  say "seed $S: DONE folds=$NF oof_sha256=$(sha256sum "$OOF" | cut -d' ' -f1) receipt_sha256=$(sha256sum "$TR" | cut -d' ' -f1) env=$EXP/T3/T0/f10_s$S/ENVIRONMENT.json"
done
say "=== LANE DONE ==="
