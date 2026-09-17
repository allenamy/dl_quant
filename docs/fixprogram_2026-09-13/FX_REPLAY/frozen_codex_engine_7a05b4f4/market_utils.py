"""Raw market fact contracts. Interval coverage is distinct from rate cash."""
import math
import numpy as np

def canonical_rates(rows):
 facts={}
 for stamp,iv,rate in rows:
  if isinstance(stamp,(bool,np.bool_)) or not isinstance(stamp,(int,np.integer)) or stamp<0:raise ValueError('invalid rate event milliseconds')
  if not math.isfinite(rate) or (iv is not None and (not math.isfinite(iv) or iv<=0)):raise ValueError('invalid rate/interval')
  value=(None if iv is None else float(iv),float(rate))
  if stamp in facts:
   old=facts[stamp]
   if old[1]!=value[1] or (old[0] is not None and value[0] is not None and old[0]!=value[0]):raise ValueError('conflicting rate event')
   if old[0] is None:facts[int(stamp)]=value
  else:facts[int(stamp)]=value
 return [(t,*v) for t,v in sorted(facts.items())]

def interval_coverage(events,starts_ms,ends_ms,*,tolerance_ms):
 """Union of declared preceding settlement intervals, without filling missing cycles.

 The last declared interval projects only to immediately before its next due
 time. This is an explicit unchanged-schedule proxy; exact coverage still
 requires archive completeness and exchange schedule evidence.
 """
 a=np.asarray(starts_ms,np.int64);b=np.asarray(ends_ms,np.int64)
 if a.shape!=b.shape or (b<a).any() or not isinstance(tolerance_ms,int) or tolerance_ms<0:raise ValueError('invalid coverage intervals')
 rows=canonical_rates(events);ranges=[]
 for stamp,iv,rate in rows:
  if iv is not None:ranges.append((stamp-int(iv*3600000),stamp))
 # A later API-only event must not invalidate a previously declared interval's
 # not-yet-due span. Projection stops before that unknown event or next due.
 typed=[i for i,r in enumerate(rows) if r[1] is not None]
 if typed:
  k=typed[-1];stamp,iv,_=rows[k];end=stamp+int(iv*3600000)-1
  if k+1<len(rows):end=min(end,rows[k+1][0]-1)
  ranges.append((stamp,end))
 merged=[]
 for lo,hi in sorted(ranges):
  if merged and lo<=merged[-1][1]+tolerance_ms:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
  else:merged.append((lo,hi))
 out=np.zeros(a.shape,bool)
 for lo,hi in merged:out|=(a>=lo-tolerance_ms)&(b<=hi)
 return out

def asof_prices(bar_ts,close,event_ms,assets,*,max_age_ms):
 t=np.asarray(bar_ts);p=np.asarray(close);e=np.asarray(event_ms);s=np.asarray(assets)
 if t.ndim!=1 or t.dtype.kind not in 'iu' or (np.diff(t.astype(np.int64))<=0).any() or p.ndim!=2 or len(p)!=len(t) or e.ndim!=1 or s.shape!=e.shape or e.dtype.kind not in 'iu' or s.dtype.kind not in 'iu' or (s<0).any() or (s>=p.shape[1]).any():raise ValueError('price lookup axes invalid')
 ix=np.searchsorted(t.astype(np.int64)*1000,e,side='right')-1;out=np.full(len(e),np.nan);good=ix>=0
 if good.any():
  k=np.flatnonzero(good);age=e[k]-t[ix[k]]*1000;v=p[ix[k],s[k]].astype(float);okay=(age<=max_age_ms)&np.isfinite(v)&(v>0);out[k[okay]]=v[okay]
 return out
