import numpy as np, importlib.util, calendar
spec=importlib.util.spec_from_file_location("j","/workspace/uplift_2026-09-11/judgeD.py"); j=importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
A0="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
t0,g0,R0=j.load(A0,"d30_n2_c42_rec")
WIN={"full":(T(2022,1,1),T(2026,8,10,20)+1),"frozen":(T(2025,3,1),T(2026,8,10,20)+1),
     "EXT 08-11->08-31":(T(2026,8,11),T(2026,8,31,20)+1),
     "2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
def st(ts,g,R,lo,hi):
    m=(ts>=lo)&(ts<hi); v=g[m]
    if m.sum()<3: return None
    c=np.concatenate([[0.0],np.cumsum(v)])
    return v.mean(), v.mean()/v.std(ddof=1)*np.sqrt(2190), float(np.max(np.maximum.accumulate(c)-c)), R[m,17].mean()
names=["IB_PARITY","IB_AM25","IB_AM50","IB_SU25","IB_AMSU"]
D={n:j.load(f"/workspace/uplift_2026-09-11/trackD_v4/{n}.npz","rec") for n in names}
# parity receipt
ts,g,R=D["IB_PARITY"]
c,ia,ib=np.intersect1d(ts,t0,return_indices=True)
print(f"PARITY receipt: IB_PARITY vs A0, common {len(c)} anchors, max|dg| = {np.max(np.abs(g[ia]-g0[ib])):.3e}")
print(f"{'window':18s} {'A0':>22s} "+" ".join(f"{n:>22s}" for n in names[1:]))
for w,(lo,hi) in WIN.items():
    a=st(t0,g0,R0,lo,hi)
    if not a: continue
    row=f"{w:18s} {a[0]:+7.3f}/{a[1]:+5.2f}/t{a[3]:.3f} "
    for n in names[1:]:
        ts,g,R=D[n]; s=st(ts,g,R,lo,hi)
        row+=f" {s[0]:+7.3f}/{s[1]:+5.2f}/t{s[3]:.3f}" if s else " "*22
    print(row)
