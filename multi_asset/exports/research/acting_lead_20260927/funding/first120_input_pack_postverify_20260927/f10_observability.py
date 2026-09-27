"""Do not make a financial observation out of a missing held-price label.

Training admission is fixed before optimization and conservative over every
possible nonzero EMA holding since the start of a contiguous burn-in window.
It is never used to delete test anchors or to choose the scoring population.
"""
import numpy as np

def span_admissible(members,y,idx,legs_ready):
    idx=np.asarray(idx)
    if idx.dtype.kind not in 'iu' or len(idx)==0 or np.any(np.diff(idx)!=1):raise ValueError('contiguous training span required')
    if idx[0]<0 or idx[-1]>=len(y):raise ValueError('span bounds')
    possible=np.zeros(y.shape[1],bool)
    for i in idx:
        if not legs_ready[i]:return False,{'reason':'missing_causal_legs','anchor':int(i)}
        m=np.asarray(members[i],int)
        if np.any(m<0) or np.any(m>=y.shape[1]) or len(np.unique(m))!=len(m):raise ValueError('member identity')
        possible[m]=True
        bad=possible&~np.isfinite(y[i])
        if bad.any():return False,{'reason':'unpriced_possible_holding','anchor':int(i),'symbol':int(np.flatnonzero(bad)[0])}
    return True,{'reason':'complete_contiguous_training_span','anchors':len(idx),'possible_names':int(possible.sum())}

def measured_dot(w,y):
    w,y=np.asarray(w),np.asarray(y)
    if w.shape!=y.shape or not np.isfinite(w).all():return None
    held=w!=0
    if not np.isfinite(y[held]).all():return None
    return float(w[held]@y[held])
