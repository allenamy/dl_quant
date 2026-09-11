"""BUILD 2 test (d): read the turnover-matched nulls, and report BOTH pnl_ex (gross) and g (net)."""
import numpy as np, calendar, time, json, hashlib, os
assert True
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
U="/workspace/uplift_2026-09-11"; R=U+"/r8b2"; APY=2190; WARM=900; CUT=T(2026,8,30,20); B=4000; TAU=4.75
S=np.load(U+"/r7f1/out/sigma_variants.npz",allow_pickle=True)
C=[str(c) for c in S["cols"]]; GL=dict(zip(S["rec"][:,0].astype(np.int64),S["rec"][:,C.index("LIVE_sig")]))
def load(p):
    Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cc)}
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    A=np.asarray(Z[k],float)[WARM:]; ts=np.round(A[:,ix["ts"]]).astype(np.int64); m=ts<=CUT
    return {"ts":ts[m],"g":(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[m],
            "pnl":(A[:,ix["pnl_ex"]]/A[:,ix["gross_total"]])[m],
            "turn":A[:,ix["turnover"]][m],"w3f":A[:,ix["w3_fund"]][m]}
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>5 else float("nan")
def bstat(ts,fn,seed):
    dd=ts//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
    o=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(o))
    rng=np.random.default_rng([20260912,seed]); pk=rng.integers(0,nd,size=(B,nd)); out=np.empty(B)
    for b in range(B):
        ii=np.concatenate([o[st[j]:en[j]] for j in pk[b]]); out[b]=fn(ii)
    return out
def ci(v,lo=2.5,hi=97.5):
    v=v[np.isfinite(v)]; return (float(np.percentile(v,lo)),float(np.percentile(v,hi)))
A0=load(U+"/r3k/arms/A0_PWR230k_s42.npz")
YRA=np.array([time.gmtime(int(t)).tm_year for t in A0["ts"]]); YEARS=sorted(set(YRA.tolist()))
def pair(arm_path):
    a=load(arm_path)
    com,ia,ib=np.intersect1d(a["ts"],A0["ts"],return_indices=True)
    d=a["g"][ia]-A0["g"][ib]; dp=a["pnl"][ia]-A0["pnl"][ib]
    yv=YRA[ib]
    th=float(np.mean([d[yv==y].mean() for y in YEARS if (yv==y).sum()>0]))
    return {"n":len(com),"n_dropped":int(len(A0["ts"])-len(com)),
            "delta_g":round(float(d.mean()),4),
            "delta_g_CI95":[round(x,4) for x in ci(bstat(com,lambda ii: d[ii].mean(),201))],
            "delta_pnl_ex_gross":round(float(dp.mean()),4),
            "theta_yearFE":round(th,4),
            "delta_sharpe":round(sr(a["g"][ia])-sr(A0["g"][ib]),4),
            "turnover_ratio_vs_A0":round(float(a["turn"][ia].mean()/A0["turn"][ib].mean()),4),
            "marginal_turnover":round(float(a["turn"][ia].mean()-A0["turn"][ib].mean()),6)}
OUT={"caliber":"g=net_ex/gross_total bps/anchor per unit gross; pnl_ex/gross_total = GROSS of carry+cost; post-warm 900; cut 2026-08-30 20Z; fitted cost","B":B,"arms":{}}
NULLS=["SHIFT101","SHIFT503","SHIFT1009","ROT1","ROT2","ROT3"]
for arm in ("S00","P10"):
    real=pair(R+"/dev/probe_artifacts/w10_ablation_series_R8_%s_s42.npz"%arm)
    rows={"REAL":real}
    for n in NULLS:
        rows[n]=pair(R+"/dev2/probe_artifacts/w10_ablation_series_R8N_%s_%s.npz"%(arm,n))
    nd=[rows[n]["delta_g"] for n in NULLS]; nt=[rows[n]["theta_yearFE"] for n in NULLS]
    np_=[rows[n]["delta_pnl_ex_gross"] for n in NULLS]
    OUT["arms"][arm]={"rows":rows,
        "null_delta_g_range":[round(min(nd),4),round(max(nd),4)],"null_delta_g_mean":round(float(np.mean(nd)),4),
        "null_theta_range":[round(min(nt),4),round(max(nt),4)],
        "null_pnl_ex_range":[round(min(np_),4),round(max(np_),4)],
        "real_beats_all_nulls_on_delta_g":bool(real["delta_g"]>max(nd)),
        "real_beats_all_nulls_on_theta":bool(real["theta_yearFE"]>max(nt)),
        "real_beats_all_nulls_on_pnl_ex":bool(real["delta_pnl_ex_gross"]>max(np_)),
        "n_nulls_beating_real_on_delta_g":int(sum(1 for x in nd if x>=real["delta_g"])),
        "empirical_p_delta_g":round((1+sum(1 for x in nd if x>=real["delta_g"]))/(1+len(nd)),4),
        "turnover_match":{"real":real["turnover_ratio_vs_A0"],"nulls":[rows[n]["turnover_ratio_vs_A0"] for n in NULLS]}}
    print("\n=== %s ==="%arm)
    print("%-10s %8s %8s %9s %9s %8s %7s"%("feed","d_g","d_pnl_ex","theta","d_SR","turn_x","n_drop"))
    for k in ["REAL"]+NULLS:
        r=rows[k]
        print("%-10s %+8.4f %+8.4f %+9.4f %+9.4f %8.4f %7d"%(k,r["delta_g"],r["delta_pnl_ex_gross"],r["theta_yearFE"],r["delta_sharpe"],r["turnover_ratio_vs_A0"],r["n_dropped"]))
    print("beats all nulls: d_g=%s theta=%s pnl_ex=%s  empirical p(d_g)=%.4f"%(
        OUT["arms"][arm]["real_beats_all_nulls_on_delta_g"],OUT["arms"][arm]["real_beats_all_nulls_on_theta"],
        OUT["arms"][arm]["real_beats_all_nulls_on_pnl_ex"],OUT["arms"][arm]["empirical_p_delta_g"]))
OUT["self_sha256"]=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
json.dump(OUT,open(R+"/out/R8_NULLS.json","w"),indent=1)
print("\nNULLJUDGE_DONE")
