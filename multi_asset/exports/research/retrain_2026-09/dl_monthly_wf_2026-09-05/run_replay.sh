#!/bin/bash
# run_replay.sh — dl_monthly_wf replay arms for one TAG (mE60 | mE1), CPU only, concurrent (4 threads each; 64 cores).
# Primary form = health_check M1_UPIT_prod_s42_ccal (chain_m1.sh COMMON + FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=UPIT COSTB_JSON=fee_steady), only FPRED (and PHI for the PHI1 arms) varies.
# usage: bash run_replay.sh <TAG> [withbase]   (withbase: also run the PHI1 baseline once)
TAG=$1; R=/workspace/review_scratch/dl_monthly_wf/replay; H=/workspace/review_scratch/health_check; cd $R || exit 2
SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
[ -f dev_alt/f8_2026-08-22/preds/f10_V2MAIN_${TAG}spl_s42.npy ] || { echo "missing spliced preds for $TAG"; exit 3; }
bash run_arm.sh M1_${TAG}spl_prod_s42_ccal prod w10_health.py $COMMON PHI=0.45 FPRED=f10_V2MAIN_${TAG}spl_s42.npy > logs/M1_${TAG}spl.out 2>&1 &
bash run_arm.sh M1_${TAG}pure_prod_s42_ccal prod w10_health.py $COMMON PHI=0.45 FPRED=f10_V2MAIN_${TAG}_s42.npy > logs/M1_${TAG}pure.out 2>&1 &
bash run_arm.sh PHI1_${TAG}spl_prod_s42_ccal prod w10_health.py $COMMON PHI=1.0 FPRED=f10_V2MAIN_${TAG}spl_s42.npy > logs/PHI1_${TAG}spl.out 2>&1 &
if [ "$2" = "withbase" ]; then bash run_arm.sh PHI1_BASE_prod_s42_ccal prod w10_health.py $COMMON PHI=1.0 > logs/PHI1_BASE.out 2>&1 & fi
wait
A="dev_alt/probe_artifacts/w10_ablation_series_M1_${TAG}spl_prod_s42_ccal.npz dev_alt/probe_artifacts/w10_ablation_series_M1_${TAG}pure_prod_s42_ccal.npz dev_alt/probe_artifacts/w10_ablation_series_PHI1_${TAG}spl_prod_s42_ccal.npz"
[ "$2" = "withbase" ] && A="$A dev_alt/probe_artifacts/w10_ablation_series_PHI1_BASE_prod_s42_ccal.npz dev_alt/probe_artifacts/w10_ablation_series_BASE_M1_UPIT_prod_s42_ccal.npz"
/workspace/venv/bin/python health_metrics.py $A > logs/health_metrics_${TAG}.log 2>&1; echo "METRICS_${TAG} rc=$? $(date -u +%FT%TZ)" >> logs/replay_chain.log
sha256sum $A >> logs/replay_chain.log
echo "REPLAY_${TAG}_DONE $(date -u +%FT%TZ)" >> logs/replay_chain.log
