"""EXPLORATORY, NOT PRE-REGISTERED (dlarch design doc §A/§T8).
Same leg arithmetic as news_legs.py L51-57 and the same y4s label as news2_layer_ladder.py,
applied to FOUR score->z maps for the SAME F10 OOF scores. No verdict is drawn here.
  hard  = production combo_target.py L28-29  rankdata/max(n-1,1)-0.5
  softX = training utility soft rank at tau=X  (news2_train_f10.py L34, hard=False)
  util  = the training utility map with wl=[1,0,0]: L1-normalise then cap*tanh(u/cap), cap=2.5/n (L35)
Control: the same four maps applied to KING's score, so any difference that is a property of the
map rather than of F10 shows up on both.
"""
import numpy as np, calendar, time, json
from scipy.stats import rankdata
W="/dev/shm/news2_2026-09-23"
leg=np.load(W+"/work/legs.npz"); a=leg["E_ts"].astype(np.int64); ready=leg["ready"]; KZraw=np.load(W+"/work/king/KING_OOF.npz")["P"]
F=np.load(W+"/work/NEWS_FEATURES.npz"); off=F["off"]; mm=F["m"].astype(np.int64)
lab=np.load("/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz",allow_pickle=True)
ya=lab["E_ts"].astype(np.int64); Y=lab["y4s"]
iy=np.searchsorted(ya,a); lab_ok=(iy<len(ya))&(ya[np.minimum(iy,len(ya)-1)]==a)
def ts(s): return calendar.timegm(time.strptime(s,"%Y-%m-%dT%H:%M:%SZ"))
SEG={"2023H2":("2023-06-30T04:00:00Z","2023-12-31T20:00:00Z"),"2024":("2024-01-01T00:00:00Z","2024-12-31T20:00:00Z"),
     "2025":("2025-01-01T00:00:00Z","2025-12-31T20:00:00Z"),"pre2026":("2023-06-30T04:00:00Z","2025-12-31T20:00:00Z")}
def hard(p):
    n=len(p); return rankdata(p)/max(n-1,1)-.5
def soft(p,tau):
    z=(p-p.mean())/(p.std()+1e-8); n=len(z)
    s=1.0/(1.0+np.exp(-(z[:,None]-z[None,:])/tau))
    return (s.sum(1)-.5)/max(n-1,1)-.5
def util(p):
    z=(p-p.mean())/(p.std()+1e-8); n=len(z)
    r=z-z.mean(); u=r/(np.abs(r).sum()+1e-8); cap=2.5/n; u=cap*np.tanh(u/cap); return u-u.mean()
def legret(z,y):
    okl=np.isfinite(y); zz=np.where(okl,np.nan_to_num(z),0.0); zz=zz-(zz[okl].mean() if okl.sum() else 0.0)
    g=np.abs(zz).sum()
    return float((zz/g*np.nan_to_num(y)).sum()*1e4) if g>1e-9 else 0.0
MAPS=[("hard",hard),("soft_tau0.30",lambda p:soft(p,.30)),("soft_tau0.10",lambda p:soft(p,.10)),("util_tanhcap",util)]
out={}
for src,Praw in [("f10_s42",np.load(W+"/work/f10_s42/F10_OOF.npz")["P"]),
                 ("f10_s2027",np.load(W+"/work/f10_s2027/F10_OOF.npz")["P"]),
                 ("king_ctrl",KZraw)]:
    acc={s:{k:[] for k,_ in MAPS} for s in SEG}
    rows=np.flatnonzero(ready&lab_ok&((a>=ts(SEG["2023H2"][0]))&(a<=ts(SEG["2025"][1]))))
    for i in rows:
        m=mm[off[i]:off[i+1]]; p=Praw[i][m]; y=Y[iy[i]][m]; ok=np.isfinite(p)
        if ok.sum()<20: continue
        segs=[s for s in SEG if (a[i]>=ts(SEG[s][0]) and a[i]<=ts(SEG[s][1]))]
        for name,fn in MAPS:
            zf=np.full(len(m),np.nan); zf[ok]=fn(p[ok])
            v=legret(zf,y)
            for s in segs: acc[s][name].append(v)
    out[src]={}
    for s in SEG:
        row={}
        for name,_ in MAPS:
            v=np.array(acc[s][name]); se=v.std(ddof=1)/np.sqrt(len(v))
            row[name]={"n":len(v),"mean":float(v.mean()),"se":float(se),"t":float(v.mean()/se)}
        out[src][s]=row
        print("%-10s %-8s " % (src,s)+"  ".join("%s=%+.4f(t%+.1f)"%(k,row[k]["mean"],row[k]["t"]) for k,_ in MAPS))
json.dump(out,open("/workspace/dlarch_2026-09-24/out/XFORM_EXPLORATORY.json","w"),indent=1)
