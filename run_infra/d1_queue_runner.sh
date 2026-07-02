#!/bin/bash
# Persistent PRIORITY-SCAN queue-runner for the D1 Stage-1+ arms.
# queue.txt is an ORDERED priority list (top = highest). Each cycle the runner
# RE-SCANS from the top and runs the FIRST entry that is (config-ready) AND
# (not-yet-done). => not-ready arms are DEFERRED (retried next cycle when their
# config lands); a higher-priority arm that lands mid-run is picked next; lower
# fillers are "pulled forward" so the GPU never idles. Edit queue.txt any time.
# Per arm: launch -> epoch-5 early-abort -> wait -> OOM retry(preload=False) ->
# verify -> auto-score (uses the config's real output_dir) -> DONE line -> mark done.
# done markers: experiments/d1gate/done/<run_name>.
#
# EARLY-ABORT (pre-registered): at epoch 5, kill if EMA val-composite <
# ABORT_FRAC(0.5) x that month's Run1 epoch-5 EMA-composite ref (logs/d1_<mo>_run1.log;
# floor ABORT_FLOOR=0.005 when no ref) AND val sigR < ABORT_SIGR(0.015).
#
# Migration: adopts the orphaned in-flight d1_2026_04_run1 at startup.
set -u
REPO=/mnt/storage/private/work_hsy/quant_research_multi_asset
cd "$REPO" || exit 2
source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate hsy_v5push 2>/dev/null
export PYTHONPATH=.
RI="$REPO/run_infra"
STATUS="$REPO/experiments/d1gate/chain_status.log"
QUEUE="$REPO/experiments/d1gate/queue.txt"
DONEDIR="$REPO/experiments/d1gate/done"
ABORT_SIGR=0.015; ABORT_FRAC=0.5; ABORT_FLOOR=0.005
mkdir -p "$REPO/experiments/d1gate" "$DONEDIR" logs
ts(){ date -u +%FT%TZ; }
say(){ echo "$(ts) $*" >> "$STATUS"; }
say "QUEUE_RUNNER_START(priority-scan) pid=$$ early-abort=ep5:ema_comp<${ABORT_FRAC}x(Run1_ref|floor ${ABORT_FLOOR}) AND sigR<${ABORT_SIGR}"

run_name_of(){ python -c "import json,sys;print(json.load(open(sys.argv[1]))['output_dir'].rstrip('/').split('/')[-1])" "$1" 2>/dev/null; }
outdir_of(){ python -c "import json,sys;print(json.load(open(sys.argv[1]))['output_dir'].rstrip('/'))" "$1" 2>/dev/null; }
month_of(){ echo "$1" | sed -E 's/.*([0-9]{4}_[0-9]{2}).*/\1/'; }

score_and_log(){ # run_name output_dir
  local rn="$1" od="$2"
  if python "$RI/verify_d1.py" "$rn" "$od" >/dev/null 2>&1; then
    local line; line=$(python "$RI/statusline_d1.py" "$rn" "$od" 2>/dev/null)
    if [ -n "$line" ]; then say "DONE $line"; else say "DONE $rn (scorer empty)"; fi
  else
    say "FAIL $rn ($(python "$RI/verify_d1.py" "$rn" "$od" 2>&1))"
  fi
}

run_arm(){ # config_path seed
  local cfg="$1" seed="$2"
  local rn od mo log ref pid rc aborted ec sr kill_it
  rn=$(run_name_of "$cfg"); od=$(outdir_of "$cfg"); mo=$(month_of "$rn"); log="logs/${rn}.log"
  if [ -z "$rn" ] || [ -z "$od" ]; then say "SKIP unreadable config $cfg"; touch "$DONEDIR/badcfg_$(basename "$cfg")"; return; fi
  say "START $rn seed=$seed cfg=$cfg out=$od"
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
      break
    fi
    sleep 30
  done
  wait "$pid" 2>/dev/null; rc=$?
  if [ "$aborted" != "1" ]; then
    if grep -qiE "out of memory|CUDA out of memory|Killed|rc=137" "$log" 2>/dev/null || [ "$rc" -ne 0 ]; then
      if ! python "$RI/verify_d1.py" "$rn" "$od" >/dev/null 2>&1; then
        say "RETRY $rn nopreload (rc=$rc/oom)"
        npf=$(python "$RI/mk_nopreload.py" "$cfg")
        python multi_asset/train/train_dual_lob.py --config "$npf" --seed "$seed" > "logs/${rn}_nopreload.log" 2>&1
      fi
    fi
    score_and_log "$rn" "$od"
  fi
  touch "$DONEDIR/$rn"   # aborted/failed/ok all count -> no infinite retry
}

# ---- startup: adopt the orphaned in-flight d1_2026_04_run1 ----
if pgrep -f "d1_2026_04_run1.json" >/dev/null 2>&1; then
  say "ADOPT_WAIT d1_2026_04_run1 (orphan from old chain)"
  while pgrep -f "d1_2026_04_run1.json" >/dev/null 2>&1; do sleep 60; done
fi
if [ ! -f "$DONEDIR/d1_2026_04_run1" ]; then
  score_and_log d1_2026_04_run1 "experiments/d1gate/d1_2026_04_run1"; touch "$DONEDIR/d1_2026_04_run1"
fi

# ---- priority-scan loop (persistent) ----
idle=0
while true; do
  picked_cfg=""; picked_seed="42"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in \#*|"") continue;; STOP) break;; esac
    c=$(echo "$line" | awk '{print $1}')
    s=$(echo "$line" | awk '{x=$2; print (x==""?42:x)}')
    [ -f "$c" ] || continue                    # config not ready -> defer
    rn=$(run_name_of "$c"); [ -n "$rn" ] || continue
    [ -f "$DONEDIR/$rn" ] && continue          # already done
    picked_cfg="$c"; picked_seed="$s"; break
  done < "$QUEUE"
  if [ -z "$picked_cfg" ]; then
    if grep -q '^STOP$' "$QUEUE" 2>/dev/null; then say "QUEUE_STOP sentinel"; break; fi
    idle=$((idle+1)); [ $((idle % 20)) -eq 1 ] && say "QUEUE_IDLE nothing ready+undone (waiting for arm configs)"; sleep 30; continue
  fi
  idle=0
  run_arm "$picked_cfg" "$picked_seed"
done
say "QUEUE_RUNNER_EXIT pid=$$"
