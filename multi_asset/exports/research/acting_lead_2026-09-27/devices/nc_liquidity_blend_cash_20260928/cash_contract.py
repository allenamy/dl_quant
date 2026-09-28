import hashlib,json
from pathlib import Path
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


def verify_record(p,pin):
    if sha(p)!=pin:raise ValueError('target result identity')
    r=json.loads(Path(p).read_text())
    if r.get('status')!='TARGET_IDENTITY_AND_SUPPORT_COMPLETE_NOT_ECONOMIC_VALIDATION':raise ValueError('targets incomplete')
    if r.get('baseline_fund_score_LR_seat_and_all_combo_arrays_exact') is not True:raise ValueError('baseline identity incomplete')
    if not r.get('seat_future_mutations') or not all(v is True for v in r['seat_future_mutations'].values()):raise ValueError('causality not verified')
    for b in ('inputs','sources','outputs'):
        for path,h in r[b].items():
            if sha(path)!=h:raise ValueError('target dependency drift: '+path)
    return r


def stress_r(r,tau):
    r,tau=np.asarray(r,float),np.asarray(tau,float)
    if r.shape!=tau.shape or not np.isfinite(r).all() or not np.isfinite(tau).all() or np.any(tau<0):raise ValueError('stress population')
    out=r-2*tau*5/10000
    if np.any(out<=-1):raise ValueError('stress return invalid')
    return out


def decide(r):
    checks=[]
    for seed in ('42','2027'):
        for w in ('pre2026','2026_JanAug'):
            x=r['results'][seed]['results'][w]
            for metric in ('paired_daily_bps','extra5bps_candidate_only_paired_daily_bps'):
                v=x[metric]
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v):raise ValueError('decision unknown')
                checks.append({'seed':seed,'window':w,'metric':metric,'value':v,'pass':v>0})
    ok=all(c['pass'] for c in checks)
    return {'status':'FOLLOWUP_COST_AND_FORWARD_VALIDATION_ONLY' if ok else 'FOLLOWUP_CRITERION_NOT_MET',
            'checks':checks,'production_authorized':False,'warning':'Historical selected configuration under pooled cost model; never a release decision.'}
