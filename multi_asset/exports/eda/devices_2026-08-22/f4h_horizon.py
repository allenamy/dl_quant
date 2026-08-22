"""F-4 修正案 C: 增量的视界寿命 — 逐锚秩 IC 对 块1[N,N+4h] 与 块2[N+4h,N+8h]。
判据冻结于 PREREG_F4 §8(commit 见 git). 装置与结论同寿命。"""
import os, json, time
import numpy as np
from scipy.stats import spearmanr, rankdata
ROOT = "/mnt/storage/private/work_hsy"; DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
y4s = TG["y4s"]; E_ts = TG["E_ts"].astype(np.int64); MS = list(TG["members"]); yrs = TG["yrs"].astype(int)
nA, NW = y4s.shape
nxt = {int(t): i for i, t in enumerate(E_ts)}
NEXT = np.array([nxt.get(int(t) + 14400, -1) for t in E_ts])          # 下一 4h 锚
def sp(a, b, nmin=30):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < nmin: return np.nan
    r = spearmanr(a[ok], b[ok]); return float(r.correlation if hasattr(r, "correlation") else r[0])
def xz(v):
    out = np.full(len(v), np.nan); ok = np.isfinite(v); n = ok.sum()
    if n >= 5: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
P78 = np.load(f"{OUT}/preds/f4_lgbm_K78raw.npy"); P167 = np.load(f"{OUT}/preds/f4_lgbm_K167raw.npy")
rep = {"n_next_ok": int((NEXT >= 0).sum())}
for tag, P in (("K78raw", P78), ("K167raw", P167), ("INCR", None)):
    ic1 = np.full(nA, np.nan); ic2 = np.full(nA, np.nan)
    for i in range(nA):
        j = NEXT[i]
        if j < 0: continue
        m = np.asarray(MS[i], np.int64)
        if m.size < 30: continue
        s = (xz(P167[i, m]) - xz(P78[i, m])) if P is None else P[i, m]
        ic1[i] = sp(s, y4s[i, m]); ic2[i] = sp(s, y4s[j, m])
    d = {"ic_block1": float(np.nanmean(ic1)), "ic_block2": float(np.nanmean(ic2)),
         "ratio_b2_over_b1": float(np.nanmean(ic2) / np.nanmean(ic1)) if np.nanmean(ic1) else None,
         "by_year_b1": {str(y): round(float(np.nanmean(ic1[yrs == y])), 4) for y in sorted(set(yrs.tolist())) if (yrs == y).sum() > 200},
         "by_year_b2": {str(y): round(float(np.nanmean(ic2[yrs == y])), 4) for y in sorted(set(yrs.tolist())) if (yrs == y).sum() > 200}}
    rep[tag] = d
    print(tag, "块1", round(d["ic_block1"], 4), "块2", round(d["ic_block2"], 4), "比", round(d["ratio_b2_over_b1"], 3), flush=True)
g = {"incr_b2_le_0.3xb1": bool(rep["INCR"]["ratio_b2_over_b1"] <= 0.3),
     "base_b2_ge_0.6xb1": bool(rep["K78raw"]["ratio_b2_over_b1"] >= 0.6)}
g["horizon_mismatch_verdict"] = bool(g["incr_b2_le_0.3xb1"] and g["base_b2_ge_0.6xb1"])
rep["gate"] = g
json.dump(rep, open(f"{OUT}/results/f4h_horizon.json", "w"), indent=1, default=float)
print("GATE", g, flush=True); print("F4H_DONE", flush=True)
