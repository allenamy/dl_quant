#!/bin/bash
# Persistent queue-runner for the D1 Stage-1+ arms (replaces the fixed chain).
# Reads a QUEUE file (one entry per line: "<config_path> [seed]"; '#'=comment;
# 'STOP'=stop sentinel), supports APPENDING while running (re-reads each iter),
# never leaves the GPU idle. Per arm: launch -> epoch-5 early-abort -> wait ->
# OOM retry(preload=False) -> verify -> auto-score -> append DONE line -> next.
#
# EARLY-ABORT (pre-registered): at epoch 5, if EMA val-composite < ABORT_FRAC(0.5)
# x that month's Run1 epoch-5 EMA-composite reference (logs/d1_<mo>_run1.log; floor
# ABORT_FLOOR=0.005 when no ref) AND val sigR < ABORT_SIGR(0.015) -> kill + ABORTED_EARLY.
#
# Migration: adopts the orphaned in-flight d1_2026_04_run1 at startup (waits +
# scores it), so the old chain can be killed without losing that run.
set -u
REPO=/mnt/storage/private/work_hsy/quant_research_multi_asset
cd "$REPO" || exit 2
source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate hsy_v5push 2>/dev/null
export PYTHONPATH=.
RI="$REPO/run_infra"
STATUS="$REPO/experiments/d1gate/chain_status.log"
QUEUE="$REPO/experiments/d1gate/queue.txt"
CURSOR="$REPO/experiments/d1gate/queue.cursor"
ABORT_SIGR=0.015; ABORT_FRAC=0.5; ABORT_FLOOR=0.005
mkdir -p "$REPO/experiments/d1gate" logs
ts(){ date -u +%FT%TZ; }
say(){ echo "$(ts) $*" >> "$STATUS"; }
say "QUEUE_RUNNER_START pid=$$ early-abort=ep5:ema_comp<${ABORT_FRAC}x(Run1_ref|floor ${ABORT_FLOOR}) AND sigR<${ABORT_SIGR}"

run_name_of(){ python -c "import json,sys;print(json.load(open(sys.argv[1]))['output_dir'].rstrip('/').split('/')[-1])" "$1" 2>/dev/null; }
month_of(){ echo "$1" | sed -E 's/^d1_([0-9]{4}_[0-9]{2}).*/\1/'; }

score_and_log(){ # run_name
  local rn="$1"
  if python "$RI/verify_d1.py" "$rn" >/dev/null 2>&1; then
    local line; line=$(python "$RI/statusline_d1.py" "$rn" 2>/dev/null)
    if [ -n "$line" ]; then say "DONE $line"; else say "DONE $rn (scorer empty)"; fi
  else
    say "FAIL $rn ($(python "$RI/verify_d1.py" "$rn" 2>&1))"
  fi
}

run_arm(){ # config_path seed
  local cfg="$1" seed="$2"
  local rn mo log ref pid rc aborted
  rn=$(run_name_of "$cfg"); mo=$(month_of "$rn"); log="logs/${rn}.log"
  if [ -z "$rn" ]; then say "SKIP unreadable config $cfg"; return; fi
  say "START $rn seed=$seed cfg=$cfg"
  python multi_asset/train/train_dual_lob.py --config "$cfg" --seed "$seed" > "$log" 2>&1 &
  pid=$!
  ref=""
  [ -f "logs/d1_${mo}_run1.log" ] && ref=$(python "$RI/parse_ep5.py" "logs/d1_${mo}_run1.log" 5 | awk '{print $1}')
  aborted=0
  while kill -0 "$pid" 2>/dev/null; do
    read -r ec sr < <(python "$RI/parse_ep5.py" "$log" 5 2>/dev/null)
    if [ "${ec:-NA}" != "NA" ] && [ "${sr:-NA}" != "NA" ]; then
      kill_it=$(python -c "
ec=float('$ec'); sr=float('$sr'); ref='$ref'
thr=($ABORT_FRAC*float(ref)) if ref not in ('','NA') else $ABORT_FLOOR
print(1 if (sr<$ABORT_SIGR and ec<thr) else 0)" 2>/dev/null)
      if [ "$kill_it" = "1" ]; then
        kill "$pid" 2>/dev/null; sleep 3; kill -9 "$pid" 2>/dev/null
        say "ABORTED_EARLY $rn ep5 ema_comp=$ec sigR=$sr ref=${ref:-none}"
        aborted=1; break
      fi
      break   # epoch-5 seen and healthy -> stop monitoring, just wait to finish
    fi
    sleep 30
  done
  wait "$pid" 2>/dev/null; rc=$?
  [ "$aborted" = "1" ] && return
  if grep -qiE "out of memory|CUDA out of memory|Killed|rc=137" "$log" 2>/dev/null || [ "$rc" -ne 0 ]; then
    if ! python "$RI/verify_d1.py" "$rn" >/dev/null 2>&1; then
      say "RETRY $rn nopreload (rc=$rc/oom)"
      npf=$(python "$RI/mk_nopreload.py" "$cfg")
      python multi_asset/train/train_dual_lob.py --config "$npf" --seed "$seed" > "logs/${rn}_nopreload.log" 2>&1
    fi
  fi
  score_and_log "$rn"
}

# ---- startup: adopt the orphaned in-flight d1_2026_04_run1 ----
if pgrep -f "d1_2026_04_run1.json" >/dev/null 2>&1; then
  say "ADOPT_WAIT d1_2026_04_run1 (orphan from old chain)"
  while pgrep -f "d1_2026_04_run1.json" >/dev/null 2>&1; do sleep 60; done
fi
if [ ! -f "$REPO/experiments/d1gate/.scored_d1_2026_04_run1" ]; then
  score_and_log d1_2026_04_run1; touch "$REPO/experiments/d1gate/.scored_d1_2026_04_run1"
fi

# ---- main queue loop (persistent) ----
[ -f "$CURSOR" ] || echo 0 > "$CURSOR"
idle=0
while true; do
  cur=$(cat "$CURSOR" 2>/dev/null || echo 0)
  line=$(sed -n "$((cur+1))p" "$QUEUE" 2>/dev/null)
  if [ -z "$line" ]; then
    idle=$((idle+1))
    [ $((idle % 20)) -eq 1 ] && say "QUEUE_IDLE waiting for appends (cursor=$cur)"
    sleep 30; continue
  fi
  idle=0
  echo $((cur+1)) > "$CURSOR"   # advance before running (no double-run on restart)
  case "$line" in
    \#*|"") continue;;
    STOP) say "QUEUE_STOP sentinel reached"; break;;
  esac
  cfg=$(echo "$line" | awk '{print $1}')
  seed=$(echo "$line" | awk '{s=$2; print (s==""?42:s)}')
  if [ ! -f "$cfg" ]; then say "SKIP missing config $cfg (cursor=$cur)"; continue; fi
  run_arm "$cfg" "$seed"
done
say "QUEUE_RUNNER_EXIT pid=$$"
