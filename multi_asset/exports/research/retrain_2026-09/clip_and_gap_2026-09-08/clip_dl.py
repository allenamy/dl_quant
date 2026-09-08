import json, os, io, zipfile, urllib.request, concurrent.futures as cf
need=json.load(open("/workspace/review_scratch/clip_need.json"))["need"]
# also the previous month for each pair (needed when the anchor is the first bar of a month)
def prev(ym):
    y,m=map(int,ym.split("-")); m-=1
    if m==0: y,m=y-1,12
    return "%04d-%02d"%(y,m)
pairs=sorted({(s,m) for s,m in need} | {(s,prev(m)) for s,m in need})
D="/workspace/review_scratch/clip_kl"
def get(p):
    s,m=p; out=os.path.join(D,"%s_%s.csv"%(s,m))
    if os.path.exists(out): return (p,"cached")
    u="https://data.binance.vision/data/futures/um/monthly/klines/%s/4h/%s-4h-%s.zip"%(s,s,m)
    try:
        raw=urllib.request.urlopen(u,timeout=60).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z: open(out,"wb").write(z.read(z.namelist()[0]))
        return (p,"ok")
    except Exception as e: return (p,"MISS %s"%type(e).__name__)
r=[]
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for x in ex.map(get,pairs): r.append(x)
from collections import Counter
print("pairs",len(pairs),Counter(v.split()[0] for _,v in r))
miss=[p for p,v in r if v.startswith("MISS")]
print("missing %d e.g. %s"%(len(miss),miss[:8]))
json.dump([[s,m] for s,m in miss],open("/workspace/review_scratch/clip_miss.json","w"))
