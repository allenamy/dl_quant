#!/bin/bash
# run_replay_arms.sh — Track B: stage each finished fit (ext grid → 0822 grid, first nB rows) and replay it through the health-check main-arm device
# (U-PIT · m1 · FTRIM zero · msharpe 900 · PHI 0.45 · live fee tiers · d30_n2_c42; prod caliber), FSEED = the fit's seed; FPRED = the staged file.
# usage: bash run_replay_arms.sh <LABEL:SEED> [<LABEL:SEED> ...]      e.g. run_replay_arms.sh IDENT:42 B1:42 B2:42 B3:42
B=/workspace/review_scratch/allweather_trackB; R=$B/replay; H=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python; cd $R || exit 2
SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
for spec in "$@"; do
  L=${spec%%:*}; S=${spec##*:}; src=$B/f8_out/preds/f10_V2MAIN_${L}_s${S}.npy
  [ -f "$src" ] || { echo "missing preds $src"; exit 3; }
  grep -q "END\[$L s$S\] .* rc=0" $B/logs/commands.txt || { echo "fit $L s$S not finished with rc=0 (commands.txt)"; exit 4; }
  (cd $B && $PY stage_preds.py $src f10_trackB_${L}_s${S}.npy | tee -a logs/stage.log)
  bash run_arm.sh ${L}_s${S} prod w10_health.py $COMMON FSEED=$S FPRED=f10_trackB_${L}_s${S}.npy > logs/${L}_s${S}.out 2>&1 &
done
wait
grep -E "^END" logs/commands.txt | tail -n $#
sha256sum dev_alt/probe_artifacts/w10_ablation_series_*.npz dev_alt/f8_2026-08-22/preds/f10_trackB_*.npy > logs/replay_sha256.txt; echo "REPLAY_BATCH_DONE $(date -u +%FT%TZ) $*" >> logs/replay_chain.log
