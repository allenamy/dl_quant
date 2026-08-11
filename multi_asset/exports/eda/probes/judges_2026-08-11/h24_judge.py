"""#59 视界判决(降级 2×1: #52 杀掉平滑 ⇒ 只比 C(y24) vs ctrl(y4)), 同 s2_replay 装置。"""
import numpy as np, glob, json
BASE="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
P=np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz",allow_pickle=True)
Y4=P["Y4"]; MEM=P["MEMBER110"]; CL4=P["CL4"]; TS=P["ts"]
def zr(x):
    m=np.isfinite(x); out=np.full(len(x),np.nan)
    if m.sum()<3: return out
    r=np.argsort(np.argsort(x[m])).astype(float); out[m]=(r-r.mean())/(r.std()+1e-12); return out
def book(w):
    w=np.where(np.isfinite(w),w,0.0); w=w-w.mean(); s=np.abs(w).sum()
    return w/s if s>1e-12 else w
def run(tag):
    rows_all=[]; ens_all=[]
    for f in sorted(glob.glob(f"{BASE}/train/{tag}/fold_*_head_scores.npz")):
        z=np.load(f,allow_pickle=True); S=z["scores"]; rows=z["te_rows"]
        for r in rows:
            mem=MEM[r]; hz=[]
            for h in range(S.shape[2]):
                v=np.where(mem,S[r,:,h],np.nan); s=np.nanstd(v)
                hz.append((v-np.nanmean(v))/s if s>0 else v*np.nan)
            rows_all.append(int(r)); ens_all.append(np.nanmean(hz,axis=0))
    o=np.argsort(rows_all); rows=np.array(rows_all)[o]; ens=np.array(ens_all)[o]
    out={}
    for a in (1.0,0.3,0.1,0.03,0.01):
        prev=None; state=None; pnl=[]; turn=[]; yrs=[]
        for k,r in enumerate(rows):
            tgt=book(zr(ens[k]))
            if a<1.0:
                state=tgt if state is None else (1-a)*state+a*tgt; w=book(state)
            else: w=tgt
            y=np.where(MEM[r]&CL4[r]&np.isfinite(Y4[r]),Y4[r],0.0)
            pnl.append(float(np.dot(w,y))); turn.append(0.0 if prev is None else float(np.abs(w-prev).sum())); prev=w
            yrs.append(int(str(np.datetime64(int(TS[r]),"ms"))[:4]))
        pnl=np.array(pnl); turn=np.array(turn); res={}
        for c in (3.63,5.8):
            net=pnl-turn*c/1e4
            per={yy:round(float(net[np.array(yrs)==yy].mean()/(net[np.array(yrs)==yy].std()+1e-12)*np.sqrt(2190)),2) for yy in sorted(set(yrs)) if (np.array(yrs)==yy).sum()>100}
            res[str(c)]={"net_ann":round(float(net.mean()/(net.std()+1e-12)*np.sqrt(2190)),3),"per_year":per}
        res["turnover_ann"]=round(float(turn.mean()*2190),0); out[str(a)]=res
    return out
print(json.dumps({t:run(t) for t in ("wideA_h24_C","wideA_psmooth_ctrl")},indent=1))
