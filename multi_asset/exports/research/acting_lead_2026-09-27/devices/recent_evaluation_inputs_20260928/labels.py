"""Raw evaluation labels from complete observed 5m paths; never a membership rule."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
import numpy as np

def build_labels(ts,close,observed,anchors):
    ts,close,observed,anchors=map(np.asarray,(ts,close,observed,anchors))
    if ts.ndim!=1 or anchors.ndim!=1 or ts.dtype.kind not in 'iu' or anchors.dtype.kind not in 'iu':
        raise ValueError('integer time axes required')
    if not len(ts) or not len(anchors) or np.any(ts%300) or np.any(np.diff(ts)!=300) or np.any(anchors%14400) or np.any(np.diff(anchors)<=0):
        raise ValueError('time grid or order')
    if close.ndim!=2 or close.shape[0]!=len(ts) or observed.shape!=close.shape or observed.dtype!=bool or close.dtype.kind not in 'fiu':
        raise ValueError('price/observation population')
    valid=observed&np.isfinite(close)&(close>0)
    bad=np.vstack([np.zeros((1,close.shape[1]),np.int64),np.cumsum(~valid,axis=0,dtype=np.int64)])
    y=np.full((len(anchors),close.shape[1]),np.nan,np.float64);known=np.zeros(y.shape,bool)
    for k,a in enumerate(anchors):
        start=int(np.searchsorted(ts,a));end=start+48
        if start>=len(ts) or ts[start]!=a or end>=len(ts) or ts[end]!=a+14400:continue
        mask=(bad[end+1]-bad[start])==0
        values=close[end,mask].astype(np.float64)/close[start,mask].astype(np.float64)-1
        if not np.isfinite(values).all():raise ValueError('observed endpoints produced nonfinite label')
        y[k,mask]=values;known[k,mask]=True
    return y,known

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def run(contract_path,source_commit):
    start=time.monotonic();cp=Path(contract_path);c=json.loads(cp.read_text());p=Path(c['input']);root=Path(c['output_root'])
    if sha(p)!=c['input_sha256']:raise ValueError('source panel changed')
    if len(source_commit)!=40 or any(x not in '0123456789abcdef' for x in source_commit):raise ValueError('full commit required')
    if c['horizon_seconds']!=14400 or c['bar_step_seconds']!=300:raise ValueError('unsupported horizon')
    lo,hi=[int(datetime.fromisoformat(c[k].replace('Z','+00:00')).timestamp()) for k in ('first_anchor','last_anchor')]
    a=np.arange(lo,hi+1,14400,dtype=np.int64)
    with np.load(p,allow_pickle=False) as z:
        sy=z['symbols'];t=z['ts'];prices=z['close'];obs=z['observed']
        if sy.ndim!=1 or len(set(sy.tolist()))!=len(sy) or len(sy)!=prices.shape[1]:raise ValueError('symbol identity')
        y,known=build_labels(t,prices,obs,a)
    if sha(p)!=c['input_sha256']:raise ValueError('input changed during build')
    if time.monotonic()-start>c['max_runtime_seconds']:raise TimeoutError('fixed build budget')
    root.mkdir(exist_ok=False)
    out=root/'RAW_Y4S.npz'
    with out.open('xb') as f:np.savez_compressed(f,E_ts=a,symbols=sy,y4s=y,known=known)
    result={'status':'RAW_LABEL_PREREQUISITE_COMPLETE_NOT_BOOK','utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':sha(__file__),'source_commit':source_commit,'contract_sha256':sha(cp),'input':{'path':str(p),'sha256':sha(p)},
        'python':sys.executable,'numpy':np.__version__,'output':{'path':str(out),'sha256':sha(out),'bytes':out.stat().st_size},
        'n_anchors':len(a),'n_symbols':len(sy),'first_anchor':int(a[0]),'last_anchor':int(a[-1]),'known_cells':int(known.sum()),
        'unknown_cells':int((~known).sum()),'known_by_anchor':[int(x) for x in known.sum(1)],
        'unknown_by_symbol':{str(s):int(v) for s,v in zip(sy,(~known).sum(0)) if v},'elapsed_seconds':time.monotonic()-start,
        'limits':c['limits'],'no_economic_or_membership_claim':True}
    (root/'CONTRACT.json').write_bytes(cp.read_bytes())
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json'),'utc':result['utc']},indent=2)+'\n')
    print({k:result[k] for k in ('status','n_anchors','known_cells','unknown_cells','elapsed_seconds')})

if __name__=='__main__':run(*sys.argv[1:])
