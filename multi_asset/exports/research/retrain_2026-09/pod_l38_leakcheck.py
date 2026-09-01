"""V2L38 泄漏门 @pod(PREREG_v2l38 AMENDMENT L1): 老网格; 三条款 = 未来侧无峰 / 谱形vs同种子V2MAIN |Δ|≤0.03 / 折外泄出=0。"""
import sys, time
import numpy as np
from scipy.stats import spearmanr
TG = np.load("/workspace/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); y4s = TG["y4s"]; members = TG["members"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts)
def spectrum(p):
    P = np.load(p)
    pre = np.where(yrs < 2023)[0]
    leak = int(np.isfinite(P[pre]).sum())
    ti = [i for i in np.where(yrs >= 2023)[0] if 3 <= i < nA - 3][:: max(1, nA // 800)]
    spec = {}
    for k in range(-3, 4):
        vals = []
        for i in ti:
            m = members[i]; a = P[i, m]; b = y4s[i + k, m]
            ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30: vals.append(spearmanr(a[ok], b[ok]).correlation)
        spec[k] = float(np.nanmean(vals))
    return spec, leak
bad = []
for S in (42, 2027):
    ns, nl = spectrum(f"/workspace/f8_2026-08-22/preds/f10_V2L38_s{S}.npy")
    bs, _ = spectrum(f"/workspace/f8_2026-08-22/preds/f10_V2MAIN_s{S}.npy")
    fut = max(abs(ns[k]) for k in (1, 2, 3)); c1 = fut < abs(ns[0])
    dmax = max(abs(ns[k] - bs[k]) for k in range(-3, 4)); c2 = dmax <= 0.03
    c3 = nl == 0
    print(f"s{S} 谱 " + " ".join(f"k{k:+d}:{ns[k]:+.4f}" for k in range(-3, 4)), flush=True)
    print(f"s{S} ①未来侧 {fut:.4f}<{abs(ns[0]):.4f} {'OK' if c1 else 'FAIL'} ②vs基线Δ {dmax:.4f} {'OK' if c2 else 'FAIL'} ③泄出 {nl} {'OK' if c3 else 'FAIL'}", flush=True)
    if not (c1 and c2 and c3): bad.append(S)
print("L38_LEAK", "PASS" if not bad else f"FAIL {bad}", flush=True)
sys.exit(0 if not bad else 3)
