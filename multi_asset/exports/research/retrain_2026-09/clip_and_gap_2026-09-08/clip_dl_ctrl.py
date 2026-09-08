import numpy as np, json, os, io, zipfile, urllib.request, time, concurrent.futures as cf
F=np.load("/workspace/review_scratch/clip_flags.npz",allow_pickle=True)
fts=F["E_ts"].astype(np.int64); has=F["has"]; syms=[str(s) for s in F["symbols"]]
A=np.load("/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s42_ccal.npz",allow_pickle=True)
W=A["d30_n2_c42_W"]; ats=A["d30_n2_c42_rec"][:,0].astype(np.int64); gi={t:i for i,t in enumerate(fts)}
rng=np.random.default_rng(7); pairs=set()
aff=[p for p,t in enumerate(ats) if t in gi and (has[gi[t]]&(np.abs(W[p])>0)).any()]
def prev(ym):
    y,m=map(int,ym.split("-")); m-=1
    if m==0: y,m=y-1,12
    return "%04d-%02d"%(y,m)
for p in aff[:60]:
    t=int(ats[p]); ym=time.strftime("%Y-%m",time.gmtime(t)); w=W[p]; hit=has[gi[t]]
    cand=np.where((np.abs(w)>0)&(~hit))[0]
    for j in rng.choice(cand,size=min(8,len(cand)),replace=False):
        pairs.add((syms[j],ym)); pairs.add((syms[j],prev(ym)))
D="/workspace/review_scratch/clip_kl"
def get(p):
    s,m=p; out=os.path.join(D,"%s_%s.csv"%(s,m))
    if os.path.exists(out): return "cached"
    u="https://data.binance.vision/data/futures/um/monthly/klines/%s/4h/%s-4h-%s.zip"%(s,s,m)
    try:
        raw=urllib.request.urlopen(u,timeout=60).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z: open(out,"wb").write(z.read(z.namelist()[0]))
        return "ok"
    except Exception as e: return "MISS"
from collections import Counter
with cf.ThreadPoolExecutor(max_workers=8) as ex: r=list(ex.map(get,sorted(pairs)))
print("control pairs",len(pairs),Counter(r))
