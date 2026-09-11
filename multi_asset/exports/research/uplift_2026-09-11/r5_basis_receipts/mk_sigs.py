"""R5/ND1 step 2: UNITS GATE + raw basis columns + orthogonalised sleeve signals.
Signal chain is VERBATIM p6_book.py mk() (= the admitted Amihud sleeve ORTHLAGA), proven identical by GATE S.
Only the raw matrix changes."""
import numpy as np, json, os
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r5_basis"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BM=np.isfinite(FE1)
FN=np.asarray(PW["f_fund_now"],float); IV=np.asarray(PW["f_fund_iv"],float)
BP=np.load(R+"/basis_panel.npz",allow_pickle=True)
assert np.array_equal(BP["ts"].astype(np.int64),ts) and [str(x) for x in BP["symbols"]]==[str(x) for x in sym]
p_last=np.asarray(BP["p_last"],float); p_tw8=np.asarray(BP["p_tw8"],float)
p_tw24=np.asarray(BP["p_tw24"],float); p_sd8=np.asarray(BP["p_sd8"],float); p_tw_iv=np.asarray(BP["p_tw_iv"],float)
# ---------------- UNITS GATE (E-0904-G: scripted, never hand-derived) ----------------
sl=[]; r2=[]
for i in range(len(ts)):
    ok=BM[i]&np.isfinite(FN[i])&np.isfinite(p_tw_iv[i])
    if ok.sum()<30: continue
    x=p_tw_iv[i][ok]; y=FN[i][ok]
    vx=float((x*x).sum())
    if vx<=1e-18: continue
    b=float((x*y).sum()/vx); sl.append(b)
    ss=float(((y-b*x)**2).sum()); tt=float((y*y).sum())
    r2.append(1.0-ss/tt if tt>1e-24 else np.nan)
sl=np.array(sl); r2=np.array(r2)
UG={"n_anchors":int(len(sl)),"slope_median":float(np.nanmedian(sl)),
    "slope_p10":float(np.nanpercentile(sl,10)),"slope_p90":float(np.nanpercentile(sl,90)),
    "r2_median":float(np.nanmedian(r2)),"r2_p10":float(np.nanpercentile(r2,10)),
    "PASS":bool(0.7<=np.nanmedian(sl)<=1.3 and np.nanmedian(r2)>=0.5)}
print("UNITS_GATE",json.dumps(UG),flush=True)
json.dump(UG,open(R+"/UNITS_GATE.json","w"),indent=1)
# ---------------- raw columns ----------------
RAW={"BLEVEL": p_last.copy(), "BGAPF": p_last-FN, "BGAPT": p_last-p_tw_iv, "BSLOPE": p_last-p_tw24, "BDISP": p_sd8}
for k,v in RAW.items():
    print("raw",k,"finite on fund-mask %.4f"%float(np.isfinite(v[BM]).mean()),flush=True)
# ---------------- signal chain (VERBATIM p6_book.py) ----------------
def rz_avg(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
ZF=rz_avg(np.where(BM,FE1,np.nan))
def mk(RAWM,lag):
    ZA=rz_avg(np.where(BM,np.asarray(RAWM,float),np.nan))
    if lag:
        ZL=np.full_like(ZA,np.nan); ZL[1:]=ZA[:-1]; ZL=np.where(BM,ZL,np.nan)
    else:
        ZL=ZA
    Rr=np.full(ZL.shape,np.nan)
    for i in range(ZL.shape[0]):
        ok=np.isfinite(ZL[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=ZL[i][ok]
        vx=float((x*x).sum()); b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
os.makedirs(R+"/dev/sig",exist_ok=True)
MAN={}
for k,v in RAW.items():
    for lg,tag in ((1,"LAG"),(0,"NOLAG")):
        S=mk(v,lg); p=R+"/dev/sig/R5_%s_%s.npz"%(k,tag)
        np.savez(p,symbols=sym,ts=ts,mat=S.astype(np.float32))
        # residual orthogonality check
        rr=[]
        for i in range(0,len(ts),50):
            ok=np.isfinite(S[i])&np.isfinite(ZF[i])
            if ok.sum()>30: rr.append(abs(float(np.corrcoef(S[i][ok],ZF[i][ok])[0,1])))
        MAN["%s_%s"%(k,tag)]={"path":p,"finite":round(float(np.isfinite(S).mean()),4),
                              "max_abs_resid_corr_to_ZF":round(float(np.nanmax(rr)),8)}
        print("sig","%s_%s"%(k,tag),json.dumps(MAN["%s_%s"%(k,tag)]),flush=True)
json.dump(MAN,open(R+"/SIG_MANIFEST.json","w"),indent=1)
print("MK_SIGS_DONE")
