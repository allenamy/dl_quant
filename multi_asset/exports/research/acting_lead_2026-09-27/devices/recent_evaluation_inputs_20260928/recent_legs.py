"""Continue the original NC leg loop from observed LR history, never reseed seats."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR')
from pathlib import Path
import ast,json,sys,time,importlib.util,traceback
from types import SimpleNamespace
import numpy as np
from funding_overlap import sha
from recent_king_features import materialize,exact,PINS,BASE

LEG_SHA='18387627f8426a45135b348dd4508281b4811894c91eb50af87751760609c0a0'
OLD_LEGS_SHA='9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65'

def seed_history(x):
    x=np.asarray(x)
    if x.ndim!=2 or x.shape[1]!=3 or not len(x) or not np.isnan(x[-1]).all():raise ValueError('last anchor must have unknown next return')
    finite=np.isfinite(x);missing=np.isnan(x)
    if not np.all(finite.all(1)|missing.all(1)):raise ValueError('partial/nonfinite LR population')
    return {k:x[finite.all(1),j].tolist() for j,k in enumerate(('king','rev24','fund'))}

def require_boundary(old,new):
    for a in (np.asarray(old),np.asarray(new)):
        if a.ndim!=1 or not len(a) or not np.isfinite(a).all() or np.any(a!=np.floor(a)) or np.any(a%14400) or np.any(np.diff(a)!=14400):raise ValueError('not continuous 4h axis')
    if old[-1]!=new[0]:raise ValueError('boundary moved')

def extract_loop(src):
    t=ast.parse(src);fn=[x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='main']
    if len(fn)!=1:raise ValueError('source main identity')
    loops=[x for x in fn[0].body if isinstance(x,ast.For) and ast.unparse(x.target)=='i' and ast.unparse(x.iter)=='range(n)']
    if len(loops)!=1:raise ValueError('source loop ambiguity')
    return compile(ast.Module(body=loops,type_ignores=[]),'fixed_nc_legs_loop','exec')

def certified(root,pins):
    root=Path(root);t=json.loads((root/'TERMINAL.json').read_text())
    if t.get('rc')!=0 or t['result_sha256']!=sha(root/'RESULT.json'):raise ValueError('uncertified upstream '+str(root))
    r=json.loads((root/'RESULT.json').read_text());pins[str(root/'RESULT.json')]=sha(root/'RESULT.json')
    for name,v in r.get('outputs',{}).items():
        p=root/name;h=v['sha256'] if isinstance(v,dict) else v
        if sha(p)!=h:raise ValueError('changed output '+str(p))
        pins[str(p)]=h
    if 'output' in r:
        v=r['output'];p=Path(v['path']) if 'path' in v else root/'FUND_CONTINUATION.npz'
        if sha(p)!=v['sha256']:raise ValueError('changed single output')
        pins[str(p)]=v['sha256']
    return r

def run_loop(loop,F,K,I,P,xz_in_base,xz,NC,LR):
    a=F['anchors'].astype(np.int64);syms=list(map(str,F['symbols']));n=len(a);NW=len(syms)
    z=np.full((n,NW),np.nan,np.float32)
    ns=dict(np=np,a=a,syms=syms,n=n,NW=NW,off=F['off'],F=F,K=K,I=I,P=P,NC=NC,xz_in_base=xz_in_base,xz=xz,
        KZ=z.copy(),Z24=z.copy(),ZFD=z.copy(),QV=z.copy(),RN8=z.copy(),WL=np.full((n,3),np.nan,np.float32),
        LRm=np.full((n,3),np.nan),ready=np.zeros(n,bool),why={},LR={k:v.copy() for k,v in LR.items()},prev=None,last_anchor=None)
    exec(loop,ns)
    return {k:ns[k] for k in ('KZ','Z24','ZFD','QV','RN8','WL','ready','LRm','why','LR')}

def main(root):
    start=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);pins=PINS.copy()
    src=BASE/'devices/nc_legs.py';oldp=Path('/dev/shm/news2_2026-09-23/work/legs.npz')
    pins.update({str(src):LEG_SHA,str(oldp):OLD_LEGS_SHA,str(Path(__file__)):sha(__file__)})
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('fixed source/input drift '+p)
    wr=Path('/dev/shm/recent_rolling_inputs_20260928');fr=Path('/dev/shm/recent_funding_continuation_20260928_materialized');kr=Path('/dev/shm/recent_king_features_20260928');pr=Path('/dev/shm/recent_nc_predictions_20260928')
    for r in (wr,fr,kr,pr):certified(r,pins)
    old=materialize(oldp);F=materialize(kr/'KING_FEATURES_AND_MEMBERS.npz');F['base_val']=F.pop('base_vals');K=materialize(pr/'KING_PREDICTIONS.npz');ax=materialize(wr/'axes.npz');fund=materialize(fr/'FUND_CONTINUATION.npz')
    require_boundary(old['E_ts'],F['anchors'])
    for z in (K,ax,fund):
        if not np.array_equal(z['symbols'],F['symbols']) or not np.array_equal(z.get('E_ts',z.get('anchors')),F['anchors']):raise ValueError('axis identity')
    if not np.array_equal(old['symbols'],F['symbols']):raise ValueError('old symbol axis')
    seed=seed_history(old['LR'])
    sys.path.insert(0,str(src.parent));spec=importlib.util.spec_from_file_location('fixed_nc_legs',src);L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L);L.H.set_tree(str(BASE/'tree'));xz_in_base,xz=L.prod_funcs();NC=L.H._G['NC']
    def funding(A):
        i=int(np.searchsorted(F['anchors'],A))
        if i>=len(F['anchors']) or F['anchors'][i]!=A:raise ValueError('funding time')
        ema,led={},{}
        for j in ax['crypto_cols']:
            if fund['ledger_ft'][i,j]<0:continue
            s=str(F['symbols'][j]);acc,iv,last=fund['acc'][i,j],fund['iv'][i,j],int(fund['last_ts'][i,j])
            ema[s]={'acc':None if np.isnan(acc) else float(acc),'last_ts':None if last<0 else last}
            led[s]=[[int(fund['ledger_ft'][i,j]),float(fund['rate'][i,j]),None if np.isnan(iv) else float(iv)]]
        return ema,led
    I=SimpleNamespace(ts=ax['ts'],cols=ax['crypto_cols'],R=np.load(wr/'R_crypto.npy',mmap_mode='r'),funding=funding)
    P=json.loads((BASE/'inputs/bundle_config.json').read_text())['params'];loop=extract_loop(src.read_text());result=run_loop(loop,F,K,I,P,xz_in_base,xz,NC,seed)
    controls={k:exact(result[k][0],old[k][-1]) for k in ('KZ','Z24','ZFD','QV','RN8','WL','ready')}
    if not all(controls.values()):raise ValueError('original boundary mismatch '+repr(controls))
    if not result['ready'].all():raise ValueError('unready recent legs '+repr(result['why']))
    # Poison future predictions: the prior declared seat/score must not change.
    altered={k:v.copy() for k,v in K.items()};altered['P'][1:]=12345
    poisoned=run_loop(loop,F,altered,I,P,xz_in_base,xz,NC,seed)
    controls['future_prediction_does_not_change_boundary']=all(exact(result[k][0],poisoned[k][0]) for k in ('KZ','Z24','ZFD','QV','RN8','WL','ready'))
    if not all(controls.values()):raise ValueError('future control')
    out=root/'LEGS_CONTINUATION.npz';arrays={k:v for k,v in result.items() if k in ('KZ','Z24','ZFD','QV','RN8','WL','ready')};arrays['LR']=result['LRm']
    np.savez_compressed(out,E_ts=F['anchors'],symbols=F['symbols'],**arrays)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('changed upstream '+p)
    rec={'status':'CONTINUOUS_ORIGINAL_NC_LEGS_NOT_BOOK_OR_CASH','utc':time.strftime('%FT%TZ',time.gmtime()),'inputs':pins,'outputs':{out.name:sha(out)},'anchors':len(F['anchors']),'old_lr_count':len(seed['king']),'new_observed_return_intervals':int(np.isfinite(result['LRm']).all(1).sum()),'controls':controls,'seconds':time.monotonic()-start,'limits':['Seat history is original hypothetical NC path, not current live intervention state','Last anchor next return is unknown, not zero','No model change, fee/cash, or deployable strategy claim']}
    (root/'RESULT.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print({k:rec[k] for k in ('status','anchors','controls','seconds')})

if __name__=='__main__':
    try:main(*sys.argv[1:])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True);(root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2));raise
