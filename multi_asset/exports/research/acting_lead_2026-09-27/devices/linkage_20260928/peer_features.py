"""Eight causal peer features. No labels, model fitting, portfolio or live writes.

All returns supplied here are completed-bar log returns with real observability.
Funding inputs are comparable 8h-rate units, not raw mixed-interval settlements.
"""
import numpy as np
NAMES=('peer_residual4h','peer_residual24h','own_minus_peer24h','peer_up_breadth',
       'peer_flow_minus_own','peer_volume_minus_own','negative_fund_x_peer4h','fund_now_minus_ema')

def numeric(x,shape=None):
    a=np.asarray(x)
    if a.dtype.kind not in 'ifu' or (shape is not None and a.shape!=shape):raise ValueError('numeric shape/type')
    return a.astype(np.float64,copy=False)

def clock(t):
    if isinstance(t,(bool,np.bool_)) or not isinstance(t,(int,np.integer)):raise ValueError('integer clock')
    if t%14400:raise ValueError('4h clock')
    return int(t)

def loo_market(r,valid,min_market):
    z=np.where(valid,r,0.)
    count=valid.sum(axis=-1,keepdims=True)-valid
    total=z.sum(axis=-1,keepdims=True)-z
    return np.divide(total,count,out=np.full_like(r,np.nan),where=count>=min_market)

def fit_graph(ts,returns,legal,symbols,graph_ts,*,window=360,min_obs=240,k=16,min_peers=8,min_market=20):
    t=numeric(ts);r=numeric(returns);l=np.asarray(legal);sy=np.asarray(symbols)
    A=clock(graph_ts)
    if A%86400 or t.ndim!=1 or r.ndim!=2 or len(t)!=len(r) or l.shape!=r.shape or l.dtype.kind!='b':raise ValueError('graph schema/day')
    if not np.isfinite(t).all() or np.any(t!=np.floor(t)) or np.any(t%14400) or np.any(np.diff(t)!=14400):raise ValueError('time axis gap/duplicate')
    if sy.shape!=(r.shape[1],) or sy.dtype.kind not in 'US' or len(set(map(str,sy)))!=len(sy):raise ValueError('symbol identity')
    if not all(type(v) is int and v>0 for v in [window,min_obs,k,min_peers,min_market]) or min_peers>k:raise ValueError('graph parameters')
    use=(t>=A-window*14400)&(t<A);rp=np.where(l[use],r[use],np.nan)
    if len(rp)<min_obs or not len(rp) or t[use][-1]!=A-14400:raise ValueError('history coverage')
    if np.isinf(rp).any():raise ValueError('infinite historical return')
    valid=np.isfinite(rp);market=loo_market(rp,valid,min_market);ok=valid&np.isfinite(market);count=ok.sum(0)
    den=np.maximum(count,1);sx=np.where(ok,rp,0.).sum(0);sm=np.where(ok,market,0.).sum(0)
    cov=np.where(ok,rp*market,0.).sum(0)-sx*sm/den
    var=np.where(ok,market**2,0.).sum(0)-sm**2/den
    beta=np.divide(cov,var,out=np.full(r.shape[1],np.nan),where=(count>=min_obs)&(var>1e-16))
    e=np.where(ok,rp-market*beta,np.nan);m=np.isfinite(e);z=np.where(m,e,0.);mf=m.astype(float)
    counts=mf.T@mf;sums=z.T@mf;cross=z.T@z;sq=(z*z).T@mf;nn=np.maximum(counts,1.)
    cv=cross-sums*sums.T/nn;v=sq-sums*sums/nn
    with np.errstate(invalid='ignore',divide='ignore'):corr=cv/np.sqrt(np.maximum(v,0)*np.maximum(v.T,0))
    corr[(counts<min_obs)|~np.isfinite(corr)]=np.nan;np.fill_diagonal(corr,np.nan)
    ne=m.sum(0);mean=z.sum(0)/np.maximum(ne,1);variance=(z*z).sum(0)/np.maximum(ne,1)-mean**2
    scale=np.sqrt(np.maximum(variance,0));eligible=l[use][-1]&np.isfinite(beta)&(scale>1e-12)&(ne>=min_obs)
    peers=np.full((len(sy),k),-1,np.int64)
    for i in np.flatnonzero(eligible):
        js=np.flatnonzero(eligible&np.isfinite(corr[i])&(corr[i]>0));js=np.array(sorted(js,key=lambda j:(-corr[i,j],str(sy[j]))),dtype=int)[:k]
        if len(js)>=min_peers:peers[i,:len(js)]=js
    return {'symbols':sy.copy(),'graph_ts':A,'last_history_ts':int(t[use][-1]),'beta':beta,'scale':scale,'peers':peers,'counts':counts,'eligible':eligible,'min_peers':min_peers,'min_market':min_market,'window':window}

def transform(graph,anchor_ts,*,r4,r24,flow_delta,qv_anomaly,fund8,ema8,active):
    A=clock(anchor_ts);G=graph;day=G['graph_ts']
    if A<day or A>=day+86400 or G['last_history_ts']>=day:raise ValueError('graph time')
    n=len(G['symbols']);active=np.asarray(active)
    if active.shape!=(n,) or active.dtype.kind!='b':raise ValueError('active population')
    values=[numeric(x,(n,)) for x in [r4,r24,flow_delta,qv_anomaly,fund8,ema8]]
    if any(np.isinf(x).any() for x in values):raise ValueError('infinite feature input')
    r4,r24,flow,qv,fund,ema=values
    m4=loo_market(r4,np.isfinite(r4)&active,G['min_market']);m24=loo_market(r24,np.isfinite(r24)&active,G['min_market'])
    e4=r4-G['beta']*m4;e24=r24-G['beta']*m24
    X=np.full((n,8),np.nan);pc=np.zeros(n,int);coverage=np.zeros((n,5),int)
    for i in np.flatnonzero(active&G['eligible']):
        ps=G['peers'][i];ps=ps[ps>=0];ps=ps[active[ps]];pc[i]=len(ps)
        def avg(x,c):
            vals=x[ps];good=np.isfinite(vals);coverage[i,c]=int(good.sum())
            return float(vals[good].mean()) if good.sum()>=G['min_peers'] else np.nan
        p4=avg(e4,0);p24=avg(e24,1)
        X[i,0]=p4/G['scale'][i];X[i,1]=p24/(G['scale'][i]*np.sqrt(6));X[i,2]=(e24[i]-p24)/(G['scale'][i]*np.sqrt(6))
        breadth=np.where(np.isfinite(e4),(e4>0).astype(float),np.nan);X[i,3]=avg(breadth,2)
        X[i,4]=avg(flow,3)-flow[i];X[i,5]=avg(qv,4)-qv[i]
        X[i,6]=max(-fund[i],0)*X[i,0] if np.isfinite(fund[i]) else np.nan
        X[i,7]=fund[i]-ema[i]
    return {'X':X,'peer_count':pc,'feature_peer_coverage':coverage,'names':NAMES,'graph_ts':day,'anchor_ts':A}
