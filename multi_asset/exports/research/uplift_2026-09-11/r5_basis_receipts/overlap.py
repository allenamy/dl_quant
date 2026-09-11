"""R5/ND1: is the basis signal NEW INFORMATION or the existing reversal leg in disguise?
Per-anchor rank correlation of each candidate raw column against the panel columns the book ALREADY has."""
import numpy as np, json
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r5_basis"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64)
FE1=np.asarray(PW["f_fund_ema_v1"],float); BM=np.isfinite(FE1); FN=np.asarray(PW["f_fund_now"],float)
BP=np.load(R+"/basis_panel.npz",allow_pickle=True)
p_last=np.asarray(BP["p_last"],float); p_tw24=np.asarray(BP["p_tw24"],float)
p_sd8=np.asarray(BP["p_sd8"],float); p_tw_iv=np.asarray(BP["p_tw_iv"],float)
MINE={"BLEVEL":p_last,"BGAPF":p_last-FN,"BGAPT":p_last-p_tw_iv,"BSLOPE":p_last-p_tw24,"BDISP":p_sd8}
HAVE={"f_rev_4h":np.asarray(PW["f_rev_4h"],float),"f_rev_24h":np.asarray(PW["f_rev_24h"],float),
      "f_rev_3d":np.asarray(PW["f_rev_3d"],float),"f_fund_ema_v1":FE1,"f_fund_now":FN,
      "f_vol_7d":np.asarray(PW["f_vol_7d"],float),"f_amihud_24h":np.asarray(PW["f_amihud_24h"],float),
      "f_range_24h":np.asarray(PW["f_range_24h"],float),"f_volq_ratio":np.asarray(PW["f_volq_ratio"],float),
      "f_cpos_24h":np.asarray(PW["f_cpos_24h"],float)}
def rz(v):
    ok=np.isfinite(v); o=np.full(len(v),np.nan)
    if ok.sum()>=30: o[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return o
OUT={}
for a,MA in MINE.items():
    OUT[a]={}
    for b,MB in HAVE.items():
        v=[]
        for i in range(0,len(ts),7):
            x=rz(np.where(BM[i],MA[i],np.nan)); y=rz(np.where(BM[i],MB[i],np.nan))
            ok=np.isfinite(x)&np.isfinite(y)
            if ok.sum()<50: continue
            sx=x[ok].std(); sy=y[ok].std()
            if sx<1e-12 or sy<1e-12: continue
            v.append(float(((x[ok]-x[ok].mean())*(y[ok]-y[ok].mean())).mean()/(sx*sy)))
        OUT[a][b]=round(float(np.mean(v)),4) if v else None
    print(a,json.dumps(OUT[a]),flush=True)
json.dump(OUT,open(R+"/OVERLAP.json","w"),indent=1)
print("OVERLAP_DONE")
