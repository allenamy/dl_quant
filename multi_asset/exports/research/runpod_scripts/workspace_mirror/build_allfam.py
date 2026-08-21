import numpy as np
base=np.load("/workspace/data/wide_dl_pm32_hz.npz",allow_pickle=True)
out={k:base[k] for k in base.files}
CH=[base["CH"]]; nm=[str(x) for x in base["ch_names"]]
for path,pref,ncol in (("/workspace/data/metrics_hourly.npz","met",21),
                       ("/workspace/data/book1p_hourly.npz","bk",13),
                       ("/workspace/data/basis_hourly.npz","bas",7)):
    try:
        z=np.load(path,allow_pickle=True); X=z["X"]
        n=min(ncol,X.shape[2]); CH.append(np.nan_to_num(X[:,:,:n]).astype(np.float32))
        nm+= [pref+str(i) for i in range(n)]; print(path.split("/")[-1], n)
    except Exception as e: print("skip",path,type(e).__name__)
out["CH"]=np.concatenate(CH,axis=2); out["ch_names"]=np.array(nm,dtype=object)
print("合并通道数", out["CH"].shape[2])
np.savez("/workspace/data/wide_dl_allfam.npz", **out)
print("ALLFAM_DONE")
