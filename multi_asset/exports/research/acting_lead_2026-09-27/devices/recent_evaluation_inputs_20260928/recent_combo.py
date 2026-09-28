"""Continue frozen NC combo kernels, explicit September universe, own prior states."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR')
from pathlib import Path
import ast,json,sys,time,traceback,importlib.util
import numpy as np
from funding_overlap import sha
from recent_king_features import materialize,exact,BASE
from recent_legs import certified,OLD_LEGS_SHA

NS=Path('/dev/shm/news2_2026-09-23')
FEATURES_SHA='3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8'
UNIVERSE=Path('/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz')
UNIVERSE_SHA='3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f'

def seeded_function(src,namespace):
    """Only replace two zero initializers with the supplied prior state arrays."""
    t=ast.parse(src);fn=[x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='evolve']
    if len(fn)!=1:raise ValueError('evolve source ambiguous')
    fn=fn[0];seen=[]
    for x in fn.body:
        if isinstance(x,ast.Assign) and len(x.targets)==1 and isinstance(x.targets[0],ast.Name) and x.targets[0].id in ('kc','fc'):
            k=x.targets[0].id
            if ast.unparse(x.value)!='np.zeros(w)':raise ValueError('state init changed')
            x.value=ast.parse('initial_'+k+'.copy()',mode='eval').body;seen.append(k)
    if sorted(seen)!=['fc','kc']:raise ValueError('two seed assignments required')
    fn.args.args.extend([ast.arg(arg='initial_kc'),ast.arg(arg='initial_fc')]);module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));env=namespace.copy();exec(compile(module,'fixed_combo_seed_only','exec'),env)
    return env['evolve']

def universe_pin(symbols,names,previous):
    symbols=list(map(str,symbols));names=list(map(str,names))
    if len(set(symbols))!=len(symbols) or len(set(names))!=len(names) or not names or not set(names)<=set(symbols):raise ValueError('universe names')
    pin=np.isin(symbols,names)
    if previous.dtype!=np.dtype(bool) or not np.array_equal(pin,previous):raise ValueError('September universe changed')
    return pin

def main(root):
    started=time.monotonic();root=Path(root);root.mkdir(exist_ok=False)
    wr=Path('/dev/shm/recent_rolling_inputs_20260928');lr=Path('/dev/shm/recent_nc_legs_20260928_attempt3');kr=Path('/dev/shm/recent_king_features_20260928');pr=Path('/dev/shm/recent_nc_predictions_20260928');pins={str(Path(__file__)):sha(__file__)}
    for r in (wr,lr,kr,pr):certified(r,pins)
    paths={'legs':NS/'work/legs.npz','features':NS/'work/NEWS_FEATURES.npz','universe':UNIVERSE,'config':NS/'inputs/bundle_config.json','mask':Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz'),'crypto':NS/'receipts/P1_members_2025H2on.npz'}
    for p in paths.values():pins[str(p)]=sha(p)
    for k,h in {'legs':OLD_LEGS_SHA,'features':FEATURES_SHA,'universe':UNIVERSE_SHA,'config':'3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e'}.items():
        if pins[str(paths[k])]!=h:raise ValueError('fixed identity '+k)
    with np.load(paths['features']) as f:F={k:f[k] for k in ('anchors','symbols','off','m')}
    old=materialize(paths['legs']);new=materialize(lr/'LEGS_CONTINUATION.npz');nf=materialize(kr/'KING_FEATURES_AND_MEMBERS.npz');u=materialize(UNIVERSE);ax=materialize(wr/'axes.npz');cfg=json.loads(paths['config'].read_text())
    for z in (old,new,nf,u,ax):
        if not np.array_equal(z['symbols'],F['symbols']):raise ValueError('symbol axis')
    if not np.array_equal(new['E_ts'],nf['anchors']) or not np.array_equal(new['E_ts'],ax['anchors']):raise ValueError('new clock')
    if u['ts'][-1]+14400!=new['E_ts'][0]:raise ValueError('combo boundary gap')
    j=int(np.searchsorted(F['anchors'],u['ts'][-1]));assert F['anchors'][j]==u['ts'][-1]
    a=np.r_[u['ts'][-1],new['E_ts']];syms=F['symbols'];n=len(a);nw=len(syms)
    members=[F['m'][F['off'][j]:F['off'][j+1]].astype(np.int64)]+[nf['m'][nf['off'][i]:nf['off'][i+1]].astype(np.int64) for i in range(n-1)]
    leg={k:np.concatenate([old[k][j:j+1],new[k]]) for k in ('KZ','ZFD','RN8','QV','WL','ready')}
    pin=universe_pin(syms,cfg['symbols_live'],u['pit'][-1])
    # The old book used this fixed September list. Extend only this declared
    # policy; eligibility is recalculated from available bars for each anchor.
    sys.path.insert(0,str(BASE/'devices'));import nc_hist_features as H
    H.set_tree(str(BASE/'tree'));C=np.load(wr/'cache_crypto.npy',mmap_mode='r');cols=ax['crypto_cols'];can=np.zeros((n,nw),bool)
    can[:,cols]=H._G['NC'].legal_live(ax['ts'],C[:,:,4],C[:,:,3],a,H._G['TR'])
    mk=materialize(paths['mask']);crypto=np.load(paths['crypto'])['crypto']
    if not np.array_equal(crypto,np.isin(np.arange(nw),cols)):raise ValueError('crypto identity')
    mi=int(np.searchsorted(mk['ts'],a[0]));assert mk['ts'][mi]==a[0]
    controls={'legal_old_boundary':exact(can[0],mk['mask'][mi]&crypto),'fixed_universe_equal_old_boundary':True}
    if not controls['legal_old_boundary']:raise ValueError('eligibility recompute boundary')
    legal=can&pin[None,:];sys.path.insert(0,str(NS/'devices'));import combo_target,continuous_combo
    combo_target.ROOT=NS
    original_evolve=continuous_combo.evolve
    evolve=seeded_function(Path(continuous_combo.__file__).read_text(),{'np':np,'step':combo_target.step})
    outputs={};summaries={}
    for seed in (42,2027):
        refroot=NS/f'work/combo_s{seed}';rr=json.loads((refroot/'TARGET_RECEIPT.json').read_text());pins[str(refroot/'TARGET_RECEIPT.json')]=sha(refroot/'TARGET_RECEIPT.json')
        for p,h in rr['sources'].items():
            if sha(p)!=h:raise ValueError('original combo source changed '+p)
            pins[p]=h
        scorep=NS/f'work/f10_s{seed}/F10_OOF.npz';score=materialize(scorep);pins[str(scorep)]=sha(scorep)
        if pins[str(scorep)]!=rr['inputs'][str(scorep)]:raise ValueError('original prediction not bound')
        npred=materialize(pr/f'NC_F10_s{seed}_PREDICTIONS.npz')
        if not np.array_equal(npred['E_ts'],new['E_ts']) or not np.array_equal(npred['symbols'],syms):raise ValueError('recent prediction axis')
        pred=np.concatenate([score['P'][j:j+1],npred['P']]).astype(float)
        for policy in ('literal','scaled_diagnostic'):
            path=refroot/(policy+'.npz');pins[str(path)]=sha(path)
            if rr['policies'][policy]['sha']!=pins[str(path)]:raise ValueError('old state not bound')
            ref=materialize(path)
            if ref['E_ts'][-1]!=a[0] or ref['E_ts'][-2]!=a[0]-14400 or not np.array_equal(ref['symbols'],syms):raise ValueError('state boundary')
            args=(a,leg['KZ'].astype(float),pred,leg['ZFD'].astype(float),leg['WL'].astype(float),leg['RN8'].astype(float),members,leg['QV'].astype(float),legal,leg['ready'],cfg['params'],policy)
            result=evolve(*args,ref['kc'][-2],ref['fc'][-2])
            checks={k:(str(v[0])==str(ref[k][-1]) if v.dtype.kind in 'US' else exact(v[0],ref[k][-1])) for k,v in result.items()}
            if not all(checks.values()):raise ValueError('combo state identity '+str((seed,policy,checks)))
            controls[f's{seed}_{policy}']=checks
            # Split-run state must equal one uninterrupted run. Also exercises
            # HOLD serialization: no converting false mask to zero inventory.
            split=12
            args2=(a[split:],leg['KZ'][split:].astype(float),pred[split:],leg['ZFD'][split:].astype(float),leg['WL'][split:].astype(float),leg['RN8'][split:].astype(float),members[split:],leg['QV'][split:].astype(float),legal[split:],leg['ready'][split:],cfg['params'],policy)
            resumed=evolve(*args2,result['kc'][split-1],result['fc'][split-1])
            for k,v in resumed.items():
                if not np.array_equal(v,result[k][split:],equal_nan=v.dtype.kind in 'fc'):raise ValueError('combo split-state mismatch '+k)
            out=root/f'NC_s{seed}_{policy}.npz';np.savez_compressed(out,E_ts=a[1:],symbols=syms,**{k:v[1:] for k,v in result.items()});outputs[out.name]=sha(out)
            summaries[f's{seed}_{policy}']={'anchors':n-1,'published':int(result['trade_mask'][1:].sum()),'held':int((~result['trade_mask'][1:]).sum()),'split_restart_exact':True}
    bookp=root/'ELIGIBILITY.npz';np.savez_compressed(bookp,E_ts=a,symbols=syms,legal=legal,causal_live=can,fixed_september_universe=pin);outputs[bookp.name]=sha(bookp)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input drift '+p)
    rec={'status':'CONTINUOUS_NC_TARGETS_COMPLETE_NOT_EXECUTED_CASH','utc':time.strftime('%FT%TZ',time.gmtime()),'inputs':pins,'outputs':outputs,'controls':controls,'summary':summaries,'python':sys.executable,'numpy':np.__version__,'seconds':time.monotonic()-started,'limits':['Fixed September symbols_live explicitly extends prior proxy; not independent historical venue membership certification','Conditional continuous NC state, not live 09-26 reseed or 09-27 external executor actions','No recent cash return, cost, leverage or stop-policy result yet','09-28 00Z target has no future pricing window in current dataset']}
    (root/'RESULT.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print({k:rec[k] for k in ('status','summary','seconds')})

if __name__=='__main__':
    try:main(*sys.argv[1:])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True);(root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2));raise
