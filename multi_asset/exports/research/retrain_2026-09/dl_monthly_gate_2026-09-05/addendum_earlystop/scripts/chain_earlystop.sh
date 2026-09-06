#!/bin/bash
# chain_earlystop.sh — PREREG_dl_monthly_earlystop post-training chain (CPU): merge both arms → splice → replay 4 arms → judge (A)/(B)/(C) → agreement2. Every command logged.
set -e; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B
for a in FLOOR5 FIX7; do grep -a -q "^END\[$a shard0\].*rc=0" logs/commands.txt && grep -a -q "^END\[$a shard1\].*rc=0" logs/commands.txt && grep -a -q "^END\[$a shard2\].*rc=0" logs/commands.txt && grep -a -q "^END\[$a shard3\].*rc=0" logs/commands.txt || { echo "arm $a not finished rc=0"; exit 3; }; done
echo "CHAIN_EARLYSTOP start $(date -u +%FT%TZ) du $(du -sm /workspace | cut -f1) MiB" >> logs/commands.txt
$PY merge_mwf3.py FLOOR5 mE1cF5 floor5 > logs/merge_FLOOR5.log 2>&1; echo "END[merge FLOOR5] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt
$PY merge_mwf3.py FIX7 mE1cX7 fix7 > logs/merge_FIX7.log 2>&1; echo "END[merge FIX7] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt
tail -3 logs/merge_FLOOR5.log | cut -c1-240; tail -3 logs/merge_FIX7.log | cut -c1-240
cd replay; H=/workspace/review_scratch/health_check; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
for t in mE1cF5 mE1cX7; do
  bash run_arm.sh G_${t}_R0_spl42 prod w10_health.py $COMMON FSEED=42 FPRED=f10_gate_${t}_R0_spl42.npy > logs/G_${t}_R0_spl42.out 2>&1 &
  bash run_arm.sh G_${t}_R0_spl27 prod w10_health.py $COMMON FSEED=2027 FPRED=f10_gate_${t}_R0_spl27.npy > logs/G_${t}_R0_spl27.out 2>&1 &
done; wait; grep -a -E "^END\[G_mE1c(F5|X7)" logs/commands.txt | cut -c1-120; cd ..
$PY judge_gate_addendum3.py > logs/judge_gate_addendum3.log 2>&1; echo "END[judge addendum3] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt; grep -E "^=====|ADDENDUM3" logs/judge_gate_addendum3.log | cut -c1-420
$PY agreement2.py > logs/agreement2.log 2>&1; echo "END[agreement2] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt; tail -1 logs/agreement2.log
$PY check_trajectory.py > logs/trajectory_check.log 2>&1; echo "END[trajectory] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt; tail -2 logs/trajectory_check.log
echo "CHAIN_EARLYSTOP done $(date -u +%FT%TZ)" >> logs/commands.txt
