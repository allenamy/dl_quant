"""R3-CRITICAL-1 step C (v2): live-fill cross-check with the confounders controlled.
v1 gave slope 307.6 +- 92.7 bps per unit z against a book-walk prediction of 9.5. Before believing
that, control for the two things that co-move with z: (i) the HALF-SPREAD (thin names have both big z
and wide spreads, and taker slip mechanically contains the half-spread), (ii) name-level idiosyncratic
vol. Then trim, bootstrap BY ANCHOR (not by row), and check the z-support overlap with the replay.
"""
import numpy as np, json
R3="/workspace/uplift_2026-09-11/r3k"
LC=np.load(R3+"/lobcube.npz",allow_pickle=True)
cum=LC["cum"]; lts=LC["ts"].astype(np.int64); lsym=[str(s) for s in LC["symbols"]]
SI={s:i for i,s in enumerate(lsym)}; LT={int(t):i for i,t in enumerate(lts)}
R=json.load(open("/workspace/uplift_2026-09-11/infra1_cost/fill_cost_rows.json"))["rows"]
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); QV=np.expm1(np.clip(MT["qvk"],0,30))*48.0
y4=np.asarray(MT["y4"],float)
SIG=np.full(y4.shape[1],np.nan)
for c in range(y4.shape[1]):
    v=y4[:,c]; v=v[np.isfinite(v)]
    if len(v)>200: SIG[c]=float(np.std(v))*1e4
EM={int(t):i for i,t in enumerate(E)}
g4=lambda ts:int(np.floor(ts/14400.0)*14400)
rows=[]
for r in R:
    if not (r["tk_nz"]>0 and r["tk_slip_cov"]>0 and r["tk_slip_bps"] is not None): continue
    k=g4(r["anchor_ts"]); ci=SI.get(r["symbol"]); li=LT.get(k)
    if ci is None or li is None: continue
    b=cum[li,ci]; a02=np.nanmean([b[6],b[5]])
    if not np.isfinite(a02) or a02<=0: continue
    ej=EM.get(k); qv=float(QV[ej,ci]) if ej is not None and np.isfinite(QV[ej,ci]) else np.nan
    rows.append((k,r["tk_nz"],r["tk_slip_bps"],float(a02),
                 r["spread_bps"] if r["spread_bps"] is not None else np.nan, qv, float(SIG[ci]) if np.isfinite(SIG[ci]) else np.nan))
A=np.array([x[0] for x in rows]); NZ=np.array([x[1] for x in rows]); SL=np.array([x[2] for x in rows])
D02=np.array([x[3] for x in rows]); SP=np.array([x[4] for x in rows]); QVr=np.array([x[5] for x in rows])
SG=np.array([x[6] for x in rows])
Zs=NZ/D02
ua,inv=np.unique(A,return_inverse=True)
def demean(v,w):
    out=np.full(len(v),np.nan)
    for i in range(len(ua)):
        m=inv==i
        if m.sum()<2: continue
        vv=v[m]; ww=w[m]; ok=np.isfinite(vv)
        if ok.sum()<2: continue
        out[np.where(m)[0][ok]]=vv[ok]-np.sum(vv[ok]*ww[ok])/np.sum(ww[ok])
    return out
def wls(X,y,w):
    sw=np.sqrt(w); b,_,_,_=np.linalg.lstsq(X*sw[:,None],y*sw,rcond=None)
    e=y-X@b; s2=float((w*e**2).sum()/w.sum()); V=np.linalg.inv((X*w[:,None]).T@X)*s2*w.sum()/len(y)
    return b,np.sqrt(np.diag(V))
def fit(sel,cols,label,boot=True):
    ds=demean(SL,NZ)
    regs=[demean(Zs,NZ)]
    names=["z"]
    if "spread" in cols: regs.append(demean(SP/2.0,NZ)); names.append("halfspread")
    if "sigma" in cols: regs.append(demean(SG,NZ)); names.append("sigma4h")
    M=np.vstack([np.ones(len(ds))]+regs).T
    ok=np.isfinite(ds)&np.isfinite(M).all(1)&sel
    if ok.sum()<50: return None
    b,se=wls(M[ok],ds[ok],NZ[ok])
    out=dict(label=label,n=int(ok.sum()),n_anchors=int(len(np.unique(A[ok]))),
             coef={nm:round(float(x),3) for nm,x in zip(["const"]+names,b)},
             se={nm:round(float(x),3) for nm,x in zip(["const"]+names,se)})
    if boot:
        uu=np.unique(A[ok]); idx={a:np.where(ok&(A==a))[0] for a in uu}
        rng=np.random.default_rng([20260905,77]); bs=[]
        for _ in range(2000):
            pick=rng.integers(0,len(uu),len(uu))
            ix=np.concatenate([idx[uu[i]] for i in pick])
            try:
                bb,_=wls(M[ix],ds[ix],NZ[ix]); bs.append(bb[1])
            except Exception: pass
        out["z_slope_anchorboot_CI95"]=[round(float(np.percentile(bs,2.5)),2),round(float(np.percentile(bs,97.5)),2)]
        out["z_slope_anchorboot_sd"]=round(float(np.std(bs)),2)
    return out
OUT={"n_rows":len(rows),"n_anchors":int(len(ua)),"taker_notional":float(NZ.sum()),
     "z_support":{"median":float(np.median(Zs)),"p90":float(np.percentile(Zs,90)),
                  "p99":float(np.percentile(Zs,99)),"max":float(Zs.max()),
                  "turnwtd":float((Zs*NZ).sum()/NZ.sum())},
     "replay_turnwtd_z_at_G230k":0.1592928508097196,
     "replay_tier2_turnwtd_z_at_G230k":0.22395}
allsel=np.ones(len(rows),bool)
OUT["fit_z_only"]=fit(allsel,[],"anchor-FE, z only")
OUT["fit_z_plus_spread"]=fit(allsel,["spread"],"anchor-FE, z + half-spread")
OUT["fit_z_plus_spread_sigma"]=fit(allsel,["spread","sigma"],"anchor-FE, z + half-spread + sigma4h")
q99=np.percentile(Zs,99); q95=np.percentile(Zs,95)
OUT["fit_trim99"]=fit(Zs<=q99,["spread"],"anchor-FE, z + half-spread, z<=p99")
OUT["fit_trim95"]=fit(Zs<=q95,["spread"],"anchor-FE, z + half-spread, z<=p95")
OUT["bookwalk_prediction_slope_bps_per_z"]=9.5
json.dump(OUT,open(R3+"/LIVECHECK2.json","w"),indent=1)
print(json.dumps(OUT,indent=1))
