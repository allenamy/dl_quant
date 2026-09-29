"""Re-read saved states independently; Decimal distances and direct source reshape."""
import ast,hashlib,io,json,sys,zipfile
from decimal import Decimal as D
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(root):
 root=Path(root);r=json.loads((root/'RESULT.json').read_bytes());t=json.loads((root/'TERMINAL.json').read_bytes())
 if t!={'rc':0,'result_sha256':sha(root/'RESULT.json')}:raise ValueError('terminal')
 for p,h in r['inputs'].items():
  if sha(p)!=h:raise ValueError('input_identity')
 if sha(root/'STATES.npz')!=r['output_sha256']:raise ValueError('output_identity')
 def one(s):
  p=[p for p in r['inputs'] if p.endswith(s)]
  if len(p)!=1:raise ValueError('path_count')
  return p[0]
 def material(p):
  with np.load(p,allow_pickle=False) as f:return {k:f[k] for k in f.files}
 a=material(root/'STATES.npz');original=material(one('/lr_recurrence_20260928/STATES.npz'));seed=material(one('/NC_s42_literal.npz'));endpoints=[x['anchor'] for x in r['rows']]
 source=Path(one('/vendor_live/fea171/combo_stage.py')).read_text();node=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='exec_reshape'];ns={'np':np};exec(compile(ast.Module(body=node,type_ignores=[]),'archived_reshape','exec'),ns)
 z=zipfile.ZipFile(one('/PRODUCTION_INPUTS.zip'));sy=json.loads(z.read('shadow_bundle/config.json'))['symbols_panel'];init={}
 for k in ('kc','fc'):
  with np.load(io.BytesIO(z.read(f'fea171/state_H_{k}_{r["seed_anchor"]}.npz')),allow_pickle=False) as f:
   v=np.zeros(len(sy));v[f['idx'].astype(int)]=f['val'];init[k]=v
 prev={label:ns['exec_reshape'](.55*init['kc']+.45*init['fc']) for label in ('B','S')};previousH={k:init[k] for k in init};totals={k:D(0) for k in prev};maxerr=0.;checks=0
 def check(x,y,tol=1e-12):
  nonlocal maxerr,checks
  e=abs(float(x)-float(y));maxerr=max(maxerr,e);checks+=1
  if not np.isfinite(e) or e>tol:raise ValueError('numeric_mismatch')
 for row in r['rows']:
  anchor=row['anchor']
  for label in ('B','S'):
   meta=row['arms'][label];kc=a[f'{label}_kc_{anchor}'];fc=a[f'{label}_fc_{anchor}'];target=a[f'{label}_target_{anchor}']
   for k,v in [('kc',kc),('fc',fc)]:
    if label=='B':
     for x,y in zip(v,original[f'C6_event_fetch_{anchor}'][0 if k=='kc' else 1]):check(x,y)
   expected=ns['exec_reshape'](.55*kc+.45*fc) if meta['accepted'] else prev[label]
   for x,y in zip(target,expected):check(x,y)
   delta=sum((abs(D(str(float(x)))-D(str(float(y)))) for x,y in zip(target,prev[label])),D(0));check(delta,meta['target_adjustment_l1']);totals[label]+=delta
   gross=sum((abs(D('.55')*D(str(float(x)))+D('.45')*D(str(float(y)))) for x,y in zip(kc,fc)),D(0));check(gross,meta['raw_gross'])
   if anchor in (1790424000,1790438400,1790481600):
    i=endpoints.index(anchor);prior=endpoints[i-1]
    if not np.array_equal(kc,a[f'{label}_kc_{prior}']) or not np.array_equal(fc,a[f'{label}_fc_{prior}']):raise ValueError('HOLD_mutation')
   prev[label]=target
  distance=sum((abs(D(str(float(x)))-D(str(float(y)))) for x,y in zip(prev['B'],prev['S'])),D(0));check(distance,row['target_between_arms_l1'])
 for k,v in totals.items():check(v,r['summary']['sum_target_adjustment_l1'][k])
 out={'status':'INDEPENDENT_STATES_AND_DECIMAL_DISTANCE_PASS','checks':checks,'max_abs_error':maxerr,'result_sha256':sha(root/'RESULT.json'),'source_sha256':sha(__file__),'totals_decimal':{k:str(v) for k,v in totals.items()},'limits':['No independent cash or full seed-history certification','Direct compiled archived reshape reused; scalar distances independently Decimal']}
 (root/'VERIFY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main(sys.argv[1])
