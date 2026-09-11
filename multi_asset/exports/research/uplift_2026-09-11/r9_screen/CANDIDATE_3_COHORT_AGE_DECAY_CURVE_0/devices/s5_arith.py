#!/usr/bin/env python3
"""r9_screen STEP 4 -- the arithmetic. ENV WHITELIST = EMPTY SET."""
import os, json, math, hashlib
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","UMASK_SCOPE","COSTB_JSON","SLOW_NPY",
     "FSEED","FPRED","FEMAT_NPZ","OUT_TAG","TILT","JUDGE_HC","V2","PANEL_IN"]
assert sorted([k for k in _CE if k in os.environ])==[]
def _f(*a,**k): raise AssertionError("E-0826-D violation")
os.environ.get=_f
OUT="/workspace/uplift_2026-09-11/r9_screen"
C=json.load(open(OUT+"/CURVE_r9screen.json")); N=json.load(open(OUT+"/NULLS_r9screen.json"))
A0=C["A0_reference_reproduced_first_hand"]; s1=A0["annualised_sharpe"]; n=A0["n"]; SE=A0["SE_annualised_sharpe"]
TARGET=3.0+1.96*SE                      # point estimate whose CI95 lower bound clears 3.0
def comb(s1,s2,r):
    num=s1*s1+s2*s2-2*r*s1*s2; den=1.0-r*r
    return math.sqrt(num/den) if den>1e-12 and num>0 else float("nan")
def s2_needed(s1,r,tgt):
    # solve comb(s1,s2,r)=tgt for s2 (take the larger root)
    a=1.0; b=-2*r*s1; c=s1*s1-tgt*tgt*(1-r*r)
    d=b*b-4*a*c
    return (-b+math.sqrt(d))/2 if d>=0 else float("nan")
R={"env_whitelist":[],"self_sha256":hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
   "A0":{"sharpe":s1,"n":n,"SE_annualised_sharpe":SE,"mean_g_bps":A0["mean_g_bps"]},
   "target_point_estimate_for_CI95_lower_bound_over_3.0":round(TARGET,4),
   "gap_in_SE_from_this_A0":round((TARGET-s1)/SE,3),
   "zero_rho_standalone_sharpe_that_would_close_it":round(math.sqrt(max(TARGET*TARGET-s1*s1,0)),4),
   "n_uncorrelated_copies_of_A0_needed":round((TARGET/s1)**2,3),
   "formula":"combined Sharpe at the variance-optimal 2-book allocation = sqrt((s1^2+s2^2-2*rho*s1*s2)/(1-rho^2))"}
rows=[]
for nm,d in C["PRORATA"]["bands"].items():
    s2=d["sharpe"]; r=d["rho_to_A0"]
    rows.append({"band":nm,"gross_share_pct":d["gross_share_pct"],"standalone_sharpe":s2,
      "standalone_sharpe_CI95":d["sharpe_CI95"],"mean_g_bps":d["mean_g_bps"],"mean_g_CI95":d["mean_g_CI95"],
      "rho_to_A0":r,"rho_to_A0_CI95":d["rho_to_A0_CI95"],
      "rho_in_A0_LOSS_cells":d["rho_to_A0_in_A0_LOSS_cells"],"rho_loss_CI95":d["rho_loss_CI95"],
      "mean_g_in_A0_loss_cells":d["mean_g_in_A0_loss_cells"],
      "PASSES_rho_screen_abs_lt_0.30":bool(abs(r)<0.30),
      "combined_sharpe_with_A0":round(comb(s1,s2,r),4),
      "delta_vs_A0":round(comb(s1,s2,r)-s1,4),
      "standalone_sharpe_this_band_would_need_at_its_own_rho":round(s2_needed(s1,r,TARGET),4),
      "shortfall_multiple":round(s2_needed(s1,r,TARGET)/s2,3) if s2>0 else None})
R["bands"]=rows
R["A0_mean_g_in_loss_cells"]=C["PRORATA"]["bands"]["age1p"]["A0_mean_g_in_loss_cells"]
R["shelf_verdict"]={b:{"REAL_holding_rate_bps":N["bands"][b]["REAL"]["holding_rate_bps"],
                       "CI95":N["bands"][b]["REAL"]["holding_rate_CI95"],
                       "null_range":N["bands"][b]["null_holding_rate_min_max"],
                       "beats_all_6_turnover_matched_nulls":N["bands"][b]["REAL_beats_all_6_nulls"]}
                    for b in ("age0","age1","age2_5","age6_11","age12_23","age24_41","age1_41","age42_83","age84p","age42p")}
open(OUT+"/ARITH_r9screen.json","w").write(json.dumps(R,indent=1))
print(json.dumps({k:v for k,v in R.items() if k!="bands"},indent=1))
print("%-10s %6s %8s %8s %8s %8s %9s %8s %8s"%("band","share%","SR","rhoA0","rhoLOSS","meanG_LOSS","comb","dSR","needSR"))
for r_ in rows:
    print("%-10s %6.2f %8.3f %+8.4f %+8.4f %10.2f %9.4f %+8.4f %8.2f"%(r_["band"],r_["gross_share_pct"],
      r_["standalone_sharpe"],r_["rho_to_A0"],r_["rho_in_A0_LOSS_cells"],
      r_["mean_g_in_A0_loss_cells"] if r_["mean_g_in_A0_loss_cells"] is not None else float("nan"),
      r_["combined_sharpe_with_A0"],r_["delta_vs_A0"],r_["standalone_sharpe_this_band_would_need_at_its_own_rho"]))
