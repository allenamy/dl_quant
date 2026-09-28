"""Offline extraction of the pinned producer's pure LR and seat recurrence."""
import copy, hashlib, textwrap
from pathlib import Path
import numpy as np

LEGS=('king','rev24','fund')
SOURCE_SHA='52baf979095752642cde16b1281911c6692f3251cd3b9d6d214a4b624d8d5f38'

def production_blocks(path,expected_sha=SOURCE_SHA):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('source_identity')
    s=raw.decode();start=s.index('    prev = st.prev_rec\n');end=s.index('            smp = ',start)
    lr=textwrap.dedent(s[start:end])
    start=s.index('    look = P["msharpe_look"]\n',end);end=s.index('    # ── 8.',start)
    seats=textwrap.dedent(s[start:end])
    ns={'np':np}
    exec(compile('def advance(st, anchor, CDf, row_of, ai):\n'+textwrap.indent(lr,'    ')+'\n'
                 +'def seats(st,P):\n'+textwrap.indent(seats,'    ')+'    return w3\n',str(path)+':pure_blocks','exec'),ns)
    return ns['advance'],ns['seats']

def validate_lr(lr):
    if set(lr)!=set(LEGS):raise ValueError('LR_keys')
    lens=set()
    for k in LEGS:
        x=np.asarray(lr[k],float)
        if x.ndim!=1 or not len(x) or not np.isfinite(x).all():raise ValueError('LR_invalid')
        lens.add(len(x))
    if len(lens)!=1:raise ValueError('LR_lengths')

def reseed(st,done,anchor,event_ts,lr):
    if done or anchor<event_ts:return done
    validate_lr(lr);st.LR=copy.deepcopy(lr)
    return True

def segment(ts,rr,cols,anchor,n,fetch_mask):
    lo=int(np.searchsorted(ts,anchor-14400));hi=int(np.searchsorted(ts,anchor,side='right'))
    if not np.array_equal(ts[lo:hi],np.arange(anchor-14400,anchor+1,300)):raise ValueError('bar_axis')
    cols=np.asarray(cols,int);mask=np.asarray(fetch_mask,bool)
    if mask.shape!=(n,) or cols.ndim!=1 or len(set(cols.tolist()))!=len(cols) or np.any(cols<0) or np.any(cols>=n):raise ValueError('symbol_axis')
    out=np.full((49,n,1),np.nan,np.float32)
    out[:,cols,0]=rr[lo:hi]
    out[:,~mask,0]=np.nan
    return out
