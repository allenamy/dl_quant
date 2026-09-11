import numpy as np, calendar
P="/workspace/uplift_2026-09-11/probe_artifacts/"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def L(nm):
    A=np.load(P+f"w10_ablation_series_{nm}.npz",allow_pickle=True); R=A["d30_n2_c42_rec"]
    return np.round(R[:,0]).astype(np.int64),R,A
def boot(v,days,k,nb=2000):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    rng=np.random.default_rng([20260905,k]); idx=rng.integers(0,nd,size=(nb,nd))
    mn=S[idx].sum(1)/N[idx].sum(1); return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
W={"DNR-comparable 2023-01->2026-08-31":(T(2023,1,1),4e9),"FULL 2022->2026-08-31":(0,4e9),"frozen":(T(2025,3,1),T(2026,8,10,20)+1)}
print("FTRIM DOSE FAMILY — is the monotone dose curve the candidate uses to reopen the DNR regime-robust?")
print("(dG vs A0, dyn, bps/anchor/gross; the DNR's own window was 2023+ and its injection layer was POST-MIX = FTPOS)")
for w,(lo,hi) in W.items():
    print(f"\n--- {w} ---")
    print("%-9s %-5s %5s %9s %22s %6s"%("arm","seed","n","dG","CI95","P>0"))
    for a in ["NOFTRIM","FT30","FT05","FT00","FT00S3","FT00S","FT00S12","FTPOS","LT10","CD1"]:
        for s in ("42","2027"):
            try: ta,Ra,_=L(f"{a}_dyn_s{s}")
            except Exception: continue
            tb,Rb,_=L(f"A0_dyn_s{s}")
            ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]; gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
            m=(ta>=lo)&(ta<hi); d=(ga-gb)[m]
            l,h,p=boot(d,ta[m]//86400,11)
            print("%-9s %-5s %5d %+9.4f [%+8.4f,%+8.4f] %6.3f"%(a,s,m.sum(),d.mean(),l,h,p))
