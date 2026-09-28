"""Fixed twenty-anchor independent LR/state propagation. No exchange, PnL or training."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR')
import copy,hashlib,importlib.util,io,json,sys,time,traceback,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import recurrence as C

FETCH=Path('/dev/shm/fetch_feature_alignment_20260928')
GAP=Path('/dev/shm/gap_history_propagation_20260928')
PARENT=Path('/dev/shm/fetch_feature_alignment_20260928_inputs')
INPUT=Path('/dev/shm/lr_recurrence_20260928_inputs')
ROLL=Path('/dev/shm/recent_rolling_inputs_20260928')
START=1790236800;END=1790553600;EVENT=1790413200
GAPS={1790424000,1790438400,1790481600}
FETCH_SHA='e40122efbc5277cbdf0ec8f48df33401574037948b09e33bbe7d0de21eaf466a'
GAP_SHA='f4ce13035843f7ddba97bcf299c83cb09c27a685cc029098e471d4ca1f327afd'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<22),b''):h.update(b)
    return h.hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def load(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def error(a,b):
    x=np.abs(np.asarray(a)-np.asarray(b));return {'l1':float(x.sum()),'max_abs':float(x.max())}

def main(root):
    t0=time.monotonic();root=Path(root);root.mkdir(exist_ok=False)
    save(root/'START.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),'pid':os.getpid(),'pgid':os.getpgid(0),'ticks':Path('/proc/self/stat').read_text().split()[21],'budget_seconds':300})
    pins={};outputs={}
    for base,expected in ((FETCH,FETCH_SHA),(GAP,GAP_SHA)):
        if sha(base/'RESULT.json')!=expected:raise ValueError('parent_identity')
        rec=json.loads((base/'RESULT.json').read_text());term=json.loads((base/'TERMINAL.json').read_text())
        if term['rc']!=0 or term['result_sha256']!=expected:raise ValueError('parent_terminal')
        pins[str(base/'RESULT.json')]=expected;pins[str(base/'TERMINAL.json')]=sha(base/'TERMINAL.json')
        for p,h in rec['inputs'].items():
            if p in pins and pins[p]!=h:raise ValueError('input_identity_conflict')
            pins[p]=h
        for name,h in rec['outputs'].items():pins[str(base/name)]=h
    ident=json.loads((INPUT/'INPUT_IDENTITY.json').read_text())
    for name,h in ident['files'].items():pins[str(INPUT/name)]=h
    for p in (INPUT/'INPUT_IDENTITY.json',Path(C.__file__),Path(__file__),Path(__file__).with_name('test_recurrence.py')):pins[str(p.resolve())]=sha(p)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input_changed:'+p)
    archive=PARENT/'PRODUCTION_INPUTS.zip';z=zipfile.ZipFile(archive)
    parent=json.loads((PARENT/'RESULT.json').read_text())
    for name,row in parent['production_inputs'].items():
        if hashlib.sha256(z.read(name)).hexdigest()!=row['sha256']:raise ValueError('archive_member_changed')
    cfg=json.loads(z.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];n=len(sy);params=cfg['params']
    rows=[r for r in parent['rows'] if START<=r['anchor']<=END and r['model_status']=='SAME_MODEL_FILES'];by={r['anchor']:r for r in rows}
    if len(rows)!=20:raise ValueError('twenty_population')
    ax=load(ROLL/'axes.npz');ts=ax['ts'];cols=ax['crypto_cols'];rr=np.load(ROLL/'R_crypto.npy',mmap_mode='r')
    if ax['symbols'].tolist()!=sy:raise ValueError('symbol_axis')
    el=load('/dev/shm/recent_nc_combo_20260928/ELIGIBILITY.npz');legal={int(a):el['legal'][i] for i,a in enumerate(el['E_ts'])}
    p=Path('/dev/shm/news2_2026-09-23/devices/combo_target.py');spec=importlib.util.spec_from_file_location('lr_combo',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);step=mod.step
    advance,seats=C.production_blocks(INPUT/'shadow_loop_v3.py')
    seed=START-14400;aux=json.loads(z.read(f'state/snap/{seed}/aux.json'));initial=json.loads(z.read(f'state/snap/{seed}/leg_returns_live.json'));C.validate_lr(initial)
    installed=json.loads((INPUT/'leg_returns_live.NEW.json').read_text());build=json.loads((INPUT/'BUILD.json').read_text());install=json.loads((INPUT/'INSTALL_20260926T0900Z.json').read_text())
    if build['candidate_sha256']!=sha(INPUT/'leg_returns_live.NEW.json') or install['leg_returns_live_sha256']!=build['candidate_sha256']:raise ValueError('reseed_identity')
    pre=z.read('state/snap/1790409600/leg_returns_live.json')
    if hashlib.sha256(pre).hexdigest()!=build['inputs']['live_file_sha256']:raise ValueError('reseed_predecessor')
    if ident['installed_utc']!='20260926T0900Z' or ident['generation_anchor']!='2026-09-26T08:00Z':raise ValueError('event_timestamp')
    def hstate(k,a):
        with np.load(io.BytesIO(z.read(f'fea171/state_H_{k}_{a}.npz')),allow_pickle=False) as f:
            if int(f['anchor'])!=a:raise ValueError('H_anchor')
            x=np.zeros(n);x[f['idx'].astype(int)]=f['val'];return x
    names=('C5_control','C6_event_fetch','C6_no_event','C6_unmasked_returns')
    modes={name:{'st':SimpleNamespace(last_anchor=seed,prev_rec=copy.deepcopy(aux['prev_rec']),LR=copy.deepcopy(initial)),'event_done':False,'h':{k:hstate(k,seed) for k in ('kc','fc')}} for name in names}
    reference=load(GAP/'STATES.npz');states={};history={};result=[];control_count=0;append_counts={name:0 for name in names};event_anchors={}
    for a in range(START,END+1,14400):
        if time.monotonic()-t0>300:raise TimeoutError('budget_300s')
        for name,d in modes.items():
            if name not in ('C5_control','C6_no_event'):
                was=d['event_done'];d['event_done']=C.reseed(d['st'],was,a,EVENT,installed)
                if not was and d['event_done']:event_anchors[name]=a
        if a not in GAPS:
            if a not in by:raise ValueError('missing_processed_anchor')
            fp=(GAP if a>=min(GAPS) else FETCH)/f'ROW_{a}.npz';f=load(fp);fa=json.loads(z.read(f'state/snap/{a}/aux.json'))
            fetch=fa['fetch_syms']
            if fa['last_anchor']!=a or len(fetch)!=len(set(fetch)) or any(s not in sy for s in fetch):raise ValueError('fetch_identity')
            mask=np.array([s in set(fetch) for s in sy]);actual_lr=json.loads(z.read(f'state/snap/{a}/leg_returns_live.json'));C.validate_lr(actual_lr)
            actual_raw=np.array([json.loads(z.read(f'state/target_live/{a}.json'))['weights'].get(s,0.) for s in sy])
            args={k:f[v].astype(float) for k,v in [('king_rank','KZ'),('fund_rank','ZFD'),('rn8','RN8'),('qv','QV'),('f10_score','P')]}
            measured={}
            for name,d in modes.items():
                st=d['st'];before=len(st.LR['king'])
                if name=='C5_control':w=np.asarray(by[a]['live_w3'])
                else:
                    x=C.segment(ts,rr,cols,a,n,np.ones(n,bool) if name=='C6_unmasked_returns' else mask)
                    row_of={int(tsi):j for j,tsi in enumerate(range(a-14400,a+1,300))}
                    advance(st,a,x,row_of,48);append_counts[name]+=len(st.LR['king'])-before
                    w=seats(st,params)
                out=step(**args,seats=w,members=f['m'],legal=legal[a],params=params,kc_prev=d['h']['kc'],fc_prev=d['h']['fc'],publication='literal')
                if not out['accepted']:raise ValueError('publication_failed:'+name)
                d['h']={k:out[k].copy() for k in ('kc','fc')}
                st.prev_rec={'anchor_ts':a,'members':f['m'].tolist(),'legz':{k:f[v].astype(float).tolist() for k,v in [('king','KZ'),('rev24','Z24'),('fund','ZFD')]}};st.last_anchor=a
                lrarr=np.array([st.LR[k][-950:] for k in C.LEGS]);history[f'{name}_{a}']=lrarr
                raw=.55*d['h']['kc']+.45*d['h']['fc'];target_error=error(actual_raw,raw)
                measured[name]={'w3':w.tolist(),'target_error':target_error,'component_errors':{k:error(hstate(k,a),d['h'][k]) for k in ('kc','fc')}}
                if name!='C5_control':
                    lrerr=error(np.array([actual_lr[k] for k in C.LEGS]),lrarr);we=error(by[a]['live_w3'],w)
                    measured[name].update(lr_error=lrerr,seat_error=we,appended=len(st.LR['king'])>before,within_fixed_tolerances=lrerr['max_abs']<=1e-4 and we['max_abs']<=1e-7 and target_error['max_abs']<=1e-8)
            result.append({'anchor':a,'utc':by[a]['utc'],'modes':measured})
        for name,d in modes.items():
            h=d['h'];stack=np.stack((h['kc'],h['fc'],.55*h['kc']+.45*h['fc']));states[f'{name}_{a}']=stack
            if name=='C5_control':
                if not np.array_equal(stack,reference[f'C5_{a}']):raise ValueError('C5_state_not_bitwise')
                control_count+=1
    if control_count!=23 or any(append_counts[n]!=18 for n in names if n!='C5_control'):raise ValueError('state_population')
    for name,arrays in (('STATES.npz',states),('LR_STATES.npz',history)):
        np.savez_compressed(root/name,**arrays);outputs[name]=sha(root/name)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input_mutated:'+p)
    r={'utc':time.strftime('%FT%TZ',time.gmtime()),'status':'EVENT_AWARE_CONTINUOUS_TOLERANCE_PASS' if all(r['modes']['C6_event_fetch']['within_fixed_tolerances'] for r in result) else 'RESIDUAL_NOT_EXPLAINED','inputs':pins,'outputs':outputs,'rows':result,'C5_exact_state_controls':control_count,'append_counts':append_counts,'event_applied_before_anchor':event_anchors,'seconds':time.monotonic()-t0,'python':sys.executable,'python_version':sys.version,'numpy':np.__version__,'env':{k:os.environ[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NPY_DISABLE_CPU_FEATURES')},'limits':['Single archived initial LR/H/prev_rec','Actual historical fetch and HOLD policy plus recorded reseed event','Float32 stored leg scores; tolerance not bitwise','Not full history, cash certification or new strategy']}
    save(root/'RESULT.json',r);save(root/'TERMINAL.json',{'rc':0,'utc':time.strftime('%FT%TZ',time.gmtime()),'result_sha256':sha(root/'RESULT.json')})

if __name__=='__main__':
    try:main(sys.argv[1])
    except BaseException as e:
        p=Path(sys.argv[1]);p.mkdir(exist_ok=True);save(p/'TERMINAL.json',{'rc':1,'utc':time.strftime('%FT%TZ',time.gmtime()),'error':repr(e),'traceback':traceback.format_exc()});raise
