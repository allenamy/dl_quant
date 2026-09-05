"""noise_floor.py — LightGBM-bits noise floor: D1 age-1 test-fold stitch (K1 recipe + seeds retrained; boosters not bitwise equal) vs K1 slow_pred_rollm.npy.
Per anchor (2024+): Spearman between the two prediction vectors over meta members; rank-IC difference vs raw y4 and dlw y4s (mean ± s.e. over anchors);
king-leg return difference (production leg definition, bps per unit gross). Read-only; writes noise_floor.json here."""
import json, time, numpy as np
from scipy.stats import rankdata, spearmanr
ROOT = "/workspace/review_scratch/cadence_seats/axisA"
A = np.load(f"{ROOT}/slow_pred_d1_testfold.npy"); B = np.load("/workspace/review_scratch/rolling_king/slow_pred_rollm.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; nA = len(E_ts)
DT = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); dmap = {int(t): k for k, t in enumerate(DT["E_ts"].astype(np.int64))}; y4s = DT["y4s"]
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pw_ts = set(PW["ts"].astype(np.int64).tolist())
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def leg(score, yv):
    ok = np.isfinite(yv); z = np.nan_to_num(xz(score)); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
    g = np.abs(z).sum(); return float((z / g * np.nan_to_num(yv, nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0
print(f"finite-mask equal: {bool(np.array_equal(np.isfinite(A), np.isfinite(B)))}; array_equal(equal_nan): {bool(np.array_equal(A, B, equal_nan=True))}; max|Δ| {float(np.nanmax(np.abs(A - B))):.3e}; "
      f"cells finite {int(np.isfinite(A).sum())}; cells exactly equal {int((A == B).sum())} ({(A == B).sum() / np.isfinite(A).sum():.4f} of finite)")
rho, dic_r, dic_s, dleg_r, dleg_s, ic_ar, ic_br = [], [], [], [], [], [], []
for i in range(nA):
    if yrs[i] < 2024: continue
    m = members[i]; a = A[i, m]; b = B[i, m]
    if not np.isfinite(a).any(): continue
    rho.append(sp(a, b)); ia = sp(a, y4[i, m]); ib = sp(b, y4[i, m]); dic_r.append(ia - ib); ic_ar.append(ia); ic_br.append(ib)
    k = dmap.get(int(E_ts[i]))
    if k is not None: dic_s.append(sp(a, y4s[k][m]) - sp(b, y4s[k][m]))
    if int(E_ts[i]) in pw_ts:
        dleg_r.append(leg(a, y4[i, m]) - leg(b, y4[i, m]))
        if k is not None: dleg_s.append(leg(a, y4s[k][m]) - leg(b, y4s[k][m]))
rho = np.array(rho); dic_r = np.array(dic_r); dic_s = np.array(dic_s); dleg_r = np.array(dleg_r); dleg_s = np.array(dleg_s)
se = lambda x: float(x.std(ddof=1) / np.sqrt(len(x)))
out = {"n_anchors": int(len(rho)), "pred_spearman_mean": float(np.nanmean(rho)), "pred_spearman_min": float(np.nanmin(rho)), "pred_spearman_p5": float(np.nanpercentile(rho, 5)),
       "IC_raw_k1rep": float(np.mean(ic_ar)), "IC_raw_k1": float(np.mean(ic_br)),
       "dIC_raw_mean": float(dic_r.mean()), "dIC_raw_se": se(dic_r), "dIC_raw_sd": float(dic_r.std(ddof=1)), "dIC_y4s_mean": float(dic_s.mean()), "dIC_y4s_se": se(dic_s),
       "dleg_raw_mean": float(dleg_r.mean()), "dleg_raw_se": se(dleg_r), "dleg_raw_sd": float(dleg_r.std(ddof=1)), "dleg_y4s_mean": float(dleg_s.mean()), "dleg_y4s_se": se(dleg_s),
       "dIC_raw_by_year": {int(y): float(dic_r[np.array([yy for yy in yrs[yrs >= 2024]]) == y].mean()) for y in (2024, 2025, 2026)} if len(dic_r) == int((yrs >= 2024).sum()) else "n/a"}
print(json.dumps(out, indent=1)); json.dump(out, open(f"{ROOT}/noise_floor.json", "w"), indent=1)
print(f"NOISE FLOOR (K1 replicate − K1): prediction Spearman mean {out['pred_spearman_mean']:.4f} (min {out['pred_spearman_min']:.4f}); ΔIC raw {out['dIC_raw_mean']:+.5f} ± {out['dIC_raw_se']:.5f} (per-anchor sd {out['dIC_raw_sd']:.4f}); "
      f"ΔIC y4s {out['dIC_y4s_mean']:+.5f} ± {out['dIC_y4s_se']:.5f}; Δleg raw {out['dleg_raw_mean']:+.4f} ± {out['dleg_raw_se']:.4f} bps (sd {out['dleg_raw_sd']:.3f}); Δleg y4s {out['dleg_y4s_mean']:+.4f} ± {out['dleg_y4s_se']:.4f}")
