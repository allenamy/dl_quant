"""compare_king.py — INFORMATIONAL (not a prereg gate): rebuilt king OOS predictions vs the real 08-21 king (ref/slow_pred_hist_oos.npy,
sha 83f57477…). Finite-mask equality, per-year Pearson corr of predictions, per-year mean per-anchor Spearman IC vs meta y4 (both kings),
and fold IC receipts (data/slow_hist_folds_rebuilt.json vs ref/slow_hist_folds.json)."""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
PA = f"{ROOT}/data/slow_pred_hist_oos_rebuilt.npy"; PB = f"{ROOT}/ref/slow_pred_hist_oos.npy"
MA = f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz"; MB = f"{ROOT}/ref/wide_fea_hist_meta.npz"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def yr(t): return time.gmtime(int(t)).tm_year
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return spearmanr(a[ok], b[ok]).correlation if ok.sum() >= 30 else np.nan
A = np.load(PA, mmap_mode="r"); B = np.load(PB, mmap_mode="r")
mA = np.load(MA, allow_pickle=True); mB = np.load(MB, allow_pickle=True)
ta = mA["E_ts"].astype(np.int64); tb = mB["E_ts"].astype(np.int64)
memA = mA["members"]; y4A = mA["y4"]; memB = mB["members"]; y4B = mB["y4"]   # load once (NpzFile re-unpickles on every access)
out = {"self_sha256": sha(os.path.abspath(__file__)), "rebuilt": {"path": PA, "sha256": sha(PA), "shape": list(A.shape)}, "ref": {"path": PB, "sha256": sha(PB), "shape": list(B.shape)}}
common = np.intersect1d(ta, tb); ia = {int(t): i for i, t in enumerate(ta)}; ib = {int(t): i for i, t in enumerate(tb)}
ra = np.array([ia[int(t)] for t in common]); rb = np.array([ib[int(t)] for t in common]); yrs = np.array([yr(t) for t in common]); years = sorted(set(yrs.tolist()))
res = {}
for y in years:
    s = np.where(yrs == y)[0]
    pa = np.asarray(A[ra[s]], np.float64); pb = np.asarray(B[rb[s]], np.float64)
    fa = np.isfinite(pa); fb = np.isfinite(pb); both = fa & fb
    corr = float(np.corrcoef(pa[both], pb[both])[0, 1]) if both.sum() > 100 else float("nan")
    ica, icb = [], []
    for q, i in enumerate(s):
        m = memA[ra[i]]; y4 = y4A[ra[i], m]
        if np.isfinite(pa[q, m]).sum() >= 30: ica.append(sp(pa[q, m], y4))
        m2 = memB[rb[i]]; y4b = y4B[rb[i], m2]
        if np.isfinite(pb[q, m2]).sum() >= 30: icb.append(sp(pb[q, m2], y4b))
    res[str(y)] = {"n_anchors": int(len(s)), "finite_frac_rebuilt": float(fa.mean()), "finite_frac_ref": float(fb.mean()), "finite_mask_equal": bool(np.array_equal(fa, fb)),
                   "pearson_pred": corr, "bitwise_equal_share": float((pa[both] == pb[both]).mean()) if both.any() else float("nan"),
                   "ic_rebuilt": float(np.nanmean(ica)) if ica else float("nan"), "ic_ref": float(np.nanmean(icb)) if icb else float("nan")}
    print(f"  {y}: n {len(s)} finite {res[str(y)]['finite_frac_rebuilt']:.4f}/{res[str(y)]['finite_frac_ref']:.4f} mask_eq {res[str(y)]['finite_mask_equal']} corr(pred) {corr:.4f} bitwise_share {res[str(y)]['bitwise_equal_share']:.4f} IC rebuilt {res[str(y)]['ic_rebuilt']:.4f} ref {res[str(y)]['ic_ref']:.4f}", flush=True)
out["by_year"] = res
try:
    out["fold_ic_rebuilt"] = json.load(open(f"{ROOT}/data/slow_hist_folds_rebuilt.json")); out["fold_ic_ref"] = json.load(open(f"{ROOT}/ref/slow_hist_folds.json"))
    print("fold IC rebuilt", out["fold_ic_rebuilt"]["ic_by_year"], "ref(08-21)", out["fold_ic_ref"]["ic_by_year"], flush=True)
except Exception as e:
    print("fold IC json:", repr(e))
json.dump(out, open(f"{ROOT}/results/compare_king.json", "w"), indent=1); print("wrote results/compare_king.json")
