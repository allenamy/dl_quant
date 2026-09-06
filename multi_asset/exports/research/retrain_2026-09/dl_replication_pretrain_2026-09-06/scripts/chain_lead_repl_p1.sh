#!/bin/bash
# chain_lead_repl_p1.sh — post-training chain run by the LEAD session while track-b-dl is limit-blocked (2026-09-06 07:5xZ).
# (a) PREREG_dl_monthly_earlystop §5 seed-2027 replication: merge 2 arms -> replay 2 (spl27, FSEED=2027) -> judge_replication.py
# (b) PREREG_incremental_retrain §3.1 P1: merge chain -> replay 2 (spl42/spl27) -> judge_gate_addendum5.py
# Only existing scripts are invoked; none is modified. Every step appended to logs/commands.txt with CMD/END lines.
set -e; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B
LOG(){ echo "$1" >> logs/commands.txt; }
for a in FLOOR5_s2027 FIX7_s2027; do for s in 0 1 2 3; do grep -a -q "^END\[$a shard$s\].*rc=0" logs/commands.txt || { echo "GUARD FAIL: END[$a shard$s]"; exit 3; }; done; done
grep -a -q "^END\[P1\].*rc=0" logs/commands.txt || { echo "GUARD FAIL: END[P1]"; exit 3; }
LOG "LEAD_CHAIN(v2, 前次因日志名含空格 rc=1 中止, 无产物写出) start $(date -u +%FT%TZ) du $(du -sm /workspace | cut -f1) MiB (replication §5 + P1 §3.1; run by lead, track-b-dl limit-blocked)"
run(){ n="$1"; f="$2"; shift 2; LOG "CMD[$n] $(date -u +%FT%TZ) : $*"; set +e; "$@" > "logs/lead_$f.log" 2>&1; rc=$?; set -e; LOG "END[$n] rc=$rc $(date -u +%FT%TZ)"; echo "== $n rc=$rc"; tail -n 3 "logs/lead_$f.log" | cut -c1-260; [ $rc -eq 0 ] || exit 4; }
run "merge FLOOR5_s2027" merge_f5s27 $PY merge_mwf3s.py FLOOR5_s2027 mE1cF5s27 floor5
run "merge FIX7_s2027" merge_x7s27 $PY merge_mwf3s.py FIX7_s2027  mE1cX7s27 fix7
run "merge P1" merge_p1 $PY merge_chain.py $B/pretrain/P1 mE1p1 1e-4 argmax
cd replay; H=/workspace/review_scratch/health_check; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
bash run_arm.sh G_mE1cF5s27_R0_spl27 prod w10_health.py $COMMON FSEED=2027 FPRED=f10_gate_mE1cF5s27_R0_spl27.npy > logs/G_mE1cF5s27_R0_spl27.out 2>&1 &
bash run_arm.sh G_mE1cX7s27_R0_spl27 prod w10_health.py $COMMON FSEED=2027 FPRED=f10_gate_mE1cX7s27_R0_spl27.npy > logs/G_mE1cX7s27_R0_spl27.out 2>&1 &
bash run_arm.sh G_mE1p1_R0_spl42     prod w10_health.py $COMMON FSEED=42   FPRED=f10_gate_mE1p1_R0_spl42.npy     > logs/G_mE1p1_R0_spl42.out 2>&1 &
bash run_arm.sh G_mE1p1_R0_spl27     prod w10_health.py $COMMON FSEED=2027 FPRED=f10_gate_mE1p1_R0_spl27.npy     > logs/G_mE1p1_R0_spl27.out 2>&1 &
wait; cd ..; grep -a -E "^END\[G_(mE1cF5s27|mE1cX7s27|mE1p1)" logs/commands.txt | tail -4 | cut -c1-130
run "judge replication" judge_repl $PY judge_replication.py
run "judge addendum5 (P1)" judge_add5 $PY judge_gate_addendum5.py
LOG "LEAD_CHAIN done $(date -u +%FT%TZ)"
echo "LEAD_CHAIN_DONE"
