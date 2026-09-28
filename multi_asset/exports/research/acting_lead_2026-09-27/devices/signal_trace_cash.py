"""Fixed-population price attribution; no deletion effect or full strategy return."""
import collections,hashlib,io,json,math,sys,zipfile
from pathlib import Path
import numpy as np

KEYS=('inherited','king','f10','fund','storage','export','clamp')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def value(parts,p0,p1):
 if set(parts)!=set(KEYS) or not all(type(v) in (int,float) and math.isfinite(v) for v in parts.values()):raise ValueError('parts')
 if not any(parts.values()):return {k:0. for k in KEYS}
 if not all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in (p0,p1)):return None
 return {k:v*(p1/p0-1) for k,v in parts.items()}
def run(trace_root,out):
 tr=json.loads((trace_root/'RESULT.json').read_bytes())
 for p,h in tr['inputs'].items():
  if sha(p)!=h:raise ValueError('trace_input_changed')
 for n,h in tr['outputs'].items():
  if sha(trace_root/n)!=h:raise ValueError('trace_output_changed')
 if tr['n_processed']!=20 or tr['n_states']!=23 or tr['max_actual_target_error']>1e-8:raise ValueError('trace_control')
 blendpath=Path(next(p for p in tr['inputs'] if p.endswith('actual_blend_cash_20260928/RESULT.json')));blend=json.loads(blendpath.read_bytes())
 for p,h in blend['input_sha256'].items():
  if sha(p)!=h:raise ValueError('blend_input_changed')
 census=Path(next(p for p in blend['input_sha256'] if p.endswith('execution_input_census_20260928_run3/RESULT.json'))).parent
 cm=json.loads((census/'RESULT.json').read_bytes())
 for p,h in cm['outputs'].items():
  if sha(census/p)!=h:raise ValueError('census_changed')
 original=json.loads(Path(next(p for p in blend['input_sha256'] if p.endswith('actual_target_cash_20260928/RESULT.json'))).read_bytes())
 aa=[r for p in census.glob('*_anchors.json') for r in json.loads(p.read_bytes())];ph=json.loads((census/'PHASES.json').read_bytes())
 archive=zipfile.ZipFile(next(p for p in tr['inputs'] if p.endswith('PRODUCTION_INPUTS.zip')));sy=json.loads(archive.read('shadow_bundle/config.json'))['symbols_panel'];index={s:i for i,s in enumerate(sy)}
 with np.load(trace_root/'STATES.npz',allow_pickle=False) as n:states={k:n[k] for k in n.files}
 maps={};max_storage=0.;maxsum=0.
 for c in cm['rows']:
  a=c['anchor'];ar=next(r for r in aa if r['rebalance_id']==c['rid']);pa=next(r['data'] for r in ph if r['phase']=='A' and r['data'].get('rebalance_id')==c['rid'])
  old=blend['mapped'][str(a)];raw=json.loads(archive.read(f'state/target_live/{a}.json'))['weights'];active=sorted(set(raw)-set(ar['reshape']['removed_names']));idx=np.array([index[s] for s in active]);mix=.55*states[f'kc_{a}']+.45*states[f'fc_{a}']
  actual=np.zeros(len(sy))
  for leg,weight in (('kc',.55),('fc',.45)):
   with np.load(io.BytesIO(archive.read(f'fea171/state_H_{leg}_{a}.npz')),allow_pickle=False) as n:actual[n['idx'].astype(int)]+=weight*n['val']
  difference=actual-mix.sum(0)
  if np.abs(difference).max()>1e-8:raise ValueError('state_roundoff_bound')
  expanded=np.concatenate([mix,difference[None,:]],axis=0);initial=expanded[:,idx]*(pa['sizing']['gross']/ar['external_book']['gross_norm']);mapped=(initial-initial.mean(1)[:,None])*old['scale'];lookup={s:mapped[:,i] for i,s in enumerate(active)};maps[a]={}
  for s,p in old['components'].items():
   v=dict(zip(KEYS[:5],map(float,lookup.get(s,np.zeros(5)))));v['export']=p['export'];v['clamp']=p['clamp'];delta=abs(math.fsum(v.values())-math.fsum(p.values()));maxsum=max(maxsum,delta)
   if delta>1e-6:raise ValueError('target_sum')
   max_storage=max(max_storage,abs(v['storage']));maps[a][s]=v
 windows=[];groups=collections.defaultdict(list)
 for w in original['windows']:
  a=w['anchor_from'];rows=[];halted=blend['mapped'][str(a)]['halted_start']
  for p in w['pieces']:
   parts=maps[a].get(p['symbol'],dict.fromkeys(KEYS,0.));v=None
   if p['verdict']!='PRICED':status='PARENT_UNPRICED'
   elif halted:status='POLICY_HOLD';v=dict(dict.fromkeys(KEYS,0.),policy_hold=p['benchmark'])
   else:
    v=value(parts,p['start_mark'],p['end_mark']);status='PRICED' if v is not None else 'COMPONENT_UNPRICED'
   if v is not None and abs(math.fsum(v.values())-p['benchmark'])>1e-7:raise ValueError('price_identity')
   rows.append({'symbol':p['symbol'],'verdict':status,'notional_parts':parts,'start_mark':p['start_mark'],'end_mark':p['end_mark'],'parent_benchmark':p['benchmark'],'contribution':v})
  ready=[r for r in rows if r['contribution'] is not None];total={k:math.fsum(r['contribution'].get(k,0) for r in ready) for k in KEYS+('policy_hold',)}
  item={'anchor_from':a,'anchor_to':w['anchor_to'],'period':w['period'],'counts':dict(collections.Counter(r['verdict'] for r in rows)),'contribution':total,'parent_benchmark_same_population':math.fsum(r['parent_benchmark'] for r in ready),'rows':rows};windows.append(item);groups[w['period']].append(item)
 summary={g:{'counts':dict(sum((collections.Counter(w['counts']) for w in ws),collections.Counter())),'contribution':{k:math.fsum(w['contribution'][k] for w in ws) for k in KEYS+('policy_hold',)},'parent_benchmark_same_population':math.fsum(w['parent_benchmark_same_population'] for w in ws)} for g,ws in groups.items()}
 result={'scope':'conditional additive contribution, shared full-book masks and scale, not signal deletion','trace_result_sha256':sha(trace_root/'RESULT.json'),'trace_states_sha256':sha(trace_root/'STATES.npz'),'blend_result_sha256':sha(blendpath),'source_sha256':sha(__file__),'max_final_target_difference_usdt':maxsum,'max_storage_notional_usdt':max_storage,'summary':summary,'windows':windows}
 with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps({'sha256':sha(out),'max_storage_notional_usdt':max_storage,'max_final_target_difference_usdt':maxsum,'summary':summary},indent=2))
if __name__=='__main__':run(*map(Path,sys.argv[1:]))
