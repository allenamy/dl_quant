"""r21_repro.py -- GATE G-A1 (PREREG_r21 SS A1): reproduce the six null numbers of NULLJUDGE.json from the ARCHIVED
r12 series with the VERBATIM r12_nulljudge.py formulas. ENV whitelist = EMPTY SET (asserted). Runs on pod2."""
import os, json, time, hashlib, glob
assert not any(k in os.environ for k in ("CAL","PHI","CEM_Q","BYP_STATE","LEGS","FTRIM","R12_NULL","R21_DOSE","FSEED","FPRED")), "env not empty"
import numpy as np
U="/workspace/uplift_2026-09-11"; R12=f"{U}/r12_intervene"; T=f"{R12}/dev_ext/probe_artifacts"; R21=f"{U}/r21_nulls_costbridge"
os.makedirs(f"{R21}/out",exist_ok=True)
PREREG_SHA="c4de6df3a37483462d4e10373c30ea4137c02c78f9a23e06148007c5ce246232"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<24),b""): h.update(c)
    return h.hexdigest()
assert sha(f"{R21}/PREREG_r21_2026-09-12.md")==PREREG_SHA, "PREREG sha mismatch"
REC=json.load(open(f"{R12}/out/NULLJUDGE.json"))
assert sha(f"{R12}/out/NULLJUDGE.json")=="e39323b0e11d0994bd51b7450efeaf710f3da4b080202d7192e5c47b5b081997"
WARM=900; RATE=2.9537; sl=slice(WARM,None)
def load(tag):
    Z=np.load(f"{T}/w10_ablation_series_{tag}.npz",allow_pickle=True)
    cols=[str(c) for c in Z["cols"]]; C={k:i for i,k in enumerate(cols)}
    Rr=np.asarray(Z["d30_n2_c42_rec"],float); gt=Rr[:,C["gross_total"]]
    D=np.asarray(Z["d30_n2_c42_DIAG"],float) if "d30_n2_c42_DIAG" in Z.files else None
    return {"ts":np.round(Rr[:,C["ts"]]).astype(np.int64),"g":Rr[:,C["net_ex"]]/gt,"tov":Rr[:,C["cost_ex"]]/gt/RATE,
            "tovf":Rr[:,C["turnover"]]/gt,"DIAG":D,"n":len(Rr)}
A0=load("R12B_GATEP_s42")
OUT={"prereg_sha256":PREREG_SHA,"env_whitelist":[],"read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"arms":{}}
worst=0.0
for arm in ("R12_CEM_99_neutral_s42","R12_CEM_95_neutral_s42","R12_BYP_either_90_a100_s42"):
    S=load(arm); true_dg=float(S["g"][sl].mean()-A0["g"][sl].mean()); true_dt=float(100*(S["tov"][sl].mean()/A0["tov"][sl].mean()-1))
    rec=REC["nulls"][arm]; row={"true_dg":true_dg,"true_dturn_frac_pct":true_dt,"true_dturn_file_caliber_pct":float(100*(S["tovf"][sl].mean()/A0["tovf"][sl].mean()-1)),
        "receipt_true_dg":rec["true_dg"],"receipt_true_dturn":rec["true_dturn_frac_pct"],"nulls":{}}
    worst=max(worst,abs(true_dg-rec["true_dg"]),abs(true_dt-rec["true_dturn_frac_pct"]))
    for nm,rv in rec["nulls"].items():
        N=load(f"{arm}_NULL_{nm}")
        dg=float(N["g"][sl].mean()-A0["g"][sl].mean()); dt=float(100*(N["tov"][sl].mean()/A0["tov"][sl].mean()-1))
        fn=int((N["DIAG"][:,3]+N["DIAG"][:,6])[sl].sum())
        rel=abs(dt-true_dt)/abs(true_dt) if true_dt!=0 else float("nan")
        row["nulls"][nm]={"dg":dg,"dturn_frac_pct":dt,"fire_n":fn,"dturn_file_caliber_pct":float(100*(N["tovf"][sl].mean()/A0["tovf"][sl].mean()-1)),
            "receipt":rv,"abs_diff_dg":abs(dg-rv["dg"]),"abs_diff_dturn":abs(dt-rv["dturn_frac_pct"]),"fire_match":fn==rv["fire_n"],
            "rel_turnover_mismatch":rel,"fire_diff":fn-int((S["DIAG"][:,3]+S["DIAG"][:,6])[sl].sum())}
        worst=max(worst,abs(dg-rv["dg"]),abs(dt-rv["dturn_frac_pct"]))
        assert fn==rv["fire_n"], (arm,nm,fn,rv["fire_n"])
    rels=[v["rel_turnover_mismatch"] for v in row["nulls"].values()]
    row["max_rel_turnover_mismatch"]=max(rels); row["receipt_flag_turnover_matched"]=rec["turnover_matched"]
    row["receipt_rule"]="max|dturn_null-dturn_true| < max(2.0, 0.5*|dturn_true|)  (r12_nulljudge.py L?, ABSOLUTE 2.0 pp floor)"
    row["rule_1pct_relative_holds"]=bool(max(rels)<=0.01)
    row["rule_fire_pm1_holds"]=bool(all(abs(v["fire_diff"])<=1 for v in row["nulls"].values()))
    OUT["arms"][arm]=row
OUT["worst_abs_diff_vs_receipt"]=worst; OUT["G_A1_PASS"]=bool(worst<1e-9)
json.dump(OUT,open(f"{R21}/out/REPRO_A1.json","w"),indent=1)
print(json.dumps({"G_A1_PASS":OUT["G_A1_PASS"],"worst":worst},indent=1))
for arm,row in OUT["arms"].items():
    print(arm,"true dturn %.6f"%row["true_dturn_frac_pct"],"max rel mismatch %.4f"%row["max_rel_turnover_mismatch"],"1pct holds",row["rule_1pct_relative_holds"],"fire+-1",row["rule_fire_pm1_holds"],"receipt flag",row["receipt_flag_turnover_matched"])
    for nm,v in row["nulls"].items(): print("   %-10s dturn %.6f rel %.4f fire %d dg %.6f"%(nm,v["dturn_frac_pct"],v["rel_turnover_mismatch"],v["fire_n"],v["dg"]))
print("REPRO_DONE")
