"""One-line DONE metrics for a d1gate run (EMA no-peek): cd-CLEAN + DENSE + Δ vs
post-fix baseline + selection provenance. Usage: python statusline_d1.py <run_name>."""
import numpy as np, json, os, sys
from scipy.stats import pearsonr, spearmanr
HZ = 600*1_000_000
# Canonical 10-month post-fix production baseline (0A caliber), recomputed self-
# consistently from the mask-fixed CSV exports/final_l01/y600_backtest_dataset.csv via
# multi_asset/eval/baseline_table.py. Validated: 2025_10->0.0844 (~0.0815), 2026_04->
# 0.0312 (~0.0308) reproduce the old entries; 2026_01 CORRECTED 0.0123->0.0304 (the old
# value was a different/weaker reference, inconsistent with the canonical production CSV).
BASE = {"2025_08": (0.0323, 0.0348), "2025_09": (0.0434, 0.0524), "2025_10": (0.0844, 0.0970),
        "2025_11": (0.0671, 0.0536), "2025_12": (0.0482, 0.0213), "2026_01": (0.0304, 0.0432),
        "2026_02": (0.0183, 0.0198), "2026_03": (0.0139, 0.0225), "2026_04": (0.0312, 0.0212),
        "2026_05": (0.0162, 0.0187)}
def clean_idx(ts):
    o = np.argsort(ts); keep = []; last = -1e18
    for i in range(len(o)):
        if ts[o[i]]-last >= HZ: keep.append(o[i]); last = ts[o[i]]
    return np.array(keep)
def load(p):
    z = np.load(p, allow_pickle=True)
    pr = z["predictions"]; q = (pr[:, 1] if pr.ndim == 2 else pr).astype(np.float64)
    y = z["targets"].astype(np.float64); ts = z["timestamps"].astype(np.int64)
    if "mask" in z.files:
        k = z["mask"].astype(bool); q, y, ts = q[k], y[k], ts[k]
    return q, y, ts
def metrics(q, y, ts):
    dP = pearsonr(q, y)[0]; b = (np.cov(y, q)[0, 1]/q.var()) if q.var() > 1e-12 else float("nan")
    sg = q.std()/(y.std()+1e-12); dk = ts//(86400*1_000_000); rs = []
    for d in np.unique(dk):
        m = dk == d; k = clean_idx(ts[m])
        if len(k) > 20:
            qk = q[m][k]; yk = y[m][k]
            if qk.std() > 1e-12:
                r = pearsonr(qk, yk)[0]
                if np.isfinite(r): rs.append(r)
    return dP, (np.mean(rs) if rs else float("nan")), b, sg
run = sys.argv[1]; month = "_".join(run.split("_")[1:3])
outdir = sys.argv[2] if len(sys.argv) > 2 else "experiments/d1gate/"+run
base = outdir.rstrip("/")+"/fold_0"
mj = json.load(open(base+"/metrics.json")); sel = mj.get("selection", {})
dP, cdP, b, sg = metrics(*load(base+"/ema_test_preds.npz"))
bcd, bd = BASE.get(month, (float("nan"), float("nan")))
f = [run, "cdCLEAN=%+.4f" % cdP, "DENSE=%+.4f" % dP, "beta=%+.3f" % b, "sigma=%.3f" % sg,
     "dCD=%+.4f" % (cdP-bcd), "dDENSE=%+.4f" % (dP-bd),
     "best_ep=%s" % sel.get("best_epoch"), "ema_ep=%s" % sel.get("ema_best_epoch"),
     "best_sigfb=%s" % mj.get("best_is_sigma_fallback"), "ema_sigfb=%s" % mj.get("ema_is_sigma_fallback"),
     "epochs_ran=%s" % mj.get("epochs_ran"), "stopped_pat=%s" % mj.get("stopped_at_patience")]
print(" ".join(f))
