"""Fixed decomposition of the liquidity filter; descriptive, not a new strategy."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
import pathlib,json,time,sys,resource,traceback
import numpy as np
from scipy.stats import rankdata
from stage import sha,stamp,unit_member

def selection_steps(w,sel):
    w=np.asarray(w,float);sel=np.asarray(sel)
    if sel.dtype!=bool or w.shape!=sel.shape or not np.isfinite(w).all() or not sel.any():raise ValueError('selection contract')
    selected=np.where(sel,w,0.);centered=np.where(sel,selected-selected[sel].mean(),0.)
    g=np.abs(centered).sum()
    if g<=0:raise ValueError('selection degenerate')
    return np.stack([w,selected,centered,centered/g])

def corr(x,y):
    x=x-x.mean();y=y-y.mean();v=np.sqrt(x@x*(y@y))
    return float(x@y/v) if v>0 else np.nan

def main(root):
    started=time.monotonic();root.mkdir(exist_ok=False)
    parent=pathlib.Path('/dev/shm/f10_stage_diagnostic_20260928_attempt2/results')
    rp=parent/'RESULT.json'
    if sha(rp)!='67b43fda062bc88c8004ea3fb88f5ffb4fd8e3907f6032d902986e3dff2c1a8e':raise ValueError('parent identity')
    d=json.loads(rp.read_text());ap=parent/'STAGE_ARRAYS.npz'
    if sha(ap)!=d['arrays_sha256']:raise ValueError('parent arrays')
    for p,h in d['inputs'].items():
        if sha(p)!=h:raise ValueError('parent input drift '+p)
    arrays=np.load(ap);NS=pathlib.Path('/dev/shm/news2_2026-09-23');F=np.load(NS/'work/NEWS_FEATURES.npz');L=np.load(NS/'work/legs.npz')
    axis=F['anchors'];sy=F['symbols'];off=F['off'];members=F['m'];nw=len(sy)
    a=arrays['anchors'];chosen=a>=stamp('2026-07-01');a=a[chosen];ii=np.searchsorted(axis,a)
    T=np.load('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz',allow_pickle=True);ti=np.searchsorted(T['E_ts'],a);y=T['y4s'][ti].astype(float)
    if not np.array_equal(T['E_ts'][ti],a) or not np.array_equal(T['symbols'],sy):raise ValueError('label identity')
    wl=L['WL'];fund=L['ZFD'];rn=L['RN8'];qv=L['QV']
    output={};counts=[];max_parity=0.;max_telescoping=0.;save={'anchors':a}
    for seed in (42,2027):
        arm={}
        for kind in ('NC','U','R180'):
            path=NS/f'work/f10_s{seed}/F10_OOF.npz' if kind=='NC' else pathlib.Path(f'/dev/shm/f10_recent_adapt_20260928_attempt2/models/{kind}_s{seed}/F10_OOF.npz')
            pred=np.load(path)['P'];v=np.full((2,4,len(a)),np.nan);group_ic=np.full((2,len(a)),np.nan)
            for t,i in enumerate(ii):
                m=members[off[i]:off[i+1]].astype(int);s=pred[i,m].astype(float);ok=np.isfinite(s);z=np.zeros(len(m));z[ok]=rankdata(s[ok])/max(int(ok.sum())-1,1)-.5
                w=np.array([wl[i,0],wl[i,2]],float);w=w/w.sum() if w.sum()>1e-12 else np.array([.5,.5]);blend=w[0]*z+w[1]*np.nan_to_num(fund[i,m].astype(float),nan=0.)
                tr=np.where((blend<0)&np.isfinite(rn[i,m])&(rn[i,m]<=-.001),0.,blend)
                keep=np.isfinite(qv[i,m])&(qv[i,m]>=250000.);sel=np.zeros(nw,bool);sel[m]=keep
                if seed==42 and kind=='NC':counts.append([int(keep.sum()),int((~keep).sum())])
                for gi,pop in enumerate((keep,~keep)):
                    pop=pop&ok&np.isfinite(y[t,m])
                    if pop.sum()>=10:group_ic[gi,t]=corr(rankdata(s[pop]),rankdata(y[t,m][pop]))
                for zno,score in enumerate((z,tr)):
                    st=selection_steps(unit_member(score,m,nw),sel)
                    if np.any((st!=0)&~np.isfinite(y[t])[None,:]):continue
                    vv=st@np.where(np.isfinite(y[t]),y[t],0)*1e4;v[zno,:,t]=vv
                    max_telescoping=max(max_telescoping,abs(float(np.diff(vv).sum()-(vv[-1]-vv[0]))))
                    if zno==1:
                        old=arrays[f'{kind}_s{seed}_natural'][3,chosen][t]
                        if np.isfinite(old):max_parity=max(max_parity,abs(float(vv[-1]-old)))
            name=f'{kind}_s{seed}';arm[kind]=(v,group_ic);save[name+'_contribution']=v;save[name+'_group_rank_ic']=group_ic
        for kind in ('U','R180'):
            n=f'NC_s{seed}';k=f'{kind}_s{seed}'
            shared=arrays[n+'_trade'][chosen]&arrays[k+'_trade'][chosen]&~np.any(arrays[n+'_unknown_exposure'][chosen]|arrays[k+'_unknown_exposure'][chosen],axis=1)
            results={}
            for period,mask in [('recent_primary',np.ones(len(a),bool)),('september',a>=stamp('2026-09-01'))]:
                use=shared&mask;delta=arm[kind][0][:,:,use]-arm['NC'][0][:,:,use]
                if not np.isfinite(delta).all():raise ValueError('common population violation')
                steps=delta.mean(2);ic=[]
                for g in range(2):
                    x=arm['NC'][1][g];z=arm[kind][1][g];m=use&np.isfinite(x)&np.isfinite(z)
                    ic.append({'anchors':int(m.sum()),'baseline':float(x[m].mean()),'candidate':float(z[m].mean())})
                results[period]={'anchors':int(use.sum()),'step_deltas_bps_per_anchor':steps.tolist(),
                    'increment_deltas':np.diff(steps,axis=1).tolist(),'group_rank_ic':ic,
                    'mean_liquid_names':float(np.array(counts)[use,0].mean()),'mean_removed_names':float(np.array(counts)[use,1].mean())}
            output[f'{kind}_minus_NC_s{seed}']=results
    if max_parity>1e-12 or max_telescoping>1e-12:raise ValueError('fixed-step numerical mapping')
    np.savez_compressed(root/'SELECTION_ARRAYS.npz',**save)
    result={'status':'SELECTION_DESCRIPTIVE_NOT_CASH','source_sha256':sha(__file__),'helper_sha256':sha(pathlib.Path(__file__).with_name('stage.py')),
      'parent_sha256':sha(rp),'steps':['original_unit','remove_only','recenter','gross_restore'],
      'score_types':['f10_rank','after_fund_and_ftrim'],'group_ic_order':['liquid','removed'],
      'max_price_mapping_error':max_parity,'max_telescoping_error':max_telescoping,'results':output,
      'arrays_sha256':sha(root/'SELECTION_ARRAYS.npz'),'runtime_seconds':time.monotonic()-started,
      'limits':['not fee or cash PnL','conditional group metrics are descriptive','negative September rank-price before selection remains unexplained by this filter','T3 whole-chain failed earlier; no inference that adding this loss filter will improve the book']}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps(result),flush=True)

if __name__=='__main__':
    root=pathlib.Path(sys.argv[1]);start=time.monotonic();rc=1;error=None
    try:
        resource.setrlimit(resource.RLIMIT_AS,(2*2**30,2*2**30));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        import signal
        signal.signal(signal.SIGALRM,lambda *args:(_ for _ in ()).throw(TimeoutError('300 second budget')));signal.alarm(300)
        main(root);rc=0
    except BaseException as e:error=repr(e);traceback.print_exc()
    finally:
        if root.exists():(root/'TERMINAL.json').write_text(json.dumps({'rc':rc,'error':error,'wall_seconds':time.monotonic()-start,'utc':time.strftime('%FT%TZ',time.gmtime()),'GPU':False},indent=2))
    sys.exit(rc)
