"""Conditioned book mapping, explicitly not historical request/cash certification."""
import ast,collections,datetime,hashlib,json,math,sys,types
from pathlib import Path
import numpy as np

def hashfile(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def compile_pure(path,names,env):
 text=Path(path).read_text();nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in nodes}!=set(names):raise ValueError('pure_names')
 source='from __future__ import annotations\n'+'\n\n'.join(ast.get_source_segment(text,n) for n in nodes);ns=dict(env);exec(compile(source,str(path), 'exec'),ns);return ns

def withheld_names(phase,external,target):
 tradable=phase['universe'].get('tradable')
 if not isinstance(tradable,list):raise ValueError('venue_tradable_unavailable')
 return (set(target)-set(tradable)) | set().union(*[set(v) for v in phase['untradable_names'].values()]) | set(external.get('held_exit') or []) | set(external.get('meta_excluded') or {}) | set((external.get('below_min_notional') or {}).get('names') or [])

def compare(target,recorded,halted):
 if not target or not recorded:raise ValueError('empty_population')
 if any(type(v) not in (int,float) or not math.isfinite(v) for v in list(target.values())+list(recorded.values())):raise ValueError('nonfinite_target')
 ds={s:target[s]-recorded[s] for s in set(target)&set(recorded)}
 return {'same_names':set(target)==set(recorded),'max_abs_usdt':max([abs(x) for x in ds.values()]+[0.]),'n_differing':sum(abs(x)>1e-6 for x in ds.values()),'missing_recorded':sorted(set(target)-set(recorded)),'unexpected_recorded':sorted(set(recorded)-set(target)),
 'conditional_target_match':set(target)==set(recorded) and bool(ds) and all(abs(x)<=1e-6 for x in ds.values()),'execution_claim':False,'opening_halted':halted}

def run(root,mutation=False):
 root=Path(root);c=json.loads((root/'RESULT.json').read_bytes());bind=json.loads((root/'SOURCE_BINDING.json').read_bytes())
 if bind['input_result_sha256']!=hashfile(root/'RESULT.json'):raise ValueError('census_identity')
 for n,h in c['outputs'].items():
  if hashfile(root/n)!=h:raise ValueError('census_output_changed')
 epochs={e['commit']:e for e in bind['epochs']};compiled={}
 for k,e in epochs.items():
  for rec in e['sources'].values():
   if hashfile(root/rec['archived'])!=rec['sha256']:raise ValueError('source_changed')
  lg=compile_pure(root/e['sources']['signal/legs.py']['archived'],['reshape_after_withhold'],{'np':np})
  al=compile_pure(root/e['sources']['scheduler/anchor_loop.py']['archived'],['apply_withhold_and_reshape','withhold_pop','clamp_held_untradable'],{'LG':types.SimpleNamespace(reshape_after_withhold=lg['reshape_after_withhold']),'RESHAPE_REDEMEAN':True,'RESHAPE_RESCALE':True})
  cfg=json.loads((root/e['sources']['config/book.json']['archived']).read_bytes())
  if cfg['beta_overlay']['mode']!='shadow':raise ValueError('non_shadow_overlay')
  compiled[k]=al['apply_withhold_and_reshape']
 an=[x for p in root.glob('*_anchors.json') for x in json.loads(p.read_bytes())];orders=[x for p in root.glob('*_orders.json') for x in json.loads(p.read_bytes())]
 ph=json.loads((root/'PHASES.json').read_bytes());flraw=json.loads((root/'CURRENT_FILTERS.json').read_bytes());out=[]
 for item,version in zip(c['rows'],bind['assignment']):
  a=item['anchor'];assert a==version['anchor'];rid=item['rid'];row=next(x for x in an if x['rebalance_id']==rid);pa=next(x['data'] for x in ph if x['phase']=='A' and x['data'].get('rebalance_id')==rid)
  pp=[x for x in ph if x['phase']=='C' and datetime.datetime.fromisoformat(x['logged_utc'].replace('Z','+00:00')).timestamp()<a+1200 and isinstance(x['data'].get('per_name_stop'),dict)]
  if not pp:raise ValueError('prior_stop_state_missing')
  prev=pp[-1];stop=prev['data']['per_name_stop'];force=set(stop['stopped'])
  cap=pa['venue_cap_clamp']
  if cap.get('capped') or cap.get('error') or cap.get('invalid'):raise ValueError('venue_cap_not_replayed')
  g=pa['sizing']['gross'];norm=row['external_book']['gross_norm'];targetfile=json.loads((root/f'TARGET_{a}.json').read_bytes())
  target={s:float(w)/norm*g for s,w in targetfile['weights'].items()}
  if mutation and a==1790553600:target[sorted(target)[0]]+=100.
  od=[x for x in orders if x['rebalance_id']==rid];by=collections.defaultdict(list)
  for x in od:by[x['symbol']].append(x)
  for s,rr in by.items():
   if len({(x['prev_w'],x['target_w']) for x in rr})!=1:raise ValueError('conflicting_order_plan:'+str(a)+':'+s)
  held={s:rr[0]['prev_w']*row['target_gross'] for s,rr in by.items()};observed={s:rr[0]['target_w']*row['target_gross'] for s,rr in by.items()}
  untr=withheld_names(pa,row['external_book'],target)
  unknown_held=sorted(untr-set(held));floors={s:float(flraw[s]['min_notional']) for s in target if s in flraw and flraw[s].get('min_notional') is not None}
  clamp,rs=compiled[version['commit']](target,held,untr,g,floors_usdt=floors,floors_source='current_cache_assumption_not_historical',force_flat=force)
  res=compare(target,observed,row['opening_halted']);res.update(anchor=a,commit=version['commit'],unknown_held_names_defaulted_zero=unknown_held,stop_state_utc=prev['logged_utc'],n_target=len(target),n_recorded=len(observed),scope='conditional_mapping_only_no_execution_certification')
  out.append(res)
 return {'rows':out,'matched':sum(x['conditional_target_match'] for x in out),'n':len(out),'max_abs_usdt':max(x['max_abs_usdt'] for x in out),'census_sha256':hashfile(root/'RESULT.json'),'sources_sha256':hashfile(root/'SOURCE_BINDING.json'),'device_sha256':hashfile(__file__),'python':sys.executable,'numpy':np.__version__,'mutation':mutation}
if __name__=='__main__':
 r=run(sys.argv[1],len(sys.argv)>2 and sys.argv[2]=='--mutate');p=Path(sys.argv[1])/('BOOK_MAPPING_GATES_MUTATION.json' if r['mutation'] else 'BOOK_MAPPING_GATES.json')
 with p.open('x') as f:json.dump(r,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
