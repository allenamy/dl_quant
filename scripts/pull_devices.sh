#!/usr/bin/env bash
# 把服务器上当日的判官脚本+结果收回仓库(规则: 判决装置与结论同寿命, 判官脚本当日入库)。
# 用法: bash scripts/pull_devices.sh 2026-08-21
set -euo pipefail
DAY="${1:?用法: pull_devices.sh YYYY-MM-DD}"
D="multi_asset/exports/eda/kcurve_2026-08-15/devices_${DAY}"
mkdir -p "$D/results"
for src in /mnt/storage/private/work_hsy/w3lane/s30 /mnt/storage/private/work_hsy/w3lane/kcurve /mnt/storage/private/work_hsy/probe_artifacts; do
  ssh jpline "find $src -maxdepth 1 -name '*.py' -newermt '$DAY' ! -newermt '$DAY +1 day' 2>/dev/null" | while read -r f; do
    [ -n "$f" ] && scp -q "jpline:$f" "$D/" || true
  done
  ssh jpline "find $src -maxdepth 1 -name '*.json' -newermt '$DAY' ! -newermt '$DAY +1 day' 2>/dev/null" | while read -r f; do
    [ -n "$f" ] && scp -q "jpline:$f" "$D/results/" || true
  done
done
( cd "$D" && shasum -a 256 *.py results/*.json 2>/dev/null > SHA256SUMS )
echo "收回 $(ls "$D"/*.py 2>/dev/null | wc -l) 脚本 / $(ls "$D"/results/*.json 2>/dev/null | wc -l) 结果 → $D"
echo "★ 别忘了 git add + commit"
