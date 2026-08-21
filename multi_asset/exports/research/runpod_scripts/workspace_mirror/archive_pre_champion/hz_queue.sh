#!/bin/bash
# T0 四视界基线: 4h/8h/12h/24h 在同一干净装置上, 建立目标对标的完整表
cd /workspace && export PYTHONPATH=/workspace/code
python3 - <<'PY' || exit 1
import numpy as np
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
S = np.load("/workspace/data/y8y12_sidecar.npz", allow_pickle=True)
d = {k: R[k] for k in R.files}
for H in (8, 12):
    for p in ("Y", "YR", "CL"):
        d["%s%d" % (p, H)] = S["%s%d" % (p, H)]
np.savez("/workspace/data/wide_dl_pm32_hz.npz", **d)
print("四视界面板: keys=%d" % len(d))
for H in (4, 8, 12, 24):
    print("  YR%-3d finite %.4f  CL%-3d rows %d" % (
        H, float(np.isfinite(d["YR%d" % H]).mean()), H, int(d["CL%d" % H].any(1).sum())))
PY
cd /workspace/code
for H in 4 8 12 24; do
  echo "=== [$(date -u +%H:%M:%SZ)] hz${H} (年折2022, xattn, s42) ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon "$H" \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 \
    --year_folds --year_folds_from 2022 --embargo_days 10 --seed 42 \
    --save_tag "hz${H}_s42" --tag "hz${H}_s42" 2>&1 | tail -5
done
echo "=== 四视界完成 $(date -u) ==="
