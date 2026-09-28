"""Read-only price mapping diagnostic; never substitutes for execution cash PnL."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
import ast,copy,hashlib,json,pathlib,sys,time
from datetime import datetime,timezone
import numpy as np
from scipy.stats import rankdata

STAGES=['rank_unit','fund_blend_unit','ftrim_unit','liquidity_demean_unit',
        'cap_renorm','ema','band','legal_fc','combo_raw','executor_neutral']
# Exact producer snapshot, verified against existing content-bound receipts.
PRODUCER_SHA='fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(16<<20),b''):h.update(b)
    return h.hexdigest()

def joint_measurable(arms,y):
    if any(not np.isfinite(a).all() for a in arms):raise ValueError('nonfinite stage exposure')
    support=np.logical_or.reduce([np.any(a!=0,axis=0) for a in arms])
    return ~np.any(support & ~np.isfinite(y),axis=1)

def price_contributions(w,y):
    if not np.isfinite(w).all():raise ValueError('nonfinite stage exposure')
    bad=np.any((w!=0)&~np.isfinite(y)[None,:,:],axis=2)
    n=np.sum(w*np.where(np.isfinite(y),y,0)[None,:,:],axis=2)*1e4
    n[bad]=np.nan;g=np.abs(w).sum(2)
    u=np.divide(n,g,out=np.full_like(n,np.nan),where=g>0)
    return n,u,g

def verify_combo(k,f,r):
    if not np.array_equal(.55*k+.45*f,r):raise ValueError('archived combo identity')

def period_readout(period,published,measured,a,b):
    use=period & published & measured
    if not np.isfinite(a[:,use]).all() or not np.isfinite(b[:,use]).all():raise ValueError('shared population leaked unknown')
    d=b[:,use]-a[:,use]
    return {'period_anchors':int(period.sum()),'common_published':int((period&published).sum()),
            'measured_published':int(use.sum()),'unmeasured_published':int((period&published&~measured).sum()),
            'mean_baseline':a[:,use].mean(1).tolist() if use.any() else None,
            'mean_candidate':b[:,use].mean(1).tolist() if use.any() else None,
            'mean_delta':d.mean(1).tolist() if use.any() else None}

def kernels(p):
    if sha(p)!=PRODUCER_SHA:raise ValueError('unapproved source')
    tree=ast.parse(pathlib.Path(p).read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='chain')
    original=copy.deepcopy(f);original.name='chain_original'
    points={4:('liquidity_demean_unit','w'),8:('cap_renorm','w'),11:('ema','smv'),13:('band','smv'),20:('unfloored_fc','smv')}
    body=[]
    for i,node in enumerate(f.body):
        body.append(node)
        if i in points:
            name,v=points[i];body+=ast.parse(f'capture({name!r}, {v})').body
    f.body=body
    funcs=[original,f]+[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='exec_reshape']
    t=ast.fix_missing_locations(ast.Module(body=funcs,type_ignores=[]));ns={'np':np};exec(compile(t,str(p),'exec'),ns)
    return ns

def unit_member(z,m,nw):
    z=np.asarray(z,float);z=z-z.mean();g=np.abs(z).sum()
    if not np.isfinite(z).all() or g<=0:raise ValueError('degenerate diagnostic score')
    w=np.zeros(nw);w[m]=z/g;return w

def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())

def main(out):
    start=time.time();out=pathlib.Path(out);out.mkdir(exist_ok=False)
    NS=pathlib.Path('/dev/shm/news2_2026-09-23');base=pathlib.Path('/workspace/dlarch_2026-09-24/chain')
    first=pathlib.Path('/dev/shm/f10_recent_adapt_20260928_attempt2/cells/U_s42')
    p_rec=first/'work/combo_s42/TARGET_RECEIPT.json';receipt=json.loads(p_rec.read_text());ident={str(p_rec):sha(p_rec),str(pathlib.Path(__file__)):sha(__file__)}
    for p,h in receipt['inputs'].items():
        if sha(p)!=h:raise ValueError('input drift '+p)
        ident[p]=h
    F=np.load(NS/'work/NEWS_FEATURES.npz');axis=F['anchors'];symbols=F['symbols'];off=F['off'];members=F['m'];nw=len(symbols)
    leg=np.load(NS/'work/legs.npz');legs={k:leg[k] for k in ('KZ','ZFD','WL','RN8','QV','ready')}
    if not np.array_equal(axis,leg['E_ts']) or not np.array_equal(symbols,leg['symbols']):raise ValueError('leg axes')
    cfg=json.loads((first/'inputs/bundle_config.json').read_text())['params']
    maskp=pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz');mask=np.load(maskp)
    universep=pathlib.Path('/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz');universe=np.load(universep)
    crypto=np.load(first/'receipts/P1_members_2025H2on.npz')['crypto'];cand=mask['mask']&crypto[None,:]
    if not np.array_equal(mask['ts'],axis) or not np.array_equal(symbols,universe['symbols']):raise ValueError('mask axes')
    tp=pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
    if sha(tp)!='ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62':raise ValueError('target drift')
    ident[str(tp)]=sha(tp);T=np.load(tp,allow_pickle=True)
    if not np.array_equal(T['symbols'],symbols):raise ValueError('target symbols')
    ai=np.flatnonzero((axis>=stamp('2023-07-01'))&(axis<stamp('2026-09-19')));a=axis[ai]
    ti=np.searchsorted(T['E_ts'],a)
    if np.any(ti>=len(T['E_ts'])) or not np.array_equal(T['E_ts'][ti],a):raise ValueError('target missing row')
    y=T['y4s'][ti].astype(float);ui=np.searchsorted(universe['ts'],a)
    if not np.array_equal(universe['ts'][ui],a):raise ValueError('universe row')
    legal=universe['pit'][ui]&cand[ai]
    ns=kernels(first/'vendor_live/fea171/combo_stage.py');ident[str(first/'vendor_live/fea171/combo_stage.py')]=PRODUCER_SHA
    ns.update(P=cfg,NW=nw)
    results={};arrays={'anchors':a};verified={};periods={
      'pre2026':(a<stamp('2026-01-01')),
      '2026_H1':(a>=stamp('2026-01-01'))&(a<stamp('2026-07-01')),
      'recent_primary':a>=stamp('2026-07-01'),
      'september':a>=stamp('2026-09-01')}
    for seed in (42,2027):
        roots={'NC':base/f'ref_nc_s{seed}X',
               'U':pathlib.Path(f'/dev/shm/f10_recent_adapt_20260928_attempt2/cells/U_s{seed}'),
               'R180':pathlib.Path(f'/dev/shm/f10_recent_adapt_20260928_cash_resume1/cells/R180_s{seed}')}
        arms={};kref=None
        for kind,root in roots.items():
            cp=root/f'work/combo_s{seed}/scaled_diagnostic.npz';rp=root/f'work/combo_s{seed}/TARGET_RECEIPT.json';rr=json.loads(rp.read_text())
            for suffix in ('/NEWS_FEATURES.npz','/legs.npz','/bundle_config.json','/P1_members_2025H2on.npz','/member_mask_tradable_AND_live_W24H_cachegrid.npz','/universe_ext.npz'):
                expected=next(v for k,v in receipt['inputs'].items() if k.endswith(suffix))
                actual=next(v for k,v in rr['inputs'].items() if k.endswith(suffix))
                if actual!=expected:raise ValueError('common input mismatch '+suffix)
            if sha(cp)!=rr['policies']['scaled_diagnostic']['sha']:raise ValueError('combo receipt identity')
            ident[str(cp)]=sha(cp);ident[str(rp)]=sha(rp)
            pp=root/f'work/f10_s{seed}/F10_OOF.npz';expected=next(v for k,v in rr['inputs'].items() if k.endswith('/F10_OOF.npz'))
            if sha(pp)!=expected:raise ValueError('prediction identity')
            ident[str(pp)]=expected;ps=np.load(pp)
            if not np.array_equal(ps['E_ts'],axis) or not np.array_equal(ps['symbols'],symbols):raise ValueError('prediction axes')
            pred=ps['P'];z=np.load(cp);ca=z['E_ts'];ci=np.searchsorted(ca,a)
            if np.any(ci<=0) or not np.array_equal(ca[ci],a) or not np.array_equal(z['symbols'],symbols):raise ValueError('combo axes/state')
            kc=z['kc'];fc=z['fc'];raw=z['raw'];trade=z['trade_mask'][ci]
            if kref is None:kref=kc.copy()
            elif not np.array_equal(kref,kc):raise ValueError('King branch changed')
            verify_combo(kc,fc,raw)
            natural=np.zeros((len(STAGES),len(ai)));unit=natural.copy();gross=natural.copy();support=np.zeros(y.shape,bool)
            fc_checks=kc_checks=0;bad_details=[]
            for r,(i,j) in enumerate(zip(ai,ci)):
                if not legs['ready'][i]:raise ValueError('unready analysis anchor')
                m=members[off[i]:off[i+1]].astype(int);score=pred[i,m].astype(float);ok=np.isfinite(score);zf=np.zeros(len(m));zf[ok]=rankdata(score[ok])/max(int(ok.sum())-1,1)-.5
                seat=np.array([legs['WL'][i,0],0.,legs['WL'][i,2]],float);seat=seat/seat.sum() if seat.sum()>1e-12 else np.array([.5,0.,.5])
                blend=seat[0]*zf+seat[2]*np.nan_to_num(legs['ZFD'][i,m].astype(float),nan=0.)
                rn=legs['RN8'][i,m].astype(float);trim=np.where((blend<0)&np.isfinite(rn)&(rn<=-.001),0.,blend)
                qv=legs['QV'][i,m].astype(float);ns.update(pm=m,sel=np.isfinite(qv)&(qv>=cfg['qv4h_min']),LIVE_MASK=legal[r],H=fc[j-1])
                probes={}
                def capture(name,v):
                    if v.shape==(nw,):probes[name]=v.copy()
                    else:
                        w=np.zeros(nw);w[m]=v;probes[name]=w
                ns['capture']=capture;traced=ns['chain'](trim);original=ns['chain_original'](trim)
                if traced is None or not np.array_equal(traced,original):raise ValueError('trace changes chain')
                final=np.where(np.abs(traced)>1e-9,traced,0.)
                if not np.array_equal(final,fc[j]):raise ValueError(f'fc state parity {kind} {seed} {a[r]}')
                fc_checks+=1
                zkc=seat[0]*np.nan_to_num(legs['KZ'][i,m].astype(float),nan=0.)+seat[2]*np.nan_to_num(legs['ZFD'][i,m].astype(float),nan=0.)
                zkc=np.where((zkc<0)&np.isfinite(rn)&(rn<=-.001),0.,zkc);ns['H']=kc[j-1];kr=ns['chain_original'](zkc)
                if kr is None or not np.array_equal(np.where(np.abs(kr)>1e-9,kr,0.),kc[j]):raise ValueError('kc parity')
                kc_checks+=1
                w=np.stack([unit_member(zf,m,nw),unit_member(blend,m,nw),unit_member(trim,m,nw),probes['liquidity_demean_unit'],probes['cap_renorm'],probes['ema'],probes['band'],final,raw[j],ns['exec_reshape'](raw[j])])
                n,u,g=price_contributions(w[:,None,:],y[r:r+1]);natural[:,r]=n[:,0];unit[:,r]=u[:,0];gross[:,r]=g[:,0];support[r]=np.any(w!=0,0)
                bad=support[r]&~np.isfinite(y[r])
                if bad.any():bad_details.append({'anchor':int(a[r]),'symbols':symbols[bad].tolist()})
                if time.time()-start>850:raise TimeoutError('diagnostic budget')
            name=f'{kind}_s{seed}';arms[kind]={'natural':natural,'unit':unit,'gross':gross,'support':support,'trade':trade}
            for k in ('natural','unit','gross','trade'):arrays[f'{name}_{k}']=arms[kind][k]
            arrays[f'{name}_unknown_exposure']=support&~np.isfinite(y)
            verified[name]={'fc_bitwise_anchors':fc_checks,'kc_bitwise_anchors':kc_checks,'combo_identity':True,'missing_return_anchors':bad_details}
            print(name,'parity',fc_checks,'unknown',len(bad_details),flush=True)
        for kind in ('U','R180'):
            x=arms['NC'];v=arms[kind];published=x['trade']&v['trade']
            measurable=~np.any((x['support']|v['support'])&~np.isfinite(y),1)
            entry={}
            for pname,period in periods.items():
                entry[pname]={metric:period_readout(period,published,measurable,x[metric],v[metric]) for metric in ('natural','unit')}
                entry[pname]['hold_mask_differences']=int((period&(x['trade']!=v['trade'])).sum())
                use=period&published&measurable
                entry[pname]['gross_baseline']=x['gross'][:,use].mean(1).tolist() if use.any() else None
                entry[pname]['gross_candidate']=v['gross'][:,use].mean(1).tolist() if use.any() else None
            results[f'{kind}_minus_NC_s{seed}']=entry
    sw=legs['WL'][ai][:,[0,2]].astype(float);sw=sw/sw.sum(1,keepdims=True)
    seat={n:{'masked_king_mean':float(sw[p,0].mean()),'masked_king_p10_p90':np.quantile(sw[p,0],[.1,.9]).tolist(),
             'implied_f10_score_coefficient_mean':float((.45*sw[p,0]).mean())} for n,p in periods.items()}
    for p,h in ident.items():
        if sha(p)!=h:raise ValueError('end drift '+p)
    np.savez_compressed(out/'STAGE_ARRAYS.npz',**arrays)
    result={'schema':'exploratory_signal_to_book_price_diagnostic/1','status':'DESCRIPTIVE_NOT_CASH_OR_PROMOTION',
      'source_sha256':sha(__file__),'inputs':ident,'stages':STAGES,'units':'bps per 4h anchor, natural or own-gross-normalized; not NAV/day',
      'population':'joint published AND all stages/arms nonzero exposures have raw y4s; no missing=zero',
      'limits':['holding clocks differ from cash simulation','old frozen universe proxy and producer kernels inherited','no unique causal attribution','post-hoc diagnostic with frozen spec','all outcomes end September 18'],
      'verified':verified,'results':results,'seats':seat,'arrays_sha256':sha(out/'STAGE_ARRAYS.npz'),
      'runtime_seconds':time.time()-start,'python':sys.executable,'numpy':np.__version__}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print('DONE',result['runtime_seconds'],flush=True)

if __name__=='__main__':main(sys.argv[1])
