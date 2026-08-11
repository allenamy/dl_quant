import numpy as np, pandas as pd, glob, os
from scipy.stats import pearsonr
HZ=600_000_000; DAY=86_400_000_000
df=pd.read_csv("exports/final_l01/y600_backtest_dataset.csv"); df=df[df.y_true_ret_bps!=0]
bt=df.timestamp_ms.values.astype(np.int64)*1000; y=df.y_true_ret_bps.values.astype(float); mo=df.month.values
days=sorted(os.path.basename(f)[:-4] for f in glob.glob("data/npz_v2arch_augms/*.npz") if os.path.basename(f)[0].isdigit())
rts=[]; rf=[]
for d in days:
    if d<"2025-08-01": continue
    z=np.load("data/npz_v2arch_augms/%s.npz"%d,allow_pickle=True); X=z["X"]
    if X.shape[-1]<98: continue
    rts.append(z["timestamps"].astype(np.int64)); rf.append(X[:,-1,88:98].astype(np.float64))
fts=np.concatenate(rts); ff=np.concatenate(rf); o=np.argsort(fts); fts=fts[o]; ff=ff[o]
idx=np.searchsorted(fts,bt,side="right")-1; feat=np.full((len(bt),10),np.nan); ok=idx>=0; feat[ok]=ff[idx[ok]]
cover=~np.isnan(feat).any(1)
print("covered rows:",int(cover.sum()),"of",len(bt),"months:",sorted(set(mo[cover])))
def cidx(t):
    oo=np.argsort(t); k=[]; last=-1e18
    for i in oo:
        if t[i]-last>=HZ: k.append(i); last=t[i]
    return np.array(k,int)
def pdc(f,yy,t):
    dk=t//DAY; rs=[]
    for dd in np.unique(dk):
        m=np.where(dk==dd)[0]; kk=cidx(t[m])
        if len(kk)>20:
            a=f[m][kk]; b=yy[m][kk]
            if a.std()>1e-9 and b.std()>1e-9:
                r=pearsonr(a,b)[0]
                if np.isfinite(r): rs.append(r)
    return np.mean(rs) if rs else np.nan
rng=np.random.default_rng(0)
def yshuf(yy,t):
    ys=yy.copy(); dk=t//DAY
    for dd in np.unique(dk):
        m=np.where(dk==dd)[0]; ys[m]=yy[m][rng.permutation(len(m))]
    return ys
NAMES=["basis_rel","ema_fast","ema_slow","basis_z","basis_vol","mom60","mom300","ar1_120","leadlag5","arb_press"]
m=cover
print("%-12s %8s %9s  verdict"%("channel","real_IC","shuf_max"))
for c in range(10):
    fv=feat[m,c]; real=pdc(fv,y[m],bt[m]); sh=[pdc(fv,yshuf(y,bt)[m],bt[m]) for _ in range(5)]; shm=np.nanmax(np.abs(sh))
    v="CLEAN" if abs(real)<=shm+0.003 else "CHECK real>>shuf"
    print("%-12s %+8.4f %9.4f  %s"%(NAMES[c],real,shm,v))
