import numpy as np, datetime as dt
meta=np.load("/workspace/data/wide_fea_v1_meta.npz",allow_pickle=True)
E=meta["E_ts"].astype(np.int64); Y4M=meta["y4"].astype(np.float64)
z5=np.load("/workspace/data/dlnative_5m_wide829_f16.npz",allow_pickle=True)
dts=z5["ts"].astype(np.int64); X=z5["data"][:,:,0].astype(np.float32); del z5
e_idx=np.searchsorted(dts,E)
def win(off,n=48):
    out=np.full((len(E),829),np.nan)
    for i,e in enumerate(e_idx):
        blk=X[e+off:e+off+n]
        ok=np.isfinite(blk); c=ok.sum(0)
        out[i]=np.where(c>=46,np.where(ok,blk,0).astype(np.float64).sum(0),np.nan)
    return out
sub=slice(4000,4400)
Es=E[sub]; ei=e_idx[sub]
for off in (-1,0,1,2):
    out=np.full((400,829),np.nan)
    for k,e in enumerate(ei):
        blk=X[e+off:e+off+48]; ok=np.isfinite(blk); c=ok.sum(0)
        out[k]=np.where(c>=46,np.where(ok,blk,0).astype(np.float64).sum(0),np.nan)
    A=Y4M[sub]; b=np.isfinite(A)&np.isfinite(out)
    print("offset %+d: corr=%.6f  maxabsdiff=%.6f  medabsdiff=%.2e  n=%d"%(off,np.corrcoef(A[b],out[b])[0,1],np.abs(A[b]-out[b]).max(),np.median(np.abs(A[b]-out[b])),b.sum()))
print("5m ts[e] for anchor 4000:",dt.datetime.fromtimestamp(int(dts[e_idx[4000]]),dt.UTC).isoformat(),"anchor",dt.datetime.fromtimestamp(int(E[4000]),dt.UTC).isoformat())
