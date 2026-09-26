import numpy as np, hashlib
def sha(p):
    h=hashlib.sha256(); f=open(p,'rb')
    for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
FR="/dev/shm/news_2026-09-23/work/fund_replay.npz"; FS="/dev/shm/nc_2026-09-23/work/fund_state.npz"; AX="/dev/shm/nc_2026-09-23/work/axes.npz"
LG="/dev/shm/news_2026-09-23/work/legs.npz"
print("sha", sha(FR)[:8], sha(FS)[:8], sha(LG)[:8])
r=np.load(FR); f=np.load(FS); ax=np.load(AX, allow_pickle=True); lg=np.load(LG)
A=r["anchors"]; assert np.array_equal(A, f["anchors"]) and np.array_equal(A, lg["E_ts"])
syms=[str(s) for s in r["symbols"]]; asyms=[str(s) for s in ax["symbols"]]; cols=f["cols"].astype(int)
assert np.array_equal(ax["crypto_cols"].astype(int), cols)
jmap=np.array([syms.index(asyms[c]) if asyms[c] in syms else -1 for c in cols]); print("cols", len(cols), "unmapped", int((jmap<0).sum()))
kidx=f["kidx"]; off=f["ev_off"]; ema=f["ema"]
n=len(A); clean=np.full((n,len(syms)),np.nan)
for ci,j in enumerate(jmap):
    if j<0: continue
    k=kidx[:,ci]; ok=k>=0
    clean[ok,j]=ema[off[ci]+k[ok]]
old=r["ema_acc"]
mem=np.isfinite(lg["ZFD"])     # member cells where the fund leg z exists in NEW_S legs
for name,m in (("member_cells",mem),("all_cells",np.ones_like(mem))):
    a=old[m]; b=clean[m]
    both=np.isfinite(a)&np.isfinite(b); d=np.abs(a-b)[both]
    print(name, "n", int(m.sum()), "both_finite", int(both.sum()), "old_only", int((np.isfinite(a)&~np.isfinite(b)).sum()), "clean_only", int((~np.isfinite(a)&np.isfinite(b)).sum()))
    edges=[0,1e-15,1e-12,1e-9,1e-7,1e-6,1e-5,1e-4,np.inf]
    h=np.histogram(d,bins=edges)[0]; print("  |diff| buckets", dict(zip([f"<{e:g}" for e in edges[1:]], h.tolist())))
    if name=="member_cells":
        yrs=(A[:,None]*np.ones((1,len(syms)),int))[m][both]
        big=d>1e-9
        import collections, time
        print("  >1e-9 by year", dict(collections.Counter(time.gmtime(int(t)).tm_year for t in yrs[big])))
        print("  median |ema| member", float(np.nanmedian(np.abs(b[both]))))
# per-year counts at two material thresholds + relative size, and anchors touched (member cells)
import collections, time, json
a=old[mem]; b=clean[mem]; d=np.abs(a-b); yrs=(A[:,None]*np.ones((1,len(syms)),int))[mem]
out={}
for thr in (1e-7,1e-5):
    big=d>thr; out[f">{thr:g}"]={"cells":int(big.sum()),"by_year":dict(collections.Counter(time.gmtime(int(t)).tm_year for t in yrs[big])),
        "anchors_touched":int(len(np.unique(yrs[big])))}
rel=d/np.maximum(np.abs(b),1e-12); out["rel_gt_10pct_cells"]=int((rel>0.1).sum()); out["sign_flips"]=int(((np.sign(a)!=np.sign(b))&(d>1e-9)).sum())
print(json.dumps(out))
