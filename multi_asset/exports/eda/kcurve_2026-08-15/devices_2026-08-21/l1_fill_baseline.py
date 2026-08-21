"""L1 基线判官: p(fill) 逻辑回归 + LGBM, 按日滚动 CV(判据 DESIGN_L1 §3 冻结). 输入: 合并后的 orders.jsonl(本机 pilot_log)."""
import json, glob, sys, math, time
import numpy as np
SRC = sys.argv[1] if len(sys.argv) > 1 else "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
O = []
for f in sorted(glob.glob(f"{SRC}/2026*/orders.jsonl")):
    for l in open(f):
        r = json.loads(l); r["_day"] = f.split("/")[-2]; O.append(r)
O = [o for o in O if o.get("order_type") == "maker" and o.get("intended_notional") and abs(float(o["intended_notional"])) > 1]
print("maker 订单", len(O), flush=True)
def f(o, k, d=0.0):
    v = o.get(k); 
    try: return float(v) if v is not None else d
    except: return d
X=[]; Y=[]; DAY=[]; SYM=[]; TIER=[]
for o in O:
    inten = abs(f(o,"intended_notional")); filled = abs(f(o,"filled_notional"))
    y = 1.0 if filled/inten >= 0.99 else 0.0
    ms = f(o,"mid_at_submit"); ma = f(o,"mid_at_anchor")
    drift = (ms/ma - 1.0) if (ms > 0 and ma > 0) else 0.0
    side = 1.0 if str(o.get("side","")).lower() == "buy" else -1.0
    ts = f(o,"submit_ts"); ts = ts/1000 if ts > 2e10 else ts
    hr = time.gmtime(int(ts)).tm_hour if ts > 0 else 0
    X.append([f(o,"spread_at_submit_bps"), f(o,"placement_eps"), math.log1p(inten), side*drift*1e4, abs(drift)*1e4,
              math.sin(hr/24*2*math.pi), math.cos(hr/24*2*math.pi), f(o,"attempt_idx"), 1.0 if o.get("placement_arm") else 0.0])
    Y.append(y); DAY.append(o["_day"]); SYM.append(o["symbol"])
X=np.array(X); Y=np.array(Y); DAY=np.array(DAY); days=sorted(set(DAY))
print("全成交率", round(Y.mean(),3), "| 天数", len(days), "| 特征", X.shape[1], flush=True)
# 按日滚动 CV
def logit_fit(Xtr, ytr, l2=1.0, it=300, lr=0.1):
    mu=Xtr.mean(0); sd=Xtr.std(0)+1e-9; Z=(Xtr-mu)/sd; w=np.zeros(Z.shape[1]); b=0.0
    for _ in range(it):
        p=1/(1+np.exp(-(Z@w+b))); g=Z.T@(p-ytr)/len(ytr)+l2*w/len(ytr); gb=(p-ytr).mean(); w-=lr*g; b-=lr*gb
    return mu,sd,w,b
def auc(y,s):
    o=np.argsort(s); r=np.empty(len(s)); r[o]=np.arange(1,len(s)+1); n1=y.sum(); n0=len(y)-n1
    return (r[y==1].sum()-n1*(n1+1)/2)/(n1*n0) if n1>0 and n0>0 else float('nan')
try:
    import lightgbm as lgb; HAVE=True
except Exception: HAVE=False
res={"by_day":[], "lgb": HAVE}
allp=[]; ally=[]
for i,d in enumerate(days):
    if i < 7: continue
    tr=DAY<d; te=DAY==d
    if te.sum()<100: continue
    mu,sd,w,b=logit_fit(X[tr],Y[tr]); p=1/(1+np.exp(-(((X[te]-mu)/sd)@w+b)))
    row={"day":d,"n":int(te.sum()),"auc_logit":round(float(auc(Y[te],p)),3),"fill_rate":round(float(Y[te].mean()),3)}
    if HAVE:
        m=lgb.LGBMClassifier(n_estimators=200,learning_rate=0.05,num_leaves=15,min_child_samples=50,verbose=-1).fit(X[tr],Y[tr]); pl=m.predict_proba(X[te])[:,1]
        row["auc_lgb"]=round(float(auc(Y[te],pl)),3); allp+=list(pl)
    else: allp+=list(p)
    ally+=list(Y[te]); res["by_day"].append(row); print(row, flush=True)
allp=np.array(allp); ally=np.array(ally)
res["pooled_auc"]=round(float(auc(ally,allp)),3)
# 校准十分位
qs=np.quantile(allp,np.linspace(0,1,11)); cal=[]
for k in range(10):
    m=(allp>=qs[k])&(allp<=qs[k+1]); 
    if m.sum()>30: cal.append([round(float(allp[m].mean()),3), round(float(ally[m].mean()),3), int(m.sum())])
res["calibration_pred_vs_real"]=cal
res["G1"]={"pooled_auc_ge_0.60": bool(res["pooled_auc"]>=0.60), "days_auc_gt_0.55": int(sum(1 for r in res["by_day"] if (r.get("auc_lgb") or r["auc_logit"])>0.55)), "n_days": len(res["by_day"])}
# 成交率 vs eps × 价差档(经验表, 供 G2 换算)
eps=X[:,1]; spr=X[:,0]; tbl={}
for e in sorted(set(np.round(eps,4)))[:8]:
    m=np.abs(eps-e)<1e-6
    if m.sum()>200: tbl[str(e)]={"n":int(m.sum()),"fill":round(float(Y[m].mean()),3),"spread_med":round(float(np.median(spr[m])),1)}
res["fill_by_eps"]=tbl
print(json.dumps({k:v for k,v in res.items() if k!="by_day"}, ensure_ascii=False), flush=True)
json.dump(res, open("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/l1_fill_baseline.json","w"), indent=1)
