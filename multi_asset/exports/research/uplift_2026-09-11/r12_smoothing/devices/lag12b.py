"""r12 §6.1 v2: responsiveness of the DEPLOYED shaping, two estimators.

(1) GAP-CLOSURE PROFILE (headline, truncation-free, band included):
      phi_h = sum_t <sm_{t+h} - sm_{t-1},  tgt_t - sm_{t-1}> / sum_t ||tgt_t - sm_{t-1}||^2
    = the fraction of the gap that existed at anchor t which the held book has closed h anchors later.
    lag50/lag90 = first h with phi_h >= .5 / .9.  Pure mechanics; no return data touched.
(2) DECONVOLUTION KERNEL: sm_t ~ sum_{k<=K} c_k tgt_{t-k}, joint LS, K=60.
    Reported WITH its own truncated-geometric theory value so the truncation is not read as a finding."""
import numpy as np, json, os, glob
R = "/workspace/uplift_2026-09-11/r12_smoothing"
K = 60; H = 30; WARM = 900
out = {}
for f in sorted(glob.glob(R + "/arms/S_*_s42.npz")):
    tag = os.path.basename(f)[:-4]; Z = np.load(f, allow_pickle=True)
    if "R12T" not in Z.files: continue
    W = Z["W"].astype(np.float64); T = Z["R12T"].astype(np.float64)
    cfg = json.loads(str(Z["config_json"])); a = cfg["SMA"]; b = cfg["SBAND"]
    nA = W.shape[0]; lo = max(WARM, K)
    # (1) gap closure
    t0, t1 = lo, nA - H                      # anchors with a full forward horizon
    GAP = T[t0:t1] - W[t0 - 1:t1 - 1]        # gap at t (target minus book carried in from t-1)
    den = float((GAP * GAP).sum())
    phi = [float(((W[t0 + h:t1 + h] - W[t0 - 1:t1 - 1]) * GAP).sum() / den) for h in range(H + 1)]
    def first(th):
        for h, v in enumerate(phi):
            if v >= th: return h
        return -1
    # (2) deconvolution
    pd_ = [(T[K:nA] * T[K - d:nA - d]).sum(1) for d in range(K + 1)]      # p_d[u] for u index offset K..nA-1
    qk = [(W[lo:nA] * T[lo - k:nA - k]).sum(1) for k in range(K + 1)]
    G = np.zeros((K + 1, K + 1)); bb = np.array([q.sum() for q in qk])
    for k in range(K + 1):
        for l in range(k, K + 1):
            d = l - k
            s = float(pd_[d][lo - k - K: nA - k - K].sum())
            G[k, l] = s; G[l, k] = s
    c = np.linalg.solve(G + 1e-10 * np.eye(K + 1) * np.trace(G) / (K + 1), bb)
    sc = float(c.sum()); ks = np.arange(K + 1)
    lag_c = float((ks * c).sum() / sc)
    p = 1.0 - a
    th_trunc = float((ks * p ** ks).sum() / (p ** ks).sum())
    pred = np.zeros_like(W[lo:nA])
    for k in range(K + 1): pred += c[k] * T[lo - k:nA - k]
    R2 = 1.0 - float(((W[lo:nA] - pred) ** 2).sum()) / float((W[lo:nA] ** 2).sum())
    out[tag] = {"SMA": a, "SBAND": b, "phi_h": phi, "lag50_anchors": first(0.5), "lag90_anchors": first(0.9),
                "lag50_hours": first(0.5) * 4.0, "lag90_hours": first(0.9) * 4.0, "phi_1": phi[1], "phi_6": phi[6],
                "phi_terminal": phi[H], "kernel_c": [float(x) for x in c], "eff_lag_kernel_K60": lag_c,
                "theory_lag_truncK60_noband": th_trunc, "theory_lag_untruncated": (1 - a) / a if a < 1 else 0.0,
                "kernel_R2": R2}
    print("%-22s a=%.2f b=%.1e | lag50=%2d (%4.0fh) lag90=%2d (%5.0fh) phi1=%.3f phi6=%.3f phiinf=%.3f | kern %.2f (th %.2f) R2=%.4f"
          % (tag, a, b, first(0.5), first(0.5) * 4, first(0.9), first(0.9) * 4, phi[1], phi[6], phi[H], lag_c, th_trunc, R2), flush=True)
json.dump(out, open(R + "/LAG12B.json", "w"), indent=1)
print("LAG2_DONE")
