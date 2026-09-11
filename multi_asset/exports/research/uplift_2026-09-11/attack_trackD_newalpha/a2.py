import numpy as np, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R
FULL=(T(2022,1,1),T(2026,8,10,20)+1); FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
def dec(ts,R,w):
    m=(ts>=w[0])&(ts<w[1]); gt=R[m,C["gross_total"]]
    px=(R[m,C["pnl_ex"]]/gt).mean(); ca=(R[m,C["carry_ex"]]/gt).mean(); co=(R[m,C["cost_ex"]]/gt).mean()
    net=(R[m,C["net_ex"]]/gt).mean(); to=R[m,C["turnover"]].mean()
    return dict(n=int(m.sum()),net=net,price=px,carry=ca,cost=co,resid=net-(px+ca-co),turn=to,
                cpu=co/to if to>0 else float("nan"))
arms=[("A0_s42",HC+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec"),
      ("IB_AM50",TD+"/IB_AM50.npz","rec"),("IB_AM25",TD+"/IB_AM25.npz","rec"),
      ("IB_AMSU",TD+"/IB_AMSU.npz","rec"),("IB_PARITY",TD+"/IB_PARITY.npz","rec"),
      ("ORTH_amihud",TD+"/SL_ORTH_f_amihud_24h__p.npz","rec"),
      ("ORTH_asz",TD+"/SL_ORTH_f_asz_24h__m.npz","rec"),
      ("ORTH_SURP",TD+"/SL_ORTH_D_SURP__m.npz","rec"),
      ("RAW_amihud",TD+"/SL_f_amihud_24h__p.npz","rec"),
      ("TBF",TD+"/SL_f_tbf_24h__p.npz","rec"),
      ("FUND_V1",TD+"/SL_FUND_V1__p.npz","rec")]
hdr="%-13s %-7s %5s %8s %8s %8s %7s %7s %7s %8s" % ("arm","win","n","net","price","carry","cost","resid","turn","bps/unit")
print(hdr)
for nm,p,k in arms:
    ts,R=load(p,k)
    for wn,w in [("full",FULL),("frozen",FROZEN)]:
        d=dec(ts,R,w)
        print("%-13s %-7s %5d %+8.3f %+8.3f %+8.3f %7.3f %+7.3f %7.4f %8.3f" % (nm,wn,d["n"],d["net"],d["price"],d["carry"],d["cost"],d["resid"],d["turn"],d["cpu"]))
