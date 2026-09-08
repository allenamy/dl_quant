"""Task A step 1 — fetch the official 2026-08 monthly 5m archive for all 829 cache symbols.
CDN only (data.binance.vision); exempt from the rate rule by the user's 2026-09-05 ruling."""
import os, io, json, zipfile, urllib.request, concurrent.futures as cf, sys
import numpy as np
sys.path.insert(0, "/workspace"); from zload import zload
OUT = "/workspace/review_scratch/holefix_kl"; os.makedirs(OUT, exist_ok=True)
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
SY = [str(s) for s in Z["symbols"]]
print("symbols in cache:", len(SY), flush=True)
def get(s):
    p = os.path.join(OUT, "%s.csv" % s)
    if os.path.exists(p) and os.path.getsize(p) > 0: return (s, "cached")
    u = "https://data.binance.vision/data/futures/um/monthly/klines/%s/5m/%s-5m-2026-08.zip" % (s, s)
    try:
        raw = urllib.request.urlopen(u, timeout=180).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z: open(p, "wb").write(z.read(z.namelist()[0]))
        return (s, "ok")
    except Exception as e:
        return (s, "MISS:%s" % type(e).__name__)
res = []
with cf.ThreadPoolExecutor(max_workers=10) as ex:
    for i, r in enumerate(ex.map(get, SY)):
        res.append(r)
        if (i + 1) % 100 == 0: print("  fetched", i + 1, flush=True)
from collections import Counter
print("RESULT:", dict(Counter(v.split(":")[0] for _, v in res)), flush=True)
miss = [s for s, v in res if v.startswith("MISS")]
print("missing %d: %s" % (len(miss), miss[:20]), flush=True)
json.dump(miss, open("/workspace/review_scratch/holefix_missing.json", "w"))
print("DOWNLOAD_DONE", flush=True)
