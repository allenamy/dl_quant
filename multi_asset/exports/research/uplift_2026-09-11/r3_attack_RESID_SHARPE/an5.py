import numpy as np, calendar, os, glob
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"F23":(T(2023,1,1),T(2026,8,10,20)+1),"F24":(T(2024,1,1),T(2026,8,10,20)+1),
      "FROZEN":(T(2025,3,1),T(2026,8,10,20)+1),"y2023":(T(2023,1,1),T(2024,1,1)),
      "y2026":(T(2026,1,1),T(2026,8,10,20)+1)}
HC="/workspace/review_scratch/health_check"; U="/workspace/uplift_2026-09-11"; W=U+"/r3_attack_b9646"
A={}
def ld(k,p,key=None):
    if not os.path.exists(p): print("MISSING",k,p); return
    Z=np.load(p,allow_pickle=True); kk=key if key else ("rec" if "rec" in Z.files else "d30_n2_c42_rec")
    R=np.asarray(Z[kk],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    ts=np.round(R[:,ix["ts"]]).astype(np.int64); gt=np.maximum(R[:,ix["gross_total"]],1e-12)
    A[k]=dict(ts=ts,g=R[:,ix["net_ex"]]/gt,p=R[:,ix["pnl_ex"]]/gt,c=R[:,ix["cost_ex"]]/gt,
              ca=R[:,ix["carry_ex"]]/gt,tn=R[:,ix["turnover"]],gt=gt,
              warm=np.abs(R[:,ix["w3_rev24"]])>=1e-9)
ld("ARM_s42",U+"/r3_integrate/out/RS_RESID_SHARPE_s42_STD.npz")
ld("ARM_s2027",U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_STD.npz")
ld("PERMplacebo",U+"/r2_learned/out/SL_RESID_SHARPE_PERM_s42.npz")
for f in sorted(glob.glob(W+"/out/NULL_*.npz")): ld(os.path.basename(f)[5:-4],f)
def st(k,w):
    d=A[k]; lo,hi=SPAN[w]; m=(d["ts"]>=lo)&(d["ts"]<hi)&np.isfinite(d["g"])&(~d["warm"])
    if m.sum()<30: return None
    v=d["g"][m]
    return dict(n=int(m.sum()),g=v.mean(),SR=v.mean()/v.std(ddof=1)*np.sqrt(APY),
                pnl=d["p"][m].mean(),cost=d["c"][m].mean(),carry=d["ca"][m].mean(),
                tn=d["tn"][m].mean(),gt=d["gt"][m].mean())
print("### TURNOVER-MATCHED NULLS vs the arm.  net_ex AND pnl_ex (gross of carry & cost), post-warm")
print("%-16s %-7s %6s %9s %9s %8s %9s %9s %9s"%("arm","win","n","pnl_ex","net_ex","SR_net","turnover","gross","turn/gross"))
order=["ARM_s42","ARM_s2027","SHUFY_s42","SHUFY_s2027","SHIFT101","SHIFT503","SHIFT1009","RELAB1","RELAB2","RELAB3","PERMplacebo"]
for k in order:
    if k not in A: continue
    for w in ["F23","y2023","F24","y2026"]:
        s=st(k,w)
        if not s: continue
        print("%-16s %-7s %6d %+9.4f %+9.4f %+8.3f %9.5f %9.4f %9.5f"%(k,w,s["n"],s["pnl"],s["g"],s["SR"],s["tn"],s["gt"],s["tn"]/s["gt"]))
    print()
print("### NULL DISTRIBUTION SUMMARY on F23 (6 nulls: 3 shift + 3 relabel)")
nl=[st(k,"F23") for k in ["SHIFT101","SHIFT503","SHIFT1009","RELAB1","RELAB2","RELAB3"] if k in A]
if nl:
    gs=np.array([x["g"] for x in nl]); srs=np.array([x["SR"] for x in nl]); pn=np.array([x["pnl"] for x in nl])
    a=st("ARM_s42","F23")
    print("  null net_ex mean %+0.4f  sd %0.4f  min %+0.4f max %+0.4f   | ARM %+0.4f  -> z = %+0.2f"%(
        gs.mean(),gs.std(ddof=1),gs.min(),gs.max(),a["g"],(a["g"]-gs.mean())/gs.std(ddof=1)))
    print("  null pnl_ex mean %+0.4f  sd %0.4f  min %+0.4f max %+0.4f   | ARM %+0.4f  -> z = %+0.2f"%(
        pn.mean(),pn.std(ddof=1),pn.min(),pn.max(),a["pnl"],(a["pnl"]-pn.mean())/pn.std(ddof=1)))
    print("  null SR     mean %+0.3f  sd %0.3f  min %+0.3f max %+0.3f   | ARM %+0.3f"%(
        srs.mean(),srs.std(ddof=1),srs.min(),srs.max(),a["SR"]))
    print("  null turn/gross mean %0.5f   | ARM %0.5f   (permutation placebo %0.5f)"%(
        np.mean([x["tn"]/x["gt"] for x in nl]),a["tn"]/a["gt"],st("PERMplacebo","F23")["tn"]/st("PERMplacebo","F23")["gt"]))
