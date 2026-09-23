"""B8: what does vendoring feature_contract.window_stats cost the King block, per anchor?

Not an opinion: the two call patterns are timed on a real 40-day rolling window from the x0918r cache.
  producer : direct window sums over the slice, 7 channels x 5 widths + the member screen
  vendor   : feature_contract.window_stats(x, rows=[last], width) once per (channel, width)
Both are run on the SAME array, 3 repeats, median reported.
"""
import json, sys, time
import numpy as np
sys.path.insert(0, "/workspace/codex_research/QNT-2026-0907/combo_20260923/devices")
from feature_contract import window_stats

W2 = "/dev/shm/news2_2026-09-23"
C = np.load(f"{W2}/inputs/parity_cache_slice.npz", allow_pickle=True)
ts = C["ts"].astype(np.int64); D = C["data"]
A = 1789660800
ia = int(np.searchsorted(ts, A)); i0 = max(ia + 1 - 11520, 0)
RD = np.array(D[i0:ia + 1], dtype=np.float16)
CDf = RD.astype(np.float32)
rows = np.array([CDf.shape[0] - 1])
WINS = (48, 288, 864, 2016, 8640)
print("window", CDf.shape, flush=True)

def producer():
    ai = CDf.shape[0] - 1
    out = []
    for ch in range(7):
        for w in WINS:
            seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]
            fin = np.isfinite(seg)
            cnt = fin.sum(0)
            s_ = np.where(fin, seg, 0).sum(0, dtype=np.float64)
            out.append(np.where(cnt > 0, s_ / np.maximum(cnt, 1), np.nan).astype(np.float32))
    for w in WINS:                      # vol block
        seg = CDf[max(ai + 1 - w, 0):ai + 1, :, 0]
        fin = np.isfinite(seg); cnt = fin.sum(0)
        z64 = np.where(fin, seg, 0).astype(np.float64)
        mm = z64.sum(0) / np.maximum(cnt, 1)
        out.append(np.sqrt(np.maximum((z64 * z64).sum(0) / np.maximum(cnt, 1) - mm ** 2, 0)))
    return out

def vendor():
    out = []
    for ch in range(7):
        for w in WINS:
            st = window_stats(CDf[:, :, ch], rows, w)
            out.append(st["sum"] if ch == 0 else st["mean"])
    for w in WINS:
        out.append(window_stats(CDf[:, :, 0], rows, w)["std"])
    return out

res = {}
for name, fn in (("producer", producer), ("vendor", vendor)):
    ts_ = []
    for _ in range(3):
        t = time.time(); fn(); ts_.append(round(time.time() - t, 2))
    res[name] = {"seconds": ts_, "median": float(np.median(ts_))}
    print(name, ts_, flush=True)
res["ratio_vendor_over_producer"] = round(res["vendor"]["median"] / res["producer"]["median"], 2)
res["note"] = "window_stats recomputes a full-axis cumsum per call; the producer sums the slice directly. 40 calls each."
print(json.dumps(res))
open(f"{W2}/receipts/B8_KERNEL_BENCH.json", "w").write(json.dumps(res, indent=1))
