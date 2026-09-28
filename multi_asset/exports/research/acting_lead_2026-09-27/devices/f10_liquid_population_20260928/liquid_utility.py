"""Same NC utility math, restricted to the known liquidity population.

Ranks still use all scoring members. This is one population ablation, NOT the
full production chain, and is not licensed by earlier failed T3 results.
"""
import numpy as np
import torch

def mask_from_qv(q):
    q=np.asarray(q)
    if q.ndim!=1:raise ValueError('qv must be current-anchor one-dimensional')
    sel=np.isfinite(q)&(q>=250000.)
    if sel.sum()<2:raise ValueError('no measurable selected population')
    return sel

def utility(score,z24,zfd,wl,tau,sel,n_selected,hard=False):
    if sel.shape!=score.shape or sel.dtype!=torch.bool or n_selected<2:raise ValueError('selected population schema')
    z=(score-score.mean())/(score.std()+1e-8);n=len(z)
    rank=torch.argsort(torch.argsort(z)).float()/max(n-1,1)-.5 if hard else (torch.sigmoid((z[:,None]-z[None,:])/tau).sum(1)-.5)/max(n-1,1)-.5
    r=wl[0]*rank+wl[1]*z24+wl[2]*zfd
    r=torch.where(sel,r,0.);r=torch.where(sel,r-r[sel].mean(),0.)
    u=r/(r.abs().sum()+1e-8);cap=2.5/n_selected;u=cap*torch.tanh(u/cap)
    return torch.where(sel,u-u[sel].mean(),0.)
