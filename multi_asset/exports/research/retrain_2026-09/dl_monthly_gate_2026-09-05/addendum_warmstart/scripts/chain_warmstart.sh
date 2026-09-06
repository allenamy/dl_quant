#!/bin/bash
# chain_warmstart.sh — PREREG_incremental_retrain §1 post-training chain (CPU): merge W1/W2 (+W1F5 if finished) → splice → replay → judge4 → agreement3.
set -e; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B
ARMS="W1:mE1w1:3e-4 W2:mE1w2:1e-4"; grep -a -q "^END\[W1F5\].*rc=0" logs/commands.txt && ARMS="$ARMS W1F5:mE1w1F5:3e-4"
for spec in $ARMS; do a=${spec%%:*}; grep -a -q "^END\[$a\].*rc=0" logs/commands.txt || { echo "arm $a not finished rc=0"; exit 3; }; done
echo "CHAIN_WARMSTART start $(date -u +%FT%TZ) arms $ARMS du $(du -sm /workspace | cut -f1) MiB" >> logs/commands.txt
for spec in $ARMS; do a=${spec%%:*}; rest=${spec#*:}; t=${rest%%:*}; lr=${rest#*:}; $PY merge_mwf4.py $a $t $lr > logs/merge_$a.log 2>&1; echo "END[merge $a] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt; tail -3 logs/merge_$a.log | cut -c1-240; done
cd replay; H=/workspace/review_scratch/health_check; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
for spec in $ARMS; do rest=${spec#*:}; t=${rest%%:*}
  bash run_arm.sh G_${t}_R0_spl42 prod w10_health.py $COMMON FSEED=42 FPRED=f10_gate_${t}_R0_spl42.npy > logs/G_${t}_R0_spl42.out 2>&1 &
  bash run_arm.sh G_${t}_R0_spl27 prod w10_health.py $COMMON FSEED=2027 FPRED=f10_gate_${t}_R0_spl27.npy > logs/G_${t}_R0_spl27.out 2>&1 &
done; wait; grep -a -E "^END\[G_mE1w" logs/commands.txt | cut -c1-120; cd ..
$PY judge_gate_addendum4.py > logs/judge_gate_addendum4.log 2>&1; echo "END[judge addendum4] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt; grep -E "^=====|ADDENDUM4" logs/judge_gate_addendum4.log | cut -c1-420
$PY agreement3.py > logs/agreement3.log 2>&1; echo "END[agreement3] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt; tail -1 logs/agreement3.log
echo "CHAIN_WARMSTART done $(date -u +%FT%TZ)" >> logs/commands.txt
