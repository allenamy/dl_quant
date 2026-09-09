"""Fetch official 5m monthly archives for the symbol-months of ALL float16(±0.3) boundary bars (not only the 440 held cells)."""
import numpy as np, sys, os, io, zipfile, urllib.request, time, json, concurrent.futures as cf
sys.path.insert(0, "/workspace"); from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_holefix.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]
ch0 = Z["data"][:, :, 0]; cand = np.isfinite(ch0) & ((ch0 == np.float16(0.3)) | (ch0 == np.float16(-0.3))); rows, cols = np.where(cand)
def prev(ym):
    y, m = map(int, ym.split("-")); m -= 1
    if m == 0: y, m = y - 1, 12
    return "%04d-%02d" % (y, m)
pairs = set()
for r, c in zip(rows, cols):
    ym = time.strftime("%Y-%m", time.gmtime(int(CTS[r]))); pairs.add((SY[c], ym)); pairs.add((SY[c], prev(ym)))
pairs = sorted(pairs); D = "/workspace/review_scratch/raw5m_kl"; os.makedirs(D, exist_ok=True)
def get(p):
    s, m = p; out = os.path.join(D, "%s_%s.csv" % (s, m))
    if os.path.exists(out) and os.path.getsize(out) > 0: return "cached"
    u = "https://data.binance.vision/data/futures/um/monthly/klines/%s/5m/%s-5m-%s.zip" % (s, s, m)
    try:
        raw = urllib.request.urlopen(u, timeout=180).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z: open(out, "wb").write(z.read(z.namelist()[0]))
        return "ok"
    except Exception as e: return "MISS:" + type(e).__name__
with cf.ThreadPoolExecutor(max_workers=10) as ex: r = list(ex.map(get, pairs))
from collections import Counter; print("candidates %d ; pairs %d ; %s" % (len(rows), len(pairs), dict(Counter(x.split(":")[0] for x in r))), flush=True)
miss = [p for p, x in zip(pairs, r) if x.startswith("MISS")]; print("missing %d: %s" % (len(miss), miss[:20]), flush=True); json.dump([list(p) for p in miss], open("/workspace/review_scratch/raw5m_missing2.json", "w")); print("RAW_DL2_DONE", flush=True)
