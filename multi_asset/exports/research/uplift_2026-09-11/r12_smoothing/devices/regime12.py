"""r12 regime table, built from the SAME meta the device reads (pod_backup_2026-08-21/wide_fea_hist_meta.npz).
Causal by construction: every quantity at anchor t uses only rows <= t.
PREREG §4 definitions, frozen before numbers."""
import numpy as np, json, time, hashlib
B = "/workspace/uplift_2026-09-11/r12_smoothing/dev/pod_backup_2026-08-21"
MT = np.load(B + "/wide_fea_hist_meta.npz", allow_pickle=True)
E = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; members = MT["members"]
nA = len(E)
mkt = np.full(nA, np.nan); pos_frac = np.full(nA, np.nan)
for i in range(nA):
    m = members[i]
    v = y4[i, m]; v = v[np.isfinite(v)]
    if len(v) >= 20:
        mkt[i] = float(np.median(v)); pos_frac[i] = float((v > 0).mean())
# 6-anchor (24h) trailing, causal (includes t)
def trail(x, w):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        s = x[max(0, i - w + 1): i + 1]; s = s[np.isfinite(s)]
        if len(s) == w: out[i] = s.mean()
    return out
bre24 = trail(pos_frac, 6)
mkt24 = np.full(nA, np.nan)
for i in range(5, nA):
    s = mkt[i - 5: i + 1]
    if np.isfinite(s).all(): mkt24[i] = float(s.sum())
q02 = float(np.nanquantile(mkt24, 0.02))
crash = np.isfinite(mkt24) & (mkt24 <= q02)
post = np.zeros(nA, bool)
ci = np.where(crash)[0]
for i in ci:
    post[i + 1: min(i + 13, nA)] = True
lab = np.full(nA, "R4_other", dtype=object)
lab[np.isfinite(bre24) & (bre24 >= 0.75)] = "R1_broad_rally"
lab[np.isfinite(bre24) & (bre24 <= 0.25)] = "R2_broad_selloff"
lab[post] = "R3_post_crash_reversal"          # R3 wins overlaps (PREREG §4)
np.savez_compressed("/workspace/uplift_2026-09-11/r12_smoothing/REGIME12.npz",
                    ts=E, label=np.array([str(x) for x in lab]), mkt=mkt, pos_frac=pos_frac,
                    bre24=bre24, mkt24=mkt24, crash=crash, post=post)
cnt = {k: int((lab == k).sum()) for k in ("R1_broad_rally", "R2_broad_selloff", "R3_post_crash_reversal", "R4_other")}
print(json.dumps({"nA": nA, "mkt24_q02": q02, "n_crash_anchors": int(crash.sum()), "counts": cnt,
                  "meta_sha16": hashlib.sha256(open(B + "/wide_fea_hist_meta.npz", "rb").read()).hexdigest()[:16]}, indent=1))
