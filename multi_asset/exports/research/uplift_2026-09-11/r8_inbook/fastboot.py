"""Exact-equivalent vectorised UTC-day-block bootstrap.
mean/std of a concatenation of day blocks depend only on per-day (n, sum, sumsq), so the identical
resample (same rng, same day indices) can be evaluated in closed form instead of materialising indices.
Validated bitwise-to-1e-12 against the round-5 battery.py loop in VALIDATE_FASTBOOT.json."""
import numpy as np
APY=2190
def prep(x,days):
    ud,inv=np.unique(days,return_inverse=True)
    nd=len(ud)
    n=np.bincount(inv,minlength=nd).astype(float)
    s=np.bincount(inv,weights=x,minlength=nd)
    q=np.bincount(inv,weights=x*x,minlength=nd)
    return nd,n,s,q
def draws(nd,k,B):
    rng=np.random.default_rng([20260905,k])
    return rng.integers(0,nd,size=(B,nd))
def msd(idx,n,s,q):
    N=n[idx].sum(1); S=s[idx].sum(1); Q=q[idx].sum(1)
    mu=S/N; var=(Q-N*mu*mu)/(N-1.0)
    return mu,np.sqrt(np.maximum(var,0.0))
def boot_dsr_dg(a,s,days,k,B):
    nd,na,sa,qa=prep(a,days); _,_,ss,qs=prep(s,days)
    idx=draws(nd,k,B)
    ma,da=msd(idx,na,sa,qa); ms,ds=msd(idx,na,ss,qs)
    return (ms/ds-ma/da)*np.sqrt(APY), ms-ma
def boot_mean(x,days,k,B):
    nd,n,s,q=prep(x,days); idx=draws(nd,k,B)
    mu,_=msd(idx,n,s,q); return mu
def boot_sr(x,days,k,B):
    nd,n,s,q=prep(x,days); idx=draws(nd,k,B)
    mu,sd=msd(idx,n,s,q); return mu/sd*np.sqrt(APY)
