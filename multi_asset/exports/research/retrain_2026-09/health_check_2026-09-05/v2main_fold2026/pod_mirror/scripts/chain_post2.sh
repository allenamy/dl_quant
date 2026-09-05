#!/bin/bash
# chain_post2.sh — composite replay inputs (old folds < 2026 + new 2026 fold), the extended primary arms EXTC (both seeds) + EXT0901C context,
# metrics + paired comparisons, re-run agreement (patched), sha listing. Supersedes the fold-only EXT arms of chain_post.sh (kept, labelled superseded).
set -o pipefail
ROOT=/workspace/review_scratch/v2main_fold2026; R=$ROOT/replay; HC=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python
cd $ROOT
$PY scripts/build_composite.py > logs/build_composite.log 2>&1; echo "COMPOSITE rc=$? $(date -u +%FT%TZ)" >> logs/chain_post2.log
for s in 42 2027; do ln -sfn $ROOT/preds/f10_V2MAIN_ext2026comp_s$s.npy $R/dev_alt_ext/f8_2026-08-22/preds/f10_V2MAIN_ext2026comp_s$s.npy; ln -sfn $ROOT/preds/f10_V2MAIN_ext0901comp_s$s.npy $R/dev_alt_ext/f8_2026-08-22/preds/f10_V2MAIN_ext0901comp_s$s.npy; done
$PY scripts/agreement.py > logs/agreement.log 2>&1; echo "AGREEMENT2 rc=$? $(date -u +%FT%TZ)" >> logs/chain_post2.log
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UP=$HC/masks/umask_UPIT.npz; CB=$HC/calib/costb_fee_steady.json
for s in 42 2027; do
  bash scripts/run_arm.sh EXTC_M1_UPIT_prod_s${s}_ccal dev_alt_ext w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB FPRED=f10_V2MAIN_ext2026comp_s${s}.npy > $R/logs/EXTC_s$s.out 2>&1 &
  bash scripts/run_arm.sh EXT0901C_M1_UPIT_prod_s${s}_ccal dev_alt_ext w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB FPRED=f10_V2MAIN_ext0901comp_s${s}.npy > $R/logs/EXT0901C_s$s.out 2>&1 &
done
wait; echo "ARMS2_DONE $(date -u +%FT%TZ)" >> logs/chain_post2.log
cd $R; A=""
for s in 42 2027; do A="$A dev_alt_ext/probe_artifacts/w10_ablation_series_EXTC_M1_UPIT_prod_s${s}_ccal.npz dev_alt_ext/probe_artifacts/w10_ablation_series_EXT0901C_M1_UPIT_prod_s${s}_ccal.npz"; done
$PY health_metrics_ext.py $A > logs/health_metrics_ext2.log 2>&1; echo "METRICS2 rc=$? $(date -u +%FT%TZ)" >> $ROOT/logs/chain_post2.log
cd $ROOT
for s in 42 2027; do $PY scripts/paired_compare.py $s $R/dev_alt_ext/probe_artifacts/w10_ablation_series_EXTC_M1_UPIT_prod_s${s}_ccal.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s${s}_ccal.npz $R/dev_alt_ext/probe_artifacts/w10_ablation_series_EXT0901C_M1_UPIT_prod_s${s}_ccal.npz > logs/pairedC_s$s.log 2>&1; mv results/paired_s$s.json results/pairedC_s$s.json; echo "PAIREDC s$s rc=$? $(date -u +%FT%TZ)" >> logs/chain_post2.log; done
$PY replay/check_equiv.py replay/dev_alt_ext/probe_artifacts/w10_ablation_series_EXTC_M1_UPIT_prod_s42_ccal.npz replay/dev_alt_ext/probe_artifacts/w10_ablation_series_EXT0901C_M1_UPIT_prod_s42_ccal.npz "EXTC vs EXT0901C s42 (same old folds + 2026 fold from this retrain vs from 09-01 run)" > logs/check_equiv_extc_vs_0901.log 2>&1
$PY replay/check_equiv.py replay/dev_alt_ext/probe_artifacts/w10_ablation_series_EXTC_M1_UPIT_prod_s2027_ccal.npz replay/dev_alt_ext/probe_artifacts/w10_ablation_series_EXT0901C_M1_UPIT_prod_s2027_ccal.npz "EXTC vs EXT0901C s2027" >> logs/check_equiv_extc_vs_0901.log 2>&1
sha256sum scripts/*.py scripts/*.sh preds/*.npy results/*.json models/* replay/w10_health.py replay/health_metrics_ext.py replay/check_equiv.py replay/dev_alt_ext/probe_artifacts/*.npz replay/dev_alt/probe_artifacts/*.npz replay/dev/probe_artifacts/*.npz replay/results/*.json replay/results/*.txt > logs/SHA256SUMS.txt 2>/dev/null
echo "CHAIN_POST2_DONE $(date -u +%FT%TZ)" >> logs/chain_post2.log; cat logs/chain_post2.log
