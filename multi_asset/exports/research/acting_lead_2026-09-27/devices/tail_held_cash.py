"""Frozen diagnostic: risk partitions of an already simulated book, not a policy."""
import numpy as np
from scipy.stats import rankdata

def observed_labels(labels,eligible,seed_index):
    labels=np.asarray(labels);eligible=np.asarray(eligible)
    if labels.ndim!=2 or labels.shape[1]!=2 or eligible.shape!=labels.shape or eligible.dtype!=bool or seed_index not in (0,1):
        raise ValueError('seed eligibility schema')
    return np.where(eligible[:,seed_index,None],labels,np.nan)

def bins(p):
    p=np.asarray(p,dtype=float)
    if p.ndim!=1 or np.isinf(p).any() or ((p<0)|(p>1)).any():
        raise ValueError('invalid probability')
    ok=np.isfinite(p); out=np.full(p.shape,5,dtype=np.int8)
    if ok.any():out[ok]=np.floor(5*(rankdata(p[ok],method='average')-.5)/ok.sum()).astype(np.int8)
    return out

def align(source,wanted):
    for a in (source,wanted):
        a=np.asarray(a)
        if a.ndim!=1 or not np.isfinite(a).all() or (a!=np.floor(a)).any() or (a%14400).any() or (np.diff(a)<=0).any():
            raise ValueError('axis invalid')
    j=np.searchsorted(source,wanted)
    if (j>=len(source)).any() or not np.array_equal(np.asarray(source)[j],wanted):
        raise ValueError('axis missing')
    return j

def group_cash(groups,mv,price,fund,fee,nav):
    groups=np.asarray(groups); mv,price,fund,fee,nav=map(np.asarray,(mv,price,fund,fee,nav))
    if groups.ndim!=2 or any(x.shape!=groups.shape for x in (mv,price,fund,fee)) or nav.shape!=(groups.shape[0],):
        raise ValueError('shape')
    if not all(np.isfinite(x).all() for x in (groups,mv,price,fund,fee,nav)) or (nav<=0).any():
        raise ValueError('nonfinite or NAV')
    if (groups!=np.floor(groups)).any() or ((groups<0)|(groups>=18)).any():raise ValueError('group')
    out=[]
    for g in range(18):
        m=groups==g; gross=float(np.abs(mv[m]).sum()); pa=np.where(m,price,0).sum(1)
        fa=np.where(m,fund,0).sum(1); ca=np.where(m,fee,0).sum(1)
        pb=pa/nav*1e4; nb=(pa+fa-ca)/nav*1e4
        out.append(dict(group=g,positions=int((m&(mv!=0)).sum()),cells=int(m.sum()),gross_usd_sum=gross,
            price_usd=float(pa.sum()),fund_usd=float(fa.sum()),fee_usd=float(ca.sum()),net_usd=float((pa+fa-ca).sum()),
            price_gain_usd=float(np.maximum(price[m],0).sum()),price_loss_usd=float(-np.minimum(price[m],0).sum()),
            price_per_initial_gross_bps=float(pa.sum()/gross*1e4) if gross else None,
            loss_per_initial_gross_bps=float(-np.minimum(price[m],0).sum()/gross*1e4) if gross else None,
            price_anchor_bps=pb.tolist(),net_anchor_bps=nb.tolist(),
            price_daily_contribution_bps=pb.reshape(-1,6).sum(1).tolist() if len(nav)%6==0 else None,
            net_daily_contribution_bps=nb.reshape(-1,6).sum(1).tolist() if len(nav)%6==0 else None))
    return out
