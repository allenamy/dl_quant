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
  local rn od mo log ref pid rc aborted ec sr kill_it existing
  rn=$(run_name_of "$cfg"); od=$(outdir_of "$cfg"); mo=$(month_of "$rn"); log="logs/${rn}.log"
  if [ -z "$rn" ] || [ -z "$od" ]; then say "SKIP unreadable config $cfg"; touch "$DONEDIR/badcfg_$(basename "$cfg")"; return; fi
  # RESTART RECOVERY: if this exact config is ALREADY training (orphan from a
  # killed runner), ADOPT it (wait + score, no relaunch, no early-abort).
  existing=$(pgrep -f "$(basename "$cfg")" | head -1)
  if [ -n "$existing" ]; then
    say "ADOPT_RUNNING $rn pid=$existing (restart recovery; no relaunch/abort)"
    while kill -0 "$existing" 2>/dev/null; do sleep 30; done
    # If the adopted run finished cleanly -> score + mark done. If it DIED without
    # metrics (crash/OOM mid-run, e.g. GPU contention), do NOT mark done -> the
    # queue scan re-runs it FRESH once (the fresh non-adopt path always marks done,
    # so this is bounded). Never FAIL-loses a run that merely got preempted.
    if python "$RI/verify_d1.py" "$rn" "$od" >/dev/null 2>&1; then
      score_and_log "$rn" "$od"; touch "$DONEDIR/$rn"
    else
      say "ADOPT_INCOMPLETE $rn (adopted run died without metrics; leaving unmarked -> one fresh re-run)"
    fi
    return
  fi
  say "START $rn seed=$seed cfg=$cfg out=$od"
  python multi_asset/train/train_dual_lob.py --config "$cfg" --seed "$seed" > "$log" 2>&1 &
  pid=$!
  aborted=0
  # ARM A (choppy-specialist, spec_*): NO ep5 early-abort. It trains on ~153
  # low-trend days so σŷ/σy warms slowly (crosses ~ep6-8); the ep5 gate would
  # false-negative it. Selection/patience-10 + live σ-crossing watch cover it.
  if [[ "$rn" == spec_* ]]; then
    say "NO_EARLY_ABORT $rn (ARM A slow-sigma-warmup exemption)"
  else
    ref=""
    [ -f "logs/d1_${mo}_run1.log" ] && ref=$(python "$RI/parse_ep5.py" "logs/d1_${mo}_run1.log" 5 | awk '{print $1}')
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
  fi
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

# (the original d1_2026_04_run1 orphan-adopt is retired — the generic restart-
# recovery in run_arm handles any in-flight run, and re-running it on relaunch
# wrongly FAIL-marked the requeued attribution run.)

# ---- priority-scan loop (persistent) ----
idle=0
while true; do
  # SELF-EXPIRING eval-window pause: `touch experiments/d1gate/PAUSE` to hold the
  # queue for a manual eval window; it AUTO-RESUMES after 30min so a forgotten
  # pause can never idle the GPU indefinitely. `rm PAUSE` to resume early.
  if [ -f "$REPO/experiments/d1gate/PAUSE" ]; then
    page=$(( $(date +%s) - $(stat -c %Y "$REPO/experiments/d1gate/PAUSE" 2>/dev/null || echo 0) ))
    if [ "$page" -lt 1800 ]; then
      idle=$((idle+1)); [ $((idle % 6)) -eq 1 ] && say "PAUSED eval-window ${page}s/1800s"; sleep 60; continue
    fi
    say "PAUSE expired (${page}s) -> auto-resume"; rm -f "$REPO/experiments/d1gate/PAUSE"
  fi
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
