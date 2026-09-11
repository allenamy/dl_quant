"""Capacity probe: where does each book put its gross, relative to name liquidity (qv4h)?"""
import numpy as np, json, time
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); qvk=MT["qvk"]
QV4=np.expm1(np.clip(qvk,0,30))*48        # 4h quote volume USDT, same formula as the device
def probe(path,key,label):
    A=np.load(path,allow_pickle=True)
    R=A[key+"_rec"]; W=A[key+"_W"]
    ts=np.round(R[:,0]).astype(np.int64)
    emap={int(t):i for i,t in enumerate(E)}
    rows=[emap.get(int(t)) for t in ts]
    sel=[k for k,r in enumerate(rows) if r is not None and ts[k]>=int(time.mktime((2025,3,1,0,0,0,0,0,0)))]
    aw=[];  pct=[]; nn=[]
    for k in sel:
        r=rows[k]; w=np.abs(W[k]); q=QV4[r]
        m=(w>1e-9)&np.isfinite(q)&(q>0)
        if m.sum()<10: continue
        g=w[m].sum()
        aw.append(float((w[m]/g*np.log10(q[m])).sum()))          # gross-weighted log10 qv4h
        # notional per name at NAV 115k, gross 2.0x  => position = w * 230000
        pct.append(float(np.max(w[m]*230000.0/q[m])))            # worst name: position as fraction of its 4h volume
        nn.append(int(m.sum()))
    print(f"{label:28s} n={len(aw):5d}  gross-wtd median qv4h = ${10**np.mean(aw):,.0f}   "
          f"median worst-name pos/qv4h = {np.median(pct)*100:.2f}%   mean names {np.mean(nn):.0f}")
probe("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42","A0 in-service form")
import sys
for p,l in [(x.split("=")[0],x.split("=")[1]) for x in sys.argv[1:]]:
    probe(p,"d30_n2_c42",l)
