#!/bin/bash
# PREREG_caliber_program §2 book layer: config verbatim = chain_kingclip.sh (CRYPTO default arm); only SLOW_NPY varies (+W3FIX for the fixed seat).
cd /workspace/review_scratch/health_check
AB=/workspace/review_scratch/king_clamp_ablation
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UC=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz; CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
sha256sum w10_health.py $UC $CB $AB/slow_pred_*.npy >> logs/chain_kclamp.log
for s in 42 2027; do for arm in OLD CLAMP DROP138; do
  bash run_arm.sh KCL_${arm}_dyn_s${s} prod w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UC COSTB_JSON=$CB SLOW_NPY=$AB/slow_pred_${arm}_s${s}.npy > logs/KCL_${arm}_dyn_s${s}.out 2>&1 &
  bash run_arm.sh KCL_${arm}_fix_s${s} prod w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UC COSTB_JSON=$CB SLOW_NPY=$AB/slow_pred_${arm}_s${s}.npy W3FIX=0.21,0,0.79 > logs/KCL_${arm}_fix_s${s}.out 2>&1 &
done; done; wait
echo "CHAIN_KCLAMP_DONE $(date -u +%FT%TZ)" >> logs/chain_kclamp.log
