"""Offline state handoff, exact prior identity and production persistence order."""
import time
import numpy as np

def select_seed(data, symbols, anchor):
    a=np.asarray(data['E_ts']);sy=np.asarray(data['symbols'])
    if a.ndim!=1 or len(a)==0 or not np.isfinite(a).all() or np.any(a!=np.floor(a)) or np.any(a%14400) or np.any(np.diff(a)!=14400):raise ValueError('seed_clock')
    if len(set(map(str,sy)))!=len(sy) or not np.array_equal(sy,np.asarray(symbols)):raise ValueError('seed_axis')
    ix=np.flatnonzero(a==anchor)
    if len(ix)!=1:raise ValueError('seed_exact_anchor')
    out={}
    for k in ('kc','fc'):
        x=np.asarray(data[k])
        if x.shape!=(len(a),len(sy)):raise ValueError('seed_shape')
        v=x[int(ix[0])].astype(float).copy()
        if not np.isfinite(v).all():raise ValueError('seed_nonfinite')
        out[k]=v
    return out

def evolve(step, frames, params, initial, holds):
    began=time.monotonic();a=np.asarray([f['anchor'] for f in frames])
    if len(a)==0 or not np.isfinite(a).all() or np.any(a!=np.floor(a)) or np.any(a%14400) or np.any(np.diff(a)!=14400) or not set(holds)<=set(a):raise ValueError('path_clock')
    state={k:np.asarray(initial[k],float).copy() for k in ('kc','fc')}
    if state['kc'].ndim!=1 or state['fc'].shape!=state['kc'].shape or not all(np.isfinite(v).all() for v in state.values()):raise ValueError('path_state')
    published=.55*state['kc']+.45*state['fc'];rows=[]
    for f in frames:
        if time.monotonic()-began>120:raise TimeoutError('120s')
        anchor=f['anchor'];accepted=False;reason='source_anchor_missing'
        raw=.55*state['kc']+.45*state['fc'];reshaped=None
        if anchor not in holds:
            r=step(**f['args'],params=params,kc_prev=state['kc'].copy(),fc_prev=state['fc'].copy(),publication='literal')
            # Producer writes both H files before publication checks.
            for k in state:
                v=np.asarray(r[k],float)
                if v.shape!=state[k].shape or not np.isfinite(v).all():raise ValueError('new_state_unknown')
                state[k]=np.where(np.abs(v)>1e-9,v,0.)
            raw=r['raw'];accepted=bool(r['accepted']);reason=r['reason'];reshaped=r['executor_reshaped']
            if accepted:
                if raw is None or not np.isfinite(raw).all():raise ValueError('published_unknown')
                published=np.where(np.abs(raw)>1e-9,raw,0.)
        rows.append({'anchor':int(anchor),'accepted':accepted,'reason':reason,'kc':state['kc'].copy(),'fc':state['fc'].copy(),'raw':None if raw is None else raw.copy(),'published':published.copy(),'reshaped':None if reshaped is None else reshaped.copy()})
    return rows
