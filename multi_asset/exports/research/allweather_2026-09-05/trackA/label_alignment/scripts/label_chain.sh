#!/bin/bash
# label_chain.sh — PREREG_king_label_alignment_2026-09-06 arms + readings (run ONLY after results/code_check.json holds and the lead has the receipt).
# Arms (only the target differs; device trackA_gate_s1.py byte-identical; NJOBS=12, OMP=12 recorded in every CONFIG line):
#   BASE    : ARMS="BASE:" no Y4_ALT                       -> preds/pred_BASE_s{42,2027}.npy   (= the 12-thread identity rerun, copied)
#   ALT_SUM : ARMS="BASE:" Y4_ALT=features/y4_startE.npz    -> preds/pred_ALT_SUM_s*.npy
#   ALT_ACC : ARMS="BASE:" Y4_ALT=features/y4_startE_acc.npz-> preds/pred_ALT_ACC_s*.npy
# Book level: health-check main-arm form (rider device copy, SPOTSUP_B=0 == w10_health.py bitwise), prod caliber dev_alt, SLOW_NPY = arm preds,
#   OUT_TAG LA_<ARM>_s<seed>; 3 runs in parallel x OMP 4 = 12 threads; paired Δ per gross (s2_paired_delta.py RULE=s2 prints; reading via label_verdict.py).
set -u
ROOT=/workspace/review_scratch/allweather_trackA; L=$ROOT/label_alignment; PY=/workspace/venv/bin/python; RL="bash $L/run_logged.sh"
cd $ROOT
echo "LABEL_CHAIN_START $(date -u +%FT%TZ)" >> $L/logs/chain.log
COMMONS="OMP_NUM_THREADS=12 OPENBLAS_NUM_THREADS=12 MKL_NUM_THREADS=12 FEA_IN=/workspace/data/wide_fea_v2ext.npy META_IN=/workspace/data/wide_fea_v2ext_meta.npz ARMS=BASE: SEEDS=42,2027 NJOBS=12"
cp $L/preds_identity/pred_BASE_s42.npy $L/preds_identity/pred_BASE_s2027.npy $L/preds/
$RL s1_ALT_SUM $COMMONS Y4_ALT=$ROOT/features/y4_startE.npz OUT_JSON=$L/results/s1_ALT_SUM.json PRED_DIR=$L/preds_altsum $PY scripts/trackA_gate_s1.py || { echo "LABEL_HALT s1_ALT_SUM" >> $L/logs/chain.log; exit 2; }
$RL s1_ALT_ACC $COMMONS Y4_ALT=$ROOT/features/y4_startE_acc.npz OUT_JSON=$L/results/s1_ALT_ACC.json PRED_DIR=$L/preds_altacc $PY scripts/trackA_gate_s1.py || { echo "LABEL_HALT s1_ALT_ACC" >> $L/logs/chain.log; exit 2; }
for s in 42 2027; do cp $L/preds_altsum/pred_BASE_s$s.npy $L/preds/pred_ALT_SUM_s$s.npy; cp $L/preds_altacc/pred_BASE_s$s.npy $L/preds/pred_ALT_ACC_s$s.npy; done
sha256sum $L/preds/*.npy > $L/results/preds_sha256.txt
# ---- book level ----
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade SPOTSUP_B=0"
UP=/workspace/review_scratch/health_check/masks/umask_UPIT.npz; CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
for s in 42 2027; do
  for k in BASE ALT_SUM ALT_ACC; do
    TAG=LA_${k}_s${s}; NPY=$L/preds/pred_${k}_s${s}.npy
    CMD="env $COMMON SLOW_NPY=$NPY FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB OUT_TAG=$TAG $PY ../w10_health_spotsup.py"
    echo "CMD[$TAG] (cwd=$ROOT/rider/dev_alt) $(date -u +%FT%TZ): $CMD" >> $L/logs/commands.txt
    (cd $ROOT/rider/dev_alt && $CMD > $L/logs/$TAG.log 2>&1; echo "END[$TAG] rc=$? $(date -u +%FT%TZ)" >> $L/logs/commands.txt) &
  done
  wait
done
for s in 42 2027; do for k in ALT_SUM ALT_ACC; do
  echo "CMD[la_paired_${k}_s${s}] $(date -u +%FT%TZ): RULE=s2 s2_paired_delta.py LA_BASE_s${s} LA_${k}_s${s}" >> $L/logs/commands.txt
  RULE=s2 $PY scripts/s2_paired_delta.py rider/dev_alt/probe_artifacts/w10_ablation_series_LA_BASE_s${s}.npz rider/dev_alt/probe_artifacts/w10_ablation_series_LA_${k}_s${s}.npz $L/results/la_paired_${k}_s${s}.json > $L/logs/la_paired_${k}_s${s}.log 2>&1
done; done
# ---- score level: cross-target IC + exec-window paired Δ CI; horizon spectrum ----
export OMP_NUM_THREADS=12 OPENBLAS_NUM_THREADS=12 MKL_NUM_THREADS=12
$RL label_eval PRED_DIR=$L/preds ARMS=BASE,ALT_SUM,ALT_ACC SEEDS=42,2027 OUT_JSON=$L/results/label_eval.json $PY scripts/label_eval.py || { echo "LABEL_HALT eval" >> $L/logs/chain.log; exit 2; }
PR=""; for k in BASE ALT_SUM ALT_ACC; do for s in 42 2027; do PR="$PR,${k}_s${s}=$L/preds/pred_${k}_s${s}.npy"; done; done
$RL horizon PREDS="${PR#,}" OUT_JSON=$L/results/horizon_profile.json $PY scripts/horizon_profile.py || { echo "LABEL_HALT horizon" >> $L/logs/chain.log; exit 2; }
$RL verdict $PY scripts/label_verdict.py || { echo "LABEL_HALT verdict" >> $L/logs/chain.log; exit 2; }
sha256sum $L/results/*.json $L/results/*.txt rider/dev_alt/probe_artifacts/w10_ablation_series_LA_*.npz >> $L/results/SHA256SUMS_pod.txt
echo "LABEL_CHAIN_DONE $(date -u +%FT%TZ)" >> $L/logs/chain.log
