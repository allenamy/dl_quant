#!/bin/bash
# PREREG_king_convexity §2: 五臂(实盘形态, 动态席位) + 判官; 全部后台一次跑完
cd /mnt/storage/private/work_hsy
PY=/root/miniconda3/envs/hsy_v5push/bin/python
run(){ tag=$1; shift; env "$@" MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=$tag $PY w10_universe.py > probe_artifacts/$tag.log 2>&1; echo "done $tag $(date -u +%H:%MZ)"; }
run w10_fu_kc_ksvol20_ms_s42 KSVOL=20 &
run w10_fu_kc_ksvol20_f10mod_ms_s42 KSVOL=20 KMOD_F10=0.5 &
run w10_fu_kc_ksvol20_f10mod_ms_s2027 KSVOL=20 KMOD_F10=0.5 FSEED=2027 &
wait
run w10_fu_kc_ksinv_ms_s42 KSVOL_INV=1 &
run w10_fu_kc_ksvol30_ms_s42 KSVOL=30 &
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
