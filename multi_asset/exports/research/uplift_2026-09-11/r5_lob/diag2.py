"""Is the +-0.2%% touch band (idx 5,6) an ERA effect or a liquidity effect? And can book price be recovered?"""
import numpy as np, glob, os, time, calendar
fs=sorted(glob.glob("/workspace/lob_npz/*.npz"))
rng=np.random.default_rng([20260911,4])
pick=[fs[i] for i in rng.choice(len(fs),8,replace=False)]
for f in pick:
    d=np.load(f); L=np.asarray(d["lnot"],np.float64); t=d["ts"].astype(np.int64)
    ok=np.isfinite(L[:,5])&np.isfinite(L[:,6])
    yr=np.array([time.gmtime(int(x)).tm_year*100+time.gmtime(int(x)).tm_mon for x in t[::997]])
    ok2=ok[::997]
    import collections
    agg=collections.defaultdict(lambda:[0,0])
    for y,o in zip(yr,ok2):
        agg[y][0]+=1; agg[y][1]+=int(o)
    ks=sorted(agg)
    s="".join("%d:%.2f "%(k%10000,agg[k][1]/agg[k][0]) for k in ks[::3])
    print("%-14s touch-band finite by month(sampled): %s"%(os.path.basename(f)[:-4],s[:300]))
