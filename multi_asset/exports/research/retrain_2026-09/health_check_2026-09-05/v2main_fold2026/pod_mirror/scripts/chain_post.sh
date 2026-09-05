#!/bin/bash
# chain_post.sh — after both trainings finished: receipts (agreement, leak gate), the extended primary arms (EXT, both seeds) + EXT0901 context arms,
# metrics (health_metrics_ext.py) on EXT/EXT0901/CTRLPAD artifacts and on the health_check primary artifacts, paired comparisons, sha256 listing.
set -o pipefail
ROOT=/workspace/review_scratch/v2main_fold2026; R=$ROOT/replay; HC=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python
cd $ROOT
$PY scripts/agreement.py > logs/agreement.log 2>&1; echo "AGREEMENT rc=$? $(date -u +%FT%TZ)" >> logs/chain_post.log
$PY scripts/leakcheck_ext2026.py > logs/leakcheck_ext2026.log 2>&1; echo "LEAKCHECK rc=$? $(date -u +%FT%TZ)" >> logs/chain_post.log
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UP=$HC/masks/umask_UPIT.npz; CB=$HC/calib/costb_fee_steady.json
for s in 42 2027; do
  bash scripts/run_arm.sh EXT_M1_UPIT_prod_s${s}_ccal dev_alt_ext w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB FPRED=f10_V2MAIN_ext2026_s${s}.npy > $R/logs/EXT_s$s.out 2>&1 &
  bash scripts/run_arm.sh EXT0901_M1_UPIT_prod_s${s}_ccal dev_alt_ext w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB FPRED=f10_V2MAIN_ext0901_s${s}.npy > $R/logs/EXT0901_s$s.out 2>&1 &
done
wait
echo "ARMS_DONE $(date -u +%FT%TZ)" >> logs/chain_post.log
$PY scripts/make_health_metrics_ext.py $R/health_metrics_orig.py $R/health_metrics_ext.py >> logs/chain_post.log 2>&1
cd $R
A=""
for s in 42 2027; do A="$A dev_alt_ext/probe_artifacts/w10_ablation_series_EXT_M1_UPIT_prod_s${s}_ccal.npz dev_alt_ext/probe_artifacts/w10_ablation_series_EXT0901_M1_UPIT_prod_s${s}_ccal.npz dev_alt_ext/probe_artifacts/w10_ablation_series_CTRLPAD_M1_UPIT_prod_s${s}_ccal.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s${s}_ccal.npz"; done
$PY health_metrics_ext.py $A > logs/health_metrics_ext.log 2>&1; echo "METRICS rc=$? $(date -u +%FT%TZ)" >> $ROOT/logs/chain_post.log
cd $ROOT
for s in 42 2027; do $PY scripts/paired_compare.py $s $R/dev_alt_ext/probe_artifacts/w10_ablation_series_EXT_M1_UPIT_prod_s${s}_ccal.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s${s}_ccal.npz $R/dev_alt_ext/probe_artifacts/w10_ablation_series_EXT0901_M1_UPIT_prod_s${s}_ccal.npz > logs/paired_s$s.log 2>&1; echo "PAIRED s$s rc=$? $(date -u +%FT%TZ)" >> logs/chain_post.log; done
sha256sum scripts/*.py scripts/*.sh preds/*.npy results/*.json models/* replay/w10_health.py replay/health_metrics_ext.py replay/check_equiv.py replay/dev_alt_ext/probe_artifacts/*.npz replay/dev_alt/probe_artifacts/*.npz replay/dev/probe_artifacts/*.npz replay/results/*.json > logs/SHA256SUMS.txt 2>/dev/null
echo "CHAIN_POST_DONE $(date -u +%FT%TZ)" >> logs/chain_post.log; cat logs/chain_post.log
