"""ANGLE 2 cross + fixed-weight-sweep analyser. Same statistic/bootstrap as an.py."""
import numpy as np, json, os, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from an import rd, SPANS, sr, boot, sub, OUT, R
def get(tag,span):
    ts,g,d,ie=rd(OUT+"/%s.npz"%tag); assert ie==0.0
    return sub(ts,g,d,span)
def pair(tA,tB,span,k):
    tsA,gA,dA=get(tA,span); tsB,gB,dB=get(tB,span)
    tc=np.intersect1d(tsA,tsB); iA=np.searchsorted(tsA,tc); iB=np.searchsorted(tsB,tc)
    assert np.array_equal(tsA[iA],tc) and np.array_equal(tsB[iB],tc)
    dg=gB[iB]-gA[iA]
    gr=lambda dd,ii,c: dd[c][ii]/dd["gross_total"][ii]
    return {"n":int(len(tc)),"g_A":round(float(gA[iA].mean()),4),"g_B":round(float(gB[iB].mean()),4),
            "SR_A":round(sr(gA[iA]),4),"SR_B":round(sr(gB[iB]),4),
            "d_g":round(float(dg.mean()),4),"d_g_CI95":boot(dg,tc,k),
            "d_pnl":round(float((gr(dB,iB,"pnl_ex")-gr(dA,iA,"pnl_ex")).mean()),4),
            "d_carry":round(float((gr(dB,iB,"carry_ex")-gr(dA,iA,"carry_ex")).mean()),4),
            "d_cost":round(float((gr(dB,iB,"cost_ex")-gr(dA,iA,"cost_ex")).mean()),4),
            "carry_A":round(float(gr(dA,iA,"carry_ex").mean()),4),"carry_B":round(float(gr(dB,iB,"carry_ex").mean()),4)}
RES={"cross":{},"sweep":{}}
for span in ("2024on_pw","FROZEN_pw","FULL_pw"):
    for sd in ("42","2027"):
        FF="R5A2_APAR_dyn_s%s"%sd; SS="R5A2_ASHIFT101_dyn_s%s"%sd
        SF="R5A2X_SF_s%s"%sd; FS="R5A2X_FS_s%s"%sd
        c={}
        c["TOTAL_SS_vs_FF"]=pair(FF,SS,span,6001)
        c["SCORE_only_SF_vs_FF"]=pair(FF,SF,span,6002)
        c["WEIGHT_only_FS_vs_FF"]=pair(FF,FS,span,6003)
        c["resid_interaction"]=round(c["TOTAL_SS_vs_FF"]["d_g"]-c["SCORE_only_SF_vs_FF"]["d_g"]-c["WEIGHT_only_FS_vs_FF"]["d_g"],4)
        RES["cross"]["%s|s%s"%(span,sd)]=c
KW=["0p0000","0p1000","0p2100","0p3000","0p3568","0p4500","0p6000","0p8000","1p0000"]
for span in ("2024on_pw","FROZEN_pw","FULL_pw"):
    for sd in ("42","2027"):
        row={}
        for j,kw in enumerate(KW):
            A="R5A2X_KW%s_APAR_s%s"%(kw,sd); B="R5A2X_KW%s_ASHIFT101_s%s"%(kw,sd)
            if not (os.path.exists(OUT+"/%s.npz"%A) and os.path.exists(OUT+"/%s.npz"%B)): continue
            row[kw.replace("p",".")]=pair(A,B,span,6100+j)
        # the two real seats for reference
        row["DYN(live rule)"]=pair("R5A2_APAR_dyn_s%s"%sd,"R5A2_ASHIFT101_dyn_s%s"%sd,span,6200)
        row["FIX(W3FIX 0.21)"]=pair("R5A2_APAR_fix_s%s"%sd,"R5A2_ASHIFT101_fix_s%s"%sd,span,6201)
        RES["sweep"]["%s|s%s"%(span,sd)]=row
json.dump(RES,open(R+"/A2_CROSS.json","w"),indent=1)
print("OK")
