"""Start from an actual pre-NC state once; thereafter each arm owns its state."""
import importlib.util, json,time,zipfile
from pathlib import Path
import numpy as np
from alignment import sha,sparse,compare,PINS
from substitute import BASE,EXTRA,load_npz,load_state

def run_arm(step,E,start,initial,args_at,hold,live_seats):
    state={k:np.array(v,copy=True) for k,v in initial.items()};out=[]
    for i in range(start,len(E)):
        a=int(E[i])
        if a in hold:
            out.append({'i':i,'held':True,'kc':state['kc'].copy(),'fc':state['fc'].copy(),'raw':.55*state['kc']+.45*state['fc']});continue
        args=args_at(i);args.update(kc_prev=state['kc'],fc_prev=state['fc'])
        if live_seats is not None:
            if a not in live_seats:raise ValueError('live_seat_missing')
            args['seats']=live_seats[a].copy()
        r=step(**args)
        if not r['accepted']:raise ValueError('unexpected_publication_failure')
        state={k:np.array(r[k],copy=True) for k in ('kc','fc')};out.append({'i':i,'held':False,**{k:r[k].copy() for k in ('kc','fc','raw')}})
    return out

def main():
    started=time.monotonic();d=json.loads((BASE/'result/RESULT.json').read_text());sub=json.loads((BASE/'result/SUBSTITUTION.json').read_text())
    if sub['reference_exact_controls']!=54 or not sub['reference_corruption_refused']:raise ValueError('one_anchor_control_missing')
    for p,h in sub['inputs'].items():
        if sha(Path(p).read_bytes())!=h:raise ValueError('changed_prerequisite')
    z=zipfile.ZipFile(BASE/'result/PRODUCTION_INPUTS.zip')
    if sha((BASE/'result/PRODUCTION_INPUTS.zip').read_bytes())!=d['archive_sha256']:raise ValueError('archive_sha')
    data={name:load_npz((BASE/'research'/name).read_bytes()) for name in dict(PINS,**EXTRA) if name.endswith('.npz')}
    c=data['NC_s42_literal.npz'];l=data['LEGS_CONTINUATION.npz'];f=data['KING_FEATURES_AND_MEMBERS.npz'];pr=data['NC_F10_s42_PREDICTIONS.npz'];el=data['ELIGIBILITY.npz'];E=c['E_ts'];N=len(c['symbols']);sy=list(map(str,c['symbols']))
    params=json.loads((BASE/'research/bundle_config.json').read_text())['params'];src=BASE/'step_sources/devices/combo_target.py'
    spec=importlib.util.spec_from_file_location('frozen_step',src);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    start=int(np.flatnonzero(E==1790236800)[0]) # 2026-09-24 08:00 UTC
    if d['rows'][start]['utc']!='2026-09-24T08:00:00Z':raise ValueError('start_identity')
    hold={1790424000,1790438400,1790481600}
    if {int(r['anchor']) for r in d['rows'][start:] if r['model_status']!='SAME_MODEL_FILES'}!=hold:raise ValueError('observed_schedule_different')
    initial={k:load_state(z,k,int(E[start])-14400,N) for k in ('kc','fc')}
    ls={r['anchor']:np.asarray(r['live_w3']) for r in d['rows'][start:] if r['model_status']=='SAME_MODEL_FILES'}
    def args_at(i):
        pm=f['m'][f['off'][i]:f['off'][i+1]].astype(int)
        return dict(king_rank=l['KZ'][i,pm].astype(float),f10_score=pr['P'][i,pm].astype(float),fund_rank=l['ZFD'][i,pm].astype(float),seats=l['WL'][i].astype(float),rn8=l['RN8'][i,pm].astype(float),members=pm,qv=l['QV'][i,pm].astype(float),legal=el['legal'][i+1],params=params,publication='literal')
    results={};output={}
    for arm,sched,seats in [('C1',set(),None),('C2',hold,None),('C3',hold,ls)]:
        run=run_arm(m.step,E,start,initial,args_at,sched,seats);results[arm]=[]
        for r in run:
            i=r['i'];a=int(E[i]);output[f'{arm}_{a}']=np.stack([r[k] for k in ('kc','fc','raw')])
            if d['rows'][i]['model_status']!='SAME_MODEL_FILES':continue
            target=json.loads(z.read(f'state/target_live/{a}.json'));live=np.array([target['weights'].get(s,0.) for s in sy]);results[arm].append({'anchor':a,'utc':d['rows'][i]['utc'],'error':compare(live,r['raw'])})
    np.savez_compressed(BASE/'result/CONTINUOUS_STATES.npz',**output)
    rec={'schema':'single_seed_continuous_state_diagnostic/1','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(Path(__file__).read_bytes()),'parent_substitution_sha256':sha((BASE/'result/SUBSTITUTION.json').read_bytes()),'states_sha256':sha((BASE/'result/CONTINUOUS_STATES.npz').read_bytes()),'start_anchor':int(E[start]),'seed_anchor':int(E[start])-14400,'hold_anchors':sorted(hold),'rows':results,'seconds':time.monotonic()-started,'limits':['Production H injected once only, never at subsequent measured anchors','Live LR seats in C3 are observed state inputs, not independently recreated leg histories','HOLD preserves producer smoothing state, not venue inventory or live cash','Remaining signal and F10 input differences retained; no return or release claim']}
    (BASE/'result/CONTINUOUS.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');print({'published_rows_per_arm':{k:len(v) for k,v in results.items()},'seconds':rec['seconds']})

if __name__=='__main__':main()
