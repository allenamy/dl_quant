"""GATE A (alignment): prove which 5m rows are causal at panel anchor E, by reconstructing panel Y4.
E-0904-F: panel y4 = SUM of 5-minute simple returns over the traded 4h window.
If row idx(E) is the bar OPENING at E, then the traded window is rows [idx(E), idx(E)+48)."""
import numpy as np, time
Z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
t0=time.time(); ts5=Z["ts"].astype(np.int64); ch=list(Z["ch"])
print("loading data...",flush=True); D=Z["data"]; print("loaded",D.shape,round(time.time()-t0,1),"s",flush=True)
R5=D[:,:,ch.index("ret5")].astype(np.float32)
np.save("/workspace/uplift_2026-09-11/r2_sleeve/feat/ret5.npy",R5)
for c in ["range","cpos","log_qv","log_cnt","log_avgsz","tbf"]:
    np.save("/workspace/uplift_2026-09-11/r2_sleeve/feat/%s.npy"%c, D[:,:,ch.index(c)].astype(np.float32))
print("channels cached",round(time.time()-t0,1),"s",flush=True)
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=P["ts"].astype(np.int64); Y4=np.asarray(P["Y4"],np.float64)
pos=np.searchsorted(ts5,pts); assert (ts5[pos]==pts).all()
# test 3 offsets: window starting at idx(E) (=E is open), at idx(E)-48 (=E is close), at idx(E)+1
S=np.nancumsum(np.nan_to_num(R5.astype(np.float64),nan=0.0),axis=0)
S=np.vstack([np.zeros((1,S.shape[1])),S])
def win(a,b): return S[b]-S[a]
i=np.arange(len(pts))
for name,a,b in [("rows[idx(E),idx(E)+48)  E=OPEN",pos,pos+48),
                 ("rows[idx(E)-48,idx(E))  E=CLOSE",pos-48,pos),
                 ("rows[idx(E)+1,idx(E)+49)",pos+1,pos+49)]:
    ok=(a>=0)&(b<=len(ts5))
    W=np.full(Y4.shape,np.nan); W[ok]=win(a[ok],b[ok])
    m=np.isfinite(Y4)&np.isfinite(W)&(np.abs(Y4)>0)
    d=np.abs(W[m]-Y4[m])
    print("%-34s  n=%d  median|d|=%.3e  p99|d|=%.3e  corr=%.6f"%(name,m.sum(),np.median(d),np.percentile(d,99),np.corrcoef(W[m],Y4[m])[0,1]),flush=True)
