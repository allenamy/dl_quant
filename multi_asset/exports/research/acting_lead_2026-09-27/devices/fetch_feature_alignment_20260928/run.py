"""Single fixed fetch-input substitution through features and continuous combo, no training/PnL."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NC_WS='/dev/shm/nc_2026-09-23/ws',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR')
import ast,hashlib,importlib.util,io,json,sys,time,types,zipfile,traceback
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

BASE=Path('/dev/shm/nc_2026-09-23');NS=Path('/dev/shm/news2_2026-09-23');PARENT=Path('/dev/shm/fetch_feature_alignment_20260928_inputs')
OLD=Path('/dev/shm/recent_f10_features_20260928');START=1790236800;HOLD={1790424000,1790438400,1790481600}
PINS={str(BASE/'devices/nc_hist_features.py'):'3eee6e8842eb86cf203c8eb86c55e7c33d8a18532c080fda0376c317d7cda343',str(BASE/'devices/nc_legs.py'):'18387627f8426a45135b348dd4508281b4811894c91eb50af87751760609c0a0',str(BASE/'tree/PATCH_RECEIPT.json'):'88a9d426c30015809c3d2b4e8a89db8a618ea3d7d6766ed79c4993102e344612',str(NS/'work/king/king_2026.txt'):'700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d',str(NS/'deploy/f10_live_s42_np.npz'):'3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f',str(NS/'devices/combo_target.py'):'d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544',str(NS/'work/NEWS_FEATURES.npz'):'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',str(PARENT/'RESULT.json'):'b40a925c9a3b4c81473199701c2bc0ccd9e2e10551c67a4ac4041ca88bc1a52e',str(PARENT/'CONTINUOUS.json'):'c448a83eb5a24c9df353a344fd959edf36ea18c516f87479621157aa9ec5e52d'}

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<22),b''):h.update(b)
    return h.hexdigest()
def load(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def same(x,y):return np.asarray(x).dtype==np.asarray(y).dtype and np.asarray(x).shape==np.asarray(y).shape and np.asarray(x).tobytes()==np.asarray(y).tobytes()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def imp(p,name):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def selected_fetch(aux,anchor,sy):
    if type(aux.get('last_anchor')) is not int or aux['last_anchor']!=anchor:raise ValueError('actual_fetch_anchor')
    names=aux.get('fetch_syms')
    if not isinstance(names,list) or not names or len(names)!=len(set(names)) or any(s not in sy for s in names):raise ValueError('invalid_actual_fetch')
    if aux.get('nc_backfill_residual'):raise ValueError('backfill_exclusion_requires_explicit_mask')
    return names,np.array([s in set(names) for s in sy],bool)
def history_asof(history,a):
    if a not in history:raise ValueError('missing_current_members')
    return {t:v.copy() for t,v in history.items() if t<=a}
def inference(source,model):
    start=source.index('from scipy.special import erf\n');end=source.index('# 对齐到 pm 序',start)
    ns={'np':np,'M':model};code=compile(source[start:end],'pinned_production_numpy_inference','exec')
    def f(x):
        ns['X171']=x;exec(code,ns);v=ns['f10'].copy()
        if v.shape!=(len(x),) or not np.isfinite(v).all():raise ValueError('inference_invalid')
        return v
    return f,hashlib.sha256(source[start:end].encode()).hexdigest()
def ranks_equal(a,b):
    a,b=np.asarray(a),np.asarray(b)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('invalid_rank_population')
    return bool(np.array_equal(rankdata(a),rankdata(b)))
def error(a,b):
    d=np.abs(a-b);return {'l1':float(d.sum()),'max_abs':float(d.max()),'actual_gross':float(np.abs(a).sum())}
def resources():
    mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    if mem['MemAvailable']<8*2**30:raise RuntimeError('shared_available_memory_below_8GiB')
    rss=0
    for d in Path('/proc').iterdir():
        if not d.name.isdigit():continue
        try:
            r={l.split(':')[0]:l.split(':',1)[1].strip() for l in (d/'status').read_text().splitlines()}
            if int(r['Uid'].split()[0])==os.getuid():rss+=int(r.get('VmRSS','0 kB').split()[0])*1024
        except (OSError,KeyError,ValueError):continue
    if rss>30*2**30:raise RuntimeError('shared_uid_RSS_above_30GiB')
    return rss

def main(root):
    start=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);pins=PINS.copy();pins[str(Path(__file__).resolve())]=sha(__file__);peak=resources()
    save(root/'START.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),'pid':os.getpid(),'pgid':os.getpgid(0),'ticks':Path('/proc/self/stat').read_text().split()[21],'budget_seconds':900,'pins':pins})
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('fixed_source_changed:'+p)
    parent=json.loads((PARENT/'RESULT.json').read_text());cont=json.loads((PARENT/'CONTINUOUS.json').read_text());arc=PARENT/'PRODUCTION_INPUTS.zip'
    if sha(arc)!=parent['archive_sha256'] or sha(PARENT/'CONTINUOUS_STATES.npz')!=cont['states_sha256']:raise ValueError('parent_artifact')
    pins[str(arc)]=sha(arc);pins[str(PARENT/'CONTINUOUS_STATES.npz')]=sha(PARENT/'CONTINUOUS_STATES.npz')
    z=zipfile.ZipFile(arc);cfg=json.loads(z.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];N=len(sy);params=cfg['params']
    for name,v in parent['production_inputs'].items():
        if hashlib.sha256(z.read(name)).hexdigest()!=v['sha256']:raise ValueError('parent_archive_member:'+name)
    sys.path.insert(0,str(BASE/'devices'));H=imp(BASE/'devices/nc_hist_features.py','Hfixed');H.set_tree(str(BASE/'tree'))
    L=imp(BASE/'devices/nc_legs.py','Lfixed');L.H.set_tree(str(BASE/'tree'));xz_base,xz=L.prod_funcs();kingblock=H._king_block()
    def certified(path):
        path=Path(path);r=json.loads((path/'RESULT.json').read_text());t=json.loads((path/'TERMINAL.json').read_text())
        if t.get('rc')!=0 or sha(path/'RESULT.json')!=t.get('result_sha256'):raise ValueError('uncertified_upstream:'+str(path))
        pins[str(path/'RESULT.json')]=sha(path/'RESULT.json')
        items=r.get('outputs',{})
        if 'output' in r:
            oo=r['output'];items={Path(oo.get('path','FUND_CONTINUATION.npz')).name:oo}
        for name,v in items.items():
            p=path/name;h=v['sha256'] if isinstance(v,dict) else v
            if sha(p)!=h:raise ValueError('upstream_output_changed:'+str(p))
            pins[str(p)]=h
        return r
    wr=Path('/dev/shm/recent_rolling_inputs_20260928');fr=Path('/dev/shm/recent_funding_continuation_20260928_materialized')
    for p in (wr,fr,Path('/dev/shm/recent_king_features_20260928'),OLD,Path('/dev/shm/recent_nc_predictions_20260928'),Path('/dev/shm/recent_nc_legs_20260928_attempt3'),Path('/dev/shm/recent_nc_combo_20260928')):certified(p)
    oldrec=json.loads((OLD/'RESULT.json').read_text());ax=load(wr/'axes.npz');bd=load(wr/'boundary.npz');fund=load(fr/'FUND_CONTINUATION.npz')
    K=load('/dev/shm/recent_king_features_20260928/KING_FEATURES_AND_MEMBERS.npz');legs=load('/dev/shm/recent_nc_legs_20260928_attempt3/LEGS_CONTINUATION.npz');pred=load('/dev/shm/recent_nc_predictions_20260928/NC_F10_s42_PREDICTIONS.npz');combo=load('/dev/shm/recent_nc_combo_20260928/NC_s42_literal.npz');elig=load('/dev/shm/recent_nc_combo_20260928/ELIGIBILITY.npz')
    E=K['anchors'];I=H.Inputs();I.ts=ax['ts'];I.anchors=E;I.C=np.load(wr/'cache_crypto.npy',mmap_mode='r');I.R=np.load(wr/'R_crypto.npy',mmap_mode='r');I.bt=bd['ts'];I.bc=bd['col'];I.br=bd['raw']
    if I.syms!=sy or not np.array_equal(E,fund['anchors']) or not np.array_equal(K['symbols'],sy) or not np.array_equal(elig['E_ts'][1:],E):raise ValueError('input_axes')
    def funding(self,A):
        i=int(np.searchsorted(E,A))
        if i>=len(E) or E[i]!=A:raise ValueError('funding_anchor')
        ema,led={},{}
        for j in self.cols:
            if fund['ledger_ft'][i,j]<0:continue
            acc,iv,last=fund['acc'][i,j],fund['iv'][i,j],int(fund['last_ts'][i,j]);s=sy[j]
            ema[s]={'acc':None if np.isnan(acc) else float(acc),'last_ts':None if last<0 else last};led[s]=[[int(fund['ledger_ft'][i,j]),float(fund['rate'][i,j]),None if np.isnan(iv) else float(iv)]]
        return ema,led
    I.funding=types.MethodType(funding,I)
    with np.load(NS/'work/NEWS_FEATURES.npz') as f:old={k:f[k] for k in ('anchors','off','m')}
    MH={int(a):old['m'][old['off'][i]:old['off'][i+1]].astype(np.int64) for i,a in enumerate(old['anchors'])}
    for i,a in enumerate(E):MH[int(a)]=K['m'][K['off'][i]:K['off'][i+1]].astype(np.int64)
    variant_mh={k:v.copy() for k,v in MH.items()};rows=[r for r in parent['rows'] if r['anchor']>=START and r['model_status']=='SAME_MODEL_FILES']
    if len(rows)!=20:raise ValueError('fixed_twenty_population')
    selected={r['anchor'] for r in rows};frows={};checks=[]
    import lightgbm as lgb
    king=lgb.Booster(model_file=str(NS/'work/king/king_2026.txt'));model=load(NS/'deploy/f10_live_s42_np.npz');predict,np_source_sha=inference(Path(H.COMBO_SRC).read_text(),model)
    for row in rows:
        a=row['anchor'];i=int(np.flatnonzero(E==a)[0]);sl=slice(K['off'][i],K['off'][i+1]);aux=json.loads(z.read(f'state/snap/{a}/aux.json'))
        names,mask=selected_fetch(aux,a,sy);original=H.pass1_anchor(I,a,params,cfg,kingblock)
        for key in ('m','king_X78','fe_v','fn_v','iv_v','qvm','rev24'):
            if not same(original[key],K[key][sl]):raise ValueError('original_King_control:'+key+':'+str(a))
        ts,cd,rr,(bt,bc,br)=I.window(a);st=H._St();st.cts=ts;st.cd=cd;st.bnd_ts=bt;st.bnd_col=bc;st.bnd_raw=br;st.crypto=I.crypto;st.fetch=names;st.fetch_mask=mask;st.syms=sy;st.NW=N;st.sym_idx={s:j for j,s in enumerate(sy)};st.ema,st.ledger=I.funding(a);st.record_members=lambda _a,_m:None
        o=kingblock(st,a,params,cfg,{int(t):i for i,t in enumerate(ts)},names,H._Diag(),lambda x:None);m=o['m']
        if not np.array_equal(m,aux['prev_rec']['members']):raise ValueError('variant_member_not_actual:'+str(a))
        variant_mh[a]=m.astype(np.int64);kp=king.predict(o['X'],num_threads=1).astype(np.float32)
        kz=xz(kp).astype(np.float32);fd=xz_base(o['fe_v'][m],[sy[j] for j in m],o['base_vals']).astype(np.float32);rv=xz(-o['wstat'](0,288,'sum')[m]).astype(np.float32)
        qv=(np.expm1(np.clip(o['qvm'][m].astype(np.float64),0,30))*48).astype(np.float32)
        ema,led=I.funding(a);rn=np.array([H._G['NC'].funding_asof(ema.get(sy[j]),led[sy[j]][-1],a)[3] if sy[j] in led else np.nan for j in m],np.float32)
        frows[a]={'m':m,'KZ':kz,'ZFD':fd,'Z24':rv,'QV':qv,'RN8':rn,'king_X78':o['X']}
        checks.append({'anchor':a,'original_king_fields_exact':True,'variant_members_exact':True,'KZ_equal_actual_f32':same(kz,np.asarray(aux['prev_rec']['legz']['king'],np.float32)),'ZFD_equal_actual_f32':same(fd,np.asarray(aux['prev_rec']['legz']['fund'],np.float32))})
    mini=H._mini_block();cf=H._combo_funcs();scratch=root/'scratch';scratch.mkdir();outputs={};old_control=[]
    for row in rows:
        a=row['anchor'];i=int(np.flatnonzero(E==a)[0])
        if time.monotonic()-start>860:raise TimeoutError('budget_900s')
        peak=max(peak,resources())
        ref=load(OLD/f'ROW_{a}.npz');xm=np.concatenate((ref['X82'],ref['X89']),axis=1).astype(np.float32);oldp=predict(xm);om=MH[a]
        if not ranks_equal(oldp,pred['P'][i,om]):raise ValueError('numpy_inference_changed_reference_ranks:'+str(a))
        if a in (START,START+14400):
            r=H.pass2_anchor(I,a,history_asof(MH,a),str(scratch),mini,cf)
            if not all(same(np.asarray(r[k],np.float32),ref[k]) for k in ('X82','X89')):raise ValueError('old_f10_feature_control:'+str(a))
            old_control.append(a)
        r=H.pass2_anchor(I,a,history_asof(variant_mh,a),str(scratch),mini,cf);xx=np.concatenate((r['X82'],r['X89']),axis=1).astype(np.float32)
        if r['mh_missing']!=0 or not np.isfinite(xx).all():raise ValueError('variant_features_unknown')
        frows[a]['P']=predict(xx);p=root/f'ROW_{a}.npz';np.savez_compressed(p,anchor=np.int64(a),X82=r['X82'],X89=r['X89'],**frows[a]);outputs[p.name]=sha(p)
        print(time.strftime('%FT%TZ',time.gmtime()),'FEATURE_ROW',a,flush=True)
    step=imp(NS/'devices/combo_target.py','combo_fixed').step;seed=int(START-14400)
    def state(k,a):
        with np.load(io.BytesIO(z.read(f'fea171/state_H_{k}_{a}.npz'))) as h:
            if int(h['anchor'])!=a:raise ValueError('state_anchor')
            v=np.zeros(N);v[h['idx'].astype(int)]=h['val'];return v
    outputs_states={};comparisons={};old_states=load(PARENT/'CONTINUOUS_STATES.npz');rows_by={r['anchor']:r for r in rows}
    for arm in ('C3_control','C4_fetch'):
        hs={k:state(k,seed) for k in ('kc','fc')};rr=[]
        for i,a0 in enumerate(E):
            a=int(a0)
            if a<START:continue
            if a not in HOLD:
                row=rows_by[a]
                if arm=='C3_control':
                    m=MH[a];args={k:legs[v][i,m].astype(float) for k,v in [('king_rank','KZ'),('fund_rank','ZFD'),('rn8','RN8'),('qv','QV')]};args['f10_score']=pred['P'][i,m].astype(float)
                else:
                    f=frows[a];m=f['m'];args={k:f[v].astype(float) for k,v in [('king_rank','KZ'),('fund_rank','ZFD'),('rn8','RN8'),('qv','QV'),('f10_score','P')]}
                got=step(**args,seats=np.asarray(row['live_w3']),members=m,legal=elig['legal'][i+1],params=params,kc_prev=hs['kc'],fc_prev=hs['fc'],publication='literal')
                if not got['accepted']:raise ValueError('new_publication_failed:'+arm+':'+str(a))
                hs={k:got[k].copy() for k in ('kc','fc')}
            raw=.55*hs['kc']+.45*hs['fc'];stack=np.stack([hs['kc'],hs['fc'],raw]);outputs_states[f'{arm}_{a}']=stack
            if arm=='C3_control' and not np.array_equal(stack,old_states[f'C3_{a}']):raise ValueError('C3_not_exact:'+str(a))
            if a in selected:
                target=json.loads(z.read(f'state/target_live/{a}.json'));live=np.array([target['weights'].get(s,0.) for s in sy]);rr.append({'anchor':a,'utc':rows_by[a]['utc'],'error':error(live,raw)})
        comparisons[arm]=rr
    out=root/'STATES.npz';np.savez_compressed(out,**outputs_states);outputs[out.name]=sha(out)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input_changed_during_run:'+p)
    result={'status':'FETCH_FEATURE_PROPAGATION_DIAGNOSTIC_NOT_PNL','utc':time.strftime('%FT%TZ',time.gmtime()),'inputs':pins,'outputs':outputs,'checks':checks,'old_f10_bitwise_controls':old_control,'numpy_inference_reference_ranks_all_equal':True,'numpy_source_span_sha256':np_source_sha,'C3_control_all_states_exact':True,'rows':comparisons,'seconds':time.monotonic()-start,'python':sys.executable,'numpy':np.__version__,'peak_sampled_shared_rss':peak,'limits':['Live seats conditional, not independently reconstructed histories','Only actual fetch substituted; original bars/funding retained','Three missing producer anchors still use original research feature membership, not GAP4 repair','No PnL, cash, model training, candidate or deployment conclusion']}
    save(root/'RESULT.json',result);save(root/'TERMINAL.json',{'rc':0,'result_sha256':sha(root/'RESULT.json'),'utc':time.strftime('%FT%TZ',time.gmtime())})

if __name__=='__main__':
    try:main(sys.argv[1])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True);save(root/'TERMINAL.json',{'rc':1,'error':repr(e),'traceback':traceback.format_exc(),'utc':time.strftime('%FT%TZ',time.gmtime())});raise
