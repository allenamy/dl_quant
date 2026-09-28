"""Reuse the frozen NC King block on joined inputs; old-boundary control must be bitwise equal."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR')
from pathlib import Path
import json,sys,time,importlib.util
import numpy as np
from funding_overlap import sha

BASE=Path('/dev/shm/nc_2026-09-23')
PINS={str(BASE/'devices/nc_hist_features.py'):'3eee6e8842eb86cf203c8eb86c55e7c33d8a18532c080fda0376c317d7cda343',str(BASE/'tree/PATCH_RECEIPT.json'):'88a9d426c30015809c3d2b4e8a89db8a618ea3d7d6766ed79c4993102e344612',str(BASE/'inputs/bundle_config.json'):'3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e'}

def materialize(path):
    with np.load(path) as z:return {k:z[k] for k in z.files}

def exact(a,b):
    a,b=np.asarray(a),np.asarray(b)
    return a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()

def main(root):
    start=time.monotonic();root=Path(root);pins=PINS.copy()
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('fixed NC source changed '+p)
    wr=Path('/dev/shm/recent_rolling_inputs_20260928');fr=Path('/dev/shm/recent_funding_continuation_20260928_materialized')
    for r in (wr,fr):
        term=json.loads((r/'TERMINAL.json').read_text())
        if term['rc']!=0 or term['result_sha256']!=sha(r/'RESULT.json'):raise ValueError('input task incomplete')
        pins[str(r/'RESULT.json')]=sha(r/'RESULT.json')
    wrec=json.loads((wr/'RESULT.json').read_text());frec=json.loads((fr/'RESULT.json').read_text())
    for n,v in wrec['outputs'].items():
        p=wr/n
        if sha(p)!=v['sha256']:raise ValueError('rolling artifact')
        pins[str(p)]=v['sha256']
    fp=fr/'FUND_CONTINUATION.npz'
    if sha(fp)!=frec['output']['sha256']:raise ValueError('fund artifact')
    pins[str(fp)]=sha(fp)
    spec=importlib.util.spec_from_file_location('fixed_history',BASE/'devices/nc_hist_features.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H);H.set_tree(str(BASE/'tree'))
    original=H.Inputs();ax=materialize(wr/'axes.npz');b=materialize(wr/'boundary.npz');f=materialize(fp)
    if not exact(ax['symbols'],f['symbols']) or not exact(ax['anchors'],f['anchors']):raise ValueError('fund/rolling axes')
    class Extended(H.Inputs):
        def __init__(self):
            self.ts=ax['ts'];self.syms=[str(s) for s in ax['symbols']];self.cols=ax['crypto_cols'];self.NW=len(self.syms);self.anchors=ax['anchors']
            self.C=np.load(wr/'cache_crypto.npy',mmap_mode='r');self.R=np.load(wr/'R_crypto.npy',mmap_mode='r');self.bt=b['ts'];self.bc=b['col'];self.br=b['raw'];self.crypto=np.zeros(self.NW,bool);self.crypto[self.cols]=True
        def funding(self,A):
            i=int(np.searchsorted(self.anchors,A))
            if i>=len(self.anchors) or self.anchors[i]!=A:raise ValueError('missing funding anchor')
            ema,led={},{}
            for j in self.cols:
                if f['ledger_ft'][i,j]<0:continue
                acc,iv,last=f['acc'][i,j],f['iv'][i,j],int(f['last_ts'][i,j]);s=self.syms[j]
                ema[s]={'acc':None if np.isnan(acc) else float(acc),'last_ts':None if last<0 else last}
                led[s]=[[int(f['ledger_ft'][i,j]),float(f['rate'][i,j]),None if np.isnan(iv) else float(iv)]]
            return ema,led
    I=Extended();cfg=json.loads((BASE/'inputs/bundle_config.json').read_text());kb=H._king_block();A=int(I.anchors[0])
    old=H.pass1_anchor(original,A,cfg['params'],cfg,kb);new=H.pass1_anchor(I,A,cfg['params'],cfg,kb)
    controls={k:exact(old[k],new[k]) for k in ('members','m','king_X78','fe_v','fn_v','iv_v','qvm','rev24')}
    controls['base_values']=list(old['base_vals'].items())==list(new['base_vals'].items())
    if not all(controls.values()):raise ValueError('boundary control '+repr(controls))
    rows=[new]
    for A in I.anchors[1:]:
        if time.monotonic()-start>300:raise TimeoutError('300s feature budget')
        row=H.pass1_anchor(I,int(A),cfg['params'],cfg,kb)
        if 'm' not in row:raise ValueError('King block unavailable at '+str(A))
        rows.append(row)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('source drift '+p)
    root.mkdir(exist_ok=False);count=np.array([len(r['m']) for r in rows],np.int64)
    arrays={k:np.concatenate([r[k] for r in rows]) for k in ('m','king_X78','fe_v','fn_v','iv_v','qvm','rev24')}
    base=np.full((len(rows),I.NW),np.nan)
    for i,r in enumerate(rows):
        for s,v in r['base_vals'].items():base[i,I.syms.index(s)]=v
    output=root/'KING_FEATURES_AND_MEMBERS.npz';np.savez_compressed(output,anchors=I.anchors,symbols=np.asarray(I.syms),count=count,off=np.r_[0,np.cumsum(count)],base_vals=base,**arrays)
    result={'status':'SAME_NC_KING_FEATURE_EXTENSION_NOT_FULL_COMBO','source_sha256':sha(__file__),'inputs':pins,'output':{'sha256':sha(output),'bytes':output.stat().st_size,'path':str(output)},'anchors':len(rows),'first_anchor':int(I.anchors[0]),'last_anchor':int(I.anchors[-1]),'count_by_anchor':count.tolist(),'boundary_controls':controls,'seconds':time.monotonic()-start,'python':sys.executable,'numpy':np.__version__,'limits':['Production-equivalent NC source, not current live state parity','Future public archive availability is not real-time arrival proof','F10 mini features, predictions, continuous sleeves and cash still outstanding']}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')},indent=2)+'\n');print({k:result[k] for k in ('status','anchors','boundary_controls','seconds')})

if __name__=='__main__':main(*sys.argv[1:])
