#!/bin/bash
# 延长链 runner: stitch → cache → (等 funding) → panel → fea → slow → extweek. 每段 DONE 标记闸.
cd /workspace
L="/workspace/ext_chain_$(date -u +%s).log"
ln -sf "$L" /workspace/ext_chain.log
echo "=== chain start $(date -u +%FT%TZ)" >> "$L"

# 0. 等 Vision 下载完
for i in $(seq 1 120); do
  if grep -q EXTEND_DL_DONE extend_dl.log 2>/dev/null; then break; fi
  sleep 30
done
grep EXTEND_DL_DONE extend_dl.log >> "$L" || { echo ABORT_DL >> "$L"; exit 1; }

# 1. stitch: daily zips → 主树命名
python3 - >> "$L" 2>&1 <<'PYEOF'
import os, glob, shutil
n_new = 0
for sd in sorted(glob.glob("/workspace/wide_multisrc/klines5m_daily/*")):
    s = os.path.basename(sd)
    dst_dir = f"/workspace/klines5m/{s}"
    if not os.path.isdir(dst_dir): continue
    for zp in sorted(glob.glob(sd + "/*.zip")):
        d = os.path.basename(zp).replace(".zip", "")
        dst = f"{dst_dir}/{s}-5m-{d}.zip"
        if os.path.exists(dst): continue
        shutil.copy2(zp, dst); n_new += 1
print(f"STITCH_DONE new {n_new}", flush=True)
PYEOF
grep -q STITCH_DONE "$L" || { echo ABORT_STITCH >> "$L"; exit 1; }

# 2. ext 缓存重建
rm -f /workspace/wide_ext.lock
python3 pod_build_wide_ext.py >> "$L" 2>&1
grep -q EXT_CACHE_DONE "$L" || { echo ABORT_CACHE >> "$L"; exit 1; }

# 3. 等 jpline funding 尾巴(最多 30 分钟)
for i in $(seq 1 60); do
  if [ -s /workspace/fund_aug.json.gz ]; then break; fi
  sleep 30
done
[ -s /workspace/fund_aug.json.gz ] || { echo ABORT_FUND_AUG_MISSING >> "$L"; exit 1; }

# 4. 面板 v2ext(含平价守卫)
python3 pod_panel_ext.py >> "$L" 2>&1
grep -q PANEL_EXT_DONE "$L" || { echo ABORT_PANEL >> "$L"; exit 1; }

# 5. 特征
python3 pod_fea_ext.py >> "$L" 2>&1
grep -q FEA_EXT_DONE "$L" || { echo ABORT_FEA >> "$L"; exit 1; }

# 6. 慢引擎(含平价守卫)
python3 pod_slow_ext.py >> "$L" 2>&1
grep -q SLOW_EXT_DONE "$L" || { echo ABORT_SLOW >> "$L"; exit 1; }

# 7. 判官
python3 pod_extweek.py >> "$L" 2>&1
grep -q EXTWEEK_DONE "$L" || { echo ABORT_EXTWEEK >> "$L"; exit 1; }
echo "=== chain ALL_DONE $(date -u +%FT%TZ)" >> "$L"
