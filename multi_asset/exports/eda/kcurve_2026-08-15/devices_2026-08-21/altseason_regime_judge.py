"""T1 山寨季 regime 判官(在役书 9821 锚回放, 判据冻结):
AS_t = 等权山寨(排除 BTC/ETH) 7日(42锚)收益 − BTC 7日收益; BR_t = 7日内跑赢 BTC 的山寨占比。
① 持久性: AS 的 1锚/6锚/42锚 自相关; ② 亏损锚(净<−50)的 AS 分位分布; ③ 可预测性: AS_{t−1} 五分位 × 下一锚书净额, 逐年同向 ≥4/5 (top−bottom ≥ 1 bps) 才算过。
附: 书净额对 AS 同期变化的回归β(结构性暴露量)。"""
import sys, json, time, numpy as np
PD="/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0,PD)
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0,MA); sys.path.insert(0,MA+"/engine/live"); sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
import engine.replay_fullhist as RF
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz"); a,yr=RF._all_anchors(src); N=src.N; n=len(a)
SY=[str(s) for s in src.symbols]; ib=SY.index("BTCUSDT") if "BTCUSDT" in SY else None; ie=SY.index("ETHUSDT") if "ETHUSDT" in SY else None
Y=np.full((n,N),np.nan)
for i,t in enumerate(a):
    ti=int(t); m=np.asarray(src.tradeable(ti)); m=np.where(m)[0] if m.dtype==bool else m
    Y[i,m]=src.Y4[ti,m].astype(float)
alt=np.array([j for j in range(N) if j not in (ib,ie)])
r_alt=np.nanmean(Y[:,alt],1); r_btc=Y[:,ib] if ib is not None else np.nanmean(Y,1)
beat=np.nanmean((Y[:,alt]>r_btc[:,None]),1)
def roll(x,k):
    o=np.full_like(x,np.nan); c=np.nancumsum(np.nan_to_num(x)); o[k:]=c[k:]-c[:-k]; return o
AS=roll(r_alt,42)-roll(r_btc,42); BR=np.array([np.nanmean(beat[max(0,i-41):i+1]) for i in range(n)])
net=np.load(f"{PD}/net_S1.npy"); assert len(net)==n
ok=np.isfinite(AS)&np.isfinite(net)
def ac(x,k):
    v=x[ok]; return float(np.corrcoef(v[:-k],v[k:])[0,1])
res={"AS_autocorr":{"lag1":round(ac(AS,1),3),"lag6":round(ac(AS,6),3),"lag42":round(ac(AS,42),3),"lag126":round(ac(AS,126),3)}}
# ② 亏损锚的 AS 分位
q=np.nanpercentile(AS[ok],[20,40,60,80])
def quint(v): return int(np.searchsorted(q,v))
bad=ok&(net<-50); res["bad_anchor_AS_quintile_dist"]=[int(((np.array([quint(v) for v in AS[bad]]))==k).sum()) for k in range(5)]
res["AS_quintile_of_bad_anchors_note"]="Q0=山寨最弱…Q4=山寨最强(山寨季)"
# ③ 可预测性: AS_{t-1} 分位 × 下一锚净额, 逐年
ASl=np.roll(AS,1); ASl[0]=np.nan
byy={}
for y in sorted(set(yr.tolist())):
    m=ok&np.isfinite(ASl)&(yr==y)
    qs=np.array([quint(v) for v in ASl[m]]); v=net[m]
    row={k:round(float(v[qs==k].mean()),2) for k in range(5) if (qs==k).sum()>50}
    row["top-bottom"]=round(row.get(4,np.nan)-row.get(0,np.nan),2) if 0 in row and 4 in row else None
    byy[int(y)]=row
res["predict_by_year"]=byy
# 同期暴露: net ~ ΔAS(同锚山寨-BTC 4h 差)
dAS=r_alt-r_btc; m2=ok&np.isfinite(dAS)
b=np.polyfit(dAS[m2]*1e4, net[m2], 1)[0]; res["same_anchor_beta_to_altminusbtc_bps_per_bps"]=round(float(b),3)
cor=np.corrcoef(dAS[m2],net[m2])[0,1]; res["same_anchor_corr"]=round(float(cor),3)
for y in sorted(set(yr.tolist())):
    m3=m2&(yr==y); res.setdefault("same_anchor_beta_by_year",{})[int(y)]=round(float(np.polyfit(dAS[m3]*1e4,net[m3],1)[0]),3)
print(json.dumps(res,ensure_ascii=False,indent=1)); json.dump(res,open(f"{PD}/altseason_regime.json","w"),indent=1,ensure_ascii=False)
