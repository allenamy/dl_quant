"""B8 decisive: across anchors, is the patched INLINE kernel bitwise equal to window_stats?
One anchor agreeing proves nothing about the rest, so this runs the full cache across years and
reports, per anchor, the number of differing cells - and refuses to report a clean result without
also reporting how many anchors were actually compared."""
import json, sys, time
import numpy as np
sys.path.insert(0, "/workspace/codex_research/QNT-2026-0907/combo_20260923/devices")
from feature_contract import window_stats
W2 = "/dev/shm/news2_2026-09-23"
ax = np.load(f"{W2}/inputs/cache_x0918r_axes.npz", allow_pickle=True)
ts = ax["ts"].astype(np.int64)
with np.load("/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz") as z:
    D = z["data"]
WINS = (48, 288, 864, 2016, 8640)
ANCH = [1657065600, 1674144000, 1685520000, 1688097600, 1702598400, 1717200000, 1731052800,
        1742428800, 1756684800, 1770883200, 1780272000, 1787961600]
rows_out = []
for A in ANCH:
    ia = int(np.searchsorted(ts, A))
    if ia >= len(ts) or ts[ia] != A: 
        rows_out.append({"anchor": A, "status": "UNAVAILABLE"}); continue
    i0 = max(ia + 1 - 11520, 0)
    CDf = np.array(D[i0:ia + 1], dtype=np.float16).astype(np.float32)
    rows = np.array([CDf.shape[0] - 1]); ai = CDf.shape[0] - 1
    nd_val = 0; nd_std = 0; worst = 0.0
    for ch in range(7):
        for w in WINS:
            seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]
            fin = np.isfinite(seg); cnt = fin.sum(0)
            s_ = np.where(fin, seg, 0).sum(0, dtype=np.float64)
            inline = (s_ if ch == 0 else np.where(cnt > 0, s_ / np.maximum(cnt, 1), np.nan)).astype(np.float32)
            ref = window_stats(CDf[:, :, ch], rows, w)
            v = (ref["sum"] if ch == 0 else ref["mean"])[0].astype(np.float32)
            bad = ~((inline == v) | (np.isnan(inline) & np.isnan(v)))
            nd_val += int(bad.sum())
            if bad.any():
                worst = max(worst, float(np.nanmax(np.abs(inline[bad].astype(np.float64) - v[bad].astype(np.float64)))))
            if ch == 0:
                z64 = np.where(fin, seg, 0).astype(np.float64)
                mm = z64.sum(0) / np.maximum(cnt, 1)
                vv = np.sqrt(np.maximum((z64 * z64).sum(0) / np.maximum(cnt, 1) - mm ** 2, 0))
                vv = np.where(cnt > 0, vv, np.nan).astype(np.float32)
                rv = ref["std"][0].astype(np.float32)
                b2 = ~((vv == rv) | (np.isnan(vv) & np.isnan(rv)))
                nd_std += int(b2.sum())
                if b2.any():
                    worst = max(worst, float(np.nanmax(np.abs(vv[b2].astype(np.float64) - rv[b2].astype(np.float64)))))
    rows_out.append({"anchor": A, "status": "OK", "value_cells_differing": nd_val,
                     "std_cells_differing": nd_std, "max_abs_diff": worst, "n_names": int(CDf.shape[1])})
    print(A, nd_val, nd_std, worst, flush=True)
ok = [r for r in rows_out if r.get("status") == "OK"]
tot = sum(r["value_cells_differing"] + r["std_cells_differing"] for r in ok)
out = {"anchors_compared": len(ok), "anchors_requested": len(ANCH),
       "cells_per_anchor": 40 * 829, "total_cells_differing": tot,
       "VERDICT": ("BITWISE_EQUAL over %d anchors" % len(ok)) if (tot == 0 and ok) else ("DIFFERS: %d cells" % tot),
       "rows": rows_out}
print(json.dumps({k: out[k] for k in ("anchors_compared", "total_cells_differing", "VERDICT")}))
open(f"{W2}/receipts/B8_INLINE_VS_WINDOWSTATS.json", "w").write(json.dumps(out, indent=1))
