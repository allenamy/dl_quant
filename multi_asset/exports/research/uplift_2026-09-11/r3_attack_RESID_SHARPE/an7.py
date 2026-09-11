import numpy as np, calendar, os, json
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"F23":(T(2023,1,1),T(2026,8,10,20)+1),"F24":(T(2024,1,1),T(2026,8,10,20)+1)}
HC="/workspace/review_scratch/health_check"; U="/workspace/uplift_2026-09-11"
def ld(p,key=None):
    Z=np.load(p,allow_pickle=True); kk=key if key else ("rec" if "rec" in Z.files else "d30_n2_c42_rec")
    R=np.asarray(Z[kk],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    gt=np.maximum(R[:,ix["gross_total"]],1e-12)
    return (np.round(R[:,ix["ts"]]).astype(np.int64), R[:,ix["net_ex"]]/gt, np.abs(R[:,ix["w3_rev24"]])>=1e-9)
A0=ld(HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
RS=ld(U+"/r2_learned/out/SL_RESID_SHARPE_s42.npz")
SH=ld(U+"/r2_learned/out/SL_SHARPE_s42.npz")
RD=ld(U+"/r2_learned/out/SL_RESID_s42.npz")
def rho(X,Y,w):
    lo,hi=SPAN[w]
    f=lambda Z: (Z[0][(Z[0]>=lo)&(Z[0]<hi)&np.isfinite(Z[1])&(~Z[2])], Z[1][(Z[0]>=lo)&(Z[0]<hi)&np.isfinite(Z[1])&(~Z[2])])
    ta,ga=f(X); tb,gb=f(Y); c,ia,ib=np.intersect1d(ta,tb,return_indices=True)
    return float(np.corrcoef(ga[ia],gb[ib])[0,1]), len(c)
print("corr_matrix_f23.json claims: anchors=5718, RS~A0=0.28272, SHARPE~A0=0.28850, RS~SHARPE=0.69315, RS~RESID=0.48695")
for w in ("F23","F24"):
    r1,n=rho(RS,A0,w); r2,_=rho(SH,A0,w); r3,_=rho(RS,SH,w); r4,_=rho(RS,RD,w)
    print("  my %s n=%d :  RS~A0 %.5f | SHARPE~A0 %.5f | RS~SHARPE %.5f | RS~RESID %.5f"%(w,n,r1,r2,r3,r4))
