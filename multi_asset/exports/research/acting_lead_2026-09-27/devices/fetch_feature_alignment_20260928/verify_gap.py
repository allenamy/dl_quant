"""Independently verify C5 saved-state arithmetic and frozen population, without rerunning."""
import io,json,time,zipfile
from pathlib import Path
import numpy as np
from run import sha,load

def main():
    root=Path('/dev/shm/gap_history_propagation_20260928');fetch=Path('/dev/shm/fetch_feature_alignment_20260928');parent=Path('/dev/shm/fetch_feature_alignment_20260928_inputs')
    r=json.loads((root/'RESULT.json').read_text());t=json.loads((root/'TERMINAL.json').read_text());old=json.loads((fetch/'RESULT.json').read_text());checks=[];errmax=0.
    def ck(name,v):
        checks.append(name)
        if not bool(v):raise ValueError(name)
    ck('terminal',t['rc']==0 and t['result_sha256']==sha(root/'RESULT.json'))
    for p,h in r['inputs'].items():ck('input:'+p,sha(p)==h)
    for n,h in r['outputs'].items():ck('output:'+n,sha(root/n)==h)
    ck('fixed_population',[x['anchor'] for x in r['rows']]==[x['anchor'] for x in old['rows']['C4_fetch']])
    z=zipfile.ZipFile(parent/'PRODUCTION_INPUTS.zip');sy=json.loads(z.read('shadow_bundle/config.json'))['symbols_panel']
    new=load(root/'STATES.npz');ref=load(fetch/'STATES.npz');gap=(1790424000,1790438400,1790481600)
    ck('23_states',len(new)==23)
    for row in r['rows']:
        a=row['anchor'];s=new[f'C5_{a}'];w=json.loads(z.read(f'state/target_live/{a}.json'))['weights'];live=np.array([w.get(n,0.) for n in sy]);d=np.abs(s[2]-live)
        ck(f'{a}_finite',np.isfinite(s).all());ck(f'{a}_identity',np.array_equal(s[2],.55*s[0]+.45*s[1]))
        for k,v in [('l1',d.sum()),('max_abs',d.max()),('actual_gross',np.abs(live).sum())]:
            e=abs(float(v)-row['error'][k]);errmax=max(errmax,e);ck(f'{a}_{k}',e<1e-14)
        ck(f'{a}_criterion',row['max_error_le_1e8']==bool(d.max()<=1e-8))
        for i,leg in enumerate(('kc','fc')):
            with np.load(io.BytesIO(z.read(f'fea171/state_H_{leg}_{a}.npz')),allow_pickle=False) as h:
                ck(f'{a}_{leg}_anchor',int(h['anchor'])==a);v=np.zeros(len(sy));v[h['idx'].astype(int)]=h['val']
            delta=np.abs(v-s[i]);ck(f'{a}_{leg}_l1',abs(float(delta.sum())-row['component_errors'][leg]['l1'])<1e-14)
        if a<gap[0]:ck(f'{a}_pre_gap_unchanged',np.array_equal(s,ref[f'C4_fetch_{a}']))
        else:
            f=load(root/f'ROW_{a}.npz');before=load(fetch/f'ROW_{a}.npz')
            for k in ('m','king_X78','KZ','ZFD','Z24','QV','RN8'):ck(f'{a}_{k}_unchanged',np.array_equal(f[k],before[k]))
            ck(f'{a}_features_finite',all(np.isfinite(f[k]).all() for k in ('X82','X89','P')))
    for a in gap:ck(f'{a}_hold',np.array_equal(new[f'C5_{a}'],new[f'C5_{a-14400}']))
    for h in r['history_checks']:
        ck(f'{h["anchor"]}_only_known_past_holes',h['removed_known_holes']==[a for a in gap if a<h['anchor']])
        ck(f'{h["anchor"]}_count',h['expected_missing']==h['actual_missing']==len(h['removed_known_holes']))
    ck('status',r['status']==('CONDITIONAL_TARGET_TOLERANCE_PASS' if all(x['max_error_le_1e8'] for x in r['rows']) else 'RESIDUAL_NOT_EXPLAINED'))
    out={'status':'SAVED_ARRAYS_VERIFIED','checks':len(checks),'max_arithmetic_error':errmax,'utc':time.strftime('%FT%TZ',time.gmtime()),'result_sha256':sha(root/'RESULT.json'),'source_sha256':sha(__file__),'max_target_error':max(x['error']['max_abs'] for x in r['rows']),'passed_anchors':sum(x['max_error_le_1e8'] for x in r['rows']),'limits':['Not an independent feature rebuild or PnL test','Conditional live seats remain supplied']}
    (root/'VERIFY.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
