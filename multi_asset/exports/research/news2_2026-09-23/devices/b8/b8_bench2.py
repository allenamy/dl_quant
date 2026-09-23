import json, sys, time
import numpy as np
sys.path.insert(0, "/workspace/codex_research/QNT-2026-0907/combo_20260923/devices")
from feature_contract import window_stats
W2 = "/dev/shm/news2_2026-09-23"
C = np.load(f"{W2}/inputs/parity_cache_slice.npz", allow_pickle=True)
ts = C["ts"].astype(np.int64); D = C["data"]
A = 1789660800
ia = int(np.searchsorted(ts, A)); i0 = max(ia + 1 - 11520, 0)
CDf = np.array(D[i0:ia + 1], dtype=np.float16).astype(np.float32)
rows = np.array([CDf.shape[0] - 1]); WINS = (48, 288, 864, 2016, 8640)

def shared_cumsum():
    """Same float64 cumsum semantics as window_stats, but ONE cumsum pass per channel reused across
    the five widths - the shape dlw_features.py already uses. Not the researcher bytes."""
    hi = rows + 1
    out = []
    for ch in range(7):
        x = CDf[:, :, ch].astype(np.float64)
        good = np.isfinite(x); z = np.where(good, x, 0.0)
        c_n = np.empty((len(x) + 1, x.shape[1]), np.int32); c_n[0] = 0
        np.cumsum(good, axis=0, dtype=np.int32, out=c_n[1:])
        c_s = np.empty((len(x) + 1, x.shape[1]), np.float64); c_s[0] = 0
        np.cumsum(z, axis=0, dtype=np.float64, out=c_s[1:])
        if ch == 0:
            c_2 = np.empty((len(x) + 1, x.shape[1]), np.float64); c_2[0] = 0
            np.cumsum(z * z, axis=0, dtype=np.float64, out=c_2[1:])
        for w in WINS:
            lo = np.maximum(hi - w, 0)
            n = c_n[hi] - c_n[lo]; s = c_s[hi] - c_s[lo]
            m = s / np.maximum(n, 1); m[n == 0] = np.nan
            out.append(s if ch == 0 else m)
            if ch == 0:
                sd = np.sqrt(np.maximum((c_2[hi] - c_2[lo]) / np.maximum(n, 1) - m * m, 0)); sd[n == 0] = np.nan
                out.append(sd)
    return out

t_ = []
for _ in range(3):
    t = time.time(); shared_cumsum(); t_.append(round(time.time() - t, 2))
res = json.load(open(f"{W2}/receipts/B8_KERNEL_BENCH.json"))
res["shared_cumsum"] = {"seconds": t_, "median": float(np.median(t_)),
                        "note": "float64 cumsum semantics identical to window_stats, one pass per channel instead of one per (channel,width); NOT the researcher bytes"}
res["ratio_shared_over_producer"] = round(res["shared_cumsum"]["median"] / res["producer"]["median"], 2)
print(json.dumps({k: (v["median"] if isinstance(v, dict) and "median" in v else v) for k, v in res.items()}))
open(f"{W2}/receipts/B8_KERNEL_BENCH.json", "w").write(json.dumps(res, indent=1))
