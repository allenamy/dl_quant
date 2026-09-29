"""Conditional cash input population, raw target and accounting contracts."""
import numpy as np

def books(rows,states,initial,anchors):
 a=np.asarray(anchors);n=len(initial['kc']);by={int(r['anchor']):r for r in rows}
 if len(a)<2 or len(by)!=len(rows) or np.any(a%14400) or np.any(np.diff(a)!=14400) or any(int(t) not in by for t in a[1:]):raise ValueError('book_clock_population')
 if np.asarray(initial['fc']).shape!=(n,):raise ValueError('initial_shape')
 first=.55*np.asarray(initial['kc'])+.45*np.asarray(initial['fc']);out={}
 if not np.isfinite(first).all():raise ValueError('initial_nonfinite')
 for arm in ('B','S'):
  W=np.zeros((len(a),n));W[0]=first;fresh=np.zeros(len(a),bool);fresh[0]=True
  for i,t in enumerate(a[1:],1):
   fresh[i]=by[int(t)]['arms'][arm]['accepted']
   if type(fresh[i].item())!=bool:raise ValueError('fresh')
   raw=.55*states[f'{arm}_kc_{int(t)}']+.45*states[f'{arm}_fc_{int(t)}']
   if raw.shape!=(n,) or not np.isfinite(raw).all():raise ValueError('state_unknown')
   if fresh[i]:W[i]=np.where(np.abs(raw)>1e-9,raw,0.)
  out[arm]=(W,fresh)
 return out

def cash_metrics(path,start,end):
 a=path['A'];ix=np.flatnonzero((a>=start)&(a<end))
 if not np.array_equal(a[ix],np.arange(start,end,14400)) or len(ix)==0:raise ValueError('window_population')
 keys=('nav0','nav1','navm0','navm1','price_trade','funding','fee','transfer','turnover','unk_held','unk_notional','n_stop_events','n_flatten_events')
 if any(not np.isfinite(path[k][ix]).all() for k in keys):raise ValueError('nonfinite')
 ident=(path['nav1']-path['nav0'])-(path['price_trade']+path['funding']-path['fee']+path['transfer'])
 if np.abs(ident[ix]).max()>1e-6 or np.any(path['nav0'][ix]<=0) or np.any(path['navm0'][ix]<=0):raise ValueError('cash_identity')
 t0=int(path['nav5_t0']);j0=(start-t0)//300;j1=(end-t0)//300;n=path['nav5_main'][j0:j1+1]
 if start<t0 or start%300 or end%300 or len(n)!=(end-start)//300+1 or not np.isfinite(n).all() or (n<=0).any():raise ValueError('NAV_coverage')
 compounded=float(np.prod(path['navm1'][ix]/path['navm0'][ix])-1.)
 if abs(compounded-(n[-1]/n[0]-1))>1e-10:raise ValueError('NAV_endpoint')
 out={'compound':compounded,'maxdd_5m':float((n/np.maximum.accumulate(n)-1).min()),'n_windows':len(ix),'nav_start':float(n[0]),'nav_end':float(n[-1]),'cash_identity_max':float(np.abs(ident[ix]).max()),'priced_complete':bool(path['unk_held'][ix].sum()==0 and path['unk_notional'][ix].sum()==0),'halt_anchors':int((path['status'][ix]==1).sum()),'hold_anchors':int((path['status'][ix]==2).sum())}
 for k in ('price_trade','funding','fee','turnover','unk_held','unk_notional','n_stop_events','n_flatten_events'):out[k]=float(path[k][ix].sum())
 return out
