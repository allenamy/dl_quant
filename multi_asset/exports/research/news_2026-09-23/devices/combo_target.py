"""Complete King/funding and F10/funding producer state, source-bound kernels.

The publication gate is part of the result. HOLD means keep contracts, not
rebalance yesterday's weights and not substitute the King-only book.
"""
import ast,pathlib,hashlib,json
import numpy as np
from scipy.stats import rankdata

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXPECTED='fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8'

def source_kernels():
    p=ROOT/'vendor_live/fea171/combo_stage.py';raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError('unreviewed producer source')
    t=ast.parse(raw);t.body=[x for x in t.body if isinstance(x,ast.FunctionDef) and x.name in ('chain','exec_reshape')]
    if len(t.body)!=2:raise ValueError('producer kernels absent')
    ns={'np':np};exec(compile(t,str(p),'exec'),ns);return ns

def step(king_rank,f10_score,fund_rank,seats,rn8,members,qv,legal,params,kc_prev,fc_prev,publication='literal'):
    m=np.asarray(members,int);nw=len(kc_prev);n=len(m)
    if len(fc_prev)!=nw or np.asarray(legal).shape!=(nw,) or len(np.unique(m))!=n or np.any(m<0) or np.any(m>=nw):raise ValueError('combo identity')
    if any(np.asarray(v).shape!=(n,) for v in (king_rank,f10_score,fund_rank,rn8,qv)):raise ValueError('member field axes')
    if np.asarray(seats).shape!=(3,) or not np.isfinite(seats).all() or np.any(np.asarray(seats)<0):raise ValueError('seats')
    if not np.isfinite(kc_prev).all() or not np.isfinite(fc_prev).all():raise ValueError('state unknown')
    if not np.isfinite(king_rank).all():return {'accepted':False,'reason':'King scores incomplete','kc':kc_prev.copy(),'fc':fc_prev.copy(),'raw':None,'executor_reshaped':None}
    if publication not in ('literal','scaled_diagnostic'):raise ValueError('publication policy')
    okf=np.isfinite(f10_score);zf=np.full(n,np.nan)
    zf[okf]=rankdata(np.asarray(f10_score)[okf])/max(okf.sum()-1,1)-.5
    w=np.array([seats[0],0.,seats[2]],float);w=w/w.sum() if w.sum()>1e-12 else np.array([.5,0.,.5])
    zkc=w[0]*np.nan_to_num(king_rank,nan=0.)+w[2]*np.nan_to_num(fund_rank,nan=0.)
    zfc=w[0]*np.nan_to_num(zf,nan=0.)+w[2]*np.nan_to_num(fund_rank,nan=0.)
    zkc=np.where((zkc<0)&np.isfinite(rn8)&(rn8<=-.001),0.,zkc)
    zfc=np.where((zfc<0)&np.isfinite(rn8)&(rn8<=-.001),0.,zfc)
    ns=source_kernels();ns.update(P=params,NW=nw,pm=m,sel=np.isfinite(qv)&(np.asarray(qv)>=params['qv4h_min']),LIVE_MASK=np.asarray(legal,bool))
    ns['H']=kc_prev;kc=ns['chain'](zkc);ns['H']=fc_prev;fc=ns['chain'](zfc)
    if kc is None or fc is None:return {'accepted':False,'reason':'degenerate signal','kc':kc_prev.copy(),'fc':fc_prev.copy(),'raw':None,'executor_reshaped':None}
    raw=.55*kc+.45*fc;gross=float(np.abs(raw).sum());names=int((np.abs(raw)>1e-9).sum())
    coverage_gate=380 if publication=='literal' else int(np.ceil(.95*n));names_gate=150 if publication=='literal' else int(np.ceil(.375*n))
    reasons=[]
    if okf.sum()<coverage_gate:reasons.append('F10 coverage')
    if not .4<=gross<=1.2:reasons.append('gross')
    if names<names_gate:reasons.append('names')
    return {'accepted':not reasons,'reason':','.join(reasons) if reasons else 'publish','kc':kc,'fc':fc,'raw':raw,'executor_reshaped':ns['exec_reshape'](raw),'gross':gross,'names':names,'f10_count':int(okf.sum()),'publication':publication,'seat_masked':w}
