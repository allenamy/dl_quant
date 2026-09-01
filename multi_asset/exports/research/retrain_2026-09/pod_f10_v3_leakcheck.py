"""门V3 泄漏仪器 @pod(PREREG addendum §A): 对新 walk-forward preds(双种子)——
① 偏移谱: mean_i spearman(pred[i], y4s[i+k]) k∈[−3..+3], 峰必须在 k=0;
② 折外泄出: 2023 前锚(无测试折)finite pred 格点数必须 = 0。
用法: python3 pod_f10_v3_leakcheck.py
"""
import sys, time
import numpy as np
from scipy.stats import spearmanr

TG = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); y4s = TG["y4s"]; members = TG["members"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
bad = []
for S in (42, 2027):
    P = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy")
    pre = np.where(yrs < 2023)[0]
    leak = int(np.isfinite(P[pre]).sum())
    spec = {}
    test_i = [i for i in np.where(yrs >= 2023)[0] if 3 <= i < nA - 3][:: max(1, nA // 800)]
    for k in range(-3, 4):
        vals = []
        for i in test_i:
            m = members[i]
            a = P[i, m]; b = y4s[i + k, m]
            ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30:
                vals.append(spearmanr(a[ok], b[ok]).correlation)
        spec[k] = float(np.nanmean(vals))
    peak = max(spec, key=lambda k: abs(spec[k]))
    print(f"s{S} 谱 " + " ".join(f"k{k:+d}:{spec[k]:+.4f}" for k in range(-3, 4)) +
          f" | 峰@{peak} | 折外泄出格点 {leak}", flush=True)
    if peak != 0: bad.append((S, "peak", peak))
    if leak != 0: bad.append((S, "leak", leak))
print("V3_GATE", "PASS" if not bad else f"FAIL {bad}", flush=True)
sys.exit(0 if not bad else 3)
