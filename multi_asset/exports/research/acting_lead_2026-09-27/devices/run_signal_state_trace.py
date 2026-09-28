"""Small offline actual-path trace; no strategy alteration or venue/production imports."""
import ast,hashlib,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
from signal_state_trace import trace_chain,trim_parts,rank_scores


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def npz(z,name):
 with np.load(io.BytesIO(z.read(name)),allow_pickle=False) as n:return {k:n[k] for k in n.files}
def main(pins_path,root):
 pins=json.loads(pins_path.read_bytes())
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input_changed:'+p)
 root.mkdir(exist_ok=False);begin=time.monotonic()
 def by_end(s):
  found=[Path(p) for p in pins if p.endswith(s)]
  if len(found)!=1:raise ValueError('input_ambiguous:'+s)
  return found[0]
 prod=zipfile.ZipFile(by_end('PRODUCTION_INPUTS.zip'));fetch=zipfile.ZipFile(by_end('fetch_feature_alignment.zip'));gap=zipfile.ZipFile(by_end('gap_history_propagation.zip'));lr=zipfile.ZipFile(by_end('lr_recurrence_20260928.zip'))
 cfg=json.loads(prod.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];N=len(sy);P=cfg['params'];rows=json.loads(lr.read('result/RESULT.json'))['rows'];reference=npz(lr,'result/STATES.npz')
 with np.load(by_end('ELIGIBILITY.npz'),allow_pickle=False) as x:legal={int(t):v.copy() for t,v in zip(x['E_ts'],x['legal'])}
 text=by_end('current_combo_stage.py').read_text();nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='chain']
 if len(nodes)!=1:raise ValueError('chain_count')
 ns={'np':np,'P':P,'NW':N};exec(compile(ast.Module(body=nodes,type_ignores=[]),'archived_chain','exec'),ns)
 start=1790236800;end=1790553600;holds={1790424000,1790438400,1790481600};by={r['anchor']:r for r in rows}
 if len(rows)!=20 or set(range(start,end+1,14400))-set(by)!=holds:raise ValueError('population')
 def actual(leg,a):
  r=npz(prod,f'fea171/state_H_{leg}_{a}.npz')
  if int(r['anchor'])!=a:raise ValueError('state_anchor')
  v=np.zeros(N);v[r['idx'].astype(int)]=r['val'];return v
 state={}
 for leg in ('kc','fc'):
  v=np.zeros((4,N));v[0]=actual(leg,start-14400);state[leg]=v
 output={};measured=[];maxkernel=0;maxlive=0;maxc6=0
 for a in range(start,end+1,14400):
  if time.monotonic()-begin>120:raise TimeoutError('budget')
  if a not in holds:
   name=f'ROW_{a}.npz';z=gap if a>=min(holds) else fetch
   choices=[n for n in z.namelist() if n.endswith('/'+name)]
   if len(choices)!=1:raise ValueError('row_missing')
   r=npz(z,choices[0]);m=r['m'].astype(int);seats=np.array(by[a]['modes']['C6_event_fetch']['w3']);w=np.array([seats[0],0.,seats[2]]);w=w/w.sum() if w.sum()>1e-12 else np.array([.5,0.,.5])
   inputs={'kc':np.zeros((4,len(m))),'fc':np.zeros((4,len(m)))}
   inputs['kc'][1]=w[0]*np.nan_to_num(r['KZ'].astype(float));inputs['fc'][2]=w[0]*np.nan_to_num(rank_scores(r['P'].astype(float)))
   for leg in inputs:inputs[leg][3]=w[2]*np.nan_to_num(r['ZFD'].astype(float))
   for leg in ('kc','fc'):
    parts=trim_parts(inputs[leg],r['RN8'].astype(float));prev=state[leg]
    ns.update(H=prev.sum(0),pm=m,sel=np.isfinite(r['QV'])&(r['QV']>=P['qv4h_min']),LIVE_MASK=legal[a])
    expected=ns['chain'](parts.sum(0))
    if expected is None:raise ValueError('original_chain_degenerate')
    candidate=trace_chain(parts,prev,m,r['QV'],legal[a],P);err=float(np.abs(candidate.sum(0)-expected).max());maxkernel=max(maxkernel,err)
    if err>1e-12:raise ValueError('kernel_mismatch')
    state[leg]=candidate
   mix=.55*state['kc']+.45*state['fc'];live=.55*actual('kc',a)+.45*actual('fc',a);err=float(np.abs(mix.sum(0)-live).max());maxlive=max(maxlive,err)
   if err>1e-8:raise ValueError('live_mismatch')
   measured.append({'anchor':a,'max_live_target_error':err,'component_gross':dict(zip(('inherited','king','f10','fund'),map(float,np.abs(mix).sum(1))))})
  stack=np.stack([state['kc'].sum(0),state['fc'].sum(0),(.55*state['kc']+.45*state['fc']).sum(0)])
  d=float(np.abs(stack-reference[f'C6_event_fetch_{a}']).max());maxc6=max(maxc6,d)
  if d>1e-12:raise ValueError('C6_reference_mismatch')
  output[f'kc_{a}']=state['kc'].copy();output[f'fc_{a}']=state['fc'].copy()
 np.savez_compressed(root/'STATES.npz',**output)
 result={'utc':time.strftime('%FT%TZ',time.gmtime()),'scope':'additive actual-path trace, not component deletion or candidate evaluation','inputs':pins,'sources':{str(p.resolve()):sha(p) for p in (Path(__file__),Path(__file__).with_name('signal_state_trace.py'))},'outputs':{'STATES.npz':sha(root/'STATES.npz')},'components':['inherited','king','f10','fund'],'rows':measured,'n_processed':len(measured),'n_states':len(output)//2,'max_kernel_error':maxkernel,'max_actual_target_error':maxlive,'max_C6_reference_error':maxc6,'python':sys.executable,'numpy':np.__version__,'seconds':time.monotonic()-begin,'limits':['full actual signal determines nonlinear masks/scales','initial state has unknown historical mixed provenance','actual LR seats retained, not policy-ablation retrained seats','no costs, no cash certification, no strategy or swap recommendation']}
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input_changed_at_end')
 (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('inputs','sources','rows','outputs')},indent=2))
if __name__=='__main__':main(*map(Path,sys.argv[1:]))
