"""R8/BUILD-1 null comparison. For each tested arm, the SAME in-book construction driven by a null tilt.
Reports BOTH pnl_ex (gross) and g (net) as marginal effects vs A0, and the turnover ratio (null/arm),
which must be ~1 for the null to be turnover-matched."""
import numpy as np, json, calendar, sys, time
sys.path.insert(0,"/workspace/uplift_2026-09-11/r8_inbook")
from fastboot import boot_dsr_dg
APY=2190; WARM=900; B=4000
R="/workspace/uplift_2026-09-11/r8_inbook"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
CEIL=T(2026,8,30,20); FULL_HI=T(2026,8,10,20)
WINS={"FULLCYCLE":(None,FULL_HI),"GIVEBACK":(T(2026,8,19),T(2026,8,21,20))}
def load(path):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec"],float)[WARM:]; ts=np.round(Rr[:,ix["ts"]]).astype(np.int64)
    m=ts<=CEIL; Rr=Rr[m]; ts=ts[m]; gt=Rr[:,ix["gross_total"]]
    return {"ts":ts,"g":Rr[:,ix["net_ex"]]/gt,"pnl":Rr[:,ix["pnl_ex"]]/gt,"turn":Rr[:,ix["turnover"]],
            "cost":Rr[:,ix["cost_ex"]]/gt}
A0=load(R+"/arms/R8_A0_dyn_s42.npz")
ARMS=["R8A_BLEND_010","R8A_BLEND_050","R8B_OVL_100","R8C_GT_025"]
NUL=["RELAB1","RELAB2","RELAB3","SHIFT101","SHIFT503","SHIFT1009"]
OUT={}
for A in ARMS:
    X=load(R+"/arms/%s_dyn_s42.npz"%A)
    o={"arm":{}}
    for wn,(lo,hi) in WINS.items():
        m=(A0["ts"]<=hi)&((A0["ts"]>=lo) if lo else True)
        o["arm"][wn]={"dpnl":float(X["pnl"][m].mean()-A0["pnl"][m].mean()),
                      "dg":float(X["g"][m].mean()-A0["g"][m].mean()),
                      "turn":float(X["turn"][m].mean())}
    o["nulls"]={}
    beat_g={w:0 for w in WINS}; beat_p={w:0 for w in WINS}; tr=[]
    for N in NUL:
        Y=load(R+"/arms/%s_NULL_%s_dyn_s42.npz"%(A,N))
        e={}
        for wn,(lo,hi) in WINS.items():
            m=(A0["ts"]<=hi)&((A0["ts"]>=lo) if lo else True)
            dp=float(Y["pnl"][m].mean()-A0["pnl"][m].mean()); dg=float(Y["g"][m].mean()-A0["g"][m].mean())
            e[wn]={"dpnl":dp,"dg":dg,"turn":float(Y["turn"][m].mean()),
                   "turn_ratio_vs_arm":float(Y["turn"][m].mean()/o["arm"][wn]["turn"])}
            if o["arm"][wn]["dg"]>dg: beat_g[wn]+=1
            if o["arm"][wn]["dpnl"]>dp: beat_p[wn]+=1
            if wn=="FULLCYCLE": tr.append(e[wn]["turn_ratio_vs_arm"])
        o["nulls"][N]=e
    o["beats_nulls_net_g"]={w:"%d/6"%beat_g[w] for w in WINS}
    o["beats_nulls_gross_pnl"]={w:"%d/6"%beat_p[w] for w in WINS}
    o["turn_ratio_range_FULLCYCLE"]=[round(min(tr),4),round(max(tr),4)]
    OUT[A]=o
    print(A,"beats(net)",o["beats_nulls_net_g"],"beats(gross)",o["beats_nulls_gross_pnl"],
          "turn-ratio",o["turn_ratio_range_FULLCYCLE"],flush=True)
    for wn in WINS:
        print("   %-10s arm dpnl %+.5f dg %+.5f | nulls dg: %s"%(wn,o["arm"][wn]["dpnl"],o["arm"][wn]["dg"],
              " ".join("%s %+.4f"%(N,o["nulls"][N][wn]["dg"]) for N in NUL)),flush=True)
json.dump(OUT,open(R+"/NULLS.json","w"),indent=1)
print("NULL_CMP_DONE")
