"""Independent arithmetic / identity check; never imports the replay or bridge."""
from pathlib import Path
import json,hashlib,sys,math
import numpy as np

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main(root):
 r=Path(root);v=json.loads((r/'RESULT.json').read_text());t=json.loads((r/'TERMINAL.json').read_text())
 assert t['rc']==0 and t['result_sha256']==digest(r/'RESULT.json')
 ncheck=0;error=0.
 def check(x,y):
  nonlocal ncheck,error
  x,y=float(x),float(y);assert math.isfinite(x) and math.isfinite(y)
  e=abs(x-y);assert e<=1e-9*max(1,abs(x),abs(y)),(x,y,e)
  ncheck+=1;error=max(error,e)
 source=Path('/dev/shm/executor_bridge_20260928_sources');c=json.loads((source/'CONTRACT.json').read_text())
 assert digest(source/'CONTRACT.json')==v['contract_sha256']
 for p,h in v['inputs'].items():assert digest(p)==h;ncheck+=1
 for p,h in v['sources'].items():assert digest(source/p)==h;ncheck+=1
 assert v['inputs']==c['inputs'] and v['sources']==c['sources']
 for seed,modes in v['paths'].items():
  zz={}
  for mode,rec in modes.items():
   assert digest(rec['path'])==rec['sha256'];z=load(rec['path']);zz[mode]=z
   assert np.all(np.diff(z['A'])==14400) and len(z['A'])==9306
   cfg=json.loads((r/f'{mode}_s{seed}'/'CONFIG.json').read_text());base=json.loads(Path(f'/dev/shm/recent_nc_cash_20260928/s{seed}/CONFIG.json').read_text())
   for k in base:
    if k not in ('pins','paths','launch','status'):assert cfg[k]==base[k];ncheck+=1
   assert {k:x for k,x in cfg['paths'].items() if k!='pod_root'}=={k:x for k,x in base['paths'].items() if k!='pod_root'}
   assert {k:x for k,x in cfg['launch'].items() if k!='max_parallel'}=={k:x for k,x in base['launch'].items() if k!='max_parallel'}
   assert cfg['launch']['max_parallel']==1
   for k,b in base['pins'].items():
    if not k.startswith('engine_'):assert cfg['pins'][k]==b;ncheck+=1
   if mode=='old_control':
    b=load(c['baselines'][seed]);assert set(b)==set(z)
    for k in b:assert b[k].dtype==z[k].dtype and b[k].shape==z[k].shape and b[k].tobytes()==z[k].tobytes();ncheck+=1
   for w,(lo,hi) in v['windows'].items():
    lo=int(np.datetime64(lo,'s').astype(np.int64));hi=int(np.datetime64(hi,'s').astype(np.int64));ix=np.where((z['A']>=lo)&(z['A']<hi))[0]
    assert z['A'][ix].tolist()==list(range(lo,hi,14400))
    a=z['navm1'][ix]/z['navm0'][ix];daily=np.array([math.prod(a[i:i+6])-1 for i in range(0,len(a),6)])
    n=z['nav5_main'];a0=(lo-int(z['nav5_t0']))//300;a1=(hi-int(z['nav5_t0']))//300;n=n[a0:a1+1]
    assert len(n)==len(ix)*48+1 and np.isfinite(n).all() and min(n)>0
    peak=np.maximum.accumulate(n);s=v['results'][seed][w][mode]
    expected={'n_days':len(daily),'compound':math.prod(1+daily)-1,'daily_mean_bps':math.fsum(daily)/len(daily)*1e4,
      'sharpe_descriptive':daily.mean()/daily.std(ddof=1)*math.sqrt(365),'maxdd_5m':min((n-peak)/peak),
      'halt_anchors':sum(z['status'][ix]==1),'hold_anchors':sum(z['status'][ix]==2),
      'stop_events':sum(z['n_stop_events'][ix]),'flatten_events':sum(z['n_flatten_events'][ix]),
      'turnover_NAV_day':math.fsum(z['turnover'][ix]/z['nav0'][ix])/len(daily),
      'cash_identity_max_usdt':max(abs(z['nav1'][ix]-z['nav0'][ix]-z['price_trade'][ix]-z['funding'][ix]+z['fee'][ix]-z['transfer'][ix]))}
    for k in ('price_trade','funding','fee'):expected[k+'_bps_day']=math.fsum(z[k][ix]/z['nav0'][ix])/len(daily)*1e4
    assert set(expected)==set(s)
    for k,x in expected.items():check(x,s[k])
  assert np.array_equal(zz['old_control']['A'],zz['current_pure']['A'])
  for w,s in v['results'][seed].items():
   for k,d in s['delta'].items():check(d,s['current_pure'][k]-s['old_control'][k])
  rows=[json.loads(x) for x in (r/f'current_pure_s{seed}/DECISION_TRACE.jsonl').read_text().splitlines()]
  for w,(lo,hi) in v['windows'].items():
   lo=int(np.datetime64(lo,'s').astype(np.int64));hi=int(np.datetime64(hi,'s').astype(np.int64));rows_w=[x for x in rows if lo<=x['anchor']<hi];s=v['traces'][seed][w]
   assert rows_w and len({x['anchor'] for x in rows_w})==len(rows_w)
   check(len(rows_w),s['trade_decisions']);check(sum(len(x['dust_popped']) for x in rows_w),s['dust_name_decisions'])
   check(sum(bool(x['dust_popped']) for x in rows_w),s['dust_decisions'])
   check(sum(len(x['caller_defaulted_floor_names']) for x in rows_w),s['caller_defaulted_floor_name_decisions'])
   check(sum(x['same_state_target_l1_delta']>1e-8 for x in rows_w),s['same_state_nonzero_target_delta_decisions'])
   for j,k in enumerate(('old_target_net','new_target_net')):check(math.fsum(x[k]/x['sizing_gross'] for x in rows_w)/len(rows_w),s['mean_net_before_and_after'][j])
   check(max(x['same_state_target_l1_delta']/x['sizing_gross'] for x in rows_w),s['target_l1_delta_max_over_gross'])
 rec={'status':'INDEPENDENT_ARITHMETIC_IDENTITY_PASS','checks':ncheck,'max_abs_error':error,'result_sha256':digest(r/'RESULT.json'),'verifier_sha256':digest(__file__),'scope':'NPZ controls, configuration identity, cash/day arithmetic and trace aggregates; not an independent engine or refit'}
 (r/'INDEPENDENT.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec))

if __name__=='__main__':main(sys.argv[1])
