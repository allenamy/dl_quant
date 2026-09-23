import numpy as np
def fold_rows(a,start,end,embargo=60):
    a=np.asarray(a)
    if a.ndim!=1 or not len(a) or not np.isfinite(a).all() or np.any(a!=np.floor(a)) or np.any(a%14400) or np.any(np.diff(a)!=14400):raise ValueError('anchor axis')
    if start>=end or embargo<1:raise ValueError('fold contract')
    train=np.flatnonzero(a+14400<=start-embargo*14400)
    test=np.flatnonzero((a>=start)&(a<end))
    return train,test
