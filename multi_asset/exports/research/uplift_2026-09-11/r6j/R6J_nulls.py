"""R6 JUDGE-2 task 3a: the turnover-matched null battery, RE-CUT on the extended windows.
Statistic, bootstrap, substreams and arm set copied VERBATIM from ANGLE1_judge_nulls.py (which copied
judge_round3.py); the ONLY change is the window list. The incumbent window (2024-01-01..2026-08-10 20Z)
is re-run as a CONTROL and must reproduce ANGLE1_NULLS_RESULT.json bitwise."""
import numpy as np, json, calendar, datetime as dt, hashlib, os
D = "/workspace/uplift_2026-09-11/seatladder/dev/probe_artifacts"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
      "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
DL_LAST=T(2026,8,30,20)
WINS=[("INC_2024on_to_0810",T(2024,1,1),T(2026,8,10,20),"CONTROL"),
      ("EXT_2024on_to_0830",T(2024,1,1),DL_LAST,"EXTENDED"),
      ("NEW_0811_to_0830",  T(2026,8,11),DL_LAST,"NEW"),
      ("LIVE_0801_to_0830", T(2026,8,1), DL_LAST,"LIVE_OVL")]
def boot(v,days,rng):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
def load(tag):
    R=np.asarray(np.load(f"{D}/w10_ablation_series_{tag}.npz",allow_pickle=True)["d30_n2_c42_rec"],float)
    return np.round(R[:,0]).astype(np.int64), R[:,C["net_ex"]]/R[:,C["gross_total"]], R[:,C["turnover"]]/R[:,C["gross_total"]]
OUT={"meta":{"self_sha256":hashlib.sha256(open(os.path.abspath(__file__),'rb').read()).hexdigest(),
             "utc":dt.datetime.utcnow().isoformat()+"Z",
             "copied_from":"ANGLE1_judge_nulls.py / ANGLE1_judge_nullsA.py (window list is the only change)"}}
for fam, ctrl_tag, nulls in (("XIB","LAD_XIB_%s_s%d",("W_SHIFT101","W_SHIFT503","W_SHIFT1009")),
                             ("A0FUND","LAD_A_PAR_%s_s%d",("A_SHIFT101","A_SHIFT503","A_SHIFT1009"))):
    print("\n===== FAMILY", fam, "=====")
    print("%-20s %-7s %-5s %-12s %9s %9s %9s %22s %6s %8s"%("window","seat","seed","null","g_ctrl","g_null","Delta","CI95 (k=0)","P>0","turn_rt"))
    for wn, lo, hi, kind in WINS:
        for seat in ("k021","k0357","k0534","dyn"):
            for sd in (42,2027):
                tx,gx,ux=load(ctrl_tag%(seat,sd)); lvl={}
                for i,nm in enumerate(nulls):
                    tn,gn,un=load(f"LAD_{nm}_{seat}_s{sd}")
                    com=np.intersect1d(tx,tn); m=(com>=lo)&(com<=hi)
                    if m.sum()<8: continue
                    ix=np.searchsorted(tx,com)[m]; iN=np.searchsorted(tn,com)[m]
                    d=gx[ix]-gn[iN]
                    lo_,hi_,p=boot(d,com[m]//86400,np.random.default_rng([20260905,300+i]))
                    tr=float(ux[ix].mean()/un[iN].mean())
                    print("%-20s %-7s %-5d %-12s %+9.4f %+9.4f %+9.4f [%+8.4f,%+8.4f] %6.3f %8.3f"%(
                        wn,seat,sd,nm,gx[ix].mean(),gn[iN].mean(),d.mean(),lo_,hi_,p,tr))
                    OUT[f"{fam}|{wn}|{seat}|s{sd}|{nm}"]={"n":int(m.sum()),"g_ctrl":float(gx[ix].mean()),
                      "g_null":float(gn[iN].mean()),"delta":float(d.mean()),"ci95":[lo_,hi_],"p_gt0":p,
                      "turn_ratio":tr,"beats_null":bool(d.mean()>0)}
                    lvl[nm]=float(gn[iN].mean())
                if not lvl: continue
                mm=(tx>=lo)&(tx<=hi); lvl[fam]=float(gx[mm].mean())
                rank=sorted(lvl,key=lambda k:-lvl[k]).index(fam)+1
                print("      -> %s rank %d of 4 on level (n=%d)"%(fam,rank,int(mm.sum())))
                OUT[f"{fam}|{wn}|{seat}|s{sd}|rank"]=rank
                OUT[f"{fam}|{wn}|{seat}|s{sd}|n"]=int(mm.sum())
json.dump(OUT,open("/workspace/uplift_2026-09-11/r6j/R6J_NULLS.json","w"),indent=1)
print("\nWROTE R6J_NULLS.json")
