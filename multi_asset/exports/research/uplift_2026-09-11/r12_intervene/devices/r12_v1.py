"""V1b: nail the 5m<->y4 row convention (E-0825-H)."""
import numpy as np, json
U="/workspace/uplift_2026-09-11"
MT=np.load(f"{U}/r6/out/meta_newprod_v4_x0910.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=MT["y4"]
Z5=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz",allow_pickle=True)
t5=Z5["ts"].astype(np.int64); D5=Z5["data"]
r5={int(t):k for k,t in enumerate(t5)}
print("5m step",t5[1]-t5[0],"first",t5[0],"anchor0",E_ts[0],"row",r5.get(int(E_ts[0])))
rng=np.random.default_rng(1); pick=rng.choice(np.arange(3000,len(E_ts)-5),40,replace=False)
res={}
for off in (-1,0,1):
    errs=[]
    for i in pick:
        k0=r5[int(E_ts[i])]+off; m=members[i]
        a=np.nansum(np.asarray(D5[k0:k0+48,m,0],np.float64),0)
        yy=np.asarray(y4[i,m],np.float64); ok=np.isfinite(yy)
        errs.append(float(np.max(np.abs(a[ok]-yy[ok]))))
    res["start_off_%+d"%off]={"max":max(errs),"median":float(np.median(errs))}
print(json.dumps(res,indent=1))
