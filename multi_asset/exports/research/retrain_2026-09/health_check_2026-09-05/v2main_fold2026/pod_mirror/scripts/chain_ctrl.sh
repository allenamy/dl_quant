#!/bin/bash
# chain_ctrl.sh — device-equivalence receipts BEFORE using the new predictions (CPU only; runs while the GPU trains):
#  (i)  eq_default : dev layout (log meta), the health_check chain_m1 equivalence command verbatim -> must be bitwise == axisB R0_pinned_log_s42
#  (ii) ctrl_alt   : dev_alt layout, the health_check M1_UPIT_prod_s42_ccal command verbatim (default FPRED) -> must be bitwise == health_check artifact
#  (iii) ctrl_pad  : dev_alt_ext layout (ext dlw_targets grid + NaN-padded copy of the same old preds), FPRED explicit -> arrays must == health_check artifact (config differs in the FPRED label only)
ROOT=/workspace/review_scratch/v2main_fold2026; R=$ROOT/replay; cd $R
HC=/workspace/review_scratch/health_check
REF=/workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UP=$HC/masks/umask_UPIT.npz; CB=$HC/calib/costb_fee_steady.json
bash $ROOT/scripts/run_arm.sh eq_default_pinned_log_s42 dev w10_health.py LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero > $R/logs/eq_default.out 2>&1 &
bash $ROOT/scripts/run_arm.sh CTRLALT_M1_UPIT_prod_s42_ccal dev_alt w10_health.py $COMMON FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB > $R/logs/ctrl_alt.out 2>&1 &
bash $ROOT/scripts/run_arm.sh CTRLPAD_M1_UPIT_prod_s42_ccal dev_alt_ext w10_health.py $COMMON FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB FPRED=f10_V2MAIN_s42_padext.npy > $R/logs/ctrl_pad.out 2>&1 &
bash $ROOT/scripts/run_arm.sh CTRLPAD_M1_UPIT_prod_s2027_ccal dev_alt_ext w10_health.py $COMMON FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB FPRED=f10_V2MAIN_s2027_padext.npy > $R/logs/ctrl_pad2027.out 2>&1 &
wait
PY=/workspace/venv/bin/python
{
$PY check_equiv.py dev/probe_artifacts/w10_ablation_series_eq_default_pinned_log_s42.npz $REF "(i) my w10_health.py copy, dev layout, default path vs axisB R0_pinned_log_s42"
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_CTRLALT_M1_UPIT_prod_s42_ccal.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz "(ii) dev_alt verbatim primary arm vs health_check M1_UPIT_prod_s42_ccal"
$PY check_equiv.py dev_alt_ext/probe_artifacts/w10_ablation_series_CTRLPAD_M1_UPIT_prod_s42_ccal.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz "(iii) dev_alt_ext (ext grid + padded old preds, FPRED explicit) vs health_check M1_UPIT_prod_s42_ccal"
$PY check_equiv.py dev_alt_ext/probe_artifacts/w10_ablation_series_CTRLPAD_M1_UPIT_prod_s2027_ccal.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s2027_ccal.npz "(iii) dev_alt_ext s2027 padded vs health_check M1_UPIT_prod_s2027_ccal"
} > $R/logs/check_equiv_ctrl.log 2>&1
echo "CHAIN_CTRL_DONE $(date -u +%FT%TZ)" >> $R/logs/check_equiv_ctrl.log
cat $R/logs/check_equiv_ctrl.log
