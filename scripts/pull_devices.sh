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
# RunPod: 同步当日新脚本/结果(直连 TCP 端口见 ~/.ssh/config Host runpod; 重启后端口会变)
if ssh -o ConnectTimeout=10 -o BatchMode=yes runpod true 2>/dev/null; then
  ssh runpod "find /workspace -maxdepth 1 \( -name '*.py' -o -name '*.sh' -o -name '*.json' \) -newermt '$DAY' ! -newermt '$DAY +1 day' 2>/dev/null" | while read -r f; do
    case "$f" in *.json) scp -q "runpod:$f" "$D/results/" || true;; *) scp -q "runpod:$f" "$D/" || true;; esac
  done
  echo "pod 同步完成"
else
  echo "★ pod 不可达 — 若 pod 上今日有新装置, 下次连通后补拉(或先写入仓库再 scp 上去)"
fi
( cd "$D" && shasum -a 256 *.py results/*.json 2>/dev/null > SHA256SUMS )
echo "收回 $(ls "$D"/*.py 2>/dev/null | wc -l) 脚本 / $(ls "$D"/results/*.json 2>/dev/null | wc -l) 结果 → $D"
echo "★ 别忘了 git add + commit"
