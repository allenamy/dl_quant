"""Read immutable paths with one calendar/estimator; never reruns an engine."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[k]='1'
from pathlib import Path
from datetime import datetime
import hashlib,json,sys
import numpy as np

BASE=Path('/workspace/baseline_tables_2026-09-19')
NC=Path('/workspace/dlarch_2026-09-24/chain')
WINDOWS={
    'to_Aug30_complete':('2023-07-01T00:00Z','2026-08-30T20:00Z',True),
    'to_Sep18_complete':('2023-07-01T00:00Z','2026-09-18T20:00Z',True),
    'pre2026':('2023-07-01T00:00Z','2025-12-31T20:00Z',True),
    '2026_JanAug':('2026-01-01T00:00Z','2026-08-31T20:00Z',True),
    'legacy_partial_to_Aug31':('2023-06-30T04:00Z','2026-08-31T00:00Z',False),
    'legacy_partial_to_Sep18':('2023-06-30T04:00Z','2026-09-18T20:00Z',False),
}

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def ts(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp())

def main(out):
    cfgs=[BASE/'RUN_CONFIG_main_A0ext_2026-09-20.json',NC/'ref_nc_s42X/configs/RUN_CONFIG_DLARCH_REF_NC_s42X.json']
    configs=[json.loads(p.read_text()) for p in cfgs]
    r={'status':'READOUT_BRIDGE_NOT_COMPONENT_CAUSAL_ATTRIBUTION','source_sha256':sha(__file__),
       'python':sys.executable,'numpy':np.__version__,'windows':WINDOWS,
       'configs':{str(p):sha(p) for p in cfgs},'paths':{},'results':{},'mean_path_results':{},
       'common_settings_equal':{k:configs[0].get(k)==configs[1].get(k) for k in
            ('nav0_usdt','paths_R','current_production_config','events','unavailable_policies','simulator')},
       'pins':{}}
    for k in sorted(set(configs[0]['pins'])&set(configs[1]['pins'])):
        x,y=configs[0]['pins'][k],configs[1]['pins'][k]
        r['pins'][k]={'old_sha':x.get('sha256'),'nc_sha':y.get('sha256'),'same':x.get('sha256')==y.get('sha256')}
    for name,tag,root in [
        ('OLD_A0ext','OBJB_A0X_scaled_rule_raw_UAFE',BASE/'runs'),
        ('NC42','DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE',NC/'ref_nc_s42X/runs'),
        ('NC2027','DLARCH_REF_NC_s2027X_scaled_rule_raw_UAFE',NC/'ref_nc_s2027X/runs')]:
        per={w:[] for w in WINDOWS}; all_ret=[]; axis=None
        for k in range(32):
            p=root/tag/f'PATH_{tag}_seed_{k:02d}.npz'
            meta=json.loads(p.with_suffix('.json').read_text());h=sha(p)
            assert meta['npz_sha256']==h and int(meta['seed'])==k
            r['paths'][str(p)]=h
            with np.load(p) as z:
                a=z['A'].astype(np.int64);ret=z['navm1']/z['navm0']-1
                assert np.isfinite(ret).all() and np.all(np.diff(a)==14400)
                if axis is None: axis=a.copy()
                assert np.array_equal(axis,a)
                all_ret.append(ret.copy())
                for w,(lo,hi,complete) in WINDOWS.items():
                    m=(a>=ts(lo))&(a<=ts(hi));days,inv,counts=np.unique(a[m]//86400,return_inverse=True,return_counts=True)
                    if complete:
                        assert np.all(counts==6)
                        assert np.array_equal(a[m].reshape(-1,6),days[:,None]*86400+np.arange(6)*14400)
                    prod=np.ones(len(days));np.multiply.at(prod,inv,1+ret[m]);d=prod-1
                    per[w].append({'sharpe':float(d.mean()/d.std(ddof=1)*np.sqrt(365)),
                        'cagr':float(np.prod(1+d)**(365/len(d))-1),'return':float(np.prod(1+d)-1),
                        'n_days':len(d),'incomplete_days':int((counts!=6).sum())})
        r['results'][name]={w:{key:float(np.mean([v[key] for v in vals])) for key in vals[0]} for w,vals in per.items()}
        mean_ret=np.stack(all_ret).mean(0); r['mean_path_results'][name]={}
        for w,(lo,hi,complete) in WINDOWS.items():
            m=(axis>=ts(lo))&(axis<=ts(hi))
            days,inv=np.unique(axis[m]//86400,return_inverse=True)
            prod=np.ones(len(days));np.multiply.at(prod,inv,1+mean_ret[m]);d=prod-1
            r['mean_path_results'][name][w]={'sharpe':float(d.mean()/d.std(ddof=1)*np.sqrt(365)),
                'cagr':float(np.prod(1+d)**(365/len(d))-1),'return':float(np.prod(1+d)-1),'n_days':len(d)}
    with open(out,'x') as f:json.dump(r,f,indent=2,allow_nan=False)
    print(json.dumps({'sha256':sha(out),'results':r['results'],'mean_path_results':r['mean_path_results']}))

if __name__=='__main__':main(sys.argv[1])
