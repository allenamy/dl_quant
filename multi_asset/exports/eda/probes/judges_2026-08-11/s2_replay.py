"""#52 阶段二判决 · 第二段: 各臂最优收割速度下的净夏普。
装置口径(如实声明): dl_only 简装置 — zr(ens) → demean → L1 → EMA(a) → demean → L1;
毛 = w·Y4(raw); 净 = 毛 − 换手×cost。两臂逐位同装置 ⇒ Δ 合法; 绝对水平不与 engine 正典并列
(无 cap/无四腿)。若 Δ 落在判据线 ±0.05 内 ⇒ 升级 engine 全装置再判。年化 = mean/std·sqrt(2190)。"""
import numpy as np, glob, json
BASE="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
P=np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz",allow_pickle=True)
Y4=P["Y4"]; MEM=P["MEMBER110"]; CL4=P["CL4"]; TS=P["ts"]
def zr(x):
    m=np.isfinite(x); out=np.full(len(x),np.nan)
    if m.sum()<3: return out
    r=np.argsort(np.argsort(x[m])).astype(float); out[m]=(r-r.mean())/(r.std()+1e-12); return out
def arm_scores(tag):
    rows_all=[]; ens_all=[]
    for f in sorted(glob.glob(f"{BASE}/train/{tag}/fold_*_head_scores.npz")):
        z=np.load(f,allow_pickle=True); S=z["scores"]; rows=z["te_rows"]
        for r in rows:
            mem=MEM[r]; hz=[]
            for h in range(S.shape[2]):
                v=np.where(mem,S[r,:,h],np.nan); s=np.nanstd(v)
                hz.append((v-np.nanmean(v))/s if s>0 else v*np.nan)
            rows_all.append(int(r)); ens_all.append(np.nanmean(hz,axis=0))
    order=np.argsort(rows_all)
    return np.array(rows_all)[order], np.array(ens_all)[order]
def book(w_raw):
    w=np.where(np.isfinite(w_raw),w_raw,0.0)
    w=w-w.mean(); s=np.abs(w).sum()
    return w/s if s>1e-12 else w
def run(tag):
    rows,ens=arm_scores(tag); out={}
    for a in (1.0,0.3,0.1,0.03,0.01):
        prev=None; pnl=[]; turn=[]; yrs=[]; state=None
        for k,r in enumerate(rows):
            tgt=book(zr(ens[k]))
            if a<1.0:
                state=tgt if state is None else (1-a)*state+a*tgt
                w=book(state)
            else: w=tgt
            y=np.where(MEM[r]&CL4[r]&np.isfinite(Y4[r]),Y4[r],0.0)
            pnl.append(float(np.dot(w,y)))
            turn.append(0.0 if prev is None else float(np.abs(w-prev).sum()))
            prev=w
            yrs.append(int(str(np.datetime64(int(TS[r]),"ms"))[:4]))
        pnl=np.array(pnl); turn=np.array(turn); res={}
        for c in (3.63,5.8):
            net=pnl-turn*c/1e4
            per_year={}
            for yy in sorted(set(yrs)):
                m=np.array(yrs)==yy
                if m.sum()>100:
                    per_year[yy]=round(float(net[m].mean()/(net[m].std()+1e-12)*np.sqrt(2190)),2)
            res[str(c)]={"net_ann":round(float(net.mean()/(net.std()+1e-12)*np.sqrt(2190)),3),
                         "per_year":per_year}
        res["turnover_ann"]=round(float(turn.mean()*2190),0)
        out[str(a)]=res
    return out
res={}
for tag in ("wideA_psmooth_L01","wideA_psmooth_ctrl"):
    res[tag]=run(tag)
print(json.dumps(res,indent=1))
