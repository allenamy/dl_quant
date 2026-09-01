"""门V3′ @pod(PREREG addendum AMENDMENT A1, 2026-09-01): 三条款 —
① 未来侧无峰: max|corr(k∈[+1,+3])| < |corr(k=0)|;
② 谱形与在役代一致: 新旧代逐 k |Δ| ≤ 0.03(旧代=同装置测 f8_2026-08-22/preds);
③ 折外(2023 前)泄出格点 = 0。
用法: python3 pod_f10_v3_leakcheck_v2.py
"""
import sys, time
import numpy as np
from scipy.stats import spearmanr

def spectrum(pred_path, tg_path):
    TG = np.load(tg_path, allow_pickle=True)
    E_ts = TG["E_ts"].astype(np.int64); y4s = TG["y4s"]; members = TG["members"]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts)
    P = np.load(pred_path)
    pre = np.where(yrs < 2023)[0]
    leak = int(np.isfinite(P[pre]).sum())
    test_i = [i for i in np.where(yrs >= 2023)[0] if 3 <= i < nA - 3][:: max(1, nA // 800)]
    spec = {}
    for k in range(-3, 4):
        vals = []
        for i in test_i:
            m = members[i]
            a = P[i, m]; b = y4s[i + k, m]
            ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30: vals.append(spearmanr(a[ok], b[ok]).correlation)
        spec[k] = float(np.nanmean(vals))
    return spec, leak

bad = []
for S in (42, 2027):
    new_spec, new_leak = spectrum(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy", "/workspace/dlw_ext/data/dlw_targets.npz")
    old_spec, _ = spectrum(f"/workspace/f8_2026-08-22/preds/f10_V2MAIN_s{S}.npy", "/workspace/dlw_2026-08-22/data/dlw_targets.npz")
    fut = max(abs(new_spec[k]) for k in (1, 2, 3))
    c1 = fut < abs(new_spec[0])
    dmax = max(abs(new_spec[k] - old_spec[k]) for k in range(-3, 4))
    c2 = dmax <= 0.03
    c3 = new_leak == 0
    print(f"s{S} 新谱 " + " ".join(f"k{k:+d}:{new_spec[k]:+.4f}" for k in range(-3, 4)), flush=True)
    print(f"s{S} ①未来侧无峰 max|k>0|={fut:.4f} < |k0|={abs(new_spec[0]):.4f} {'OK' if c1 else 'FAIL'}"
          f" | ②谱形一致 max|Δ|={dmax:.4f} {'OK' if c2 else 'FAIL'} | ③泄出 {new_leak} {'OK' if c3 else 'FAIL'}", flush=True)
    if not (c1 and c2 and c3): bad.append(S)
print("V3P_GATE", "PASS" if not bad else f"FAIL {bad}", flush=True)
sys.exit(0 if not bad else 3)
