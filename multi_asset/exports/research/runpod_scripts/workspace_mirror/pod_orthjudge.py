"""事后正交化判官: raw臂/resid臂 preds 对 zoo 复合逐锚投影剔除后的剩余 IC.
受据依据: 110 案『风格惩罚判负, 事后投影才对』. 三问: raw king 的 zoo 皮多厚 / 正交化剩余增量 / resid 训练是否优于 raw+事后投影.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_ts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pw_ts)}
F6_KEYS = ["f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]
F6_SIGN = np.array([-1.0, -1.0, -1.0, -1.0, -1.0, +1.0])
F6 = [PW[k] for k in F6_KEYS]
Y4P = PW["Y4"]; NWp = Y4P.shape[1]
yrs_p = np.array([time.gmtime(int(t)).tm_year for t in pw_ts])
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xz(v):
    ok = np.isfinite(v); out = np.zeros(len(v))
    n = ok.sum()
    if n >= 10:
        r = rankdata(v[ok]); out[ok] = (r - (n + 1) / 2) / max(n - 1, 1)
    return out
M = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
E_ts = M["E_ts"].astype(np.int64); members = M["members"]; dev_yrs = M["yrs"]
def load_pred(prefix):
    P = None
    for YV in (2023, 2024, 2025, 2026):
        try:
            p = np.load(f"/workspace/exports_train/{prefix}_s42_{YV}.npy")
            if P is None: P = np.full_like(p, np.nan)
            rows = np.where(dev_yrs == YV)[0]; P[rows] = p[rows]
        except FileNotFoundError: pass
    return P
PRAW = load_pred("kcurve_pred_K400"); PRES = load_pred("kcurveR_pred_K400")
res = {nm: {"rho": [], "ic_raw": [], "ic_orth": [], "by_year": {}} for nm in ("raw", "resid")}
for i in range(len(E_ts)):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    y = Y4P[j, m]
    zc = np.zeros(len(m))
    for c in range(6):
        zc += F6_SIGN[c] * xz(F6[c][j, m])
    for nm, P in (("raw", PRAW), ("resid", PRES)):
        p = P[i, m]
        ok = np.isfinite(p) & np.isfinite(y) & np.isfinite(zc)
        if ok.sum() < 60: continue
        pz = xz(p); zz = (zc - zc[ok].mean()) / (zc[ok].std() + 1e-9)
        beta = np.nanmean(pz[ok] * zz[ok]) / (np.nanmean(zz[ok] ** 2) + 1e-12)
        porth = pz - beta * zz
        r = res[nm]
        r["rho"].append(sp(p, zc)); r["ic_raw"].append(sp(p, y)); r["ic_orth"].append(sp(porth[ok], y[ok]))
        r["by_year"].setdefault(int(dev_yrs[i]), []).append(sp(porth[ok], y[ok]))
out = {}
for nm, r in res.items():
    out[nm] = {"rho_zoo": float(np.nanmean(r["rho"])), "ic": float(np.nanmean(r["ic_raw"])),
               "ic_orth": float(np.nanmean(r["ic_orth"])),
               "orth_by_year": {str(y): round(float(np.nanmean(v)), 4) for y, v in sorted(r["by_year"].items())}}
    print(f"[{nm:>5s}] rho_zoo {out[nm]['rho_zoo']:+.3f}  IC {out[nm]['ic']:+.4f}  IC⊥zoo {out[nm]['ic_orth']:+.4f}  逐年⊥ {out[nm]['orth_by_year']}", flush=True)
# zoo 复合自身的 IC 作参照
zic = []
for i in range(0, len(E_ts), 4):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    zc = np.zeros(len(m))
    for c in range(6): zc += F6_SIGN[c] * xz(F6[c][j, m])
    zic.append(sp(zc, Y4P[j, m]))
out["zoo_composite_ic"] = float(np.nanmean(zic))
print(f"[参照] zoo六因子等权复合自身 IC {out['zoo_composite_ic']:+.4f}", flush=True)
json.dump(out, open("/workspace/orthjudge.json", "w"), indent=1)
print("ORTH_DONE", flush=True)
