"""r10 G4: S5 offset spectrum on the PINNED RAW target meta_newprod_v4.y4 (E-0904-F caliber:
pod 5m lineage y4 = SUM of 5-minute simple returns; NO expm1). corr(signal rank @ anchor i,
y4 @ anchor i+k), k=-3..+4, computed on the PINNED post-warm axis (n=9138)."""
import numpy as np, sys, calendar, json, hashlib, os
ENV_WL=["CAL","LEGS","PHI","FTRIM","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ",
 "COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","EXPORT_PANEL","EMA_STATE_JSON",
 "PANEL_IN","JUDGE_HC","TILT","TILT_TAU","TILT_K"]
assert not [k for k in ENV_WL if k in os.environ]
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
from scipy.stats import rankdata
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
W10="/workspace/uplift_2026-09-11/r10_slowclock"
MP="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
MT=np.load(MP,allow_pickle=True); E=MT["E_ts"].astype(np.int64); Y=np.asarray(MT["y4"],np.float64)
rmap={int(t):k for k,t in enumerate(E)}
F1=np.load(R+"/feats_r2.npz",allow_pickle=True); F2=np.load(R+"/feats_r2b.npz",allow_pickle=True)
g1=lambda k: np.asarray(F1[k],np.float64); g2=lambda k: np.asarray(F2[k],np.float64)
IVf=np.where(np.isfinite(PW["f_fund_iv"])&(np.asarray(PW["f_fund_iv"])>0),np.asarray(PW["f_fund_iv"],np.float64),8.0)
RN8=np.nan_to_num(np.asarray(PW["f_fund_now"],np.float64),nan=0.0)*(8.0/IVf)
RN8=np.where(np.isfinite(np.asarray(PW["f_fund_now"])),RN8,np.nan)
FE2=np.asarray(PW["f_fund_ema_v2"],np.float64)
def lagrank(Z,L):
    o=np.full(Z.shape,np.nan); o[L:]=Z[:-L]; return o
ZRN=ZR(RN8)
SIG={
 "ORTH_C_TBF3D":  orth(g1("TBF_MEAN_864")),
 "ORTH_C_TBF7D":  orth(g2("TBF_MEAN_2016")),
 "ORTH_C_TBF14D": orth(g2("TBF_MEAN_4032")),
 "ORTH_C_TBF30D": orth(g2("TBF_MEAN_8640")),
 "ORTH_B_TBF12H": orth(g1("TBF_MEAN_144")),
 "ORTH_D_FCHG3D_m": -orth(ZRN-lagrank(ZRN,18)),
 "ORTH_C_AMI3D":  orth(g1("RET_MABS_864")/np.exp(g1("LQV_MEAN_864"))),
 "FUND_deployed": ZF,
}
# pinned axis
WARM=900; CUT=T(2026,8,30,20)
idx=np.arange(len(TS))[WARM:]; idx=idx[TS[idx]<=CUT]
assert len(idx)==9138, len(idx)
ri=np.array([rmap.get(int(t),-1) for t in TS])
KS=[-3,-2,-1,0,1,2,3,4]
OUT={"target_file":MP,"target_sha16":hashlib.sha256(open(MP,'rb').read(1<<20)).hexdigest()[:16],
     "target_caliber":"meta_newprod_v4.y4 = RAW v4 accounting target, pod 5m lineage (sum of 5m simple returns, no expm1)",
     "axis_n":int(len(idx)),"ks":KS,"spectrum":{}}
print("%-18s"%"signal"+"".join("%10s"%("k=%+d"%k) for k in KS),flush=True)
for nm,S in SIG.items():
    Zs=ZR(S) if nm!="FUND_deployed" else S
    row=[]
    for k in KS:
        cs=[]
        for i in idx:
            ii=i+k
            if ii<0 or ii>=len(TS) or ri[ii]<0: continue
            a=Zs[i]; b=Y[ri[ii]]
            m=np.isfinite(a)&np.isfinite(b)
            if m.sum()>50: cs.append(np.corrcoef(rankdata(a[m]),rankdata(b[m]))[0,1])
        row.append(round(float(np.mean(cs)),5))
    OUT["spectrum"][nm]=dict(zip(["k%+d"%k for k in KS],row))
    i0=KS.index(0); im1=KS.index(-1)
    OUT["spectrum"][nm]["ratio_bwd_over_fwd"]=round(row[im1]/row[i0],3) if row[i0]!=0 else None
    OUT["spectrum"][nm]["S5_PASS_peak_at_k0_and_fwd>=bwd"]=bool(row[i0]>=row[im1] and row[i0]==max(row))
    print("%-18s"%nm+"".join("%+10.5f"%v for v in row),flush=True)
json.dump(OUT,open(W10+"/rc/OFFSPEC.json","w"),indent=1)
print("WROTE OFFSPEC.json")
