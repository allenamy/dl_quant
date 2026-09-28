"""Four fixed paths: exact old controls first, then current pure dust rule.

Keeps the old immutable mirror manifest and all original input gates. The
additional post-load pure-function replacement is separately pinned and named.
No production imports, no API, no GPU, no candidate selection.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import sys,json,time,subprocess,signal,shutil,traceback,copy,hashlib
import numpy as np
from executor_bridge import sha,patch_driver

PY='/workspace/venv/bin/python'
BASE=Path('/dev/shm/recent_nc_cash_20260928')
WINDOWS={'recent_H2':['2026-07-01','2026-09-27'],'september':['2026-09-01','2026-09-27'],'recent8':['2026-09-19','2026-09-27'],
         '2026H1':['2026-01-01','2026-07-01'],'2025':['2025-01-01','2026-01-01'],'2024':['2024-01-01','2025-01-01'],'2023H2':['2023-07-01','2024-01-01']}

def read(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def exact(a,b):
 if set(a)!=set(b):raise ValueError('control field population')
 for k,v in a.items():
  if v.shape!=b[k].shape or v.dtype!=b[k].dtype or v.tobytes()!=b[k].tobytes():raise ValueError('control mismatch '+k)
 return {'fields':len(a),'anchors':len(a['A']),'bitwise_equal':True}

def summary(z,lo,hi):
 ts=lambda s:int(np.datetime64(s,'s').astype('int64'));lo,hi=ts(lo),ts(hi);a=z['A'];ix=np.flatnonzero((a>=lo)&(a<hi))
 assert np.array_equal(a[ix],np.arange(lo,hi,14400));r=z['navm1'][ix]/z['navm0'][ix]-1;days=np.expm1(np.log1p(r.reshape(-1,6)).sum(1))
 n=z['nav5_main'][(lo-int(z['nav5_t0']))//300:(hi-int(z['nav5_t0']))//300+1]
 assert len(n)==len(ix)*48+1 and np.isfinite(n).all() and (n>0).all()
 return {'n_days':len(days),'compound':float(np.expm1(np.log1p(days).sum())),'daily_mean_bps':float(days.mean()*1e4),
         'sharpe_descriptive':float(days.mean()/days.std(ddof=1)*np.sqrt(365)), 'maxdd_5m':float((n/np.maximum.accumulate(n)-1).min()),
         **{k+'_bps_day':float(np.sum(z[k][ix]/z['nav0'][ix])/len(days)*1e4) for k in ('price_trade','funding','fee')},
         'turnover_NAV_day':float(np.sum(z['turnover'][ix]/z['nav0'][ix])/len(days)),
         'halt_anchors':int(np.sum(z['status'][ix]==1)),'hold_anchors':int(np.sum(z['status'][ix]==2)),
         'stop_events':int(z['n_stop_events'][ix].sum()),'flatten_events':int(z['n_flatten_events'][ix].sum()),
         'cash_identity_max_usdt':float(np.abs((z['nav1']-z['nav0'])-(z['price_trade']+z['funding']-z['fee']+z['transfer']))[ix].max())}

def main(root,cp):
 root=Path(root);root.mkdir(exist_ok=False);start=time.monotonic();C=json.loads(Path(cp).read_text());deadline=start+C['budget_seconds'];src=Path(__file__).parent
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('input identity '+p)
 for n,h in C['sources'].items():
  if sha(src/n)!=h:raise ValueError('device identity '+n)
 eng=root/'engine';eng.mkdir();pins={}
 for p in (BASE/'engine').glob('*.py'):shutil.copyfile(p,eng/p.name);pins[str(p)]=sha(p)
 lib=eng/'bt_driver_lib.py';original=lib.read_text();lib.write_text(patch_driver(original));shutil.copyfile(src/'executor_bridge.py',eng/'executor_bridge.py')
 (root/'DRIVER_DIFF.json').write_text(json.dumps({'old_sha':sha(BASE/'engine/bt_driver_lib.py'),'new_sha':sha(lib),'change':'one post-context-load bridge call; old input/mirror gates retained'},indent=2))
 sys.path.insert(0,str(eng));import bt_driver_lib as DL
 paths={};controls={};childs=[]
 for mode in ('old_control','current_pure'):
  for seed in (42,2027):
   cfg=copy.deepcopy(json.loads((BASE/f's{seed}/CONFIG.json').read_text()));rr=root/f'{mode}_s{seed}';rr.mkdir();(rr/'receipts').mkdir();tag=cfg['runs'][0]['tag'];cfg['paths']['pod_root']=str(rr)
   cfg['launch']['max_parallel']=1;cfg['status']='RESEARCH_CURRENT_DUST_SEMANTICS_NOT_RELEASE';cfg['executor_semantic_bridge']={'mode':mode,'source_root':str(src),'trace':str(rr/'DECISION_TRACE.jsonl')}
   for p in eng.glob('*.py'):cfg['pins']['engine_'+p.stem]={'path':str(p),'sha256':sha(p)}
   cfg['pins']['bridge_helper']={'path':str(eng/'executor_bridge.py'),'sha256':sha(eng/'executor_bridge.py')}
   cfg['pins']['bridge_manifest']={'path':str(src/'SOURCES.json'),'sha256':sha(src/'SOURCES.json')}
   for n in json.loads((src/'SOURCES.json').read_text()):cfg['pins']['bridge_'+n]={'path':str(src/n),'sha256':sha(src/n)}
   q=rr/'CONFIG.json';q.write_text(json.dumps(cfg,indent=2));cmd=[PY,'-B','-u',str(eng/'bt_launch.py'),'PATH,HOME,LC_CTYPE',str(q),'--smoke',cfg['window']['first_anchor'],str(cfg['window']['n_anchors']),'0',tag,'bridge']
   with (rr/'RUN.log').open('x') as f:
    p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env={'PATH':'/usr/bin:/bin','HOME':'/root','LC_CTYPE':'C.UTF-8'},start_new_session=True)
    ident={'pid':p.pid,'pgid':os.getpgid(p.pid),'start_ticks':Path(f'/proc/{p.pid}/stat').read_text().split()[21],'mode':mode,'seed':seed};childs.append(ident);(root/'CHILDREN.json').write_text(json.dumps(childs,indent=2))
    try:rc=p.wait(timeout=max(1,deadline-time.monotonic()))
    except BaseException:
     if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=30)
     raise
   if rc:raise ValueError('engine rc '+str(rc)+' '+str(rr))
   prefix='PATH_'+tag.replace('|','_')+'_seed_00';out=rr/'runs_smoke/bridge'/tag.replace('|','_')/(prefix+'.npz');o=json.loads(out.with_suffix('.json').read_text())
   if sha(out)!=o['npz_sha256'] or not DL.audits_clean(o['audits']):raise ValueError('path identity/accounting audit')
   if mode=='old_control':controls[str(seed)]=exact(read(C['baselines'][str(seed)]),read(out));(root/'CONTROLS.json').write_text(json.dumps(controls,indent=2))
   paths.setdefault(str(seed),{})[mode]={'path':str(out),'sha256':sha(out)};print('COMPLETED',mode,seed,round(time.monotonic()-start,2),flush=True)
 results={};traces={}
 for seed in (42,2027):
  pp={k:read(v['path']) for k,v in paths[str(seed)].items()};results[str(seed)]={}
  for w,(lo,hi) in WINDOWS.items():
   values={k:summary(z,lo,hi) for k,z in pp.items()};values['delta']={k:values['current_pure'][k]-values['old_control'][k] for k in values['old_control'] if k!='n_days'};results[str(seed)][w]=values
  p=root/f'current_pure_s{seed}/DECISION_TRACE.jsonl';rows=[json.loads(s) for s in p.read_text().splitlines()];traces[str(seed)]={}
  for w,(lo,hi) in WINDOWS.items():
   ts=lambda s:int(np.datetime64(s,'s').astype('int64'));r=[x for x in rows if ts(lo)<=x['anchor']<ts(hi)]
   traces[str(seed)][w]={'trade_decisions':len(r),'dust_decisions':sum(bool(x['dust_popped']) for x in r),'dust_name_decisions':sum(len(x['dust_popped']) for x in r),'caller_defaulted_floor_name_decisions':sum(len(x['caller_defaulted_floor_names']) for x in r),
                       'same_state_nonzero_target_delta_decisions':sum(x['same_state_target_l1_delta']>1e-8 for x in r),
                       'mean_net_before_and_after':[[sum(x[k]/x['sizing_gross'] for x in r)/len(r) for k in ('old_target_net','new_target_net')]][0],
                       'target_l1_delta_max_over_gross':max([x['same_state_target_l1_delta']/x['sizing_gross'] for x in r]+[0.])}
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('input changed '+p)
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('engine source changed '+p)
 rec={'status':'PURE_EXECUTOR_BRIDGE_COMPLETE_NOT_CURRENT_LIVE_CERTIFIED','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(cp),'inputs':C['inputs'],'sources':C['sources'],'original_engine':pins,'controls':controls,'paths':paths,'windows':WINDOWS,'results':results,'traces':traces,'seconds':time.monotonic()-start,'limits':C['limits']}
 (root/'RESULT.json').write_text(json.dumps(rec,indent=2,allow_nan=False));(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')}));print(rec['status'],flush=True)

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  r=Path(sys.argv[1]);r.mkdir(exist_ok=True);(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2));raise
