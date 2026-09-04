#!/bin/bash
# 口径复验(2026-09-04 11:5xZ): 面板 y4 = Σ 5m 简单收益(实证逐位), 装置 CAL=simple 的 expm1 是伪凸性; CAL=log 分支 = 原始 y4 = 无偏简单口径。
# 用 CAL=log 复跑: 正典基线 / 实盘形态(M1+FTRIM) 两种子 / T3c 两种子 → 判官(BASE 同口径)。
cd /mnt/storage/private/work_hsy
PY=/root/miniconda3/envs/hsy_v5push/bin/python
run(){ tag=$1; shift; env "$@" LEGS=101 CAL=log OUT_TAG=$tag $PY w10_universe.py > probe_artifacts/$tag.log 2>&1 && cp probe_artifacts/w10_ablation_series_$tag.npz probe_artifacts/$tag.npz; echo "done $tag rc=$? $(date -u +%H:%MZ)"; }
LF="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
run w10_uni2_canon_callog_s42 FSEED=42 &
run w10_uni2_N829T400F_callog_s42 $LF FSEED=42 &
run w10_uni2_N829T400F_callog_s2027 $LF FSEED=2027 &
run w10_fu_t3c_f10mod_callog_s42 $LF KMOD_F10=0.5 FSEED=42 &
run w10_fu_t3c_f10mod_callog_s2027 $LF KMOD_F10=0.5 FSEED=2027 &
wait
echo CALLOG_RUNS_DONE
{
echo "== 实盘形态(M1+FTRIM) vs 正典, 无偏口径(CAL=log), s42"; BASE=w10_uni2_canon_callog_s42 RUN_FILTER=uni2_N829T400F_callog_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo "== T3c vs 实盘形态, 无偏口径, s42"; BASE=w10_uni2_N829T400F_callog_s42 RUN_FILTER=fu_t3c_f10mod_callog_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo "== T3c vs 实盘形态, 无偏口径, s2027"; BASE=w10_uni2_N829T400F_callog_s2027 SEEDTAG=s2027 RUN_FILTER=fu_t3c_f10mod_callog_s2027 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo CALLOG_JUDGE_DONE
} > probe_artifacts/callog_judge.out 2>&1
