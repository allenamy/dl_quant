"""Full archive history EMA, preserving settlement milliseconds and declared iv."""
import math
import numpy as np
from market_utils import canonical_rates

def at_anchors(events,anchors,*,half_life_ms,stale_after_ms,visibility_cutoff_ms=0,ema_floor_seconds=False):
 if type(visibility_cutoff_ms) is not int or visibility_cutoff_ms not in (0,999) or type(ema_floor_seconds) is not bool:raise ValueError('explicit funding observation contract required')
 rows=canonical_rates(events);a=np.asarray(anchors)
 if a.ndim!=1 or a.dtype.kind not in 'iu' or (np.diff(a.astype(np.int64))<0).any() or not math.isfinite(half_life_ms) or half_life_ms<=0 or stale_after_ms<0:raise ValueError('invalid funding feature clock')
 result={k:np.full(len(a),np.nan) for k in ('v0','v1','v1_known_interval_only','rate','iv')};result.update(last_settle_ms=np.full(len(a),-1,np.int64),fresh=np.zeros(len(a),bool),v1_history_complete=np.zeros(len(a),bool),history_ms=np.full(len(a),-1,np.int64),v1_preseed_untyped_events=np.zeros(len(a),np.int64),v1_postseed_untyped_events=np.zeros(len(a),np.int64))
 k=0;acc0=acc1=None;last=last1=last_clock=last1_clock=None;first=None;pre=post=0;rate=iv=None
 for i,anchor in enumerate(a):
  stamp=int(anchor)*1000
  while k<len(rows) and rows[k][0]<=stamp+visibility_cutoff_ms:
   ft,iv,rate=rows[k];k+=1;clock_ft=(ft//1000)*1000 if ema_floor_seconds else ft
   if first is None:first=ft
   alpha=1-.5**((clock_ft-last_clock)/half_life_ms) if last is not None else None
   acc0=rate if acc0 is None else acc0+alpha*(rate-acc0)
   if iv is None:
    if acc1 is None:pre+=1
    else:post+=1
   else:
    normalized=rate*(8/iv)
    aa=1-.5**((clock_ft-last1_clock)/half_life_ms) if last1 is not None else None
    acc1=normalized if acc1 is None else acc1+aa*(normalized-acc1);last1=ft;last1_clock=clock_ft
   last=ft;last_clock=clock_ft
   if not math.isfinite(acc0) or (acc1 is not None and not math.isfinite(acc1)):raise ValueError('funding EMA overflow')
  if last is None:continue
  result['v0'][i]=acc0;result['v1_known_interval_only'][i]=np.nan if acc1 is None else acc1
  result['v1'][i]=acc1 if acc1 is not None and post==0 and pre==0 and iv is not None else np.nan
  result['rate'][i]=rate;result['iv'][i]=np.nan if iv is None else iv;result['last_settle_ms'][i]=last;result['fresh'][i]=stamp-last<=stale_after_ms
  result['v1_history_complete'][i]=acc1 is not None and post==0 and pre==0
  result['history_ms'][i]=stamp-first;result['v1_preseed_untyped_events'][i]=pre;result['v1_postseed_untyped_events'][i]=post
 return result
