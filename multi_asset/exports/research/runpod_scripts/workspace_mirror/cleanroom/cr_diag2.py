import numpy as np, datetime as dt
m=np.load("/workspace/data/wide_fea_v1_meta.npz",allow_pickle=True)
E=m["E_ts"]; mem=m["members"]; y4=m["y4"]; qvk=m["qvk"]
p=np.load("/workspace/data/wide_panel_4h_v1.npz",allow_pickle=True)
ts=p["ts"]; rev=p["f_rev_24h"]; fe=p["f_fund_ema"]; fn=p["f_fund_now"]
pred=np.load("/workspace/exports_train/slow_lgbm_pred.npy")
pos={t:i for i,t in enumerate(ts)}
yrs=np.array([dt.datetime.fromtimestamp(int(x),dt.UTC).year for x in E])
for Y in [2022,2023,2024,2025,2026]:
    idx=np.where(yrs==Y)[0][::5]
    a=b=c=n=0; nf=0; both=0
    for k in idx:
        t=E[k]
        if t not in pos: continue
        j=pos[t]; mm=np.asarray(mem[k]); n+=len(mm)
        fp=np.isfinite(pred[k,mm]); ff=np.isfinite(fe[j,mm])
        a+=(~fp).sum(); b+=(~ff).sum(); both+=(fp&ff).sum()
        # after liquidity+y4 filter
        keep=np.isfinite(y4[k,mm])&(np.expm1(qvk[k,mm])*48>=250000)
        nf+=keep.sum(); c+=(keep&~fp).sum()
    print(Y,"members",n,"nan_pred %.4f nan_fundema %.4f bothfinite %.4f | filtered_members %d nan_pred_in_filtered %.4f"%(a/n,b/n,both/n,nf,c/max(nf,1)))
# is pred NaN whole-row or scattered?
k=8000; mm=np.asarray(mem[k]); print("anchor",dt.datetime.fromtimestamp(int(E[k]),dt.UTC).isoformat(),"nmem",len(mm),"nan pred",(~np.isfinite(pred[k,mm])).sum())
rowna=np.array([(~np.isfinite(pred[k,np.asarray(mem[k])])).mean() for k in range(0,len(E),50)])
print("per-anchor pred-nan frac: min %.3f med %.3f max %.3f ; frac of anchors with 0 nan %.3f"%(rowna.min(),np.median(rowna),rowna.max(),(rowna==0).mean()))
