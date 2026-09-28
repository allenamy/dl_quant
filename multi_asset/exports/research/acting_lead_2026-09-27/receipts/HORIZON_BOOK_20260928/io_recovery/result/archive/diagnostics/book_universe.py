"""Book eligibility is separate from the wider model training population.

This consumes the frozen historical U-PIT/CRYPTO proxy, not today's symbols
retroactively. Its post-August extension uses the frozen production list and is
explicitly an inherited policy, not independently certified exchange history.
"""
import numpy as np

PATH='/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz'
SHA='3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f'

def align(anchors,symbols,source):
    a=np.asarray(anchors);t=np.asarray(source['ts']);s=np.asarray(symbols)
    if not np.array_equal(s,source['symbols']) or len(np.unique(s))!=len(s):
        raise ValueError('universe symbol identity')
    for x in (a,t):
        if x.ndim!=1 or not len(x) or not np.isfinite(x).all() or np.any(x!=np.floor(x)) or np.any(x%14400) or np.any(np.diff(x)<=0):
            raise ValueError('universe clock')
    pit=np.asarray(source['pit'])
    if pit.shape!=(len(t),len(s)) or pit.dtype!=np.dtype(bool):
        raise ValueError('universe mask schema')
    ix=np.searchsorted(t,a)
    if np.any(ix>=len(t)) or not np.array_equal(t[ix],a):
        raise ValueError('universe missing anchor; no forward/backfill')
    return pit[ix].copy()
