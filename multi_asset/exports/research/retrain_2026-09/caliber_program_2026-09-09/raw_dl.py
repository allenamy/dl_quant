import json, os, io, zipfile, urllib.request, concurrent.futures as cf
from collections import Counter
need = json.load(open("/workspace/review_scratch/clip_need.json"))["need"]
def prev(ym):
    y, m = map(int, ym.split("-")); m -= 1
    if m == 0: y, m = y - 1, 12
    return "%04d-%02d" % (y, m)
pairs = sorted({(s, m) for s, m in need} | {(s, prev(m)) for s, m in need})
D = "/workspace/review_scratch/raw5m_kl"; os.makedirs(D, exist_ok=True)
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
print("pairs", len(pairs), dict(Counter(x.split(":")[0] for x in r)))
miss = [p for p, x in zip(pairs, r) if x.startswith("MISS")]; print("missing", len(miss), miss[:10])
json.dump([list(p) for p in miss], open("/workspace/review_scratch/raw5m_missing.json", "w")); print("RAW_DL_DONE")
