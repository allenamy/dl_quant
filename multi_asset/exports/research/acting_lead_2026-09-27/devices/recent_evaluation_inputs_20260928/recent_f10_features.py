"""Same NC mini pipeline, continuous member history, fixed old-boundary control; no model selection."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR',NC_WS='/dev/shm/nc_2026-09-23/ws')
from pathlib import Path
import json,sys,time,importlib.util,types,traceback
import numpy as np
from funding_overlap import sha
from recent_king_features import PINS,BASE,materialize,exact

FEATURES=Path('/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz')
FEATURES_SHA='3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8'
INPUTS={
 '/dev/shm/recent_king_features_20260928/KING_FEATURES_AND_MEMBERS.npz':'0a8f4bb1f9a01d5c6ecd7047e4f63a72fe627809186dbb176b9d202ff36b6855',
 '/dev/shm/recent_rolling_inputs_20260928/axes.npz':'5f52c24b760fbd713145f877f2eb6be38453c3f9d856abe310248c1924e55153',
 '/dev/shm/recent_rolling_inputs_20260928/cache_crypto.npy':'7e9b8007ec362844b72b3f27c92df77c8998f2d2227691db7453acfef4c99b68',
 '/dev/shm/recent_rolling_inputs_20260928/R_crypto.npy':'124356330f765ceb4c8690bcc7be581dd43aedebc4d2e2cf4ab26966c89c968b',
 '/dev/shm/recent_rolling_inputs_20260928/boundary.npz':'022d519beb788728a4c59d8b608301ac869d7709d87b9a2452007c128866ae5e',
 '/dev/shm/recent_funding_continuation_20260928_materialized/FUND_CONTINUATION.npz':'8314a8dadfcad415d66d34e3c0adb3a408f82a77e2060a9bcaeb677238a10275'}

def resources():
    mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    if mem['MemAvailable']<8*2**30:raise RuntimeError('shared memory headroom <8GiB')
    uid=os.getuid();rss=0
    for d in Path('/proc').iterdir():
        if not d.name.isdigit():continue
        try:
            lines={l.split(':')[0]:l.split(':',1)[1].strip() for l in (d/'status').read_text().splitlines()}
            if int(lines['Uid'].split()[0])==uid:rss+=int(lines.get('VmRSS','0 kB').split()[0])*1024
        except (FileNotFoundError,ProcessLookupError,PermissionError,KeyError):continue
    if rss>30*2**30:raise RuntimeError('shared uid RSS >30GiB')
    return rss

def main(root):
    start=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);pins={**PINS,**INPUTS,str(FEATURES):FEATURES_SHA,str(Path(__file__).resolve()):sha(__file__)}
    for name in ('funding_overlap.py','recent_king_features.py'):
        p=Path(__file__).with_name(name);pins[str(p)]=sha(p)
    (root/'START.json').write_text(json.dumps({'pid':os.getpid(),'pgid':os.getpgid(0),'ticks':Path('/proc/self/stat').read_text().split()[21],'utc':time.strftime('%FT%TZ',time.gmtime()),'budget_seconds':900,'inputs':pins},indent=2)+'\n')
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input identity '+p)
    peak=resources();spec=importlib.util.spec_from_file_location('fixed_history',BASE/'devices/nc_hist_features.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H);H.set_tree(str(BASE/'tree'))
    wr=Path('/dev/shm/recent_rolling_inputs_20260928');ax=materialize(wr/'axes.npz');b=materialize(wr/'boundary.npz');f=materialize('/dev/shm/recent_funding_continuation_20260928_materialized/FUND_CONTINUATION.npz');k=materialize('/dev/shm/recent_king_features_20260928/KING_FEATURES_AND_MEMBERS.npz')
    if not exact(ax['anchors'],f['anchors']) or not exact(ax['anchors'],k['anchors']) or not exact(ax['symbols'],f['symbols']) or not exact(ax['symbols'],k['symbols']):raise ValueError('new axes')
    I=H.Inputs();I.ts=ax['ts'];I.anchors=ax['anchors'];I.C=np.load(wr/'cache_crypto.npy',mmap_mode='r');I.R=np.load(wr/'R_crypto.npy',mmap_mode='r');I.bt=b['ts'];I.bc=b['col'];I.br=b['raw']
    if I.syms!=list(ax['symbols']) or not exact(I.cols,ax['crypto_cols']):raise ValueError('original axis')
    def funding(self,A):
        ix=int(np.searchsorted(self.anchors,A))
        if ix>=len(self.anchors) or self.anchors[ix]!=A:raise ValueError('funding anchor')
        ema,led={},{}
        for j in self.cols:
            if f['ledger_ft'][ix,j]<0:continue
            s=self.syms[j];acc,iv=f['acc'][ix,j],f['iv'][ix,j];last=int(f['last_ts'][ix,j]);ema[s]={'acc':None if np.isnan(acc) else float(acc),'last_ts':None if last<0 else last};led[s]=[[int(f['ledger_ft'][ix,j]),float(f['rate'][ix,j]),None if np.isnan(iv) else float(iv)]]
        return ema,led
    I.funding=types.MethodType(funding,I)
    with np.load(FEATURES) as z:
        old={q:z[q] for q in ('anchors','off','m','count','symbols')}
    if list(old['symbols'])!=I.syms:raise ValueError('old feature axis')
    MH={int(a):old['m'][old['off'][i]:old['off'][i+1]].astype(np.int64) for i,a in enumerate(old['anchors'])}
    for i,a in enumerate(k['anchors']):
        m=k['m'][k['off'][i]:k['off'][i+1]].astype(np.int64)
        if a in MH and not exact(m,MH[int(a)]):raise ValueError('member prefix drift')
        MH[int(a)]=m
    code=H._mini_block();cf=H._combo_funcs();work=root/'scratch';work.mkdir();rows=[];checks={};outputs={}
    for i,A in enumerate(I.anchors):
        if time.monotonic()-start>880:raise TimeoutError('reserved finalization time')
        peak=max(peak,resources());r=H.pass2_anchor(I,int(A),MH,str(work),code,cf)
        if int(r['mh_missing'])!=0:raise ValueError('member history missing')
        if i==0:
            ai=np.flatnonzero(old['anchors']==A)
            if len(ai)!=1:raise ValueError('old boundary absent')
            j=int(ai[0]);sl=slice(int(old['off'][j]),int(old['off'][j+1]))
            with np.load(FEATURES) as z:
                for key in ('X82','X89'):
                    expected=z[key][sl].copy();checks[key]=exact(np.asarray(r[key],np.float32),expected)
            if not all(checks.values()):raise ValueError('frozen original feature control '+repr(checks))
            (root/'BOUNDARY_CONTROL.json').write_text(json.dumps({'status':'BITWISE_EQUAL','checks':checks,'anchor':int(A),'reference':FEATURES_SHA},indent=2)+'\n')
        p=root/f'ROW_{A}.npz';np.savez_compressed(p,anchor=np.int64(A),members=MH[int(A)],X82=np.asarray(r['X82'],np.float32),X89=np.asarray(r['X89'],np.float32),btcv=np.float64(r['btcv_anchor']))
        outputs[p.name]={'sha256':sha(p),'bytes':p.stat().st_size};rows.append(r)
        print(time.strftime('%H:%M:%S',time.gmtime()),'ROW',i+1,len(I.anchors),int(A),flush=True)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input changed '+p)
    result={'status':'SAME_NC_F10_FEATURES_COMPLETE_NOT_PREDICTION_OR_CASH','source_sha256':sha(__file__),'inputs':pins,'outputs':outputs,'anchors':len(rows),'first_anchor':int(I.anchors[0]),'last_anchor':int(I.anchors[-1]),'boundary_controls':checks,'seconds':time.monotonic()-start,'peak_sampled_shared_rss':peak,'python':sys.executable,'mini_python':str((BASE/'ws/venv/bin/python').resolve()),'limits':['Fixed original NC feature-code path; production state parity not asserted','Final public archive availability is not original arrival evidence','No training, prediction, strategy outcome or release decision']}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json'),'utc':time.strftime('%FT%TZ',time.gmtime())},indent=2)+'\n')

if __name__=='__main__':
    try:main(sys.argv[1])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True);(root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'utc':time.strftime('%FT%TZ',time.gmtime())},indent=2)+'\n');raise
