#!/bin/bash
# 容器重启后一键复原(卷上持久; 用法: bash /workspace/BOOTSTRAP.sh)
# 1) SSH 直连钥匙(容器每次重启重置)
mkdir -p ~/.ssh
grep -q "haosiyu@haosiyudeMacBook-Pro" ~/.ssh/authorized_keys 2>/dev/null || \
  echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGNMzv6D4thHu3sgWYEg7/0IMnu/9OTIK38mOB4U+dIO haosiyu@haosiyudeMacBook-Pro.local" >> ~/.ssh/authorized_keys
# 2) 科学栈(容器镜像不带)
python3 -c "import numpy, scipy, pandas, lightgbm" 2>/dev/null || \
  pip install --break-system-packages -q numpy scipy pandas lightgbm
# 3) 关键产物体检(缺失即红字, 不静默)
for f in data/dlnative_5m_wide829_f16_ext.npz data/wide_panel_4h_v2ext.npz data/wide_fea_v2ext_meta.npz shadow_bundle/slow_pred_pinned.npy shadow_bundle/MANIFEST.json; do
  [ -e "/workspace/$f" ] && echo "OK  $f" || echo "MISSING  $f  <-- 需从本机/正典重灌"
done
python3 -c "import numpy, scipy, pandas, lightgbm; print(\"env OK lgbm\", lightgbm.__version__)"
echo BOOTSTRAP_DONE
