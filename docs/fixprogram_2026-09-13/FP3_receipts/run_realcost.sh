#!/bin/bash
R=/workspace/fp2_2026-09; H=$R/health_check; D=$R/devices_v4chain; KD=$R/king_v4; UP=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz
export RUN_ARM_ROOT=$H RUN_ARM_PY=/workspace/venv/bin/python
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$R/realcost/costb_fee_real_0907.json"
for s in 42 2027; do
  bash $D/run_arm.sh V4_A0_dyn_s${s}_REALCOST v4 w10_health.py $COMMON SLOW_NPY=$KD/SLOW_v3_on_v4axis.npy FSEED=$s FPRED=f10_A0_s$s.npy > $R/realcost/A0_s$s.out 2>&1 &
  bash $D/run_arm.sh V4_A1_dyn_s${s}_REALCOST v4 w10_health.py $COMMON SLOW_NPY=$KD/SLOW_v4.npy FSEED=$s FPRED=f10_v4RAW_s$s.npy > $R/realcost/A1_s$s.out 2>&1 &
done
wait; echo "ARMS_DONE $(date -u +%FT%TZ)"
mkdir -p $R/realcost/arms; for s in 42 2027; do for a in A0 A1; do cp $H/dev_v4/probe_artifacts/w10_ablation_series_V4_${a}_dyn_s${s}_REALCOST.npz $R/realcost/arms/w10_ablation_series_V4_${a}_dyn_s${s}.npz; done; done
env ARMS_DIR=$R/realcost/arms OUT_JSON=$R/realcost/PER_YEAR_TABLE_REALCOST.json OUT_MD=$R/realcost/PER_YEAR_TABLE_REALCOST.md UMASK_NPZ=$UP ARMS=A0,A1 SEATS=dyn SEEDS=42,2027 LEV=2.0 UB=2026-08-30T20:00:00Z WA_START=2022-06-30T00:00:00Z /workspace/venv/bin/python $D/fp2_per_year_table.py > $R/realcost/per_year.log 2>&1; echo "TABLE_RC=$? $(date -u +%FT%TZ)"
