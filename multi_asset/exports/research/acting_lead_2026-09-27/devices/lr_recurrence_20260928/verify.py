"""Independent arithmetic check from retained arrays; no imports from runner."""
import hashlib,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<22),b''):h.update(b)
    return h.hexdigest()

def main(root):
    root=Path(root);r=json.loads((root/'RESULT.json').read_text());t=json.loads((root/'TERMINAL.json').read_text())
    assert t['rc']==0 and t['result_sha256']==sha(root/'RESULT.json')
    for p,h in r['inputs'].items():assert sha(p)==h,(p,'input_sha')
    for p,h in r['outputs'].items():assert sha(root/p)==h,(p,'output_sha')
    z=zipfile.ZipFile('/dev/shm/fetch_feature_alignment_20260928_inputs/PRODUCTION_INPUTS.zip');cfg=json.loads(z.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];look=cfg['params']['msharpe_look']
    history=np.load(root/'LR_STATES.npz',allow_pickle=False);states=np.load(root/'STATES.npz',allow_pickle=False)
    ctl=np.load('/dev/shm/gap_history_propagation_20260928/STATES.npz',allow_pickle=False)
    checks=0;mx=0.
    def eq(x,y,tol=1e-12):
        nonlocal checks,mx
        x,y=np.asarray(x),np.asarray(y);assert x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all()
        d=float(np.max(np.abs(x-y)));assert d<=tol,d;mx=max(mx,d);checks+=1
    def err(x,y):
        d=np.abs(x-y);return [d.sum(),d.max()]
    def recorded_err(v):return [v['l1'],v['max_abs']]
    for a in range(1790236800,1790553600+1,14400):
        eq(states[f'C5_control_{a}'],ctl[f'C5_{a}'],0)
        for name in ('C5_control','C6_event_fetch','C6_no_event','C6_unmasked_returns'):
            x=states[f'{name}_{a}'];eq(x[2],.55*x[0]+.45*x[1],0)
    counts={name:0 for name in ('C6_event_fetch','C6_no_event','C6_unmasked_returns')}
    for row in r['rows']:
        a=row['anchor'];js=json.loads(z.read(f'state/target_live/{a}.json'));actual=np.array([js['weights'].get(s,0.) for s in sy]);actual_lr=json.loads(z.read(f'state/snap/{a}/leg_returns_live.json'))
        aux=json.loads(z.read(f'state/snap/{a}/aux.json'))
        for name,summary in row['modes'].items():
            x=states[f'{name}_{a}'];eq(err(actual,x[2]),recorded_err(summary['target_error']))
            for i,k in enumerate(('kc','fc')):
                with np.load(io.BytesIO(z.read(f'fea171/state_H_{k}_{a}.npz')),allow_pickle=False) as h:
                    aa=np.zeros(len(sy));aa[h['idx'].astype(int)]=h['val']
                eq(err(aa,x[i]),recorded_err(summary['component_errors'][k]))
            if name=='C5_control':continue
            lr=history[f'{name}_{a}'];eq(err(np.array([actual_lr[k] for k in ('king','rev24','fund')]),lr),recorded_err(summary['lr_error']))
            rr=lr[:,-look:];s=np.maximum(np.mean(rr,axis=1)/(np.std(rr,axis=1)+1e-9),0);w=s/s.sum() if s.sum()>0 else np.ones(3)/3
            eq(w,summary['w3'])
            live=np.array([actual_lr[k][-look:] for k in ('king','rev24','fund')]);s=np.maximum(np.mean(live,axis=1)/(np.std(live,axis=1)+1e-9),0);w_live=s/s.sum() if s.sum()>0 else np.ones(3)/3
            eq(err(w_live,w),recorded_err(summary['seat_error']))
            good=summary['lr_error']['max_abs']<=1e-4 and summary['seat_error']['max_abs']<=1e-7 and summary['target_error']['max_abs']<=1e-8
            assert good==summary['within_fixed_tolerances'];checks+=1;counts[name]+=summary['appended']
    assert counts=={k:v for k,v in r['append_counts'].items() if k!='C5_control'}
    assert r['status']==('EVENT_AWARE_CONTINUOUS_TOLERANCE_PASS' if all(v['modes']['C6_event_fetch']['within_fixed_tolerances'] for v in r['rows']) else 'RESIDUAL_NOT_EXPLAINED')
    out={'utc':time.strftime('%FT%TZ',time.gmtime()),'status':'VERIFIED_REPORTED_ARITHMETIC_AND_IDENTITIES','checks':checks,'max_difference':mx,'result_sha256':sha(root/'RESULT.json'),'source_sha256':sha(__file__),'limits':['No independent feature rebuild or model training','Validates reported result including FAIL; does not upgrade it']}
    (root/'VERIFY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main(sys.argv[1])
