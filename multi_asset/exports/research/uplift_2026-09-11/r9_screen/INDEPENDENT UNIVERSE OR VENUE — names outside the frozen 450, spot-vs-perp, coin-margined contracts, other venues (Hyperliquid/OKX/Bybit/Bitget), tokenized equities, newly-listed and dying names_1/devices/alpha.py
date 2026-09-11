"""What a cross-venue data vendor would actually buy: the OKX book's return NOT explained by
A0 and by the same-universe Binance book. Block-bootstrapped OLS intercept (not the residual mean,
which is zero by construction). ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, json
OUT="/workspace/r9okx"; A0B="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/"; MINE=f"{OUT}/dev/probe_artifacts/"
CAP=1788120000
def ser(p,key="d30_n2_c42_rec"):
    a=np.load(p,allow_pickle=True); ci={str(c):i for i,c in enumerate(a["cols"])}; r=a[key]
    ts=r[:,ci["ts"]].astype(np.int64); gt=r[:,ci["gross_total"]]
    return ts, r[:,ci["net_ex"]]/np.where(gt>0,gt,np.nan)
fe=np.load(f"{OUT}/fe_mats.npz",allow_pickle=True); LO=int(fe["okx_t0"])+14*86400
tA,gA=ser(A0B+"w10_ablation_series_V4_A0_dyn_s42.npz")
tO,gO=ser(MINE+"w10_ablation_series_R9_OKX_fund.npz")
t3,g3=ser(MINE+"w10_ablation_series_R9_BINCOLD388_fund.npz")
mA={int(t):v for t,v in zip(tA,gA)}; m3={int(t):v for t,v in zip(t3,g3)}
TS=np.array([int(t) for t in tO if LO<=int(t)<=CAP and int(t) in mA and int(t) in m3])
y=np.array([dict(zip([int(t) for t in tO],gO))[t] for t in TS]); a0=np.array([mA[t] for t in TS]); b3=np.array([m3[t] for t in TS])
ok=np.isfinite(y)&np.isfinite(a0)&np.isfinite(b3); TS,y,a0,b3=TS[ok],y[ok],a0[ok],b3[ok]
def blocks(ts):
    d=ts//86400; u,inv=np.unique(d,return_inverse=True); return [np.where(inv==k)[0] for k in range(len(u))]
def fit(y,X): return np.linalg.lstsq(X,y,rcond=None)[0]
def run(cols,names):
    X=np.column_stack([np.ones(len(TS))]+cols)
    b=fit(y,X); bl=blocks(TS); nb=len(bl); B=2000; out=np.empty(B)
    for k in range(B):
        rng=np.random.default_rng([20260905,k]); idx=np.concatenate([bl[p] for p in rng.integers(0,nb,nb)])
        out[k]=fit(y[idx],X[idx])[0]
    return {"regressors":names,"alpha_bps_per_anchor":round(float(b[0]),4),
            "ci95_alpha":[round(float(np.percentile(out,2.5)),4),round(float(np.percentile(out,97.5)),4)],
            "betas":{n:round(float(v),4) for n,v in zip(names,b[1:])},
            "R2":round(float(1-((y-X@b).var()/y.var())),4)}
res={"n":int(len(TS)),
     "raw_mean_g_OKX":round(float(y.mean()),4),
     "alpha_vs_A0_only":run([a0],["A0"]),
     "alpha_vs_A0_and_BIN388":run([a0,b3],["A0","BIN388"]),
     "alpha_vs_BIN388_only":run([b3],["BIN388"])}
print(json.dumps(res,indent=1)); json.dump(res,open(f"{OUT}/RESULT_alpha.json","w"),indent=1)
