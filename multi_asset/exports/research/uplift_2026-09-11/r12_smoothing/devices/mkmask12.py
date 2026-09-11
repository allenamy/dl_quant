"""r12c EXPLORATORY probe masks. ALTSURGE = R72_i >= 0.08, R72_i = sum_{k=i-18..i-1} A_ew[k]
(strictly causal: only anchors <= i-1). Primitives file = r12_regime agent's causal_primitives_r12.npz.
Nulls = the SAME mask rotated +101/+503/+1009 anchors (identical on-density => turnover-matched by
construction; the defective per-anchor permutation placebo is NOT used)."""
import numpy as np, json, hashlib
R = "/workspace/uplift_2026-09-11/r12_smoothing"
P = np.load(R + "/causal_primitives_r12.npz", allow_pickle=True)
c = {str(x): i for i, x in enumerate(P["cols"])}; pr = P["rec"]
ts = pr[:, c["ts"]].astype(np.int64); A = pr[:, c["A_ew"]]
n = len(ts); R72 = np.full(n, np.nan)
for i in range(18, n):
    s = A[i - 18:i]
    if np.isfinite(s).all(): R72[i] = s.sum()
m = np.isfinite(R72) & (R72 >= 0.08)
rec = {}
for nm, sh in (("ALTSURGE", 0), ("NULLSHIFT101", 101), ("NULLSHIFT503", 503), ("NULLSHIFT1009", 1009)):
    mm = np.roll(m, sh)
    p = "%s/mask_%s.npz" % (R, nm)
    np.savez_compressed(p, ts=ts, mask=mm)
    rec[nm] = {"path": p, "n_on": int(mm.sum()), "frac": float(mm.mean()),
               "sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "shift_anchors": sh}
    print(nm, mm.sum(), "%.4f" % mm.mean(), rec[nm]["sha16"])
json.dump({"rule": "R72_i = sum_{k=i-18..i-1} A_ew[k] >= 0.08 (causal)", "primitives_sha16":
           hashlib.sha256(open(R + "/causal_primitives_r12.npz", "rb").read()).hexdigest()[:16], "masks": rec},
          open(R + "/MASKS12.json", "w"), indent=1)
