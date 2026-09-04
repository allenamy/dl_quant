"""滚动季度 OOS king(LGBM 171)@jpline — RUNBOOK §8 / PREREG_allweather 后续。与 f8_higher_order_features.py 的 LGBM 折拟合逐字同配方
(X = concat(fea82, fea89) 171 列; Y = YRZ[pair]; LGB_PARAMS 同; EMBARGO=60), 唯一变化: 折 = 季度(训练集 = 该季度首锚之前全部锚 − EMBARGO), 从 2022Q1 到 2026Q3。
输出 f8_2026-08-22/preds/f4_lgbm_K171_rollq.npy(10086×829, 季度外样本)+ 逐季 IC 报告。"""
import numpy as np, json, time, os, sys
from scipy.stats import spearmanr
W="/mnt/storage/private/work_hsy"; DLW=f"{W}/dlw_2026-08-22"; OUT=f"{W}/f8_2026-08-22"; EMB=60
LGB_PARAMS=dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, random_state=0, n_jobs=int(os.environ.get("NJOBS","24")), verbose=-1)
TG=np.load(f"{DLW}/data/dlw_targets.npz",allow_pickle=True); E_ts=TG["E_ts"].astype(np.int64); YRZ=TG["YRZ"]; YR4s=TG["YR4s"]; y4s=TG["y4s"]; nA,NW=YRZ.shape
FE=np.load(f"{DLW}/data/dlw_fea82.npz",allow_pickle=True); X82=FE["X"]; pa=FE["pair_a"].astype(np.int64); ps=FE["pair_s"].astype(np.int64)
F9=np.load(f"{OUT}/data/f8_fea89.npz",allow_pickle=True); assert np.array_equal(F9["pair_a"].astype(np.int64),pa)
X=np.concatenate([X82.astype(np.float32),F9["X"].astype(np.float32)],1); del X82,FE,F9
Y=YRZ[pa,ps]; ok=np.isfinite(Y)
def yq(t): g=time.gmtime(int(t)); return g.tm_year*10+(g.tm_mon-1)//3+1
Q=np.array([yq(t) for t in E_ts]); quarters=[q for q in sorted(set(Q)) if q>=20221]
P=np.full((nA,NW),np.nan,np.float32); rep={}
import lightgbm as lgb
print(f"rows {len(Y)} X {X.shape} anchors {nA} quarters {quarters[0]}..{quarters[-1]} ({len(quarters)})", flush=True)
for q in quarters:
    te_anchor=np.where(Q==q)[0]; first_te=int(te_anchor[0])
    tr_ok=np.zeros(nA,bool); tr_ok[:max(first_te-EMB,0)]=True
    tr=tr_ok[pa]&ok; te=(Q[pa]==q)
    if tr.sum()<100000: print(f"skip {q}: train rows {tr.sum()}"); continue
    t1=time.time(); gbm=lgb.LGBMRegressor(**LGB_PARAMS).fit(X[tr],Y[tr]); pv=gbm.predict(X[te]).astype(np.float32); P[pa[te],ps[te]]=pv
    icr=[spearmanr(P[i][np.isfinite(P[i])&np.isfinite(YR4s[i])],YR4s[i][np.isfinite(P[i])&np.isfinite(YR4s[i])]).correlation for i in te_anchor if (np.isfinite(P[i])&np.isfinite(YR4s[i])).sum()>50]
    icy=[spearmanr(P[i][np.isfinite(P[i])&np.isfinite(y4s[i])],y4s[i][np.isfinite(P[i])&np.isfinite(y4s[i])]).correlation for i in te_anchor if (np.isfinite(P[i])&np.isfinite(y4s[i])).sum()>50]
    rep[str(q)]={"n_train_rows":int(tr.sum()),"n_test_anchors":int(len(te_anchor)),"ic_resid":round(float(np.nanmean(icr)),4),"ic_raw":round(float(np.nanmean(icy)),4),"sec":round(time.time()-t1,1)}
    print(f"[{q}] train {tr.sum()} rows | IC resid {rep[str(q)]['ic_resid']:+.4f} raw {rep[str(q)]['ic_raw']:+.4f} ({time.time()-t1:.0f}s)", flush=True)
    np.save(f"{OUT}/preds/f4_lgbm_K171_rollq.npy",P); json.dump(rep,open(f"{OUT}/results/f4_lgbm_K171_rollq.json","w"),indent=1)
print("KING_ROLLQ_DONE", flush=True)
