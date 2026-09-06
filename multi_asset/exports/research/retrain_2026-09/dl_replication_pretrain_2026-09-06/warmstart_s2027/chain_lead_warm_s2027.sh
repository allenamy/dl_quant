#!/bin/bash
# chain_lead_warm_s2027.sh — 热启动种子 2027 复验后链, 由 LEAD 执行(track-b-dl 受额度阻塞)。
# PREREG_dl_warmstart_replication_2026-09-06: merge_chain.py -> replay(spl27 FSEED=2027 主 / spl42 FSEED=42 并列) -> judge_gate_addendum5.py
# 只调既有脚本; 每步 CMD/END 写入 logs/commands.txt; 日志名不含空格。
set -e; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B
LOG(){ echo "$1" >> logs/commands.txt; }
for a in W1_s2027 W2_s2027; do grep -a -q "^END\[$a\].*rc=0" logs/commands.txt || { echo "GUARD FAIL: END[$a]"; exit 3; }; done
LOG "LEAD_CHAIN_WARM_S2027(v2: merge 用 merge_chain_s2027.py, 前次因 merge_chain.py 硬编码 SEED=42 判 rc=1 无产物) start $(date -u +%FT%TZ) du $(du -sm /workspace | cut -f1) MiB (run by lead)"
run(){ n="$1"; f="$2"; shift 2; LOG "CMD[$n] $(date -u +%FT%TZ) : $*"; set +e; "$@" > "logs/lead_$f.log" 2>&1; rc=$?; set -e; LOG "END[$n] rc=$rc $(date -u +%FT%TZ)"; echo "== $n rc=$rc"; tail -n 3 "logs/lead_$f.log" | cut -c1-260; [ $rc -eq 0 ] || exit 4; }
run "merge W1_s2027" merge_w1s27 $PY merge_chain_s2027.py $B/warmstart/W1_s2027 mE1w1s27 3e-4 argmax
run "merge W2_s2027" merge_w2s27 $PY merge_chain_s2027.py $B/warmstart/W2_s2027 mE1w2s27 1e-4 argmax
cd replay; H=/workspace/review_scratch/health_check; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
for t in mE1w1s27 mE1w2s27; do
  bash run_arm.sh G_${t}_R0_spl27 prod w10_health.py $COMMON FSEED=2027 FPRED=f10_gate_${t}_R0_spl27.npy > logs/G_${t}_R0_spl27.out 2>&1 &
  bash run_arm.sh G_${t}_R0_spl42 prod w10_health.py $COMMON FSEED=42   FPRED=f10_gate_${t}_R0_spl42.npy > logs/G_${t}_R0_spl42.out 2>&1 &
done; wait; cd ..; grep -a -E "^END\[G_mE1w[12]s27" logs/commands.txt | tail -4 | cut -c1-130
LOG "LEAD_CHAIN_WARM_S2027 merged+replayed $(date -u +%FT%TZ)"
echo "CHAIN_WARM_S2027_REPLAY_DONE"
