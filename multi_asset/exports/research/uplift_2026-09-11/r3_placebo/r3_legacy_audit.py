"""Round-3 audit of the ARCHIVED round-1/2 placebo arms, on the post-warm v4 footing.
Reads only existing artifacts. Two things are measured for every archived null:
  (a) its cost ratio to its own real arm  -> how much of its negative net was churn;
  (b) the round-2 'fixed column permutation' relabel null's BASE-MASK COVERAGE, which is the
      second defect: permuting a mask-imposed matrix silently halves the book's breadth.
"""
import numpy as np, os, json
U = "/workspace/uplift_2026-09-11"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember",
        "fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover",
        "net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
def ep(s): return int((np.datetime64(s)-np.datetime64("1970-01-01T00:00:00"))/np.timedelta64(1,"s"))
FULL = (ep("2022-01-01T00:00"), ep("2026-08-10T20:00"))
def rd(p):
    if not os.path.exists(p): return None
    Z = np.load(p, allow_pickle=True)
    k = "rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R = np.asarray(Z[k], float)
    cols = [str(c) for c in Z["cols"]] if "cols" in Z.files else COLS
    ix = {c:i for i,c in enumerate(cols)}
    ts = np.round(R[:, ix["ts"]]).astype(np.int64)
    gt = R[:, ix["gross_total"]]
    warm = np.zeros(len(ts), bool); warm[:900] = True
    m = (~warm) & (ts >= FULL[0]) & (ts <= FULL[1])
    return {"n": int(m.sum()),
            "g": float(np.mean(R[m, ix["net_ex"]]/gt[m])),
            "ggross": float(np.mean(R[m, ix["pnl_ex"]]/gt[m])),
            "gcost": float(np.mean(R[m, ix["cost_ex"]]/gt[m])),
            "turn": float(np.mean(R[m, ix["turnover"]]))}
GROUPS = {
 "AMI_lag (r2_attack)": {"real": U+"/r2_attack/out/AM_REAL.npz",
   "PERMFEAT": U+"/r2_attack/out/AM_PLA_permfeat.npz",
   "PERMORTH": U+"/r2_attack/out/AM_PLA_orthperm.npz",
   "RELABEL1": U+"/r2_attack/out/AM_PLA_relabel1.npz",
   "RELABEL2": U+"/r2_attack/out/AM_PLA_relabel2.npz",
   "RELABEL3": U+"/r2_attack/out/AM_PLA_relabel3.npz"},
 "ORTH_AMIRESID (r2_factor)": {"real": U+"/r2_factor/out/SL2_ORTH_AMIRESID__p.npz",
   "PERMFEAT": U+"/r2_factor/out/SL2_PERMFEAT_AMIRESID__p.npz",
   "PERMORTH": U+"/r2_factor/out/SL2_PERMORTH_AMIRESID__p.npz",
   "GPERM1": U+"/r2_factor/vout/V_GPERM1_AMIRESID__p.npz",
   "GPERM2": U+"/r2_factor/vout/V_GPERM2_AMIRESID__p.npz",
   "GPERM3": U+"/r2_factor/vout/V_GPERM3_AMIRESID__p.npz"},
 "ORTH_RESSKEW (r2_factor)": {"real": U+"/r2_factor/out/SL2_ORTH_RESSKEW__m.npz",
   "PERMFEAT": U+"/r2_factor/out/SL2_PERMFEAT_RESSKEW__m.npz",
   "PERMORTH": U+"/r2_factor/out/SL2_PERMORTH_RESSKEW__m.npz",
   "GPERM1": U+"/r2_factor/vout/V_GPERM1_RESSKEW__m.npz",
   "GPERM2": U+"/r2_factor/vout/V_GPERM2_RESSKEW__m.npz"},
 "TBF_ema08 (r2_sleeve)": {"real": U+"/r2_sleeve/out/TBF_ema08.npz",
   "PERMFEAT": U+"/r2_sleeve/out/TBF_PLA_permfeat.npz",
   "PERMORTH": U+"/r2_sleeve/out/TBF_PLA_orthperm.npz",
   "PERMSM": U+"/r2_sleeve/out/TBF_PLA_permsm.npz",
   "RELABEL": U+"/r2_sleeve/out/TBF_PLA_relabel.npz"},
 "ORTH_AMI3D (r2_horizon)": {"real": U+"/r2_horizon/out/C_AMI3D__p.npz",
   "PERMFEAT": U+"/r2_horizon/out/PLF_AMI3D__p.npz",
   "PERMORTH": U+"/r2_horizon/out/PL_ORTHPERM__p.npz"},
 "XIB_LAG50 in-book (r2_attack)": {"real": U+"/r2_attack/out/XIB_AM50_s42.npz",
   "PERMFEAT": U+"/r2_attack/out/XIB_AM50_PLAperm.npz",
   "RELABEL1": U+"/r2_attack/out/XIB_AM50_PLAr1.npz",
   "RELABEL2": U+"/r2_attack/out/XIB_AM50_PLAr2.npz",
   "RELABEL3": U+"/r2_attack/out/XIB_AM50_PLAr3.npz"},
}
res = {}
print("%-34s %-10s %6s %9s %9s %9s %7s %7s"%("group","arm","n","g_net","g_gross","g_cost","turn","cost_x"))
for gname, g in GROUPS.items():
    real = rd(g["real"]); res[gname] = {}
    if real is None: print(gname, "REAL MISSING", g["real"]); continue
    res[gname]["real"] = real
    print("%-34s %-10s %6d %+9.4f %+9.4f %9.4f %7.4f %7s"%(gname,"REAL",real["n"],real["g"],real["ggross"],real["gcost"],real["turn"],"1.00"))
    for k,p in g.items():
        if k == "real": continue
        d = rd(p)
        if d is None: print("   MISSING", k, p); continue
        d["cost_ratio"] = d["gcost"]/max(real["gcost"],1e-12)
        d["margin_net"] = real["g"]-d["g"]; d["margin_gross"] = real["ggross"]-d["ggross"]
        res[gname][k] = d
        print("%-34s %-10s %6d %+9.4f %+9.4f %9.4f %7.4f %7.2f"%("",k,d["n"],d["g"],d["ggross"],d["gcost"],d["turn"],d["cost_ratio"]))
    print()
# ---- the coverage defect of the round-2 'fixed column permutation of the masked matrix' null
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
B = np.isfinite(np.asarray(PW["f_fund_ema_v1"], float))
cov = {}
for nm, X in (("f_amihud_24h", np.asarray(PW["f_amihud_24h"], float)),
              ("AMIRESID", np.asarray(np.load(U+"/r2_factor/feat/AMIRESID.npy"), float)),
              ("RESSKEW", np.asarray(np.load(U+"/r2_factor/feat/RESSKEW.npy"), float)),
              ("f_tbf_24h", np.asarray(PW["f_tbf_24h"], float))):
    F = np.isfinite(X)
    r = {"real_finite_within_base": float((F & B).sum()/B.sum())}
    for sd in (40001, 777, 20260913):
        p = np.random.default_rng(sd).permutation(X.shape[1])
        r["colperm_seed%d_finite_within_base" % sd] = float((F[:, p] & B).sum()/B.sum())
    cov[nm] = r
    print("COVERAGE %-12s real %.4f | after fixed column permutation %s"
          % (nm, r["real_finite_within_base"],
             " ".join("%.4f" % v for k, v in r.items() if k.startswith("colperm"))))
res["_coverage_defect_of_round2_colperm_null"] = cov
json.dump(res, open(U+"/r3_placebo/LEGACY_AUDIT.json", "w"), indent=1)
print("\nwritten", U+"/r3_placebo/LEGACY_AUDIT.json")
