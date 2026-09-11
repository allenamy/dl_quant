"""R8/BUILD-1 battery.  Windows / statistics / K frozen by PREREG_r8 sha 83f4bed0...
g = net_ex/gross_total (bps/anchor/unit gross).  Paired per anchor vs the SAME-cell A0.
Bootstrap = UTC-day blocks, default_rng([20260905,k]), k in {0,9}, B=4000; closed-form evaluation
validated to 3e-16 against the round-5 loop (VALIDATE_FASTBOOT.json).
Bonferroni K=13 two-sided alpha=0.05/13 -> percentiles 0.192308 / 99.807692."""
import numpy as np, json, calendar, glob, os, sys, hashlib, time
sys.path.insert(0,"/workspace/uplift_2026-09-11/r8_inbook")
from fastboot import boot_dsr_dg
APY=2190; WARM=900; B_BOOT=4000; KDECL=13
PLO=100*(0.05/KDECL)/2; PHI_=100-PLO
R="/workspace/uplift_2026-09-11/r8_inbook"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
CEIL=T(2026,8,30,20); FULL_HI=T(2026,8,10,20)
WINS={"FULLCYCLE":(None,FULL_HI),"EXT":(T(2026,8,11),CEIL),"GIVEBACK":(T(2026,8,19),T(2026,8,21,20)),
      "FROZEN":(T(2025,3,1),FULL_HI),"FULL_TO_CEIL":(None,CEIL)}
BOOTW=("FULLCYCLE","EXT","GIVEBACK")
def load(path):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec"],float)[WARM:]
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<=CEIL; Rr=Rr[m]; ts=ts[m]
    gt=Rr[:,ix["gross_total"]]
    return {"ts":ts,"g":Rr[:,ix["net_ex"]]/gt,"carry":-Rr[:,ix["carry_ex"]]/gt,
            "pnl":Rr[:,ix["pnl_ex"]]/gt,"cost":Rr[:,ix["cost_ex"]]/gt,
            "turn":Rr[:,ix["turnover"]],"gross":gt,"netlong":np.abs(Rr[:,ix["netlong"]])}
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def cis(v): return {"ci95":[float(np.percentile(v,2.5)),float(np.percentile(v,97.5))],
                    "ci_bonf13":[float(np.percentile(v,PLO)),float(np.percentile(v,PHI_))]}
A0FILE=sys.argv[1]; PAT=sys.argv[2]; TAGSUF=sys.argv[3]
A0=load(A0FILE)
OUT={"prereg_sha256":"83f4bed01cd90f9f415e0d2a89e173fb23ff8c89c2567633a99c923ddea03c8e",
     "self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest()[:16],
     "A0_file":A0FILE,"K_declared":KDECL,"B":B_BOOT,"coverage_ceiling":"2026-08-30 20:00Z",
     "read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"A0":{},"arms":{}}
for wn,(lo,hi) in WINS.items():
    m=(A0["ts"]<=hi)&((A0["ts"]>=lo) if lo else True)
    OUT["A0"][wn]={"n":int(m.sum()),"SR":sr(A0["g"][m]),"mean_g":float(A0["g"][m].mean()),
                   "mean_pnl":float(A0["pnl"][m].mean()),"mean_cost":float(A0["cost"][m].mean()),
                   "mean_carry":float(A0["carry"][m].mean()),"turnover":float(A0["turn"][m].mean())}
print("A0 "+json.dumps({k:{kk:round(vv,5) for kk,vv in v.items()} for k,v in OUT["A0"].items()}),flush=True)
yrs=np.array([time.gmtime(int(t)).tm_year for t in A0["ts"]])
for p in sorted(glob.glob(R+"/arms/%s.npz"%PAT)):
    tag=os.path.basename(p)[:-4]
    if tag.startswith("R8_A0"): continue
    S=load(p)
    assert np.array_equal(S["ts"],A0["ts"]), tag+" ts axis mismatch"
    d={}
    for wn,(lo,hi) in WINS.items():
        m=(A0["ts"]<=hi)&((A0["ts"]>=lo) if lo else True)
        a=A0["g"][m]; s=S["g"][m]; days=A0["ts"][m]//86400
        row={"n":int(m.sum()),"SR":sr(s),"dSharpe":sr(s)-sr(a),
             "mean_g":float(s.mean()),"dg":float(s.mean()-a.mean()),
             "dpnl":float(S["pnl"][m].mean()-A0["pnl"][m].mean()),
             "dcost":float(S["cost"][m].mean()-A0["cost"][m].mean()),
             "dcarry":float(S["carry"][m].mean()-A0["carry"][m].mean()),
             "turnover":float(S["turn"][m].mean()),
             "dturn":float(S["turn"][m].mean()-A0["turn"][m].mean()),
             "dturn_frac":float(S["turn"][m].mean()/A0["turn"][m].mean()-1.0),
             "rho_to_A0":float(np.corrcoef(a,s)[0,1])}
        row["identity_resid"]=float((row["dpnl"]-row["dcarry"]-row["dcost"])-row["dg"])
        row["cost_surv_frac"]=float(1-row["dcost"]/row["dpnl"]) if row["dpnl"]>1e-12 else None
        row["dnav_bps_per_year_at_2x"]=float(row["dg"]*2190*2.0)
        if wn in BOOTW:
            for k in (0,9):
                D,G=boot_dsr_dg(a,s,days,k,B_BOOT)
                row["dSharpe_k%d"%k]=cis(D); row["dg_k%d"%k]=cis(G)
        d[wn]=row
    mfull=(A0["ts"]<=FULL_HI)
    d["by_year_dg"]={str(y):round(float(S["g"][(yrs==y)&mfull].mean()-A0["g"][(yrs==y)&mfull].mean()),5)
                     for y in range(2022,2027) if ((yrs==y)&mfull).sum()>50}
    d["by_year_dSharpe"]={str(y):round(sr(S["g"][(yrs==y)&mfull])-sr(A0["g"][(yrs==y)&mfull]),3)
                     for y in range(2022,2027) if ((yrs==y)&mfull).sum()>50}
    OUT["arms"][tag]=d
    f=d["FULLCYCLE"]
    print("%-26s n=%d SR %.4f dSR %+.4f[%+.4f,%+.4f] dg %+.5f[%+.5f,%+.5f] dturn %+.2f%% dpnl %+.5f dcost %+.5f surv %s"%(
        tag,f["n"],f["SR"],f["dSharpe"],f["dSharpe_k0"]["ci_bonf13"][0],f["dSharpe_k0"]["ci_bonf13"][1],
        f["dg"],f["dg_k0"]["ci_bonf13"][0],f["dg_k0"]["ci_bonf13"][1],
        100*f["dturn_frac"],f["dpnl"],f["dcost"],
        ("%.1f%%"%(100*f["cost_surv_frac"])) if f["cost_surv_frac"] is not None else "N/A"),flush=True)
json.dump(OUT,open(R+"/BATTERY_%s.json"%TAGSUF,"w"),indent=1)
print("BATTERY_DONE")
