"""R3-CRITICAL-1 step B (v2, walk bug fixed): FIT THE IMPACT CONSTANT K from the real order book.

v1 BUG (found and fixed here): a partially-consumed band was charged the midpoint of the WHOLE band
instead of the midpoint of the part actually consumed, so every trade returned exactly 10.0 bps (fine)
/ 50.0 bps (coarse). v2 charges (x_lo + x_end)/2 with x_end = x_lo + taken/density.

Trade caliber VERBATIM from infra1_cost/calib6.py: W = archived A0 d30_n2_c42_W, dW = |diff(W,prepend 0)|,
Q = dW*G, tier by QV4h from meta_newprod_v4, turnover-weighted.
Book: r3k/lobcube.npz, causal mean cumulative notional over [E-3600,E).
+-0.2% band exists only from 2026 (Binance added it) -> FINE = 2026 anchors; COARSE (1% inner band)
runs on everything, for the span comparison.
"""
import numpy as np, json, time, os
R3="/workspace/uplift_2026-09-11/r3k"
LC=np.load(R3+"/lobcube.npz",allow_pickle=True)
cum=LC["cum"]; lts=LC["ts"].astype(np.int64)
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); y4=np.asarray(MT["y4"],float)
QV=np.expm1(np.clip(MT["qvk"],0,30))*48.0
Z=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
W=np.asarray(Z["d30_n2_c42_W"],float); cols=[str(c) for c in Z["cols"]]
rec=np.asarray(Z["d30_n2_c42_rec"],float); rts=rec[:,cols.index("ts")].astype(np.int64)
emap={int(t):i for i,t in enumerate(E)}; ridx=np.array([emap.get(int(t),-1) for t in rts]); assert (ridx>=0).all()
lmap={int(t):i for i,t in enumerate(lts)}; lidx=np.array([lmap.get(int(t),-1) for t in rts])
QVr=QV[ridx]
SIG=np.full(y4.shape[1],np.nan)
for c in range(y4.shape[1]):
    v=y4[:,c]; v=v[np.isfinite(v)]
    if len(v)>200: SIG[c]=float(np.std(v))*1e4
dWs=np.diff(W,axis=0,prepend=np.zeros((1,W.shape[1]))); dW=np.abs(dWs)
TT=np.full(QVr.shape,2,np.int8); TT[QVr>=1e6]=1; TT[QVr>=5e6]=0
HALFSPREAD=np.array([1.0999658777781905,1.638999737554008,2.4344380023739175])
IMP_K1=np.array([0.638144642177287,1.557767793871295,4.5250173304217896])
ASK=[6,7,8,9,10,11]; BID=[5,4,3,2,1,0]
XF=np.array([0.0,0.2,1.0,2.0,3.0,4.0,5.0]); XC=np.array([0.0,1.0,2.0,3.0,4.0,5.0])
def walk(Q,C,X):
    n=len(Q); k=C.shape[1]
    acc=np.zeros(n); rem=Q.copy(); prev=np.zeros(n)
    for j in range(k):
        seg=np.maximum(C[:,j]-prev,0.0)
        take=np.minimum(rem,seg)
        dens=np.where(seg>0, seg/(X[j+1]-X[j]), np.inf)          # notional per % of price
        xend=np.where(np.isfinite(dens)&(dens>0), X[j]+take/np.maximum(dens,1e-300), X[j])
        acc+=take*(X[j]+xend)/2.0
        rem-=take; prev=C[:,j]
    cens=rem>1e-9
    acc=acc+np.where(cens,rem*X[-1],0.0)
    return np.where(Q>0,acc/np.maximum(Q,1e-12)*100.0,np.nan), cens
# ---- self-test of walk on a hand-computable case
_C=np.array([[100.0,200.0,300.0,400.0,500.0,600.0]]); _X=XF
v,_=walk(np.array([50.0]),_C,_X); assert abs(v[0]-100*0.5*(0.2*0.5))<1e-9, v   # half of inner band -> mean dist 0.05% = 5bps
v,_=walk(np.array([100.0]),_C,_X); assert abs(v[0]-10.0)<1e-9, v               # full inner band -> 10 bps
print("walk self-test PASS")
def build(G,mode,rowmask):
    rows=np.where(rowmask&(lidx>=0))[0]
    O={k:[] for k in ("Q","vwap","part","tier","sig","row","cens","dw","z")}
    XX=XF if mode=="fine" else XC
    ca=ASK if mode=="fine" else ASK[1:]; cb=BID if mode=="fine" else BID[1:]
    for i in rows:
        li=lidx[i]; d=dW[i]; s=dWs[i]
        m=(d>1e-12)&np.isfinite(QVr[i])&(QVr[i]>0)
        if not m.any(): continue
        book=cum[li]; sel=np.where(m)[0]; buy=s[sel]>0
        Cb=np.where(buy[:,None],book[sel][:,ca],book[sel][:,cb]).astype(np.float64)
        good=np.isfinite(Cb).all(1)&(Cb[:,0]>0)
        if not good.any(): continue
        sel=sel[good]; Cb=Cb[good]; Q=d[sel]*G
        v,cen=walk(Q,Cb,XX)
        O["Q"].append(Q); O["vwap"].append(v); O["part"].append(Q/QVr[i][sel]); O["tier"].append(TT[i][sel])
        O["sig"].append(SIG[sel]); O["row"].append(np.full(len(sel),i)); O["cens"].append(cen)
        O["dw"].append(d[sel]); O["z"].append(Q/Cb[:,0])
    return {k:(np.concatenate(v) if v else np.array([])) for k,v in O.items()}
def summarise(B,mask_all,label,G):
    w=B["dw"]; out={"label":label,"G":G,"n_trades":int(len(B["Q"])),
        "turnover_coverage":float(w.sum()/dW[mask_all].sum()),
        "censored_frac_turnwtd":float(w[B["cens"]].sum()/w.sum()),
        "frac_turn_inside_inner_band":float(w[B["z"]<=1].sum()/w.sum()),
        "turnwtd_z":float((B["z"]*w).sum()/w.sum()),"p99_z":float(np.percentile(B["z"],99))}
    for t in range(3):
        m=B["tier"]==t
        if m.sum()<50: continue
        ww=w[m]; vw=float((B["vwap"][m]*ww).sum()/ww.sum())
        imp=np.maximum(B["vwap"][m]-HALFSPREAD[t],0.0)
        impw=float((imp*ww).sum()/ww.sum())
        sq=float((np.sqrt(np.clip(B["part"][m],0,None))*B["sig"][m]*ww).sum()/ww.sum())
        out["tier%d"%t]=dict(n=int(m.sum()),turn_share=round(float(ww.sum()/w.sum()),4),
            vwap_bps=round(vw,4),impact_excess_halfspread_bps=round(impw,4),
            participation=float((B["part"][m]*ww).sum()/ww.sum()),
            turnwtd_z=round(float((B["z"][m]*ww).sum()/ww.sum()),5),
            sqrt_law_K1_bps=round(sq,4),infra1_K1_bps=round(float(IMP_K1[t]),4),
            K_fitted_vwap=round(vw/IMP_K1[t],4),K_fitted_excess=round(impw/IMP_K1[t],4))
    vw=float((B["vwap"]*w).sum()/w.sum())
    imp=np.maximum(B["vwap"]-HALFSPREAD[B["tier"]],0.0); impw=float((imp*w).sum()/w.sum())
    ia=float((IMP_K1[B["tier"]]*w).sum()/w.sum())
    out["book_avg"]=dict(vwap_bps=round(vw,4),impact_excess_halfspread_bps=round(impw,4),
        infra1_K1_bps=round(ia,4),K_fitted_vwap=round(vw/ia,4),K_fitted_excess=round(impw/ia,4))
    # power law vs participation
    fits={}
    for lab,mm in [("pooled",np.ones(len(B["Q"]),bool))]+[("tier%d"%t,B["tier"]==t) for t in range(3)]:
        x=np.log(B["part"][mm]); y=np.log(np.maximum(B["vwap"][mm],1e-9)); ww=w[mm]
        ok=np.isfinite(x)&np.isfinite(y)&(ww>0)
        if ok.sum()<100: continue
        X=np.vstack([np.ones(ok.sum()),x[ok]]).T; sw=np.sqrt(ww[ok])
        b,_,_,_=np.linalg.lstsq(X*sw[:,None],y[ok]*sw,rcond=None)
        e=y[ok]-X@b; s2=float((ww[ok]*e**2).sum()/ww[ok].sum())
        V=np.linalg.inv((X*ww[ok][:,None]).T@X)*s2*ww[ok].sum()/ok.sum()
        se=np.sqrt(np.diag(V))
        fits[lab]=dict(alpha=round(float(b[1]),4),alpha_se=round(float(se[1]),4),
                       K_at_p1=round(float(np.exp(b[0])),4),n=int(ok.sum()))
    out["powerlaw_vwap_vs_participation"]=fits
    # block bootstrap (UTC day) on the turnover-weighted book-average K
    rowts=rts[B["row"]]; day=(rowts//86400).astype(np.int64)
    ud,inv=np.unique(day,return_inverse=True); nb=len(ud)
    idxby=[np.where(inv==i)[0] for i in range(nb)]
    rng=np.random.default_rng([20260905,31])
    bs=[]
    for _ in range(2000):
        pick=rng.integers(0,nb,nb); ix=np.concatenate([idxby[i] for i in pick])
        ww=w[ix]; vv=float((B["vwap"][ix]*ww).sum()/ww.sum())
        ii=float((IMP_K1[B["tier"][ix]]*ww).sum()/ww.sum())
        bs.append(vv/ii)
    out["K_fitted_vwap_CI95_dayblock"]=[round(float(np.percentile(bs,2.5)),4),round(float(np.percentile(bs,97.5)),4)]
    out["K_fitted_vwap_boot_sd"]=round(float(np.std(bs)),4)
    out["n_day_blocks"]=nb
    return out
yr=np.array([time.gmtime(int(t)).tm_year for t in rts])
RES={}
m26=(yr==2026); mall=np.ones(len(rts),bool)
RES["FINE2026_G230k"]=summarise(build(230000.0,"fine",m26),m26,"fine 0.2% band, 2026 anchors",230000.0)
print(json.dumps(RES["FINE2026_G230k"],indent=1),flush=True)
RES["COARSE_ALL_G230k"]=summarise(build(230000.0,"coarse",mall),mall,"coarse 1% band, all anchors",230000.0)
print(json.dumps(RES["COARSE_ALL_G230k"],indent=1),flush=True)
RES["COARSE2026_G230k"]=summarise(build(230000.0,"coarse",m26),m26,"coarse 1% band, 2026 anchors (bridge control)",230000.0)
print(json.dumps(RES["COARSE2026_G230k"],indent=1),flush=True)
# capacity sweep: book-average vwap impact vs G, fine band, 2026
CAP={}
for G in (57500.,115000.,230000.,345000.,460000.,690000.,920000.,1380000.,2300000.,4600000.,9200000.,23000000.):
    B=build(G,"fine",m26); w=B["dw"]
    vw=float((B["vwap"]*w).sum()/w.sum())
    imp=np.maximum(B["vwap"]-HALFSPREAD[B["tier"]],0.0)
    CAP["%d"%int(G)]=dict(vwap_bps=round(vw,4),excess_bps=round(float((imp*w).sum()/w.sum()),4),
        frac_inside_inner=round(float(w[B["z"]<=1].sum()/w.sum()),4),
        censored=round(float(w[B["cens"]].sum()/w.sum()),5),
        turnwtd_z=round(float((B["z"]*w).sum()/w.sum()),5))
    print("G=%10.0f  vwap %.4f bps  excess %.4f  inside_inner %.4f"%(G,vw,CAP["%d"%int(G)]["excess_bps"],CAP["%d"%int(G)]["frac_inside_inner"]),flush=True)
RES["capacity_sweep_fine2026"]=CAP
json.dump(RES,open(R3+"/FITK_v2.json","w"),indent=1)
print("WROTE",R3+"/FITK_v2.json")
