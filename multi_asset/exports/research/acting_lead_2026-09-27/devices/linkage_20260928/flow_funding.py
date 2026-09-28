"""Causal flow/funding adapter. Existing D10 convention, never re-normalize EMA.

Flow is a mean taker-buy quote-volume fraction, NOT net capital inflow.
Volume anomaly is a difference of mean log1p quote volume, NOT dollar turnover.
"""
import numpy as np
import warnings

OWN_NAMES=('raw_settlement_rate','ema8','fund8','negative_fund8','own_residual4h','own_residual24h','buy_fraction_delta','log_volume_anomaly')
NEW_NAMES=('peer_buy_fraction_minus_own','peer_log_volume_minus_own','negative_fund8_x_peer_residual4h')

def past_mad(ts,values,day,*,window=360,min_obs=240):
 t=np.asarray(ts);x=np.asarray(values,float)
 if t.ndim!=1 or x.ndim!=2 or len(t)!=len(x) or np.any(np.diff(t)!=14400) or day%86400:raise ValueError('MAD axis')
 z=x[(t>=day-window*14400)&(t<day)]
 if np.isinf(z).any():raise ValueError('MAD infinity')
 with warnings.catch_warnings():
  warnings.simplefilter('ignore',RuntimeWarning);mu=np.nanmedian(z,axis=0);sc=1.4826*np.nanmedian(np.abs(z-mu),axis=0)
 ok=(np.isfinite(z).sum(0)>=min_obs)&(sc>1e-12);return np.where(ok,mu,np.nan),np.where(ok,sc,np.nan)

def window_mean(x,end,n):
 x=np.asarray(x,dtype=float);e=np.asarray(end)
 if x.ndim!=2 or e.ndim!=1 or e.dtype.kind not in 'iu' or type(n)is not int or n<1 or np.any(e>=len(x)):raise ValueError('rolling schema')
 finite=np.isfinite(x);cs=np.vstack((np.zeros(x.shape[1]),np.cumsum(np.where(finite,x,0),axis=0)))
 nn=np.vstack((np.zeros(x.shape[1],np.int64),np.cumsum(finite,axis=0)))
 out=np.full((len(e),x.shape[1]),np.nan);sel=e>=n-1;hi=e[sel]+1;lo=hi-n
 out[sel]=np.where(nn[hi]-nn[lo]==n,(cs[hi]-cs[lo])/n,np.nan);return out

def fund_asof(anchor,ft,rate,iv,ema):
 a,t,r,v,e=[np.asarray(z) for z in (anchor,ft,rate,iv,ema)]
 if not (a.shape==t.shape==r.shape==v.shape==e.shape) or a.dtype.kind not in 'iu' or t.dtype.kind not in 'iu':raise ValueError('fund schema')
 if np.any(t>a):raise ValueError('future funding')
 ok=(t>=0)&(a-t<=43200)&np.isfinite(r)&np.isfinite(v)&(v>0)&np.isfinite(e)
 out=np.full(a.shape+(3,),np.nan)
 out[...,0]=np.divide(r*8,v,out=np.full(r.shape,np.nan),where=ok)
 out[...,1]=np.where(ok,e,np.nan);out[...,2]=np.where(ok,r,np.nan)
 return out

def baseline_inputs(old78,own,price):
 old=np.asarray(old78);o=np.asarray(own);p=np.asarray(price)
 if old.ndim!=2 or old.shape[1]!=78 or o.shape!=(len(old),8) or p.shape!=(len(old),4):raise ValueError('baseline schema')
 if not np.isfinite(old[:,:76]).all() or np.isinf(o).any() or np.isinf(p).any():raise ValueError('baseline nonfinite')
 # Drop NC funding columns completely. Missing new controls get explicit flags;
 # a real zero and unknown are distinguishable. Normalization is training-only.
 return np.c_[old[:,:76],np.where(np.isfinite(o),o,0),np.isfinite(o).astype(float),np.where(np.isfinite(p),p,0),np.isfinite(p).astype(float)]

def peer_flows(peers,active,flow,volume,min_peers=8):
 ps=np.asarray(peers);a=np.asarray(active);f=np.asarray(flow);v=np.asarray(volume);n=len(a)
 if ps.ndim!=2 or ps.shape[0]!=n or a.shape!=(n,) or a.dtype.kind!='b' or ps.dtype.kind not in 'iu' or f.shape!=(n,) or v.shape!=(n,):raise ValueError('peer schema')
 if np.any(ps>=n) or np.any(ps<-1) or np.any(ps==np.arange(n)[:,None]):raise ValueError('invalid peer identity')
 out=np.full((n,2),np.nan)
 for i in np.flatnonzero(a):
  ix=ps[i];ix=ix[ix>=0];ix=ix[a[ix]]
  for j,x in enumerate((f,v)):
   use=ix[np.isfinite(x[ix])]
   if len(use)>=min_peers and np.isfinite(x[i]):out[i,j]=x[use].mean()-x[i]
 return out
