import numpy as np, json, calendar, time, os
AD="/workspace/uplift_2026-09-11/artifacts"; DV="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
C={c:i for i,c in enumerate(["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"])}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
def ld(tag):
    p=f"{AD}/w10_ablation_series_{tag}.npz"
    if not os.path.exists(p): p=f"{DV}/w10_ablation_series_{tag}.npz"
    A=np.load(p,allow_pickle=True); R=A["d30_n2_c42_rec"]
    ts=np.round(R[:,0]).astype(np.int64); return ts, R[:,C["net_ex"]]/R[:,C["gross_total"]], R
def sharpe_ci(ta,ga,tb,gb,seed):
    com=np.intersect1d(ta,tb); ia=np.searchsorted(ta,com); ib=np.searchsorted(tb,com)
    m=(com>=FROZEN[0])&(com<FROZEN[1]); a=ga[ia][m]; b=gb[ib][m]; d=com[m]//86400
    ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    rng=np.random.default_rng([20260905,seed]); idx=rng.integers(0,nd,size=(2000,nd))
    # per-day lists
    order=np.argsort(inv,kind="stable"); a_s=a[order]; b_s=b[order]; cnt=np.bincount(inv,minlength=nd); off=np.concatenate([[0],np.cumsum(cnt)])
    sh=np.empty(2000); shb=np.empty(2000)
    for k in range(2000):
        sel=idx[k]; pieces_a=[a_s[off[j]:off[j+1]] for j in sel]; pieces_b=[b_s[off[j]:off[j+1]] for j in sel]
        va=np.concatenate(pieces_a); vb=np.concatenate(pieces_b)
        sh[k]=va.mean()/va.std(ddof=1)*np.sqrt(2190); shb[k]=vb.mean()/vb.std(ddof=1)*np.sqrt(2190)
    dd=sh-shb
    return (float(a.mean()/a.std(ddof=1)*np.sqrt(2190)), float(b.mean()/b.std(ddof=1)*np.sqrt(2190)),
            float(dd.mean()), float(np.percentile(dd,2.5)), float(np.percentile(dd,97.5)), float((dd>0).mean()))
out={}
print("== SECONDARY: paired annualised-Sharpe difference (arm - baseline), frozen window, UTC-day block bootstrap 2000 ==")
print("%-26s %7s %7s %8s %20s %6s"%("arm vs base","Shp_arm","Shp_base","dShp","CI95","P>0"))
k=0
for s in ("42","2027"):
    tb,gb,_=ld(f"V4_A0_dyn_s{s}")
    for tag,label in [(f"E3_PHI0.55_dyn_s{s}","PHI0.55"),(f"E3_PHI0.65_dyn_s{s}","PHI0.65"),(f"E2_BOOK_dyn_s{s}","SEATBOOK900"),(f"E1X_L1200_dyn_s{s}","LOOK1200")]:
        ta,ga,_=ld(tag); r=sharpe_ci(ta,ga,tb,gb,200+k); k+=1
        out[f"{label}|s{s}"]={"sharpe_arm":r[0],"sharpe_base":r[1],"dsharpe":r[2],"ci95":[r[3],r[4]],"p_gt0":r[5]}
        print("%-26s %7.2f %7.2f %+8.3f [%+8.3f,%+8.3f] %6.3f"%(f"{label} s{s}",r[0],r[1],r[2],r[3],r[4],r[5]))
print()
print("== E5 DECIDING QUESTION: does a FAST window destroy alpha in blocks where fund won and king was weak? ==")
for s in ("42","2027"):
    tk,gk,_=ld(f"LEG_king_s{s}"); tf,gf,_=ld(f"LEG_fund_s{s}")
    tb,gb,_=ld(f"V4_A0_dyn_s{s}"); t6,g6,_=ld(f"E1_L60_dyn_s{s}")
    com=np.intersect1d(np.intersect1d(tk,tf),np.intersect1d(tb,t6))
    m=(com>=FROZEN[0])&(com<FROZEN[1]); com=com[m]
    gkv=gk[np.searchsorted(tk,com)]; gfv=gf[np.searchsorted(tf,com)]
    d=(g6[np.searchsorted(t6,com)]-gb[np.searchsorted(tb,com)])
    B=190; nb=len(com)//B
    rows=[]
    for j in range(nb):
        sl=slice(j*B,(j+1)*B)
        rows.append((float(gkv[sl].mean()),float(gfv[sl].mean()),float(d[sl].mean()),
                     time.strftime("%Y-%m",time.gmtime(int(com[sl][0])))))
    kk=np.array([r[0] for r in rows]); ff=np.array([r[1] for r in rows]); dd=np.array([r[2] for r in rows])
    win_fund = (ff>kk)
    king_weak = kk < np.median(kk)
    grp = win_fund & king_weak
    print(f"-- s{s}: {nb} non-overlapping 190-anchor blocks on the frozen window; n(fund-won & king-weak)={int(grp.sum())} --")
    print("   %-8s %8s %8s %9s %s"%("block","g_king","g_fund","d(L60-L900)","group"))
    for r,gsel in zip(rows,grp):
        print("   %-8s %+8.3f %+8.3f %+9.3f %s"%(r[3],r[0],r[1],r[2],"FUND-WON&KING-WEAK" if gsel else ""))
    def mse(v):
        return float(v.mean()), float(v.std(ddof=1)/np.sqrt(len(v))) if len(v)>1 else float("nan")
    a=mse(dd[grp]); b=mse(dd[~grp])
    print(f"   MEAN d(L60-L900) in fund-won&king-weak blocks: {a[0]:+.4f} +/- {a[1]:.4f} (n={int(grp.sum())})")
    print(f"   MEAN d(L60-L900) in all other blocks         : {b[0]:+.4f} +/- {b[1]:.4f} (n={int((~grp).sum())})")
    out[f"E5|s{s}"]={"blocks":rows,"grp":[bool(x) for x in grp],"mean_grp":a,"mean_other":b}
json.dump(out,open("/workspace/uplift_2026-09-11/OUT_E5_secondary.json","w"),indent=1)
print("E5_DONE")
