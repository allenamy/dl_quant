#!/bin/bash
# PREREG_king_convexity §1-§2: 等价校验(LEGS=101 逐字同正典 env) → 五臂(实盘形态 = T3c 臂自报 config: MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero LEGS=101, 动态席位) → 判官
# 教训(E-0826-D 型, 09-04 11:2xZ): 首次漏 LEGS=101(装置默认 111) ⇒ 三臂被 S0 复现断言拦下; 本版全部显式给 env。
cd /mnt/storage/private/work_hsy
PY=/root/miniconda3/envs/hsy_v5push/bin/python
run(){ tag=$1; shift; env "$@" LEGS=101 OUT_TAG=$tag $PY w10_universe.py > probe_artifacts/$tag.log 2>&1 && cp probe_artifacts/w10_ablation_series_$tag.npz probe_artifacts/$tag.npz; echo "done $tag rc=$? $(date -u +%H:%MZ)"; }
run w10_kc_eq_s42 FSEED=42
$PY jp_eq_compare.py > probe_artifacts/kc_eq_compare.out 2>&1
LF="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
run w10_fu_kc_ksvol20_ms_s42 $LF KSVOL=20 FSEED=42 &
run w10_fu_kc_ksvol20_f10mod_ms_s42 $LF KSVOL=20 KMOD_F10=0.5 FSEED=42 &
run w10_fu_kc_ksvol20_f10mod_ms_s2027 $LF KSVOL=20 KMOD_F10=0.5 FSEED=2027 &
wait
run w10_fu_kc_ksinv_ms_s42 $LF KSVOL_INV=1 FSEED=42 &
run w10_fu_kc_ksvol30_ms_s42 $LF KSVOL=30 FSEED=42 &
wait
echo KC_RUNS_DONE
{
echo "== KC1 vs 实盘形态基线(s42)"; BASE=w10_uni2_N829T400F_ms_s42 RUN_FILTER=fu_kc_ksvol20_ms_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo "== KC1xT3c vs T3c(s42)"; BASE=w10_fu_t3c_f10mod_ms_s42 RUN_FILTER=fu_kc_ksvol20_f10mod_ms_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo "== KC1xT3c vs T3c(s2027)"; BASE=w10_fu_t3c_f10mod_ms_s2027 SEEDTAG=s2027 RUN_FILTER=fu_kc_ksvol20_f10mod_ms_s2027 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo "== KC2 逆波动 vs 基线(s42)"; BASE=w10_uni2_N829T400F_ms_s42 RUN_FILTER=fu_kc_ksinv_ms_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo "== KC1-30 形状 vs 基线(s42)"; BASE=w10_uni2_N829T400F_ms_s42 RUN_FILTER=fu_kc_ksvol30_ms_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -v Warning
echo KC_JUDGE_DONE
} > probe_artifacts/kc_judge.out 2>&1
