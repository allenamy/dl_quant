#!/bin/bash
# PREREG_king_clip_label_ablation §4 book layer. Config copied verbatim from chain_m1.sh's M1_UCRYPTO arm;
# the ONLY thing that varies is SLOW_NPY (the king leg's predictions) and, for the FIX block, W3FIX.
# Paired contrast: for each seed s, {OLD,WORST,DROP}_s share the same FSEED=s and the same everything else.
cd /workspace/review_scratch/health_check
AB=/workspace/review_scratch/king_clip_ablation
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UC=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz
CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
sha256sum w10_health.py $UC $CB $AB/slow_pred_*.npy >> logs/chain_kingclip.log
for s in 42 2027; do
  for arm in OLD WORST DROP; do
    bash run_arm.sh KC_${arm}_dyn_s${s} prod w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UC COSTB_JSON=$CB SLOW_NPY=$AB/slow_pred_${arm}_s${s}.npy > logs/KC_${arm}_dyn_s${s}.out 2>&1 &
    bash run_arm.sh KC_${arm}_fix_s${s} prod w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UC COSTB_JSON=$CB SLOW_NPY=$AB/slow_pred_${arm}_s${s}.npy W3FIX=0.21,0,0.79 > logs/KC_${arm}_fix_s${s}.out 2>&1 &
  done
done
wait
A=""
for s in 42 2027; do for arm in OLD WORST DROP; do for k in dyn fix; do A="$A dev_alt/probe_artifacts/w10_ablation_series_KC_${arm}_${k}_s${s}.npz"; done; done; done
/workspace/venv/bin/python health_metrics.py $A > logs/health_metrics_kingclip.log 2>&1
echo "METRICS rc=$? $(date -u +%FT%TZ)" >> logs/chain_kingclip.log
sha256sum dev_alt/probe_artifacts/w10_ablation_series_KC_*.npz >> logs/chain_kingclip.log
echo "CHAIN_KINGCLIP_DONE $(date -u +%FT%TZ)" >> logs/chain_kingclip.log
