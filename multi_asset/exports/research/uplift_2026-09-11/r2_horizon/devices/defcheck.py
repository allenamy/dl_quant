import numpy as np
from scipy.stats import rankdata, spearmanr
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64)
z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
pos={int(t):k for k,t in enumerate(ts5)}
K=np.array([pos[int(t)] for t in pts])
D=z["data"]
J=np.arange(3000,9000,29); KJ=K[J]
def grab(ci,a,b):
    # rows [a,b) for each anchor -> (len(J), W, 829)
    return np.stack([D[k+a:k+b,:,ci].astype(np.float32) for k in KJ])
def sp(A,Bm):
    r=[]
    for i in range(A.shape[0]):
        a=A[i];b=Bm[i];m=np.isfinite(a)&np.isfinite(b)
        if m.sum()>50: r.append(spearmanr(a[m],b[m]).statistic)
    return float(np.nanmean(r)), len(r)
ir=ch.index("ret5"); iq=ch.index("log_qv"); ia=ch.index("log_avgsz"); it=ch.index("tbf"); ic=ch.index("cpos"); ig=ch.index("range")
R=grab(ir,-288,0); Q=grab(iq,-288,0); A=grab(ia,-288,0); T=grab(it,-288,0); C=grab(ic,-288,0); G=grab(ig,-288,0)
def nm(X,f=np.nanmean): 
    with np.errstate(all="ignore"): return f(X,axis=1)
qv=np.exp(Q.astype(np.float64))
print("f_range_24h vs mean(range):", sp(np.asarray(PW["f_range_24h"])[J], nm(G)))
print("f_cpos_24h  vs mean(cpos) :", sp(np.asarray(PW["f_cpos_24h"])[J], nm(C)))
print("f_tbf_24h   vs mean(tbf)  :", sp(np.asarray(PW["f_tbf_24h"])[J], nm(T)))
print("f_asz_24h   vs mean(log_avgsz):", sp(np.asarray(PW["f_asz_24h"])[J], nm(A)))
print("f_asz_24h   vs mean(exp avgsz):", sp(np.asarray(PW["f_asz_24h"])[J], nm(np.exp(A.astype(np.float64)))))
am1=nm(np.abs(R)/np.maximum(qv,1e-9))
with np.errstate(all="ignore"):
    am2=np.nansum(np.abs(R),1)/np.nansum(qv,1)
    am3=nm(np.abs(R))/nm(qv)
print("f_amihud_24h vs mean(|r|/qv):", sp(np.asarray(PW["f_amihud_24h"])[J], am1))
print("f_amihud_24h vs sum|r|/sumqv:", sp(np.asarray(PW["f_amihud_24h"])[J], am2))
print("f_amihud_24h vs mean|r|/meanqv:", sp(np.asarray(PW["f_amihud_24h"])[J], am3))
print("f_volq_ratio vs mean(logqv24)-?:", sp(np.asarray(PW["f_volq_ratio"])[J], nm(Q)))
