"""Independent Decimal projection/price arithmetic using pinned traced states and parent marks."""
from decimal import Decimal as D
from pathlib import Path
import collections,hashlib,io,json,sys,zipfile
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(root,out):
 tr=json.loads((root/'RESULT.json').read_bytes());cash=json.loads((root/'CASH.json').read_bytes())
 assert cash['trace_result_sha256']==sha(root/'RESULT.json') and cash['trace_states_sha256']==sha(root/'STATES.npz')
 for p,h in tr['inputs'].items():assert sha(p)==h
 bp=Path(next(p for p in tr['inputs'] if p.endswith('actual_blend_cash_20260928/RESULT.json')));b=json.loads(bp.read_bytes());assert sha(bp)==cash['blend_result_sha256']
 for p,h in b['input_sha256'].items():assert sha(p)==h
 z=zipfile.ZipFile(next(p for p in tr['inputs'] if p.endswith('PRODUCTION_INPUTS.zip')));sy=json.loads(z.read('shadow_bundle/config.json'))['symbols_panel'];ix={s:i for i,s in enumerate(sy)}
 census=Path(next(p for p in b['input_sha256'] if p.endswith('execution_input_census_20260928_run3/RESULT.json'))).parent;cm=json.loads((census/'RESULT.json').read_bytes())
 for p,h in cm['outputs'].items():assert sha(census/p)==h
 aa=[v for p in census.glob('*_anchors.json') for v in json.loads(p.read_bytes())];ph=json.loads((census/'PHASES.json').read_bytes())
 par=json.loads(Path(next(p for p in b['input_sha256'] if p.endswith('actual_target_cash_20260928/RESULT.json'))).read_bytes())
 st=np.load(root/'STATES.npz',allow_pickle=False);maps={};checks=0;maximum=0.
 def check(a,v):
  nonlocal checks,maximum
  delta=abs(float(a)-float(v));checks+=1;maximum=max(maximum,delta);assert delta<1e-7,(a,v)
 keys=('inherited','king','f10','fund','storage','export','clamp')
 for c in cm['rows']:
  a=c['anchor'];ar=next(r for r in aa if r['rebalance_id']==c['rid']);pa=next(r['data'] for r in ph if r['phase']=='A' and r['data'].get('rebalance_id')==c['rid']);old=b['mapped'][str(a)];raw=json.loads(z.read(f'state/target_live/{a}.json'))['weights'];active=sorted(set(raw)-set(ar['reshape']['removed_names']))
  actual=np.zeros(len(sy))
  for leg,w in (('kc',.55),('fc',.45)):
   with np.load(io.BytesIO(z.read(f'fea171/state_H_{leg}_{a}.npz')),allow_pickle=False) as n:actual[n['idx'].astype(int)]+=w*n['val']
  components={}
  for s in active:
   i=ix[s];vals=[D('.55')*D(str(float(st[f'kc_{a}'][j,i])))+D('.45')*D(str(float(st[f'fc_{a}'][j,i]))) for j in range(4)];vals.append(D(str(float(actual[i])))-sum(vals,D(0)));components[s]=vals
  avg=[sum((v[k] for v in components.values()),D(0))/len(active) for k in range(5)];factor=D(str(pa['sizing']['gross']))/D(str(ar['external_book']['gross_norm']))*D(str(old['scale']));maps[a]={}
  for s,oldparts in old['components'].items():
   vals=[(components[s][k]-avg[k])*factor if s in components else D(0) for k in range(5)];p=dict(zip(keys[:5],vals));p.update(export=D(str(oldparts['export'])),clamp=D(str(oldparts['clamp'])));maps[a][s]=p
 assert [(x['anchor_from'],x['anchor_to']) for x in cash['windows']]==[(x['anchor_from'],x['anchor_to']) for x in par['windows']]
 totals=collections.defaultdict(lambda:{k:D(0) for k in keys+('policy_hold',)})
 for w,pw in zip(cash['windows'],par['windows']):
  a=w['anchor_from'];assert [r['symbol'] for r in w['rows']]==[r['symbol'] for r in pw['pieces']]
  wt={k:D(0) for k in keys+('policy_hold',)}
  for r,old in zip(w['rows'],pw['pieces']):
   parts=maps[a].get(r['symbol'],dict.fromkeys(keys,D(0)))
   for k,v in parts.items():check(v,r['notional_parts'][k])
   if old['verdict']!='PRICED':assert r['verdict']=='PARENT_UNPRICED' and r['contribution'] is None;continue
   if b['mapped'][str(a)]['halted_start']:assert r['verdict']=='POLICY_HOLD';wt['policy_hold']+=D(str(old['benchmark']));continue
   if any(parts.values()) and (old['start_mark'] is None or old['end_mark'] is None):assert r['verdict']=='COMPONENT_UNPRICED' and r['contribution'] is None;continue
   rate=D(str(old['end_mark']))/D(str(old['start_mark']))-1 if any(parts.values()) else D(0)
   for k,v in parts.items():check(v*rate,r['contribution'][k]);wt[k]+=v*rate
  for k,v in wt.items():check(v,w['contribution'][k]);totals[w['period']][k]+=v
  check(sum(wt.values(),D(0)),w['parent_benchmark_same_population'])
 for g,parts in totals.items():
  for k,v in parts.items():check(v,cash['summary'][g]['contribution'][k])
 receipt={'verdict':'PASS','checks':checks,'max_arithmetic_delta':maximum,'trace_sha256':sha(root/'RESULT.json'),'cash_sha256':sha(root/'CASH.json'),'source_sha256':sha(__file__),'method':'independent Decimal projection and price arithmetic; original producer chain controls establish trace total, not uniqueness of causal attribution'}
 out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main(*map(Path,sys.argv[1:]))
