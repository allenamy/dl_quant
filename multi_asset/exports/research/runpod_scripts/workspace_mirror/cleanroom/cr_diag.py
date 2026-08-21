import numpy as np
m=np.load("/workspace/data/wide_fea_v1_meta.npz",allow_pickle=True)
E=m["E_ts"]; mem=m["members"]; y4=m["y4"]; qvk=m["qvk"]
p=np.load("/workspace/data/wide_panel_4h_v1.npz",allow_pickle=True)
ts=p["ts"]; Y4=p["Y4"]; rev=p["f_rev_24h"]; fe=p["f_fund_ema"]; fn=p["f_fund_now"]
pred=np.load("/workspace/exports_train/slow_lgbm_pred.npy")
print("meta names[:6]",m["names"][:6])
# axis alignment: compare meta y4 vs panel Y4 on shared ts
pos={t:i for i,t in enumerate(ts)}
rows=[(i,pos[t]) for i,t in enumerate(E) if t in pos]
ii=np.array([a for a,b in rows]); jj=np.array([b for a,b in rows])
A=y4[ii]; B=Y4[jj]
both=np.isfinite(A)&np.isfinite(B)
print("y4 vs Y4: n_both",both.sum(),"maxabsdiff",np.nanmax(np.abs(A[both]-B[both])),"corr",np.corrcoef(A[both],B[both])[0,1])
# per-column check to confirm no permutation
c=[]
for col in [0,100,400,828]:
    b=both[:,col]
    c.append(round(float(np.corrcoef(A[b,col],B[b,col])[0,1]),6) if b.sum()>10 else None)
print("per-col corr",c)
# NaN prevalence within members
import collections
cnt=collections.Counter(); tot=0
nan_pred=nan_rev=nan_fe=nan_y4=nan_fn=0; nmem=0
for k in range(0,len(E),7):
    t=E[k]
    if t not in pos: continue
    j=pos[t]; mm=np.asarray(mem[k])
    nmem+=len(mm); 
    nan_pred+=np.sum(~np.isfinite(pred[k,mm])); nan_rev+=np.sum(~np.isfinite(rev[j,mm]))
    nan_fe+=np.sum(~np.isfinite(fe[j,mm])); nan_y4+=np.sum(~np.isfinite(y4[k,mm])); nan_fn+=np.sum(~np.isfinite(fn[j,mm]))
print("sampled member-cells",nmem,"nan frac pred %.5f rev %.5f fundema %.5f y4 %.5f fundnow %.5f"%(nan_pred/nmem,nan_rev/nmem,nan_fe/nmem,nan_y4/nmem,nan_fn/nmem))
# how many anchors >=2024 lack panel row
import datetime as dt
yrs=np.array([dt.datetime.fromtimestamp(int(x),dt.UTC).year for x in E])
miss=[t for t in E[yrs>=2024] if t not in pos]
print("missing panel rows >=2024:",len(miss),[dt.datetime.fromtimestamp(int(t),dt.UTC).isoformat() for t in miss])
