#!/bin/bash
# chain_trainfrac.sh — PREREG_dl_full_gradient_window_2026-09-07 (d5f078a0910e826e) 训练后链:
#   守卫 -> 符号链接 -> merge x2 -> 训练器 sha 真话核对(E-0907-G 自省) -> 回放 x2(仅 spl42, 第二种子按 §4.5 挂条件) -> 判官
set -e
B=/workspace/review_scratch/allweather_trackB; T=/workspace/review_scratch/trainfrac; PY=/workspace/venv/bin/python
MYSHA=20b531ba0e65a899
cd $T
# ── 守卫: 8 分片必须全 rc=0 ──
for A in X7FULL X6FULL; do for K in 0 1 2 3; do
  grep -a -q "^END\[$A shard$K\].*rc=0" logs/commands.txt || { echo "GUARD FAIL: $A shard$K 未 rc=0"; exit 3; }
done; done
echo "CHAIN_TRAINFRAC start $(date -u +%FT%TZ)" >> logs/commands.txt
# ── 符号链接: 不 fork 已验证的 merge/replay 装置 ──
mkdir -p $B/earlystop
for A in X7FULL X6FULL; do [ -e $B/earlystop/$A ] || ln -s $T/$A $B/earlystop/$A; done
[ -e $T/replay ] || ln -s $B/replay $T/replay
# ── merge ──
cd $B
$PY merge_mwf3.py X7FULL mE1x7full fix7 > $T/logs/merge_X7FULL.log 2>&1; echo "END[merge X7FULL] rc=$? $(date -u +%FT%TZ)" >> $T/logs/commands.txt
$PY merge_mwf3.py X6FULL mE1x6full fix6 > $T/logs/merge_X6FULL.log 2>&1; echo "END[merge X6FULL] rc=$? $(date -u +%FT%TZ)" >> $T/logs/commands.txt
tail -2 $T/logs/merge_X7FULL.log | cut -c1-200; tail -2 $T/logs/merge_X6FULL.log | cut -c1-200
# ── E-0907-G 自省: merge 的顶层 trainer_sha256 指向基底训练器, 对本臂是错的; 逐折 self_sha256 才是真话 ──
$PY - <<PYEOF
import json,glob,os
MY="$MYSHA"; out={}
for A,TAG in (("X7FULL","mE1x7full"),("X6FULL","mE1x6full")):
    p=f"$B/earlystop/{A}/results/f10_V2MAIN_{TAG}_s42_merged.json"
    J=json.load(open(p)); top=J.get("trainer_sha256","")[:16]; tp=J.get("trainer","")
    folds=J["folds"]; shas={f["self_sha256"][:16] for f in folds.values()}
    ok = shas=={MY}
    out[A]={"merged_json":p,"top_level_trainer":tp,"top_level_trainer_sha16":top,
            "top_level_is_MISLEADING_for_this_arm": top!=MY,
            "per_fold_self_sha256_set":sorted(shas),"all_folds_match_patched_trainer":ok,"n_folds":len(folds)}
    print(f"{A}: 顶层 trainer_sha16={top} ({'误导 — 是基底' if top!=MY else 'ok'}) | 逐折 self_sha={sorted(shas)} | 全折匹配补丁训练器={ok} ({len(folds)} 折)")
    assert ok, f"{A}: 有折不是本补丁训练器产出"
json.dump({"note":"merge_mwf3.py hardcodes the BASE trainer path in its top-level trainer_sha256 field; for the TRAIN_FRAC arms that field is MISLEADING. The truth is per-fold self_sha256. Same defect class as E-0907-G — recorded rather than silently inherited.","patched_trainer_sha16":MY,"arms":out}, open("$T/TRAINER_SHA_NOTE.json","w"), indent=1)
print("TRAINER_SHA_NOTE.json written")
PYEOF
echo "END[trainer_sha_check] rc=$? $(date -u +%FT%TZ)" >> $T/logs/commands.txt
# ── 回放(仅 spl42; 第二种子按 PREREG §4.5 需干净 CONST2027, 本轮不跑) ──
cd $B/replay; H=/workspace/review_scratch/health_check; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
for t in mE1x7full mE1x6full; do
  bash run_arm.sh G_${t}_R0_spl42 prod w10_health.py $COMMON FSEED=42 FPRED=f10_gate_${t}_R0_spl42.npy > $T/logs/replay_${t}.out 2>&1 &
done; wait
grep -a -E "^END\[G_mE1x[67]full" logs/commands.txt | cut -c1-140
# ── 判官(sha 2191186853531b6d, 写于数字之前) ──
cd $T
$PY judge_trainfrac.py > logs/judge.log 2>&1; RC=$?; echo "END[judge] rc=$RC $(date -u +%FT%TZ)" >> logs/commands.txt
sed -n "/TF-3/,\$p" logs/judge.log | head -40
echo "CHAIN_TRAINFRAC done $(date -u +%FT%TZ)" >> logs/commands.txt
