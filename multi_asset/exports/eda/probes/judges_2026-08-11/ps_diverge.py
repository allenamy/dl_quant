exec(open('ic_recon.py').read().split('def run(')[0])
import statistics
def series(winsor=None, weight=False):
    out=[]
    for k in range(len(ts)-1):
        T,T2=ts[k],ts[k+1]; m0,m1=mids[T],mids[T2]
        src={s: float(p.get('venue_position_notional') or 0) for s,p in pos.get(T,{}).items()}
        xs,ys=[],[]
        for s,w in src.items():
            if w==0: continue
            a,b=float(m0.get(s,0) or 0), float(m1.get(s,0) or 0)
            if a and b: xs.append(w); ys.append(b/a-1)
        if len(xs)<8: continue
        if winsor:
            lo,hi=sorted(ys)[int(winsor*len(ys))], sorted(ys)[int((1-winsor)*len(ys))-1]
            ys=[min(max(v,lo),hi) for v in ys]
        out.append((T,xs,ys))
    return out
def rep(label, f_):
    v=[f_(xs,ys) for _,xs,ys in series()]
    v=[x for x in v if x is not None]
    m=statistics.mean(v); sd=statistics.stdev(v)
    print('  %-42s n=%2d  %+7.4f  t=%+5.2f'%(label,len(v),m,m/(sd/len(v)**0.5)))
print('=== P/S 分歧的来源 (实际持仓, 10 锚对) ===')
rep('Spearman (你的口径)', lambda x,y: corr(rank(x),rank(y)))
rep('Pearson  (原始)', lambda x,y: corr(x,y))
for w in (0.05,0.10):
    rep('Pearson  (收益 winsorize %d%%)'%int(w*100),
        lambda x,y,w=w: corr(x,[min(max(v,sorted(y)[int(w*len(y))]),sorted(y)[int((1-w)*len(y))-1]) for v in y]))
rep('Pearson  (双侧 rank-normal 变换)', lambda x,y: corr(rank(x),rank(y)))
print()
print('=== 组合真正赚到的: 名义加权收益 (= P&L, 这是 Pearson 那一侧的量) ===')
tot=0.0; g=[]
for T,xs,ys in series():
    p=sum(xs[i]*ys[i] for i in range(len(xs))); gr=sum(abs(v) for v in xs)
    tot+=p; g.append(gr)
    print('  %-14s gross $%8.0f  PnL $%+7.2f  = %+7.2f bps'%(f(T),gr,p,1e4*p/gr))
print('  合计 PnL $%+.2f  = %+.2f bps of 中位 gross'%(tot,1e4*tot/statistics.median(g)))
