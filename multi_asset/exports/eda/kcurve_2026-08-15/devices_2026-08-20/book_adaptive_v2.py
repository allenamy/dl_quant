"""v2: 深度=真实成本均价口径 unrealizedProfit/|notional|(v1 用累计盈亏无重置 ⇒ S1 假触发, 换手翻倍是签名)。
记账: 份额 sh=w/P; 加仓→成本加权; 减仓→按比例实现; 反向/清零→重置。depth=sign*(1−avg/P)。
自检: 触发频率必须与实盘经验同量级(110名20天1次 ≈ 18次/年), 否则仪器仍错。"""
import sys, json, datetime
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA+"/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002; ANN = np.sqrt(6*365)
DEPTH = -0.25; COOL = 42
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h"); SYMS = [str(s) for s in src.symbols]
dates = []; cnt = {}
for i in range(n):
    y = int(yr[i]); cnt[y] = cnt.get(y, 0)+1
    dates.append(datetime.date(y,1,1).toordinal() + min(365, cnt[y]//6))
dates = np.array(dates)
closes = {k: {int(x): v2 for x, v2 in v.items()} for k, v in json.load(open('/mnt/storage/private/work_hsy/w3lane/s30/daily_closes_2020.json')).items()}
D0 = datetime.date(2020,1,5).toordinal(); D1 = datetime.date(2026,8,19).toordinal(); DD = D1-D0+1
def px(s):
    p = np.full(DD, np.nan)
    for dd, c in closes.get(s, {}).items():
        if D0 <= dd <= D1: p[dd-D0] = c
    return p
lb = np.log(px('BTCUSDT')); E=[]; Hh=[]
for s in closes:
    if s == 'BTCUSDT': continue
    lp = np.log(px(s)); r = np.diff(lp)-np.diff(lb)
    for t0_ in range(0, DD-10, 5):
        lpc=0.0; hit=-1
        for k in range(t0_, min(t0_+60, DD-9)):
            if k >= len(r) or not np.isfinite(r[k]): break
            lpc += r[k]
            if np.expm1(-lpc) <= DEPTH: hit=k; break
        if hit<0: continue
        w = r[hit+1:hit+8]
        if len(w)<7 or not np.isfinite(w).all(): continue
        E.append(D0+hit); Hh.append(-float(np.expm1(w.sum())))
E=np.array(E); Hh=np.array(Hh); rc={}
def reg(d):
    if d in rc: return rc[d]
    m=(E>=d-395)&(E<=d-30)
    rc[d]='H' if m.sum()<200 else ('C' if Hh[m].mean()<-0.0002 else 'H')
    return rc[d]
REG = np.array([reg(d) for d in dates])
TGT, MSK, RET = [], [], []
held = {"k": np.full(N,np.nan), "s": np.full(N,np.nan), "f": np.full(N,np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i==0 or ti%8==0:
        v=np.full(N,np.nan); v[m]=src.king[ti,m]; held["k"]=v
    if i==0 or ti%24==0:
        v=np.full(N,np.nan); v[m]=src.s2[ti,m]; held["s"]=v
    if i==0 or ti%8==0:
        v=np.full(N,np.nan); v[m]=src.CH[ti,m,FI]; held["f"]=v
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=src.CH[ti,m,RVI].astype(float), risk_budget=RB)
    w = np.full(N,0.0); w[m]=np.asarray(r["target_w"],float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti,m].astype(float))
def run(mode):
    state=None; prev=np.zeros(N)
    P=np.ones(N); sh=np.zeros(N); cost=np.zeros(N)
    cnt2=np.zeros(N,int); su=np.full(N,-1); fires=[]
    pnl=np.zeros(n); trn=np.zeros(n)
    for i in range(n):
        m=MSK[i]; syms=[SYMS[j] for j in m]
        out=LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05); state=out["state"]
        tgt=np.asarray(out["target_w"],float)
        if mode!='S0':
            bs=set(np.where(su>i)[0].tolist())
            if bs:
                for k2,j in enumerate(m):
                    if j in bs: tgt[k2]=0.0
        w=prev.copy(); w[[j for j in range(N) if j not in set(m)]]=0.0
        delta=tgt-w[m]; T=np.abs(delta)>BW
        wm=w[m].copy(); wm[T]=tgt[T]
        if T.any(): wm[T]-=wm.sum()/T.sum()
        w[m]=wm
        # ---- 成本均价记账 ----
        nsh = np.where(np.abs(P)>1e-12, w/P, 0.0)
        same = np.sign(nsh)==np.sign(sh)
        add = same & (np.abs(nsh)>np.abs(sh))
        red = same & (np.abs(nsh)<=np.abs(sh)) & (np.abs(nsh)>1e-12)
        new = (~same) | (np.abs(sh)<1e-12)
        cost = np.where(add, cost + (nsh-sh)*P, cost)
        with np.errstate(all='ignore'):
            cost = np.where(red, cost*np.where(np.abs(sh)>1e-12, nsh/np.where(np.abs(sh)>1e-12, sh, 1.0), 0.0), cost)
        cost = np.where(new, nsh*P, cost)
        cost = np.where(np.abs(nsh)<1e-12, 0.0, cost)
        sh = nsh
        with np.errstate(all='ignore'):
            avg = np.where(np.abs(sh)>1e-12, cost/sh, np.nan)
            depth = np.where(np.isfinite(avg)&(P>0), np.sign(sh)*(1.0-avg/P), 0.0)
        if mode!='S0':
            need = 2 if mode=='S1' else 1
            gate = (mode!='S3') or (REG[i]=='C')
            hit = (np.abs(sh)>1e-12)&(depth<=DEPTH)&(su<=i)&gate
            cnt2=np.where(hit, cnt2+1, 0)
            fire=cnt2>=need
            if fire.any():
                su[fire]=i+COOL; cnt2[fire]=0; fires.append((int(yr[i]), int(fire.sum())))
        y=RET[i]; ok=np.isfinite(y); idx=m[ok]
        c=np.zeros(N); c[idx]=w[m][ok]*y[ok]*1e4
        pnl[i]=c.sum(); trn[i]=float(np.abs(w-prev).sum()); prev=w
        upd=np.zeros(N); upd[idx]=y[ok]
        P=P*(1.0+upd)
    return pnl, trn, fires
res={}
for mode in ('S0','S1','S2','S3'):
    g,t,fr = run(mode)
    net=g-t*C1; df=pd.DataFrame({'y':yr,'net':net})
    fy={}
    for y_,k in fr: fy[y_]=fy.get(y_,0)+k
    res[mode]={'net_all':round(float(net.mean()),3),'sharpe':round(float(net.mean()/net.std(ddof=1)*ANN),2),
               'by_year':{int(y_):round(float(gg.net.mean()),3) for y_,gg in df.groupby('y')},
               'p5':round(float(np.percentile(net,5)),1),'turnover':round(float(t.mean()),4),
               'fires_total':int(sum(v for _,v in fr)),'fires_per_year':fy}
    print(mode, json.dumps(res[mode],ensure_ascii=False))
json.dump(res, open(f'{PD}/book_adaptive_v2.json','w'))
