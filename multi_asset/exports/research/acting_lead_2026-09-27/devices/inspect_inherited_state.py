"""Measure inherited-state persistence; no changed-band counterfactual."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
import numpy as np

def main(root,out):
 tr=json.loads((root/'RESULT.json').read_bytes());p=Path(next(p for p in tr['inputs'] if p.endswith('PRODUCTION_INPUTS.zip')))
 if hashlib.sha256(p.read_bytes()).hexdigest()!=tr['inputs'][str(p)]:raise ValueError('archive_changed')
 if hashlib.sha256((root/'STATES.npz').read_bytes()).hexdigest()!=tr['outputs']['STATES.npz']:raise ValueError('states_changed')
 z=zipfile.ZipFile(p);cfg=json.loads(z.read('shadow_bundle/config.json'));n=len(cfg['symbols_panel']);st=np.load(root/'STATES.npz',allow_pickle=False);previous={};initial={};stats=[]
 for leg in ('kc','fc'):
  with np.load(io.BytesIO(z.read(f'fea171/state_H_{leg}_1790222400.npz')),allow_pickle=False) as d:
   a=np.zeros(n);a[d['idx'].astype(int)]=d['val'];previous[leg]=a.copy();initial[leg]=a.copy()
 for a in range(1790236800,1790553600+1,14400):
  for leg in ('kc','fc'):
   p=previous[leg];q=st[f'{leg}_{a}'][0];use=np.abs(p)>1e-12;ratio=q[use]/p[use]
   same=int(np.count_nonzero(np.isclose(ratio,1,rtol=0,atol=1e-12)));ema=int(np.count_nonzero(np.isclose(ratio,1-cfg['params']['alpha'],rtol=0,atol=1e-12)));exitn=int(np.count_nonzero(np.isclose(ratio,0,rtol=0,atol=1e-12)))
   if same+ema+exitn!=int(use.sum()):raise ValueError('unexpected_transition')
   stats.append({'anchor':a,'leg':leg,'prior_nonzero':int(use.sum()),'unchanged':same,'ema_updated':ema,'exited':exitn,'scheduled_hold':a in {1790424000,1790438400,1790481600}});previous[leg]=q
 end={}
 for leg in ('kc','fc'):
  p=initial[leg];q=previous[leg];use=np.abs(p)>1e-12;counts=[None if f<=1e-12 else int(round(np.log(f)/np.log(1-cfg['params']['alpha']))) for f in q[use]/p[use]]
  end[leg]={'initial_gross':float(np.abs(p).sum()),'inherited_final_gross':float(np.abs(q).sum()),'ratio_of_gross':float(np.abs(q).sum()/np.abs(p).sum()),'surviving_names':sum(x is not None for x in counts),'update_count_median_survivors':float(np.median([x for x in counts if x is not None])),'no_updates':sum(x==0 for x in counts),'nominal_all20_updates_retention':(1-cfg['params']['alpha'])**20}
 receipt={'trace_sha256':hashlib.sha256((root/'RESULT.json').read_bytes()).hexdigest(),'method':'inherited state multiplicative ratios; only original full-path band mask and exits; not changed-band counterfactual','parameters':{k:cfg['params'][k] for k in ('alpha','band','cap_mult')},'rows':stats,'endpoints':end,'model_identity':{}}
 for a in (1790222400,1790236800):
  t=json.loads(z.read(f'state/target_live/{a}.json'));receipt['model_identity'][str(a)]={k:t[k] for k in ('booster_sha','f10_sha')}
 with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps(end,indent=2))
if __name__=='__main__':main(*map(Path,sys.argv[1:]))
