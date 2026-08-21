#!/bin/bash
# bookDepth 无损压缩 —— 拉取器存的是解压后 CSV, 占了 242 GB。gzip 可逆, 零数据损失。
# 32 路并行(留核给正在跑的 metrics 补齐)。gzip 是【原地替换】: 成功才删原文件, 失败保留。
cd /workspace/data/raw/bookDepth
find . -maxdepth 1 -name '*.csv' -print0 | xargs -0 -P 32 -n 40 gzip -6
echo "=== gzip 完成 $(date -u) ==="
du -sh /workspace/data/raw/bookDepth
df -h /workspace | tail -1
