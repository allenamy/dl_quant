"""TRACK B forensics on the band/EMA winners:
 (1) G5 re-pricing of every arm at COST_M in {0.133 (live cash-only), 1.0 (device), 1.638 (re-audited 3.52/unit)}
 (2) decomposition of dG into cost / carry / price-pnl
 (3) FREEZE diagnostic: is the uplift a permanently-frozen legacy basket? (position staleness + gross drift)"""
import numpy as np, calendar, json, os
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_TB_%s_dyn_s%s.npz"
def get(nm,s):
    A=np.load(TB%(nm,s),allow_pickle=True); R=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]
    ts=np.round(R[:,0].astype(float)).astype(np.int64)
    return ts,R,W
ARMS=["BASE","BAND35e5","BAND45e5","BAND5e4","BAND6e4","EMA005","EMA004","CAD2","TOPD100"]
print("== (1)+(2) RE-PRICING AND DECOMPOSITION, frozen window, dyn seat, per gross bps/anchor ==")
print("%-9s %-4s | %8s %8s %8s | %8s %8s %8s | %8s %8s %8s"%("arm","seed","g@0.133","g@1.0","g@1.638","dG@0.133","dG@1.0","dG@1.638","d_pnl","d_carry","d_cost@1"))
base={}
out={}
for s in ("42","2027"):
    ts,R,_=get("BASE",s); m=(ts>=FROZEN[0])&(ts<FROZEN[1]); base[s]=(ts[m],R[m])
for nm in ARMS:
    for s in ("42","2027"):
        ts,R,_=get(nm,s); m=(ts>=FROZEN[0])&(ts<FROZEN[1]); R=R[m]
        tb,Rb=base[s]; assert np.array_equal(ts[m],tb)
        gt=R[:,C["gross_total"]]; gtb=Rb[:,C["gross_total"]]
        def gg(RR,GG,cm): return ((RR[:,C["pnl_ex"]]-RR[:,C["carry_ex"]]-cm*RR[:,C["cost_ex"]])/GG).mean()
        row=[gg(R,gt,cm) for cm in (0.133,1.0,1.638)]
        rowb=[gg(Rb,gtb,cm) for cm in (0.133,1.0,1.638)]
        dp=(R[:,C["pnl_ex"]]/gt).mean()-(Rb[:,C["pnl_ex"]]/gtb).mean()
        dc=(R[:,C["carry_ex"]]/gt).mean()-(Rb[:,C["carry_ex"]]/gtb).mean()
        dk=(R[:,C["cost_ex"]]/gt).mean()-(Rb[:,C["cost_ex"]]/gtb).mean()
        out[(nm,s)]=dict(g=row,dg=[a-b for a,b in zip(row,rowb)],dp=dp,dc=dc,dk=dk)
        print("%-9s %-4s | %+8.4f %+8.4f %+8.4f | %+8.4f %+8.4f %+8.4f | %+8.4f %+8.4f %+8.4f"%(
            nm,s,row[0],row[1],row[2],row[0]-rowb[0],row[1]-rowb[1],row[2]-rowb[2],dp,-dc,-dk))
print("\n  (d_pnl + (-d_carry) + (-d_cost) = dG@1.0 ; a POSITIVE -d_carry/-d_cost means the arm pays LESS)")

print("\n== (3) FREEZE DIAGNOSTIC (frozen window, s42): is the uplift a permanently-frozen legacy basket? ==")
print("%-9s %8s %8s %9s %9s %9s %9s"%("arm","gross","nnz","%gross in","%gross in","median","mean |w|"))
print("%-9s %8s %8s %9s %9s %9s %9s"%("","total","names","names un-","names un-","hold-age","of held"))
print("%-9s %8s %8s %9s %9s %9s %9s"%("","","","changed","changed","(anchors)",""))
print("%-9s %8s %8s %9s %9s %9s %9s"%("","","",">=30 anc",">=90 anc","",""))
for nm in ARMS:
    ts,R,W=get(nm,"42"); m=(ts>=FROZEN[0])&(ts<FROZEN[1])
    i0=int(np.argmax(m)); W=W[i0:i0+int(m.sum())].astype(np.float64); R=R[m]
    n,ns=W.shape
    chg=np.abs(np.diff(W,axis=0))>1e-12       # (n-1, ns) did the weight move?
    # for each row t and name k: anchors since last change
    age=np.zeros((n,ns),np.int32)
    a=np.zeros(ns,np.int32)
    for t in range(1,n):
        a=np.where(chg[t-1],0,a+1); age[t]=a
    held=np.abs(W)>1e-12
    gt=np.abs(W).sum(1)
    def frac(k):
        msk=held&(age>=k)
        return (np.abs(W)*msk).sum(1)/np.maximum(gt,1e-12)
    ages=age[held]
    print("%-9s %8.4f %8.1f %9.3f %9.3f %9.1f %9.5f"%(nm,gt.mean(),held.sum(1).mean(),frac(30).mean(),frac(90).mean(),np.median(ages),np.abs(W)[held].mean()))
