"""Is the shared-cumsum variant BITWISE equal to feature_contract.window_stats, or only similar?
Assert, do not assume. Compared on the real 40-day window, all 7 channels x 5 widths, plus std."""
import json, sys
import numpy as np
sys.path.insert(0, "/workspace/codex_research/QNT-2026-0907/combo_20260923/devices")
from feature_contract import window_stats
W2 = "/dev/shm/news2_2026-09-23"
C = np.load(f"{W2}/inputs/parity_cache_slice.npz", allow_pickle=True)
ts = C["ts"].astype(np.int64); D = C["data"]
A = 1789660800
ia = int(np.searchsorted(ts, A)); i0 = max(ia + 1 - 11520, 0)
CDf = np.array(D[i0:ia + 1], dtype=np.float16).astype(np.float32)
rows = np.array([CDf.shape[0] - 1]); hi = rows + 1; WINS = (48, 288, 864, 2016, 8640)
def eq(a, b):
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    return int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
diffs = {}
for ch in range(7):
    x = CDf[:, :, ch].astype(np.float64)
    good = np.isfinite(x); z = np.where(good, x, 0.0)
    c_n = np.empty((len(x)+1, x.shape[1]), np.int32); c_n[0] = 0; np.cumsum(good, axis=0, dtype=np.int32, out=c_n[1:])
    c_s = np.empty((len(x)+1, x.shape[1]), np.float64); c_s[0] = 0; np.cumsum(z, axis=0, dtype=np.float64, out=c_s[1:])
    c_2 = np.empty((len(x)+1, x.shape[1]), np.float64); c_2[0] = 0; np.cumsum(z*z, axis=0, dtype=np.float64, out=c_2[1:])
    for w in WINS:
        lo = np.maximum(hi - w, 0)
        n = c_n[hi] - c_n[lo]; s = c_s[hi] - c_s[lo]
        m = s / np.maximum(n, 1); m[n == 0] = np.nan
        sd = np.sqrt(np.maximum((c_2[hi]-c_2[lo]) / np.maximum(n, 1) - m*m, 0)); sd[n == 0] = np.nan
        ref = window_stats(CDf[:, :, ch], rows, w)
        diffs[f"ch{ch}_w{w}"] = {"count": eq(n, ref["count"]), "sum": eq(s, ref["sum"]), "mean": eq(m, ref["mean"]), "std": eq(sd, ref["std"])}
bad = {k: v for k, v in diffs.items() if any(v.values())}
out = {"n_comparisons": len(diffs)*4, "n_cells_per_comparison": int(CDf.shape[1]),
       "BITWISE_EQUAL": not bad, "differing": bad,
       "verdict": "PASS shared-cumsum == window_stats bitwise" if not bad else "FAIL"}
print(json.dumps(out))
open(f"{W2}/receipts/B8_SHARED_CUMSUM_BITWISE.json", "w").write(json.dumps(out, indent=1))
