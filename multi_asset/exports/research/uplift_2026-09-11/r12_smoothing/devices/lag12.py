"""r12 §6.1: impulse response / effective lag of the DEPLOYED shaping, measured on the replay book.
Estimand: the held book sm_t as a linear filter of the unshaped target book tgt_t.
  joint LS   : min_c || sm_t - sum_k c_k tgt_{t-k} ||^2   over k=0..K, pooled over anchors AND names
  effective lag = sum_k k*c_k / sum_k c_k   (anchors; x4h for hours)
Theory check with band off: c_k = alpha*(1-alpha)^k, lag = (1-alpha)/alpha exactly."""
import numpy as np, json, os, sys, glob
R = "/workspace/uplift_2026-09-11/r12_smoothing"
K = 24
WARM = 900          # lag measured on post-warm anchors (EMA state warm-up is not the object)
out = {}
for f in sorted(glob.glob(R + "/arms/S_*.npz")):
    tag = os.path.basename(f)[:-4]
    Z = np.load(f, allow_pickle=True)
    if "R12T" not in Z.files: continue
    W = Z["W"].astype(np.float64); T = Z["R12T"].astype(np.float64)
    cfg = json.loads(str(Z["config_json"])); sma = cfg["SMA"]; sband = cfg["SBAND"]
    nA = W.shape[0]; lo = max(WARM, K)
    G = np.zeros((K + 1, K + 1)); b = np.zeros(K + 1)
    for k in range(K + 1):
        b[k] = float((W[lo:nA] * T[lo - k:nA - k]).sum())
        for l in range(k, K + 1):
            v = float((T[lo - k:nA - k] * T[lo - l:nA - l]).sum()); G[k, l] = v; G[l, k] = v
    c = np.linalg.solve(G + 1e-12 * np.eye(K + 1) * np.trace(G) / (K + 1), b)
    uni = np.array([b[k] / G[k, k] for k in range(K + 1)])
    ssum = float(c.sum())
    lag_js = float((np.arange(K + 1) * c).sum() / ssum) if abs(ssum) > 1e-12 else float("nan")
    lag_uni = float((np.arange(K + 1) * uni).sum() / uni.sum())
    # R^2 of the fit
    pred = np.zeros_like(W[lo:nA])
    for k in range(K + 1): pred += c[k] * T[lo - k:nA - k]
    ss_res = float(((W[lo:nA] - pred) ** 2).sum()); ss_tot = float((W[lo:nA] ** 2).sum())
    # half-life of the fitted kernel (cumulative)
    cum = np.cumsum(c) / ssum
    hl = int(np.argmax(cum >= 0.5)) if (cum >= 0.5).any() else -1
    p90 = int(np.argmax(cum >= 0.9)) if (cum >= 0.9).any() else -1
    th_lag = (1 - sma) / sma
    out[tag] = {"SMA": sma, "SBAND": sband, "c": [float(x) for x in c], "uni": [float(x) for x in uni],
                "sum_c": ssum, "eff_lag_anchors_jointLS": lag_js, "eff_lag_anchors_univar": lag_uni,
                "eff_lag_hours": lag_js * 4.0, "half_life_anchors": hl, "p90_anchors": p90,
                "R2": 1.0 - ss_res / ss_tot, "theory_lag_noband": th_lag,
                "lag_inflation_vs_theory": lag_js / th_lag if th_lag > 0 else float("inf")}
    print(tag, "lag=%.2f anchors (%.1fh) theory=%.2f R2=%.4f" % (lag_js, lag_js * 4, th_lag, out[tag]["R2"]), flush=True)
json.dump(out, open(R + "/LAG12.json", "w"), indent=1)
print("LAG_DONE")
