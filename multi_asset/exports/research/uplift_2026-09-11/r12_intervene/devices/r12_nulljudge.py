"""r12 null judge + second seed + w12b device re-gate. ENV whitelist = EMPTY SET."""
import os, json, time, hashlib, glob
import numpy as np
assert not any(k in os.environ for k in ("CAL","PHI","CEM_Q","BYP_STATE","LEGS","FTRIM","R12_NULL"))
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"; T=f"{R}/dev_ext/probe_artifacts"
APY=2190; WARM=900; NB=2000; K=29; PLO=100*(0.05/K)/2; PHI_=100-PLO
MON=np.load(f"{R}/out/monitors.npz",allow_pickle=True)
COLS=[str(c) for c in MON["cols"]]; C={k:i for i,k in enumerate(COLS)}
def load(tag):
    Z=np.load(f"{T}/w10_ablation_series_{tag}.npz",allow_pickle=True)
    Rr=np.asarray(Z["d30_n2_c42_rec"],float); gt=Rr[:,C["gross_total"]]
    return {"ts":np.round(Rr[:,C["ts"]]).astype(np.int64),"g":Rr[:,C["net_ex"]]/gt,
            "tov":Rr[:,C["cost_ex"]]/gt/2.9537,"rec":Rr,"W":np.asarray(Z["d30_n2_c42_W"]),
            "DIAG":np.asarray(Z["d30_n2_c42_DIAG"],float) if "d30_n2_c42_DIAG" in Z.files else None}
OUT={"read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"env_whitelist":[],"K_declared":K}
# ---- device re-gate: w12b with every branch off == w12 with every branch off, BITWISE ----
for s in ("42","2027"):
    A=load("R12_GATEP_s42") if s=="42" else None
    B=load(f"R12B_GATEP_s{s}")
    if s=="42":
        OUT.setdefault("GATE_P2",{})["s42_w12b_vs_w12"]={"rec_bitwise":bool(np.array_equal(A["rec"],B["rec"])),
            "W_bitwise":bool(np.array_equal(A["W"],B["W"])),"maxabs":float(np.max(np.abs(A["rec"]-B["rec"])))}
    arch=np.load(f"{U}/r9/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s{s}.npz",allow_pickle=True)
    OUT["GATE_P2"][f"s{s}_w12b_vs_archived_R9_A1x"]={
        "rec_bitwise":bool(np.array_equal(np.asarray(arch["d30_n2_c42_rec"]),B["rec"])),
        "W_bitwise":bool(np.array_equal(np.asarray(arch["d30_n2_c42_W"]),B["W"]))}
assert OUT["GATE_P2"]["s42_w12b_vs_w12"]["rec_bitwise"]
assert all(v["rec_bitwise"] and v["W_bitwise"] for k,v in OUT["GATE_P2"].items() if "archived" in k)
A0={s:load(f"R12B_GATEP_s{s}") for s in ("42","2027")}
sl=slice(WARM,None)
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def prep(x,d):
    u,inv=np.unique(d,return_inverse=True); nd=len(u)
    return nd,np.bincount(inv,minlength=nd).astype(float),np.bincount(inv,weights=x,minlength=nd),np.bincount(inv,weights=x*x,minlength=nd)
def boot(a,s,d,k,B=NB):
    nd,n,sa,qa=prep(a,d); _,_,ss,qs=prep(s,d)
    rng=np.random.default_rng([20260905,k]); idx=rng.integers(0,nd,size=(B,nd))
    def msd(S,Q):
        N=n[idx].sum(1); SS=S[idx].sum(1); QQ=Q[idx].sum(1); mu=SS/N
        return mu,np.sqrt(np.maximum((QQ-N*mu*mu)/(N-1.0),0.0))
    ma,da=msd(sa,qa); ms,ds=msd(ss,qs)
    return (ms/ds-ma/da)*np.sqrt(APY), ms-ma
d42=A0["42"]["ts"][sl]//86400
# ---- second seed ----
OUT["second_seed"]={}
for tg in ("R12_CEM_99_neutral","R12_CEM_95_neutral","R12_CEM_99_derisk","R12_CEM_90_neutral",
           "R12_BYP_either_90_a100","R12_BYP_rev_90_a100"):
    row={}
    for s in ("42","2027"):
        tag=f"{tg}_s{s}"
        if not os.path.exists(f"{T}/w10_ablation_series_{tag}.npz"): continue
        S=load(tag); a=A0[s]["g"][sl]; g=S["g"][sl]; dd=A0[s]["ts"][sl]//86400
        D,G=boot(a,g,dd,0)
        row[f"s{s}"]={"dg":float(g.mean()-a.mean()),"dSharpe":sr(g)-sr(a),
                      "ci95":[float(np.percentile(G,2.5)),float(np.percentile(G,97.5))],
                      "ci_bonf29":[float(np.percentile(G,PLO)),float(np.percentile(G,PHI_))],
                      "dturn_frac_pct":float(100*(S["tov"][sl].mean()/A0[s]["tov"][sl].mean()-1))}
    if len(row)==2:
        row["same_sign"]=bool(row["s42"]["dg"]*row["s2027"]["dg"]>0)
    OUT["second_seed"][tg]=row
# ---- nulls ----
OUT["nulls"]={}
for arm in ("R12_CEM_99_neutral_s42","R12_CEM_95_neutral_s42","R12_BYP_either_90_a100_s42"):
    S=load(arm); a=A0["42"]["g"][sl]; true_dg=float(S["g"][sl].mean()-a.mean())
    true_dturn=float(100*(S["tov"][sl].mean()/A0["42"]["tov"][sl].mean()-1))
    ns={}
    for f in sorted(glob.glob(f"{T}/w10_ablation_series_{arm}_NULL_*.npz")):
        nm=os.path.basename(f)[len(f"w10_ablation_series_{arm}_NULL_"):-4]
        N=load(f"{arm}_NULL_{nm}")
        ns[nm]={"dg":float(N["g"][sl].mean()-a.mean()),
                "dturn_frac_pct":float(100*(N["tov"][sl].mean()/A0["42"]["tov"][sl].mean()-1)),
                "fire_n":int((N["DIAG"][:,3]+N["DIAG"][:,6])[sl].sum()) if N["DIAG"] is not None else None}
    vals=np.array([v["dg"] for v in ns.values()])
    OUT["nulls"][arm]={"true_dg":true_dg,"true_dturn_frac_pct":true_dturn,"nulls":ns,
        "n_nulls":len(vals),"null_dg_mean":float(vals.mean()),"null_dg_max":float(vals.max()),
        "n_nulls_beating_true":int((vals>=true_dg).sum()) if true_dg>0 else int((vals<=true_dg).sum()),
        "beats_all_nulls":bool((vals<true_dg).all()) if true_dg>0 else bool((vals>true_dg).all()),
        "turnover_matched":bool(max(abs(v["dturn_frac_pct"]-true_dturn) for v in ns.values())<max(2.0,0.5*abs(true_dturn)))}
print(json.dumps(OUT,indent=1))
json.dump(OUT,open(f"{R}/out/NULLJUDGE.json","w"),indent=1)
print("NULLJUDGE_DONE")
