#!/bin/bash
# 精确清理双开: 列出 → 按 PID 杀(不用模式杀, pkill 教训) → 放行 relay3
echo "── 现役清单 ──"
pgrep -af "rp_queue2.sh|train_wide_harness" | grep -v "cleanup_dup"
Q=$(pgrep -f "bash rp_queue2.sh" | head -20)
T=$(pgrep -f "train_wide_harness" | head -20)
for p in $Q $T; do
  # 不杀 relay3 和自己
  cmd=$(ps -o args= -p "$p" 2>/dev/null)
  case "$cmd" in *relay3*|*cleanup*) continue;; esac
  kill "$p" 2>/dev/null && echo "  killed $p: ${cmd:0:70}"
done
sleep 3
echo "── 残留 ──"; pgrep -af "rp_queue2|train_wide" | grep -v cleanup || echo "  无"
echo "── relay3 应即刻放行 ──"; sleep 25; tail -4 /workspace/relay3.log
python3 /workspace/readab.py 2>/dev/null | tail -2
python3 - <<'PY'
import json
B="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/"
d=json.load(open(B+"wide_harness_ch53_yr24_s2027.json"))
print("ch53_s2027:",d["mean_resid_rank_ic"],d["per_fold_resid_ic"])
PY
