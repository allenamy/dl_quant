"""门V3′ for the v4 chain = pod_f10_v3_leakcheck_v2.py verbatim clauses, paths parameterised:
① future side no peak: max|corr(k∈[+1,+3])| < |corr(k=0)|; ② spectrum shape vs the in-service generation: per-k |Δ| ≤ 0.03; ③ out-of-fold (<2023) leaked cells = 0.
usage: v4_leakcheck.py <T: RAW|CLIP>  (new = /workspace/f8_v4/mwf/<T>_s<S>/preds/f10_V2MAIN_<T>_mE1cX7_s<S>.npy on the v4 axis; old = in-service f8_ext yearly on dlw_ext)"""
import sys, time, json
import numpy as np
from scipy.stats import spearmanr
T = sys.argv[1]; DLW = {"RAW": "/workspace/dlw_v4raw", "CLIP": "/workspace/dlw_hf3"}[T]
def spectrum(pred_path, tg_path):
    TG = np.load(tg_path, allow_pickle=True); E_ts = TG["E_ts"].astype(np.int64); y4s = TG["y4s"]; members = TG["members"]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); P = np.load(pred_path)
    pre = np.where(yrs < 2023)[0]; leak = int(np.isfinite(P[pre]).sum())
    test_i = [i for i in np.where(yrs >= 2023)[0] if 3 <= i < nA - 3][:: max(1, nA // 800)]
    spec = {}
    for k in range(-3, 4):
        vals = []
        for i in test_i:
            m = members[i]; a = P[i, m]; b = y4s[i + k, m]; ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30: vals.append(spearmanr(a[ok], b[ok]).correlation)
        spec[k] = float(np.nanmean(vals))
    return spec, leak
bad = []; out = {}
for S in (42, 2027):
    new_spec, new_leak = spectrum(f"/workspace/f8_v4/mwf/{T}_s{S}/preds/f10_V2MAIN_{T}_mE1cX7_s{S}.npy", f"{DLW}/data/dlw_targets.npz")
    old_spec, _ = spectrum(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy", "/workspace/dlw_ext/data/dlw_targets.npz")
    fut = max(abs(new_spec[k]) for k in (1, 2, 3)); c1 = fut < abs(new_spec[0]); dmax = max(abs(new_spec[k] - old_spec[k]) for k in range(-3, 4)); c2 = dmax <= 0.03; c3 = new_leak == 0
    print(f"{T} s{S} 新谱 " + " ".join(f"k{k:+d}:{new_spec[k]:+.4f}" for k in range(-3, 4)) + " | 在役谱 " + " ".join(f"k{k:+d}:{old_spec[k]:+.4f}" for k in range(-3, 4)), flush=True)
    print(f"{T} s{S} ①未来侧无峰 max|k>0|={fut:.4f} < |k0|={abs(new_spec[0]):.4f} {'OK' if c1 else 'FAIL'} | ②谱形一致 max|Δ|={dmax:.4f} {'OK' if c2 else 'FAIL'} | ③泄出 {new_leak} {'OK' if c3 else 'FAIL'}", flush=True)
    out[str(S)] = {"new": new_spec, "old": old_spec, "c1": c1, "c2": c2, "c3": c3, "dmax": dmax, "leak": new_leak}
    if not (c1 and c2 and c3): bad.append(S)
json.dump(out, open(f"/workspace/review_scratch/v4_gates/V3P_{T}.json", "w"), indent=1)
print("V3P_GATE", T, "PASS" if not bad else f"FAIL {bad}", flush=True); sys.exit(0 if not bad else 3)
