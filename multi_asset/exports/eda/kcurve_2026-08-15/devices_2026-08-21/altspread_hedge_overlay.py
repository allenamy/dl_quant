"""叠加层判官: 书外加 h×(等权山寨 − BTC) 多头叠加(h=0.25/0.5/1.0 × 实测β), 不改书; 与五臂(改书中性化)不同。
度量: 逐年 均值/夏普/maxDD/最坏30天窗; 叠加成本=山寨多头 funding(用面板 funding 估) + 忽略换手(β 慢变);
触线概率 @gross 2.0/3.0(块180). 判据(冻结先于看数): 采纳候选需 全史夏普 ≥ 基线 且 逐年夏普不劣 ≥4/5 且 最坏窗改善 ≥25%."""
import sys, json, time, numpy as np
PD="/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0,PD)
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0,MA); sys.path.insert(0,MA+"/engine/live"); sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
import engine.replay_fullhist as RF
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz"); a,yr=RF._all_anchors(src); N=src.N; n=len(a)
SY=[str(s) for s in src.symbols]; ib=SY.index("BTCUSDT"); ie=SY.index("ETHUSDT") if "ETHUSDT" in SY else -1; FI=src.fund_idx
Y=np.full((n,N),np.nan); F=np.full((n,N),np.nan)
for i,t in enumerate(a):
    ti=int(t); m=np.asarray(src.tradeable(ti)); m=np.where(m)[0] if m.dtype==bool else m
    Y[i,m]=src.Y4[ti,m].astype(float); F[i,m]=src.CH[ti,m,FI].astype(float)
alt=np.array([j for j in range(N) if j not in (ib,ie)])
r_alt=np.nanmean(Y[:,alt],1); r_btc=Y[:,ib]; dAS=(r_alt-r_btc)*1e4            # bps/锚
f_alt=np.nanmean(F[:,alt],1); f_btc=F[:,ib]
# 山寨多头叠加的 funding 成本(bps/锚): 多山寨付 funding(费率正=多付), 空 BTC 收 BTC funding; 资金费每8h结算 ⇒ 每锚 1/2
carry=(-(np.nan_to_num(f_alt))+np.nan_to_num(f_btc))*1e4*0.5
net=np.load(f"{PD}/net_S1.npy")
ok=np.isfinite(dAS)&np.isfinite(net)
beta=-float(np.polyfit(dAS[ok],net[ok],1)[0]); print("实测β(书对山寨-BTC)", round(beta,3), "| dAS 均值 bps/锚", round(float(dAS[ok].mean()),3), "| 叠加carry均值 bps/锚(×1.0β)", round(float((beta*carry[ok]).mean()),3), flush=True)
ANN=np.sqrt(6*365)
def stats(x):
    cum=np.cumsum(x); dd=cum-np.maximum.accumulate(cum); w=np.array([x[i:i+180].sum() for i in range(0,len(x)-180,6)])
    return {"mean":round(float(x.mean()),3),"sharpe":round(float(x.mean()/x.std()*ANN),2),"maxDD":round(float(-dd.min()),0),"worst30d":round(float(w.min()),0)}
def killp(x,gross,seed=11):
    rng=np.random.RandomState(seed); L_=180; nb=len(x)//L_; NY=2190; nbk=NY//L_+1; hit=0
    for _ in range(1500):
        idx=rng.randint(0,nb,nbk); path=np.concatenate([x[i*L_:(i+1)*L_] for i in idx])[:NY]*gross/1e4
        cum=np.cumprod(1+path); hit+= (cum/np.maximum.accumulate(cum)-1).min()<=-0.25
    return round(hit/1500,3)
res={}
for hmul in (0.0,0.25,0.5,0.75,1.0):
    h=hmul*beta; x=net+h*dAS+h*carry; x=x[ok]; yy=yr[ok]
    r=stats(x); r["by_year_sharpe"]={int(y):round(float(x[yy==y].mean()/x[yy==y].std()*ANN),2) for y in sorted(set(yy.tolist()))}
    r["by_year_mean"]={int(y):round(float(x[yy==y].mean()),3) for y in sorted(set(yy.tolist()))}
    r["P_hit25_g2"]=killp(x,2.0); r["P_hit25_g3"]=killp(x,3.0)
    res[f"h{hmul}"]=r; print(f"h={hmul}×β", json.dumps(r,ensure_ascii=False), flush=True)
# 同 gross 约束下, 叠加层会占用 gross(|h|×(1+1)), 报告叠加名义占比
res["overlay_gross_per_unit_book"]={f"h{hm}":round(hm*beta*2,3) for hm in (0.25,0.5,0.75,1.0)}
json.dump(res,open(f"{PD}/altspread_hedge_overlay.json","w"),indent=1,ensure_ascii=False); print("HEDGE_DONE")
