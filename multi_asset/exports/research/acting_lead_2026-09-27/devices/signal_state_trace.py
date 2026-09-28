"""Additive attribution conditional on the full actual nonlinear path, not deletion effects."""
import numpy as np


def rank_scores(x):
 x=np.asarray(x,float);out=np.full(x.shape,np.nan);valid=np.flatnonzero(np.isfinite(x));values=x[valid]
 order=np.argsort(values,kind='stable');i=0
 while i<len(order):
  j=i+1
  while j<len(order) and values[order[j]]==values[order[i]]:j+=1
  out[valid[order[i:j]]]=((i+1+j)/2)/max(len(order)-1,1)-.5;i=j
 return out


def trim_parts(parts,rn8):
 parts=np.asarray(parts,float);rn8=np.asarray(rn8,float)
 if parts.ndim!=2 or rn8.shape!=(parts.shape[1],):raise ValueError('trim_axis')
 if not np.isfinite(parts).all():raise ValueError('trim_nonfinite')
 mask=(parts.sum(0)<0)&np.isfinite(rn8)&(rn8<=-.001)
 return np.where(mask[None,:],0.,parts)


def trace_chain(parts,previous,members,qv,legal,params):
 c=np.asarray(parts,float);h=np.asarray(previous,float);m=np.asarray(members);q=np.asarray(qv,float);legal=np.asarray(legal,bool)
 if c.ndim!=2 or h.ndim!=2 or c.shape[0]!=h.shape[0] or m.shape!=(c.shape[1],) or m.dtype.kind not in 'iu' or len(set(map(int,m)))!=len(m) or np.any(m<0) or np.any(m>=h.shape[1]) or q.shape!=m.shape or legal.shape!=(h.shape[1],):raise ValueError('axis')
 if not np.isfinite(c).all() or not np.isfinite(h).all():raise ValueError('nonfinite')
 if not all(np.isfinite(params[k]) for k in ('cap_mult','alpha','band','qv4h_min')) or not 0<params['alpha']<=1 or params['cap_mult']<=0 or params['band']<0:raise ValueError('params')
 sel=np.isfinite(q)&(q>=params['qv4h_min']);w=np.where(sel[None,:],c,0.)
 if sel.any():w=np.where(sel[None,:],w-w[:,sel].mean(1)[:,None],w)
 combined=w.sum(0);g=np.abs(combined).sum()
 if g<1e-9:raise ValueError('degenerate')
 w=w/g;total=combined/g;cap=params['cap_mult']/max(int(sel.sum()),1)
 factor=np.ones(len(total));nz=np.abs(total)>0;factor[nz]=np.minimum(1.,cap/np.abs(total[nz]));w*=factor[None,:]
 g2=np.abs(np.clip(total,-cap,cap)).sum()
 if g2>1e-9:w/=g2
 target=np.zeros_like(h);target[:,m]=w
 updated=h+params['alpha']*(target-h)
 frozen=np.abs(updated.sum(0)-h.sum(0))<params['band'];updated=np.where(frozen[None,:],h,updated)
 keep=np.zeros(h.shape[1],bool);keep[m[sel]]=True;keep&=legal
 leave=(~keep)&(np.abs(updated.sum(0))>1e-12)
 return np.where(leave[None,:],0.,updated)
