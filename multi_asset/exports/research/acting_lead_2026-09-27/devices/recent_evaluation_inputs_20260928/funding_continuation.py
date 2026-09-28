"""Continue fixed NC funding state through Sep 28 00Z without reseeding its past.

No source file is modified. Only future event rows from the separately frozen
production archive are appended, using the very NC contract that built the
original state. This is not proof of venue completeness or live arrival times.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
from datetime import datetime,timezone
import sys,json,time,importlib.util
import numpy as np
from funding_overlap import event_map,no_duplicates,sha

OVERLAP_SHA='28d1a72787b222085b8c2e218665f3935c5d07beb29ba74682427551ae68f1ec'
END=int(datetime(2026,9,28,tzinfo=timezone.utc).timestamp())

def ordered_events(events,begin,end):
    times=[t for t,r in events]
    if any(type(t)!=int for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('event order')
    return [(t,r) for t,r in events if begin<t<=end]

def main(root):
    start=time.monotonic();root=Path(root);prior=Path('/dev/shm/recent_funding_overlap_20260928/RESULT.json')
    if sha(prior)!=OVERLAP_SHA:raise ValueError('overlap changed')
    r=json.loads(prior.read_text());pins=r['inputs'].copy();pins[str(prior)]=OVERLAP_SHA
    if r['rate_differences'] or r['new_only_oldwindow_count']:raise ValueError('old/recent funding disagreement')
    # Three absent ONG rows are retained from the old input, never replaced by zero.
    if r['old_only']!=[['ONGUSDT',1788220800],['ONGUSDT',1788224400],['ONGUSDT',1788228000]]:raise ValueError('known old-only population changed')
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input drift '+p)
    op=Path('/dev/shm/nc_2026-09-23');prep=json.loads((op/'receipts/NC_PREP.json').read_text());ncp=op/'tree/fea171/nc_contract.py'
    if sha(ncp)!=prep['nc_contract_sha256']:raise ValueError('wrong funding contract')
    pins[str(ncp)]=sha(ncp);spec=importlib.util.spec_from_file_location('fixed_nc',ncp);nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
    # NpzFile is lazy: indexing it inside the symbol loop decompresses the whole
    # member every time. Materialize each fixed input exactly once, then index
    # the same arrays; no state, event order or numerical operation is changed.
    with np.load(op/'work/fund_state.npz') as z:
        f={k:z[k] for k in ('ev_off','ft','kidx','iv','ema','prev','rate')}
    with np.load(op/'work/axes.npz') as z:
        ax={k:z[k] for k in ('crypto_cols','symbols','anchors')}
    cols=ax['crypto_cols'];symbols=ax['symbols'];begin=int(ax['anchors'][-1]);anchors=np.arange(begin,END+1,14400,dtype=np.int64)
    raw=json.loads(Path('/dev/shm/recent_funding_overlap_20260928/funding_ledger_2026-09.json').read_text(),object_pairs_hook=no_duplicates);new=event_map(raw);by={str(s):[] for s in symbols}
    for (s,t),rate in sorted(new.items()):
        if s in by:by[s].append((t,rate))
    shape=(len(anchors),len(symbols));out={k:np.full(shape,np.nan) for k in ('rate','iv','acc','fe_asof','fn_asof','fi_asof','rn8_asof')}
    out['ledger_ft']=np.full(shape,-1,np.int64);out['last_ts']=np.full(shape,-1,np.int64);applied=0;first_checked=0
    for ci,j in enumerate(cols):
        b,e=int(f['ev_off'][ci]),int(f['ev_off'][ci+1]);old_t=f['ft'][b:e];last=int(f['kidx'][-1,ci])
        if last!=int(np.searchsorted(old_t,begin,side='right')-1):raise ValueError('old asof state index')
        if last<0:led=[];state={'acc':None,'last_ts':None}
        else:
            pos=b+last;iv=float(f['iv'][pos]);acc=float(f['ema'][pos]);prev=int(f['prev'][pos]);led=[[int(f['ft'][pos]),float(f['rate'][pos]),iv if np.isfinite(iv) else None]];state={'acc':acc if np.isfinite(acc) else None,'last_ts':prev if prev>=0 else None}
        initial=(list(led[0]) if led else None,state.copy());events=ordered_events(by[str(symbols[j])],begin,END);n=0
        for i,A in enumerate(anchors):
            while n<len(events) and events[n][0]<=A:
                led,state,_=nc.ingest_settlements(led[-1:],state,[events[n]]);n+=1;applied+=1
            if i==0:
                if (list(led[0]) if led else None,state)!=initial:raise ValueError('prefix changed')
                first_checked+=1
            if led:
                row=led[-1];out['ledger_ft'][i,j]=row[0];out['rate'][i,j]=row[1];out['iv'][i,j]=np.nan if row[2] is None else row[2]
                if row[0]>A:raise ValueError('future row used')
            out['acc'][i,j]=np.nan if state['acc'] is None else state['acc'];out['last_ts'][i,j]=-1 if state['last_ts'] is None else state['last_ts']
            asof=nc.funding_asof(state,led[-1] if led else None,int(A))
            for k,v in zip(('fe_asof','fn_asof','fi_asof','rn8_asof'),asof):out[k][i,j]=v
        if n!=len(events):raise ValueError('unconsumed in-window events')
    if time.monotonic()-start>120:raise TimeoutError('120s data preparation budget')
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input changed during continuation')
    root.mkdir(exist_ok=False);output=root/'FUND_CONTINUATION.npz'
    with output.open('xb') as f_out:np.savez_compressed(f_out,anchors=anchors,symbols=symbols,**out)
    result={'status':'FUND_STATE_CONTINUATION_COMPLETE_NOT_MODEL_OR_CASH','utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(__file__),'helper_sha256':sha(Path(__file__).with_name('funding_overlap.py')),
        'inputs':pins,'output':{'path':str(output),'sha256':sha(output),'bytes':output.stat().st_size},'first_anchor':int(anchors[0]),'last_anchor':int(anchors[-1]),'anchors':len(anchors),'source_names':len(cols),'initial_states_unchanged':first_checked,'applied_events':applied,
        'fresh_known_by_anchor':[int(x) for x in np.isfinite(out['fe_asof']).sum(1)],'old_only_retained':r['old_only'],'new_archive_names_not_in_research_crypto_axis':r['new_archive_outside_old_crypto_axis'],'seconds':time.monotonic()-start,
        'limits':['Research NC state continuation, not a production state replacement','Same old interval/EMA contract, no D10 policy switch','Archive completeness and original arrival timestamps not certified','Feature reconstruction, continuous book and cash evaluation still required']}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')},indent=2)+'\n')
    print({k:result[k] for k in ('status','anchors','initial_states_unchanged','applied_events','seconds')})

if __name__=='__main__':main(*sys.argv[1:])
