import numpy as np, json
U="/workspace/uplift_2026-09-11"
MT=np.load(f"{U}/r6/out/meta_newprod_v4_x0910.npz",allow_pickle=True)
print("meta keys",list(MT.keys()))
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=MT["y4"]
Z5=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz",allow_pickle=True)
t5=Z5["ts"].astype(np.int64); D5=Z5["data"]; r5={int(t):k for k,t in enumerate(t5)}
rng=np.random.default_rng(1); pick=rng.choice(np.arange(3000,len(E_ts)-5),25,replace=False)
forms={}
for off in (0,1):
  for nm in ("sum","cmp"):
    errs=[];rel=[]
    for i in pick:
        k0=r5[int(E_ts[i])]+off; m=members[i]
        blk=np.asarray(D5[k0:k0+48,m,0],np.float64)
        a=np.nansum(blk,0) if nm=="sum" else np.prod(1.0+np.nan_to_num(blk),0)-1.0
        yy=np.asarray(y4[i,m],np.float64); ok=np.isfinite(yy)
        e=np.abs(a[ok]-yy[ok]); errs.append(float(np.max(e))); rel.append(float(np.median(e)))
    forms["off%d_%s"%(off,nm)]={"max_of_max":max(errs),"median_of_max":float(np.median(errs)),
                                "median_of_median":float(np.median(rel))}
print(json.dumps(forms,indent=1))
# what does the device's CAL branch do?
i=pick[0]; k0=r5[int(E_ts[i])]+1; m=members[i][:6]
blk=np.asarray(D5[k0:k0+48,m,0],np.float64)
print("sample sum ",np.nansum(blk,0))
print("sample cmp ",np.prod(1.0+np.nan_to_num(blk),0)-1.0)
print("sample y4  ",np.asarray(y4[i,m],np.float64))
