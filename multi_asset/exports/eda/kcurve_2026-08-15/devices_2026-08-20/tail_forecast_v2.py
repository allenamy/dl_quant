"""风险预测重做(推翻 AUC 0.51 草率结论的尝试)。
诊断: 旧测直接预测"挤压事件"= 罕见二元 + 弱特征 ⇒ AUC≈0.5 是题目设错, 不是"风险不可知"。
正统分解: ① 条件方差 σ̂(可预测: 波动聚集) ② 尾部是否有超出 σ̂ 的信息 ③ 判据=效用(vol-targeting 后书的净额/夏普/尾部), 不是 AUC。
全部特征因果(≤i), purged CV(embargo 12锚), 基线=在役 RB 用的已实现波动。
"""
import sys, json
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA+"/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
TGT, MSK, RET, RV, FD = [], [], [], [], []
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
    w=np.full(N,0.0); w[m]=np.asarray(r["target_w"],float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti,m].astype(float))
    RV.append(np.nanmean(src.CH[ti,m,RVI].astype(float))); FD.append(src.CH[ti,m,FI].astype(float))
# 基线路径(S0)+ 状态特征
state=None; prev=np.zeros(N); Pi=np.ones(N); sh=np.zeros(N); cb=np.zeros(N)
net=np.zeros(n); FEAT=[]
for i in range(n):
    m=MSK[i]; syms=[SYMS[j] for j in m]
    out=LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05); state=out["state"]
    tgt=np.asarray(out["target_w"],float)
    w=prev.copy(); w[[j for j in range(N) if j not in set(m)]]=0.0
    d=tgt-w[m]; T=np.abs(d)>BW
    wm=w[m].copy(); wm[T]=tgt[T]
    if T.any(): wm[T]-=wm.sum()/T.sum()
    w[m]=wm
    y=RET[i]; ok=np.isfinite(y); idx=m[ok]
    c=np.zeros(N); c[idx]=w[m][ok]*y[ok]*1e4
    g=c.sum(); tn=float(np.abs(w-prev).sum()); net[i]=g-tn*C1
    nsh=np.where(Pi>1e-12, w/Pi, 0.0)
    same=np.sign(nsh)==np.sign(sh); add=same&(np.abs(nsh)>np.abs(sh))
    red=same&(~add)&(np.abs(nsh)>1e-12); new=(~same)|(np.abs(sh)<1e-12)
    cb=np.where(add, cb+(nsh-sh)*Pi, cb)
    with np.errstate(all='ignore'):
        ratio=np.where(np.abs(sh)>1e-12, nsh/np.where(np.abs(sh)>1e-12, sh, 1.0), 0.0)
    cb=np.where(red, cb*ratio, cb); cb=np.where(new, nsh*Pi, cb); cb=np.where(np.abs(nsh)<1e-12,0.0,cb)
    sh=nsh
    with np.errstate(all='ignore'):
        avg=np.where(np.abs(sh)>1e-12, cb/sh, np.nan)
        dep=np.where(np.isfinite(avg)&(Pi>0), np.sign(sh)*(1.0-avg/Pi), 0.0)
    aw=np.abs(w); gr=aw.sum(); hhi=(aw**2).sum()/max(gr**2,1e-12)
    shortm=w<0; yv=np.nan_to_num(y)
    f={'gross':gr,'neff':1.0/max(hhi,1e-12),'short_share':float(aw[shortm].sum()/max(gr,1e-12)),
       'dep_min':float(dep.min()),'dep_p10':float(np.percentile(dep[np.abs(w)>1e-9],10)) if (np.abs(w)>1e-9).any() else 0.,
       'n_deep15':float((dep<=-0.15).sum()),'n_deep25':float((dep<=-0.25).sum()),
       'unreal':float((dep*aw).sum()),'rvol':float(RV[i]) if np.isfinite(RV[i]) else 0.,
       'xsec_disp':float(np.nanstd(yv)) if len(yv) else 0.,'mkt_move':float(np.nanmean(yv)) if len(yv) else 0.,
       'fund_mean':float(np.nanmean(FD[i])),'fund_disp':float(np.nanstd(FD[i])),
       'pump_breadth':float(np.nanmean(yv>0.03)) if len(yv) else 0.}
    for L in (6,18,42,126):
        s=net[max(0,i-L+1):i+1]
        f[f'netvol{L}']=float(s.std()) if len(s)>2 else 0.
        f[f'netmean{L}']=float(s.mean()) if len(s)>0 else 0.
        f[f'absmean{L}']=float(np.abs(s).mean()) if len(s)>0 else 0.
    FEAT.append(f); prev=w; upd=np.zeros(N); upd[idx]=y[ok]; Pi=Pi*(1.0+upd)
F=pd.DataFrame(FEAT); F['yr']=yr
H=6
fwd=np.array([net[i+1:i+1+H].sum() if i+1+H<=n else np.nan for i in range(n)])
fvol=np.array([net[i+1:i+1+H].std() if i+1+H<=n else np.nan for i in range(n)])
ok=np.isfinite(fwd)&(F.index>=126)
X=F.drop(columns=['yr']).values[ok]; yv_=fwd[ok]; yvol=fvol[ok]; YRo=yr[ok]
cols=list(F.drop(columns=['yr']).columns)
print('样本', X.shape, '特征', len(cols))
try:
    import lightgbm as lgb; HAVE=True
except Exception: HAVE=False
print('lightgbm:', HAVE)
from scipy.stats import spearmanr
folds=[]; idx=np.arange(len(X)); step=len(X)//6
for k in range(2,6):
    te=idx[k*step:(k+1)*step]; tr=idx[:max(0,k*step-12)]
    if len(tr)>500: folds.append((tr,te))
def cv(target, clf=False):
    oof=np.full(len(X), np.nan)
    for tr,te in folds:
        if HAVE:
            mdl=(lgb.LGBMClassifier if clf else lgb.LGBMRegressor)(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=60, subsample=.8, colsample_bytree=.7, verbose=-1)
            mdl.fit(X[tr], target[tr])
            oof[te]=mdl.predict_proba(X[te])[:,1] if clf else mdl.predict(X[te])
        else:
            from sklearn.linear_model import Ridge, LogisticRegression
            from sklearn.preprocessing import StandardScaler
            sc=StandardScaler().fit(X[tr]); mdl=(LogisticRegression(max_iter=500) if clf else Ridge(1.0)).fit(sc.transform(X[tr]), target[tr])
            oof[te]=mdl.predict_proba(sc.transform(X[te]))[:,1] if clf else mdl.predict(sc.transform(X[te]))
    return oof
res={}
# ① 条件方差
ov=cv(yvol)
mk=np.isfinite(ov)
base=X[:, cols.index('netvol42')]
res['vol_forecast']={'spearman_model':round(float(spearmanr(ov[mk], yvol[mk]).statistic),3),
                     'spearman_baseline_netvol42':round(float(spearmanr(base[mk], yvol[mk]).statistic),3),
                     'r2_model':round(float(1-np.mean((ov[mk]-yvol[mk])**2)/np.var(yvol[mk])),3)}
# ② 尾部(超出 σ̂ 之外?)
thr=np.percentile(yv_, 10); tail=(yv_<=thr).astype(int)
ot=cv(tail, clf=True)
from sklearn.metrics import roc_auc_score
mk2=np.isfinite(ot)
auc_full=roc_auc_score(tail[mk2], ot[mk2])
auc_vol=roc_auc_score(tail[mk2], -( -ov[mk2]))  # 仅用 σ̂ 排序(σ大→更可能尾)
res['tail']={'auc_model':round(float(auc_full),3),'auc_sigma_only':round(float(auc_vol),3),
             'base_rate':round(float(tail[mk2].mean()),3),
             'precision_top_decile':round(float(tail[mk2][ot[mk2]>=np.percentile(ot[mk2],90)].mean()),3)}
# ③ 效用: vol-targeting
sig=np.full(n, np.nan); sig[np.where(ok)[0][mk]]=ov[mk]
k=np.clip(np.nanmedian(sig)/np.where(np.isfinite(sig)&(sig>1e-9), sig, np.nan), 0.5, 1.5)
kk=np.where(np.isfinite(k), k, 1.0)
scaled=net*kk
m3=np.isfinite(scaled)&(np.arange(n)>=126)
res['utility_voltarget']={'base_net':round(float(net[m3].mean()),3),'base_sharpe':round(float(net[m3].mean()/net[m3].std(ddof=1)*ANN),2),
  'scaled_net':round(float(scaled[m3].mean()),3),'scaled_sharpe':round(float(scaled[m3].mean()/scaled[m3].std(ddof=1)*ANN),2),
  'base_p5':round(float(np.percentile(net[m3],5)),1),'scaled_p5':round(float(np.percentile(scaled[m3],5)),1),
  'note':'近似: 按预测σ缩放已实现净额(未重跑换手, 缩放会略增换手 ⇒ 乐观上界)'}
if HAVE:
    mdl=lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=60, verbose=-1).fit(X, yvol)
    imp=sorted(zip(cols, mdl.feature_importances_), key=lambda x:-x[1])[:8]
    res['top_features_vol']=[(c,int(v)) for c,v in imp]
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open(f'{PD}/tail_forecast_v2.json','w'))
