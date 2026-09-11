import numpy as np, time, sys, calendar
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); qvk=MT["qvk"]; QV4=np.expm1(np.clip(qvk,0,30))*48
T0=calendar.timegm((2025,3,1,0,0,0))
def probe(path,label):
    A=np.load(path,allow_pickle=True); R=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]
    ts=np.round(R[:,0]).astype(np.int64); emap={int(t):i for i,t in enumerate(E)}
    L=[];S=[];WP=[]
    for k,t in enumerate(ts):
        r=emap.get(int(t))
        if r is None or t<T0: continue
        w=W[k]; q=QV4[r]; ok=np.isfinite(q)&(q>0)
        for side,arr in (("L",w>1e-9),("S",w<-1e-9)):
            m=arr&ok
            if m.sum()<5: continue
            a=np.abs(w[m]); g=a.sum()
            v=float((a/g*np.log10(q[m])).sum())
            (L if side=="L" else S).append(v)
        m=(np.abs(w)>1e-9)&ok
        if m.sum()>5: WP.append(float(np.percentile(np.abs(w[m])*230000.0/q[m],95)))
    print(f"{label:34s} LONG side gross-wtd qv4h ${10**np.mean(L):>12,.0f} | SHORT side ${10**np.mean(S):>12,.0f} | p95 pos/qv4h {np.median(WP)*100:.3f}%")
probe("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","A0 in-service form")
for x in sys.argv[1:]:
    p,l=x.split("="); probe(p,l)
