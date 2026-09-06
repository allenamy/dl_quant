#!/bin/bash
# chain_lead_w1f5.sh — W1F5 组合臂后链, 由 LEAD 会话执行(track-b-dl 受额度阻塞)。
# PREREG_incremental_retrain §1.1(c63a216): merge_chain.py -> replay(spl42 FSEED=42 / spl27 FSEED=2027) -> judge_gate_addendum5.py
# 只调既有脚本, 不修改任何脚本; 每步 CMD/END 写入 logs/commands.txt; 日志名不含空格。
set -e; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B
LOG(){ echo "$1" >> logs/commands.txt; }
grep -a -q "^END\[W1F5\].*rc=0" logs/commands.txt || { echo "GUARD FAIL: END[W1F5]"; exit 3; }
LOG "LEAD_CHAIN_W1F5 start $(date -u +%FT%TZ) du $(du -sm /workspace | cut -f1) MiB (run by lead)"
run(){ n="$1"; f="$2"; shift 2; LOG "CMD[$n] $(date -u +%FT%TZ) : $*"; set +e; "$@" > "logs/lead_$f.log" 2>&1; rc=$?; set -e; LOG "END[$n] rc=$rc $(date -u +%FT%TZ)"; echo "== $n rc=$rc"; tail -n 3 "logs/lead_$f.log" | cut -c1-260; [ $rc -eq 0 ] || exit 4; }
run "merge W1F5" merge_w1f5 $PY merge_chain.py $B/warmstart/W1F5 mE1w1F5 3e-4 floor5
cd replay; H=/workspace/review_scratch/health_check; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
bash run_arm.sh G_mE1w1F5_R0_spl42 prod w10_health.py $COMMON FSEED=42   FPRED=f10_gate_mE1w1F5_R0_spl42.npy > logs/G_mE1w1F5_R0_spl42.out 2>&1 &
bash run_arm.sh G_mE1w1F5_R0_spl27 prod w10_health.py $COMMON FSEED=2027 FPRED=f10_gate_mE1w1F5_R0_spl27.npy > logs/G_mE1w1F5_R0_spl27.out 2>&1 &
wait; cd ..; grep -a -E "^END\[G_mE1w1F5" logs/commands.txt | tail -2 | cut -c1-130
run "judge addendum5 (W1F5)" judge_add5_w1f5 $PY judge_gate_addendum5.py
LOG "LEAD_CHAIN_W1F5 done $(date -u +%FT%TZ)"
echo "LEAD_CHAIN_W1F5_DONE"
