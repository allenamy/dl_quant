"""One-line DONE metrics for a d1gate run (EMA no-peek): cd-CLEAN + DENSE + Δ vs
post-fix baseline + selection provenance. Usage: python statusline_d1.py <run_name>."""
import numpy as np, json, os, sys
from scipy.stats import pearsonr, spearmanr
HZ = 600*1_000_000
BASE = {"2025_10": (0.0815, 0.0786), "2026_01": (0.0123, 0.0150), "2026_04": (0.0308, 0.0183)}
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
