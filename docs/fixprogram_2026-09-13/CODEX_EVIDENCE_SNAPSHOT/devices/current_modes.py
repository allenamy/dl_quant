"""Select only the approved E55 no-halt versus E55/E60 halt event domain."""
from current_plan import need,MODES
PRIORITY={'DAY':0,'FUNDING':1,'CLOSE':2,'OPEN':3,'NAV_SNAPSHOT':4,'PLAN':5,'ATTEMPT':6,'READBACK':7,'RISK_ATTEMPT':8}
def identity(mode):
 need(mode in MODES,'fixed explicit economic mode')
 return dict(schema='CURRENT_CASH_EXECUTION_MODE_1',mode=mode,pns_readback_offset_ms=3300000,ordinary_attempt_offset_ms=1500000,risk_attempt_offset_ms=3600000 if mode=='ECONOMIC_HALT' else None,manual_resume_events=[],sigma_external_events=[],sigma_multiplier=1.,economic_halt_enabled=mode=='ECONOMIC_HALT')
def mode_frames(mode,augmented):
 """Receive source-admitted restricted augmentation; do not retime any event.

 The no-halt comparator removes only RISK_ATTEMPT. Both modes keep every
 observed funding event and the exact same E55 PNS observation. The caller
 still validates full 3648/609 population and every source identity.
 """
 identity(mode);nav=set();readback=set();risk=set();previous=None
 for e in augmented:
  kind=e.get('type');ts=e.get('ts_ms');need(kind in PRIORITY and type(ts)is int,'known event type and exact integer clock')
  k=(ts,PRIORITY[kind]);need(previous is None or previous<=k,'source-augmented events ordered');previous=k
  if kind in ('NAV_SNAPSHOT','READBACK','RISK_ATTEMPT'):
   offset={'NAV_SNAPSHOT':1200000,'READBACK':3300000,'RISK_ATTEMPT':3600000}[kind];anchor=ts-offset
   need(anchor%14400000==0,'fixed N20/E55/E60 clock')
   seen={'NAV_SNAPSHOT':nav,'READBACK':readback,'RISK_ATTEMPT':risk}[kind];need(anchor not in seen,'one event at each fixed mode clock');seen.add(anchor)
   if kind=='READBACK':need(type(e.get('price_asof_ms'))is int and e['price_asof_ms']==ts,'exact E55 PNS observation')
   if kind=='RISK_ATTEMPT':need(type(e.get('anchor_ms'))is int and e['anchor_ms']==anchor,'exact E60 risk anchor identity')
  if kind!='RISK_ATTEMPT' or mode=='ECONOMIC_HALT':yield e
 need(nav==readback==risk,'no missing N20/E55/E60 source frames')
