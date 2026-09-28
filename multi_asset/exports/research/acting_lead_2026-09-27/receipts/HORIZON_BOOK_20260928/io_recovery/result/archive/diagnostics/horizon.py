"""Fixed 48h price-only EMA impulse label; no inference-time future input."""
import numpy as np

HORIZON=12
DECAY=.9
EMBARGO=60

def targets(y):
    y=np.asarray(y,dtype=float)
    if y.ndim!=2:raise ValueError('label shape')
    n,s=y.shape;out=np.full_like(y,np.nan)
    if n<HORIZON:return out
    k=n-HORIZON+1;p=np.ones((k,s));total=np.zeros_like(p);ok=np.ones_like(p,dtype=bool)
    for h in range(HORIZON):
        r=y[h:h+k];valid=np.isfinite(r)&(r>-1);ok&=valid
        safe=np.where(valid,r,0.)
        total+=(DECAY**h)*p*safe
        p*=1+safe
    out[:k]=np.where(ok,total/sum(DECAY**np.arange(HORIZON)),np.nan)
    return out

def training_rows(anchors,pair_anchor,valid,test_start):
    a=np.asarray(anchors);p=np.asarray(pair_anchor);v=np.asarray(valid)
    if a.ndim!=1 or not len(a) or not np.isfinite(a).all() or np.any(a!=np.floor(a)) or np.any(a%14400) or np.any(np.diff(a)!=14400):raise ValueError('4h axis')
    if p.ndim!=1 or v.shape!=p.shape or v.dtype!=bool or np.any(p<0) or np.any(p>=len(a)):raise ValueError('pair axis')
    if not np.issubdtype(p.dtype,np.integer):raise ValueError('pair integer index')
    return np.flatnonzero(v&(p%HORIZON==0)&(a[p]+HORIZON*14400<=test_start-EMBARGO*14400))
