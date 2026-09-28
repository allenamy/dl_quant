"""Extend fixed NC rolling inputs; never splice absolute closes into log-price cash tables."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import json,sys,time,importlib.util
import numpy as np
from funding_overlap import sha

PREP_SHA='09e769d1e1e6e88e0c437671874455d4ade587540d926fd09cf2f0554b65af33'
PANEL_SHA='ac8bfa6f438d6e96c0bd4317d29961172d8cfe8ef76629f2fdfa474e90dc1fbe'
END=1790553600

def regular(t):
    if t.dtype.kind not in 'iu' or not len(t) or np.any(t%300) or np.any(np.diff(t)!=300):raise ValueError('5m axis')

def raw_return_channel(ts,close,data,observed):
    regular(ts)
    if close.shape!=observed.shape or observed.dtype!=bool or data.shape!=(*close.shape,7) or data.dtype!=np.float16:raise ValueError('panel schema')
    if np.any(observed&(~np.isfinite(close)|(close<=0))):raise ValueError('invalid observed close')
    good=np.zeros(close.shape,bool);good[1:]=observed[1:]&observed[:-1]
    raw=np.full(close.shape,np.nan);raw[1:][good[1:]]=close[1:][good[1:]]/close[:-1][good[1:]]-1
    stored=np.clip(raw,-.3,.3).astype(np.float16)
    # First row's return can have a predecessor outside this panel; do not use it.
    a,b=stored[1:],data[1:,:,0]
    if not np.array_equal(a,b,equal_nan=True):raise ValueError('stored return disagrees with raw adjacent closes')
    rr=stored.astype(np.float32);bound=np.isfinite(stored)&(np.abs(stored.astype(np.float32))==np.float32(np.float16(.3)))
    i,j=np.nonzero(bound);rr[i,j]=raw[i,j].astype(np.float32)
    return rr,ts[i],j.astype(np.int32),raw[i,j].astype(np.float32)

def append_window(ts,c,r,nt,nc,nr,end):
    regular(ts);regular(nt)
    if c.shape!=(len(ts),r.shape[1],7) or r.shape[0]!=len(ts) or nc.shape!=(len(nt),r.shape[1],7) or nr.shape!=(len(nt),r.shape[1]):raise ValueError('join shape')
    if c.dtype!=np.float16 or nc.dtype!=np.float16 or r.dtype!=np.float32 or nr.dtype!=np.float32:raise ValueError('join dtype')
    sel=(nt>ts[-1])&(nt<=end)
    if not sel.any() or nt[sel][0]!=ts[-1]+300 or nt[sel][-1]!=end:raise ValueError('missing seam or end')
    out=(np.concatenate([ts,nt[sel]]),np.concatenate([c,nc[sel]]),np.concatenate([r,nr[sel]]));regular(out[0])
    return out

def main(root):
    start=time.monotonic();root=Path(root);old=Path('/dev/shm/nc_2026-09-23');prep=old/'receipts/NC_PREP.json'
    panel=Path('/dev/shm/recent_inputs_overlap_20260928/RAW_AND_PRODUCTION_CHANNELS.npz')
    if sha(prep)!=PREP_SHA or sha(panel)!=PANEL_SHA:raise ValueError('receipt/panel identity')
    rec=json.loads(prep.read_text());pins={str(prep):PREP_SHA,str(panel):PANEL_SHA}
    for name in ('axes.npz','cache_crypto.npy','R_crypto.npy','boundary.npz'):
        p=old/'work'/name;pins[str(p)]=rec['outputs'][name]
        if sha(p)!=pins[str(p)]:raise ValueError('old input identity '+name)
    with np.load(old/'work/axes.npz') as z:ax={k:z[k] for k in z.files}
    with np.load(panel) as z:n={k:z[k] for k in z.files}
    if not np.array_equal(n['symbols'][:len(ax['symbols'])],ax['symbols']):raise ValueError('symbol identity')
    cols=ax['crypto_cols'];nt=n['ts'];nc=n['data'][:,cols,:]
    nr,bt,bc,br=raw_return_channel(nt,n['close'][:,cols],nc,n['observed'][:,cols])
    C=np.load(old/'work/cache_crypto.npy',mmap_mode='r');R=np.load(old/'work/R_crypto.npy',mmap_mode='r')
    ts=ax['ts'][-11520:];c=np.asarray(C[-11520:]);r=np.asarray(R[-11520:]);tt,cc,rr=append_window(ts,c,r,nt,nc,nr,END)
    if cc[:len(ts)].tobytes()!=c.tobytes() or rr[:len(ts)].tobytes()!=r.tobytes():raise ValueError('old prefix changed')
    with np.load(old/'work/boundary.npz') as z:b={k:z[k] for k in z.files}
    keep=(b['ts']>=ts[0])&(b['ts']<=ts[-1]);new=(bt>ts[-1])&(bt<=END)
    btime=np.concatenate([b['ts'][keep],bt[new]]);bcol=np.concatenate([b['col'][keep],cols[bc[new]]]).astype(np.int32);braw=np.concatenate([b['raw'][keep],br[new]])
    source=old/'tree/fea171/nc_contract.py'
    if sha(source)!=rec['nc_contract_sha256']:raise ValueError('NC contract identity')
    pins[str(source)]=sha(source);spec=importlib.util.spec_from_file_location('nc',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    loc=np.searchsorted(cols,bcol)
    if not np.array_equal(cols[loc],bcol):raise ValueError('boundary axis')
    got=mod.rr_from_ch0(tt,cc[:,:,0],btime,loc,braw)
    same=(got.view(np.uint32)==rr.view(np.uint32))|(np.isnan(got)&np.isnan(rr))
    if not same.all():raise ValueError('G3 rr mismatch')
    if time.monotonic()-start>120:raise TimeoutError('120s input preparation budget')
    root.mkdir(exist_ok=False)
    np.save(root/'cache_crypto.npy',cc);np.save(root/'R_crypto.npy',rr)
    np.savez(root/'axes.npz',ts=tt,symbols=ax['symbols'],crypto_cols=cols,anchors=tt[(tt%14400==0)&(tt>=ts[-1])])
    np.savez(root/'boundary.npz',ts=btime,col=bcol,raw=braw)
    out={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in root.iterdir()}
    # Small inputs and boundaries rechecked; source arrays are read-only mmaps.
    for p in (prep,panel,source,old/'work/axes.npz',old/'work/boundary.npz'):
        if sha(p)!=pins[str(p)]:raise ValueError('input changed during preparation')
    result={'status':'ROLLING_INPUT_EXTENSION_COMPLETE_NOT_FEATURE_OR_CASH','source_sha256':sha(__file__),'inputs':pins,'outputs':out,'old_boundary':int(ts[-1]),'end':END,'old_prefix_rows':len(ts),'new_rows':len(tt)-len(ts),'crypto_names':len(cols),'rr_cells_checked':int(same.size),'old_prefix_bitwise_unchanged':True,'new_boundary_cells':int(new.sum()),'seconds':time.monotonic()-start,'limits':['Original historical prefix retained, not replaced by newly downloaded overlap','No tradability or model/member gate is inferred from file availability','No cash-price table splice or candidate performance measurement','Public final bars are not proof of live arrival timestamps']}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')},indent=2)+'\n');print({k:result[k] for k in ('status','new_rows','rr_cells_checked','new_boundary_cells','seconds')})

if __name__=='__main__':main(*sys.argv[1:])
