"""书级组合首扫: score = w*z(zooC) + (1-w)*z(king_pred), 逐种子(不做多种子集成), 固定锚.
对照: 纯zoo w=1 / 纯king w=0 / 正交算术 0.0748. Q4 = BTC vol_7d 最坏五分位.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_ts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pw_ts)}
psyms = list(PW["symbols"]); BTC_P = psyms.index("BTCUSDT")
F6_KEYS = ["f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]
F6_SIGN = np.array([-1., -1., -1., -1., -1., +1.])
F6 = [PW[k] for k in F6_KEYS]; Y4P = PW["Y4"]; BVOL = PW["f_vol_7d"][:, BTC_P]
M = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
E_ts = M["E_ts"].astype(np.int64); members = M["members"]; dev_yrs = M["yrs"]
SEEDS = (42, 2027, 3037)
def load_pred(sd):
    P = None
    for YV in (2023, 2024, 2025, 2026):
        try:
            p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s{sd}_{YV}.npy")
            if P is None: P = np.full_like(p, np.nan)
            P[np.where(dev_yrs == YV)[0]] = p[np.where(dev_yrs == YV)[0]]
        except FileNotFoundError: pass
    return P
PR = {sd: load_pred(sd) for sd in SEEDS}
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10:
        r = rankdata(v[ok]); out[ok] = (r - (n + 1) / 2) / max(n - 1, 1)
    return out
WS = [0, .2, .3, .4, .5, .6, .7, .8, 1.0]
fixed = []
for i in range(len(E_ts)):
    j = pw_row.get(int(E_ts[i]))
    if j is None or len(members[i]) < 360: continue
    if all(np.isfinite(PR[sd][i, members[i]]).sum() >= 300 for sd in SEEDS):
        fixed.append((i, j))
print(f"固定锚 {len(fixed)}", flush=True)
IC = {sd: {w: [] for w in WS} for sd in SEEDS}
bv = []
for i, j in fixed:
    m = members[i]
    y = Y4P[j, m]
    zc = np.zeros(len(m))
    for c in range(6): zc += F6_SIGN[c] * xz(F6[c][j, m])
    zcz = xz(zc)
    bv.append(BVOL[j])
    for sd in SEEDS:
        pz = xz(PR[sd][i, m])
        for w in WS:
            IC[sd][w].append(sp(w * np.nan_to_num(zcz) + (1 - w) * np.nan_to_num(pz), y))
bv = np.array(bv)
qb = np.quantile(bv[np.isfinite(bv)], [0.8])
q4mask = bv >= qb[0]
out = {"n_fixed": len(fixed), "curve": {}, "per_seed_best": {}}
print("\nw      " + "".join(f"  s{sd:<6d}" for sd in SEEDS) + "  均值")
best_w = {}
for w in WS:
    vals = [float(np.nanmean(IC[sd][w])) for sd in SEEDS]
    mv = float(np.mean(vals))
    out["curve"][str(w)] = {"per_seed": vals, "mean": mv}
    print(f"{w:.1f}  " + "".join(f"  {v:+.4f}" for v in vals) + f"  {mv:+.4f}")
for sd in SEEDS:
    bw = max(WS, key=lambda w: np.nanmean(IC[sd][w]))
    best_w[sd] = bw
out["per_seed_best"] = {str(sd): best_w[sd] for sd in SEEDS}
wm = max(WS, key=lambda w: out["curve"][str(w)]["mean"])
arr_best = np.nanmean(np.stack([IC[sd][wm] for sd in SEEDS]), 0)
arr_zoo = np.nanmean(np.stack([IC[sd][1.0] for sd in SEEDS]), 0)
yrs_f = np.array([time.gmtime(int(E_ts[i])).tm_year for i, _ in fixed])
out["best_w"] = wm
out["best_by_year"] = {str(y): round(float(np.nanmean(arr_best[yrs_f == y])), 4) for y in sorted(set(yrs_f))}
out["best_q4"] = float(np.nanmean(arr_best[q4mask])); out["zoo_q4"] = float(np.nanmean(arr_zoo[q4mask]))
print(f"\n最优 w={wm}(逐种子 {best_w}), 逐年 {out['best_by_year']}")
print(f"Q4(BTC波动最坏档): 组合 {out['best_q4']:+.4f} vs 纯zoo {out['zoo_q4']:+.4f}")
json.dump(out, open("/workspace/combo_sweep.json", "w"), indent=1)
print("COMBO_DONE", flush=True)
