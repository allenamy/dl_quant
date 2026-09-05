#!/bin/bash
# chain_eq.sh — health_check bootstrap: layout, pristine + patched equivalence runs (parallel), mask build (parallel), bitwise checks.
cd /workspace/review_scratch/health_check
bash setup_dev.sh > logs/setup_dev.log 2>&1
ENV="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
bash run_arm.sh eq_pristine_pinned_log_s42 log w10_universe_recheck.py $ENV > logs/eq_pristine.out 2>&1 &
P1=$!
bash run_arm.sh eq_patched_pinned_log_s42 log w10_health.py $ENV > logs/eq_patched.out 2>&1 &
P2=$!
/workspace/venv/bin/python build_umask.py > logs/build_umask.log 2>&1 &
P3=$!
wait $P1 $P2
REF=/workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz
/workspace/venv/bin/python check_equiv.py dev/probe_artifacts/w10_ablation_series_eq_pristine_pinned_log_s42.npz $REF "pristine 5424aceb vs axisB R0_pinned_log_s42" > logs/check_equiv.log 2>&1
/workspace/venv/bin/python check_equiv.py dev/probe_artifacts/w10_ablation_series_eq_patched_pinned_log_s42.npz $REF "w10_health.py default path vs axisB R0_pinned_log_s42" >> logs/check_equiv.log 2>&1
wait $P3
echo "CHAIN_EQ_DONE $(date -u +%FT%TZ)" >> logs/check_equiv.log
