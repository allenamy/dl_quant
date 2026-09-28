"""Verify final identities and arithmetic from saved arrays, no retraining or strategy judgment."""
import hashlib,io,json,sys,zipfile,time
from pathlib import Path
import numpy as np

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<22),b''):h.update(b)
    return h.hexdigest()
def load(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def main(root,parent):
    root,parent=Path(root),Path(parent);rec=json.loads((root/'RESULT.json').read_text());term=json.loads((root/'TERMINAL.json').read_text());rows=rec['rows'];checks=[];maxerr=0.
    def check(k,v):
        checks.append(k)
        if not bool(v):raise ValueError(k)
    check('terminal',term['rc']==0 and term['result_sha256']==sha(root/'RESULT.json'))
    for p,h in rec['inputs'].items():check('input_sha:'+p,sha(p)==h)
    for name,h in rec['outputs'].items():check('output_sha:'+name,sha(root/name)==h)
    arc=zipfile.ZipFile(parent/'PRODUCTION_INPUTS.zip');cfg=json.loads(arc.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];old=load(parent/'CONTINUOUS_STATES.npz');new=load(root/'STATES.npz')
    check('arms',set(rows)=={'C3_control','C4_fetch'})
    check('population',[r['anchor'] for r in rows['C3_control']]==[r['anchor'] for r in rows['C4_fetch']] and len(rows['C4_fetch'])==20)
    details=[]
    for arow in rows['C4_fetch']:
        a=arow['anchor'];f=load(root/f'ROW_{a}.npz');aux=json.loads(arc.read(f'state/snap/{a}/aux.json'));target=json.loads(arc.read(f'state/target_live/{a}.json'));live=np.array([target['weights'].get(s,0.) for s in sy])
        check(str(a)+' anchor',int(f['anchor'])==a)
        check(str(a)+' actual_members',np.array_equal(f['m'],aux['prev_rec']['members']))
        check(str(a)+' finite_models',np.isfinite(f['king_X78']).all() and np.isfinite(f['X82']).all() and np.isfinite(f['X89']).all() and np.isfinite(f['P']).all())
        component_errors={}
        actual_h=[]
        for leg in ('kc','fc'):
            with np.load(io.BytesIO(arc.read(f'fea171/state_H_{leg}_{a}.npz')),allow_pickle=False) as h:
                check(f'{a} {leg} state_anchor',int(h['anchor'])==a)
                vec=np.zeros(len(sy));vec[h['idx'].astype(int)]=h['val'];actual_h.append(vec)
        for arm in rows:
            row=next(r for r in rows[arm] if r['anchor']==a);state=new[f'{arm}_{a}'];d=np.abs(state[2]-live)
            check(f'{a} {arm} raw_identity',np.array_equal(state[2],.55*state[0]+.45*state[1]))
            for k,v in [('l1',float(d.sum())),('max_abs',float(d.max())),('actual_gross',float(np.abs(live).sum()))]:
                de=abs(row['error'][k]-v);maxerr=max(maxerr,de);check(f'{a} {arm} {k}',de<1e-14)
            if arm=='C3_control':check(str(a)+' unchanged_reference',np.array_equal(state,old[f'C3_{a}']))
            component_errors[arm]={leg:{'l1':float(np.abs(state[i]-actual_h[i]).sum()),'max_abs':float(np.abs(state[i]-actual_h[i]).max())} for i,leg in enumerate(('kc','fc'))}
        ref=load(Path('/dev/shm/recent_f10_features_20260928')/f'ROW_{a}.npz');common=np.intersect1d(f['m'],ref['members']);p={int(s):i for i,s in enumerate(f['m'])};q={int(s):i for i,s in enumerate(ref['members'])};d={}
        for k in ('X82','X89'):
            x=f[k][[p[int(s)] for s in common]];y=ref[k][[q[int(s)] for s in common]];delta=np.abs(x-y)
            d[k]={'common_names':len(common),'different_cells':int(np.count_nonzero(delta)),'max_abs':float(delta.max())}
        details.append({'anchor':a,'feature_changes_on_common_names':d,'component_errors':component_errors})
    for a in (1790424000,1790438400,1790481600):
        for arm in rows:check(f'{a} {arm} HOLD',np.array_equal(new[f'{arm}_{a}'],new[f'{arm}_{a-14400}']))
    out={'status':'VERIFIED_SAVED_ARRAYS_NOT_PNL','utc':time.strftime('%FT%TZ',time.gmtime()),'checks':len(checks),'max_arithmetic_error':maxerr,'result_sha256':sha(root/'RESULT.json'),'source_sha256':sha(__file__),'feature_differences':details,'limits':['Does not independently rerun model training or feature pipeline','Conditional live LR inputs remain conditional']}
    (root/'VERIFY.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print({k:out[k] for k in ('status','checks','max_arithmetic_error')})
if __name__=='__main__':main(*sys.argv[1:])
