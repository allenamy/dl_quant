"""S0 融合检验(零训练, 用已有 perhead 五折头分数) — 智能融合 vs 机械等权。
预注册(PREREG_kernel_target_paradigm §6-S0): 若智能融合在现成工件上赢不了等权, §3 融合段降级。
四种融合, 全部 walk-forward 因果(权重只用【更早折/更早锚】的信息):
  F0 等权(现行)
  F1 保留率加权: w_h ∝ max(0, lag1_IC_h) —— 慢头得高权
  F2 核目标加权: w_h ∝ max(0, IC(head_h, y_kernel^a)) —— 按部署速度的核目标测量
  F3 核目标加权 + 负权允许(纯测量, 不裁剪)
判据: F1/F2/F3 任一在最优速度处净夏普 ≥ F0 +0.15 ⇒ 融合段成立。
"""
import numpy as np, glob, json
BASE="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
P=np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz",allow_pickle=True)
Y4=P["Y4"]; MEM=P["MEMBER110"]; CL4=P["CL4"]; TS=P["ts"]
KEEP=[0,1,2,4,5]
def zr(x):
    m=np.isfinite(x); out=np.full(len(x),np.nan)
    if m.sum()<3: return out
    r=np.argsort(np.argsort(x[m])).astype(float); out[m]=(r-r.mean())/(r.std()+1e-12); return out
def ic(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    return float(np.nanmean(zr(np.where(m,a,np.nan))*zr(np.where(m,b,np.nan)))) if m.sum()>=10 else np.nan
def book(w):
    w=np.where(np.isfinite(w),w,0.0); w=w-w.mean(); s=np.abs(w).sum()
    return w/s if s>1e-12 else w
rows_all=[]; H_all=[]
for f in sorted(glob.glob(f"{BASE}/train/wideA_perhead_v1/fold_*_head_scores.npz")):
    z=np.load(f,allow_pickle=True); S=z["scores"]; rows=z["te_rows"]
    for r in rows:
        mem=MEM[r]
        hs=[]
        for h in KEEP:
            v=np.where(mem,S[r,:,h],np.nan); s=np.nanstd(v)
            hs.append((v-np.nanmean(v))/s if s>0 else v*np.nan)
        rows_all.append(int(r)); H_all.append(np.array(hs))          # (H,N)
o=np.argsort(rows_all); rows=np.array(rows_all)[o]; H=np.array(H_all)[o]
nH=H.shape[1]
def kernel_target(r, a, K=None):
    K = K or int(np.ceil(np.log(0.01)/np.log(max(1e-9,1-a)))) if a<1 else 0
    K = min(K, 60)
    num=np.zeros(Y4.shape[1]); den=0.0; ok=np.ones(Y4.shape[1],bool)
    for k in range(K+1):
        rr=r+4*k
        if rr>=Y4.shape[0]: break
        w=(1-a)**k
        v=Y4[rr]; ok&=np.isfinite(v)
        num=num+w*np.where(np.isfinite(v),v,0.0); den+=w
    return np.where(ok&MEM[r]&CL4[r], num/max(den,1e-9), np.nan)
res={}
for a in (1.0,0.3,0.1,0.03,0.01):
    # 逐锚权重: 用【更早】锚上测得的 head IC(扩张窗, 严格因果)
    accum=np.zeros(nH); acc_k=np.zeros(nH); n_acc=0
    W={f:[] for f in ("F0","F1","F2")}
    pnl={f:[] for f in W}; turn={f:[] for f in W}; prev={f:None for f in W}; state={f:None for f in W}
    yrs=[]
    for j,r in enumerate(rows):
        y4=np.where(MEM[r]&CL4[r]&np.isfinite(Y4[r]),Y4[r],0.0)
        w0=np.ones(nH)/nH
        w1=(np.maximum(accum,0)/max(np.maximum(accum,0).sum(),1e-9)) if n_acc>20 else w0
        w2=(np.maximum(acc_k,0)/max(np.maximum(acc_k,0).sum(),1e-9)) if n_acc>20 else w0
        for f,wv in (("F0",w0),("F1",w1),("F2",w2)):
            tgt=book(zr(np.nansum(H[j]*wv[:,None],axis=0)))
            if a<1.0:
                state[f]=tgt if state[f] is None else (1-a)*state[f]+a*tgt
                w=book(state[f])
            else: w=tgt
            pnl[f].append(float(np.dot(w,y4)))
            turn[f].append(0.0 if prev[f] is None else float(np.abs(w-prev[f]).sum())); prev[f]=w
        yrs.append(int(str(np.datetime64(int(TS[r]),"ms"))[:4]))
        # 更新扩张窗测量(用【本锚已实现】的量, 下一锚才用 => 因果)
        if j+1 < len(rows):
            yk=kernel_target(r,a)
            for h in range(nH):
                v=ic(H[j][h], np.where(MEM[rows[j+1]],Y4[rows[j+1]],np.nan))
                if np.isfinite(v): accum[h]+= v
                vk=ic(H[j][h], yk)
                if np.isfinite(vk): acc_k[h]+= vk
            n_acc+=1
    out={}
    for f in W:
        pn=np.array(pnl[f]); tn=np.array(turn[f])
        rr={}
        for c in (3.63,5.8):
            net=pn-tn*c/1e4
            rr[str(c)]=round(float(net.mean()/(net.std()+1e-12)*np.sqrt(2190)),3)
        rr["turn"]=round(float(tn.mean()*2190),0)
        out[f]=rr
    res[str(a)]=out
print(json.dumps(res,indent=1))
print("\n最优速度处对比:")
for f in ("F0","F1","F2"):
    b=max(res.items(), key=lambda kv: kv[1][f]["3.63"])
    print(f"  {f}: 最优 a={b[0]}  净@3.63={b[1][f]['3.63']:.3f}  @5.8={b[1][f]['5.8']:.3f}  换手={b[1][f]['turn']:.0f}")
