"""Single frozen offline handoff pair, no cash/production API or GPU."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import ast,hashlib,io,json,sys,time,traceback,zipfile
from pathlib import Path
import numpy as np
from state_handoff import select_seed,evolve

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def save(p,r):p.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
def main(root):
 t=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);pins={}
 def pin(p,h=None):
  p=Path(p);s=sha(p)
  if h is not None and s!=h:raise ValueError('identity:'+str(p))
  pins[str(p)]=s;return p
 def parent(base,h):
  base=Path(base);r=json.loads(pin(base/'RESULT.json',h).read_bytes())
  for name,s in r['outputs'].items():pin(base/name,s)
  return base,r
 fetch,fr=parent('/dev/shm/fetch_feature_alignment_20260928','e40122efbc5277cbdf0ec8f48df33401574037948b09e33bbe7d0de21eaf466a')
 gap,gr=parent('/dev/shm/gap_history_propagation_20260928','f4ce13035843f7ddba97bcf299c83cb09c27a685cc029098e471d4ca1f327afd')
 lr,lrr=parent('/dev/shm/lr_recurrence_20260928','057013775db4017a132181932212148caf0fafc847303b398addd42b3fb4c9c6')
 seedp=pin('/dev/shm/recent_nc_combo_20260928/NC_s42_literal.npz','f6e7da7b8f9428752ef3abf973193c3d00628fca9636b80e5bedff0ce22b6ca8')
 sr=json.loads(pin(seedp.parent/'RESULT.json').read_bytes())
 if sr['outputs'][seedp.name]!=pins[str(seedp)]:raise ValueError('seed_receipt')
 # The candidate prefix's recorded old state and generating code are required;
 # this does not certify the entire historical training pipeline anew.
 for p,h in sr['inputs'].items():
  if p.endswith('.py') or p.endswith('.sh') or p.endswith('/combo_s42/literal.npz') or p.endswith('/combo_s42/TARGET_RECEIPT.json'):pin(p,h)
 archive=pin('/dev/shm/fetch_feature_alignment_20260928_inputs/PRODUCTION_INPUTS.zip','d6c793dab6174f4d2f81636e655c9cf5f271a426fe09e89c1d408c6c2666e09a')
 z=zipfile.ZipFile(archive);cfg=json.loads(z.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];N=len(sy);params=cfg['params']
 eligibility=load(pin('/dev/shm/recent_nc_combo_20260928/ELIGIBILITY.npz','1777b5d92974de23bd2593ad02779aa9e4c510aefae1aa89d212479b2c418cd3'))
 if not np.array_equal(eligibility['symbols'],sy):raise ValueError('eligibility_axis')
 legal={int(a):v for a,v in zip(eligibility['E_ts'],eligibility['legal'])}
 ns=Path('/dev/shm/news2_2026-09-23');p=pin(ns/'devices/combo_target.py','d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544')
 pin(ns/'vendor_live/fea171/combo_stage.py','fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8')
 sys.path.insert(0,str(p.parent));import combo_target
 combo_target.ROOT=ns
 start=1790236800;end=1790553600;holds={1790424000,1790438400,1790481600};rows={r['anchor']:r for r in lrr['rows']};ref=load(lr/'STATES.npz')
 if set(range(start,end+1,14400))-set(rows)!=holds or len(rows)!=20:raise ValueError('population')
 initial={}
 for k in ('kc','fc'):
  with np.load(io.BytesIO(z.read(f'fea171/state_H_{k}_{start-14400}.npz')),allow_pickle=False) as a:
   if int(a['anchor'])!=start-14400:raise ValueError('actual_seed_clock')
   v=np.zeros(N);v[a['idx'].astype(int)]=a['val'];initial[k]=v
 candidate=select_seed(load(seedp),sy,start-14400)
 frames=[]
 for a in range(start,end+1,14400):
  args={}
  if a not in holds:
   b=gap if a>=min(holds) else fetch;r=load(b/f'ROW_{a}.npz')
   args={k:r[v].astype(float) for k,v in [('king_rank','KZ'),('f10_score','P'),('fund_rank','ZFD'),('rn8','RN8'),('qv','QV')]}
   args.update(seats=np.array(rows[a]['modes']['C6_event_fetch']['w3']),members=r['m'],legal=legal[a])
  frames.append({'anchor':a,'args':args})
 baseline=evolve(combo_target.step,frames,params,initial,holds)
 err=0.;liveerr=0.
 for r in baseline:
  a=r['anchor'];stack=np.stack([r['kc'],r['fc'],.55*r['kc']+.45*r['fc']]);e=float(np.abs(stack-ref[f'C6_event_fetch_{a}']).max());err=max(err,e)
  if e>1e-12:raise ValueError('baseline_C6')
  if a not in holds:
   if not r['accepted']:raise ValueError('baseline_gate')
   d=json.loads(z.read(f'state/target_live/{a}.json'));v=np.array([d['weights'].get(s,0.) for s in sy]);e=float(np.abs(r['published']-v).max());liveerr=max(liveerr,e)
   if e>1e-8:raise ValueError('baseline_live')
 # Candidate summaries only after all controls above.
 alternative=evolve(combo_target.step,frames,params,candidate,holds)
 # Same-state identity + no post-cutoff H values consumed.
 twin=evolve(combo_target.step,frames,params,initial,holds)
 for a,b in zip(baseline,twin):
  if any(not np.array_equal(a[k],b[k]) for k in ('kc','fc','published')):raise ValueError('identical_arm')
 arrays={};out=[];shape=combo_target.source_kernels()['exec_reshape'];prev={k:shape(.55*initial['kc']+.45*initial['fc']) for k in ('B','S')};sums={'B':0.,'S':0.}
 for rb,rs in zip(baseline,alternative):
  row={'anchor':rb['anchor'],'arms':{}}
  for label,r in (('B',rb),('S',rs)):
   adjusted=prev[label] if not r['accepted'] else shape(r['published']);distance=float(np.abs(adjusted-prev[label]).sum());sums[label]+=distance;prev[label]=adjusted.copy()
   row['arms'][label]={'accepted':r['accepted'],'reason':r['reason'],'raw_gross':float(np.abs(.55*r['kc']+.45*r['fc']).sum()),'target_adjustment_l1':distance}
   arrays[f'{label}_kc_{r["anchor"]}']=r['kc'];arrays[f'{label}_fc_{r["anchor"]}']=r['fc'];arrays[f'{label}_target_{r["anchor"]}']=adjusted
  row['target_between_arms_l1']=float(np.abs(prev['B']-prev['S']).sum());out.append(row)
 np.savez_compressed(root/'STATES.npz',**arrays)
 for p in (Path(__file__),Path(__file__).with_name('state_handoff.py'),Path(__file__).with_name('test_state_handoff.py')):pin(p.resolve())
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input_drift:'+p)
 if time.monotonic()-t>120:raise TimeoutError('total_budget')
 result={'utc':time.strftime('%FT%TZ',time.gmtime()),'status':'CONDITIONAL_STATE_HANDOFF_COMPLETE_NOT_CASH_OR_DEPLOYMENT','seed_anchor':start-14400,'initial_policy':'NC walk-forward historical state, not final-model full-history replay','controls':{'C6_max':err,'actual_target_max':liveerr,'state_count':23,'processed_count':20,'same_seed_exact':True},'inputs':pins,'output_sha256':sha(root/'STATES.npz'),'rows':out,'summary':{'published':{k:sum(r['arms'][k]['accepted'] for r in out) for k in ('B','S')},'first_target_adjustment_l1':out[0]['arms'],'sum_target_adjustment_l1':sums,'final_target_between_arms_l1':out[-1]['target_between_arms_l1']},'python':sys.executable,'numpy':np.__version__,'seconds':time.monotonic()-t,'limits':['Exploratory selected after observing losses; no confirmatory efficacy claim','Seed uses research historical membership/funding/model-policy prefix not certified as production-equivalent','C6 LR valid conditional common original leg signals, not ablation or new-model seats','Adjustment is unit-gross target distance, not market-drift turnover, filled volume or fees','HOLD carries last target only for this diagnostic; actual contracts/cash not simulated','No promotion, leverage/stop/state/model changes']}
 save(root/'RESULT.json',result);save(root/'TERMINAL.json',{'rc':0,'result_sha256':sha(root/'RESULT.json')});print(json.dumps({k:result[k] for k in ('status','controls','summary','seconds')},indent=2))

if __name__=='__main__':
 try:main(sys.argv[1])
 except BaseException as e:
  p=Path(sys.argv[1]);p.mkdir(exist_ok=True);save(p/'TERMINAL.json',{'rc':1,'error':repr(e),'traceback':traceback.format_exc()});raise
