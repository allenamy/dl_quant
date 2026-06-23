"""F3 GATE — Book dynamics & churn family.

Tests whether engineered book-dynamics features (bkAdd/bkDel churn, multi-level
OFI Cont-Kukanov-Stoikov, depth-weighted imbalance dynamics, queue-imbalance
change) add per-asset signal beyond the existing 44 hand features.

Strictly causal: every feature at pred-bar t uses only bars <= t.
Aligns panel_cache pred timestamps onto the 1s raw bar grid via searchsorted.

GATE: pass if avg per-asset dP>=+0.005 OR dS>=+0.005 OR rank-IC delta>=+0.005,
sign-consistent across folds, leakage-safe.
"""
from __future__ import annotations
import json, os.path as pth, sys, time
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV

REPO="/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.bar_loader import load_day_panel  # noqa

CACHE=pth.join(REPO,"multi_asset/exports/panel_cache")
SYMS=["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada","bnflink",
      "bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALPHAS=np.logspace(-2,4,13); EMB=1
FOLDS=[dict(tr=(0,250),te=(272,312)),dict(tr=(80,330),te=(352,392)),dict(tr=(160,410),te=(432,472))]
EPS=1e-9

# ---- causal primitives -----------------------------------------------------
def roll_sum(x,w):
    xf=np.where(np.isfinite(x),x,0.0); cs=np.cumsum(xf); out=cs.copy()
    if w<x.shape[0]: out[w:]=cs[w:]-cs[:-w]
    return out

def lag(x,k):
    out=np.full_like(x,np.nan)
    if k<x.shape[0]: out[k:]=x[:-k]
    return out

# 5-level book column names
BID_PX=["bid","bid_1","bid_2","bid_3","bid_4"]
ASK_PX=["ask","ask_1","ask_2","ask_3","ask_4"]
BID_SZ=["bidsz","bidsz_1","bidsz_2","bidsz_3","bidsz_4"]
ASK_SZ=["asksz","asksz_1","asksz_2","asksz_3","asksz_4"]

def col(P,sym,name): return P.data[sym][:,P.cols.index(name)].astype(np.float64)

# ---- F3 feature builder on the FULL 1s day grid -----------------------------
def build_f3_day(P, sym):
    """Return dict name->array(T,) of F3 features on the 1s grid for `sym`."""
    bpx=np.column_stack([col(P,sym,c) for c in BID_PX])  # (T,5)
    apx=np.column_stack([col(P,sym,c) for c in ASK_PX])
    bsz=np.column_stack([col(P,sym,c) for c in BID_SZ])
    asz=np.column_stack([col(P,sym,c) for c in ASK_SZ])
    mid=col(P,sym,"mid"); mid=np.where(mid>0,mid,np.nan)
    addB=col(P,sym,"bkAddBid"); addA=col(P,sym,"bkAddAsk")
    delB=col(P,sym,"bkDelBid"); delA=col(P,sym,"bkDelAsk")
    T=mid.shape[0]
    F={}

    # --- 1. book churn rate + add/del imbalance (rolling 30/60/300) ---------
    churn=addB+addA+delB+delA            # gross churn per bar
    netB=addB-delB; netA=addA-delA       # net replenishment per side
    net_repl=netB-netA                   # bid-replenishment minus ask (bullish if >0)
    addimb=(addB-addA); delimb=(delB-delA)
    for w in (30,60,300):
        F[f"churn_{w}s"]=np.log1p(roll_sum(churn,w))
        sB=roll_sum(netB,w); sA=roll_sum(netA,w)
        F[f"netrepl_{w}s"]=roll_sum(net_repl,w)                    # signed (bid-ask) net replenishment
        # replenishment imbalance normalized: (netB-netA)/(|netB|+|netA|+eps) bounded
        denom=roll_sum(np.abs(netB),w)+roll_sum(np.abs(netA),w)
        F[f"replimb_{w}s"]=sB-sA  # raw signed net (already net-repl summed = same as netrepl; keep ratio below)
        F[f"replratio_{w}s"]=(sB-sA)/(np.abs(sB)+np.abs(sA)+1.0)
        F[f"addimb_{w}s"]=roll_sum(addimb,w)
        F[f"delimb_{w}s"]=roll_sum(delimb,w)
        # churn asymmetry: add vs del pressure (net liquidity provision)
        F[f"netliq_{w}s"]=roll_sum((addB+addA)-(delB+delA),w)

    # --- 2. Multi-level OFI (Cont-Kukanov-Stoikov), summed over 5 levels ----
    # per level n: e_bid = (dPb>0)*qb_t + (dPb==0)*(qb_t-qb_{t-1}) - (dPb<0)*qb_{t-1}
    #             e_ask = (dPa<0)*qa_t + (dPa==0)*(qa_t-qa_{t-1}) - (dPa>0)*qa_{t-1}
    #   OFI_n = e_bid - e_ask  (positive = net buy pressure)
    ofi=np.zeros(T)
    for L in range(5):
        Pb=bpx[:,L]; Pa=apx[:,L]; qb=bsz[:,L]; qa=asz[:,L]
        Pb_p=lag(Pb,1); Pa_p=lag(Pa,1); qb_p=lag(qb,1); qa_p=lag(qa,1)
        dPb=Pb-Pb_p; dPa=Pa-Pa_p
        eb=np.where(dPb>0,qb,np.where(dPb<0,-qb_p,qb-qb_p))
        ea=np.where(dPa<0,qa,np.where(dPa>0,-qa_p,qa-qa_p))
        ofi=ofi+np.nan_to_num(eb-ea)
    for w in (30,60,300):
        F[f"ofi_{w}s"]=roll_sum(ofi,w)
    # OFI only on top-of-book (level-1) — often cleaner
    Pb=bpx[:,0];Pa=apx[:,0];qb=bsz[:,0];qa=asz[:,0]
    Pb_p=lag(Pb,1);Pa_p=lag(Pa,1);qb_p=lag(qb,1);qa_p=lag(qa,1)
    dPb=Pb-Pb_p;dPa=Pa-Pa_p
    eb=np.where(dPb>0,qb,np.where(dPb<0,-qb_p,qb-qb_p))
    ea=np.where(dPa<0,qa,np.where(dPa>0,-qa_p,qa-qa_p))
    ofi1=np.nan_to_num(eb-ea)
    for w in (30,60,300):
        F[f"ofi1_{w}s"]=roll_sum(ofi1,w)

    # --- 3. depth-weighted multi-level OBI + its change (queue-imb dynamics)-
    # level weights decay (closer to top = more informative)
    wts=np.array([1.0,0.8,0.6,0.4,0.2])
    bd=(bsz*wts).sum(1); ad=(asz*wts).sum(1)
    obi_w=(bd-ad)/(bd+ad+EPS)            # depth-weighted OBI in [-1,1]
    F["obi_w"]=obi_w
    # change in OBI over horizons (queue-imbalance dynamics)
    for w in (30,60,300):
        F[f"d_obi_w_{w}s"]=obi_w-lag(obi_w,w)
    # simple L5 OBI level + L1 OBI for completeness of dynamics
    bd5=bsz.sum(1);ad5=asz.sum(1)
    obi5=(bd5-ad5)/(bd5+ad5+EPS)
    F["obi5"]=obi5
    for w in (30,60,300):
        F[f"d_obi5_{w}s"]=obi5-lag(obi5,w)
    obi1=(bsz[:,0]-asz[:,0])/(bsz[:,0]+asz[:,0]+EPS)
    for w in (30,60,300):
        F[f"d_obi1_{w}s"]=obi1-lag(obi1,w)

    # --- 4. spread / midChg interaction ------------------------------------
    spread_bps=(apx[:,0]-bpx[:,0])/mid*1e4
    F["spread_bps"]=np.clip(spread_bps,0,500)
    # spread change rolling (liquidity stress)
    for w in (30,60,300):
        F[f"d_spread_{w}s"]=F["spread_bps"]-lag(F["spread_bps"],w)
    # OFI x inverse-spread interaction (flow more impactful when book thin)
    F["ofi300_x_spread"]=np.nan_to_num(F["ofi_300s"])*np.nan_to_num(spread_bps)

    return F

# ---- alignment + per-asset feature matrix at pred bars ----------------------
def build_panel_features(sample_days, names_ref=None):
    """For each sym, build (Nrows_in_cache, n_f3) aligned to cache ts, but only
    over `sample_days`. Returns per-sym dict with rows mask + F3 matrix +
    feature names. We only fill rows whose day is in sample_days."""
    # cache arrays
    cache={s:dict(np.load(pth.join(CACHE,f"{s}.npz"))) for s in SYMS}
    # per-sym output accumulators
    out={s:{"X44":[],"y":[],"day":[],"clean":[],"F3":[],"ts_cache":[]} for s in SYMS}
    feat_names=None
    for di,day in enumerate(sample_days):
        if di%10==0:
            print(f"[F3] build day {di}/{len(sample_days)} ({day})",flush=True)
        try:
            P=load_day_panel(int(day),SYMS)
        except Exception as e:
            print(f"[F3] skip {day}: {e}",flush=True); continue
        praw_ts=P.ts  # (85800,) ns 1s grid
        for s in SYMS:
            c=cache[s]
            dmask=c["day"]==day
            if not dmask.any(): continue
            cts=c["ts"][dmask]
            # align: find raw-grid index for each cache ts
            pos=np.searchsorted(praw_ts,cts)
            pos=np.clip(pos,0,praw_ts.shape[0]-1)
            ok=praw_ts[pos]==cts  # exact match required
            F=build_f3_day(P,s)
            if feat_names is None: feat_names=list(F.keys())
            fm=np.column_stack([F[k][pos] for k in feat_names]).astype(np.float32)  # (ndayrows, nf)
            fm[~ok]=np.nan
            del F
            out[s]["X44"].append(c["X"][dmask])
            out[s]["y"].append(c["y"][dmask])
            out[s]["day"].append(c["day"][dmask])
            out[s]["clean"].append(c["clean600"][dmask])
            out[s]["F3"].append(fm)
            out[s]["ts_cache"].append(cts)
    for s in SYMS:
        for k in ("X44","y","day","clean","F3","ts_cache"):
            out[s][k]=np.concatenate(out[s][k],0) if out[s][k] else np.empty((0,))
        # finalize F3: nan->0 (after standardize fit train only, but z-score needs finite)
        f=out[s]["F3"]
        out[s]["F3"]=np.nan_to_num(np.clip(f,-1e12,1e12),nan=0.0,posinf=0.0,neginf=0.0).astype(np.float64)
    return out,feat_names

def mad(x):
    x=x[np.isfinite(x)]; return float(np.median(np.abs(x-np.median(x)))*1.4826) if x.size else np.nan

def folddays(f,uniq):
    # `uniq` MUST be the GLOBAL sorted-unique day axis (all 487 days), since the
    # fold (tr/te) windows are day-INDICES into the full dataset, not the sample.
    n=uniq.shape[0]
    te0,te1=f["te"]; tr0,tr1=f["tr"]
    if te1>n: te1=n
    if te0>=n: return None
    tri=np.arange(tr0,min(tr1,n)); tri=tri[tri<te0-EMB]
    return set(uniq[tri].tolist()),set(uniq[te0:te1].tolist())

def run_asset(X44,F3,y,day,clean,use_f3,uniq):
    Xall=np.concatenate([X44,F3],1) if use_f3 else X44
    preds=[]
    for f in FOLDS:
        r=folddays(f,uniq)
        if r is None: continue
        trd,ted=r
        trm=np.isin(day,list(trd)); tem=np.isin(day,list(ted))&clean.astype(bool)
        if trm.sum()<500 or tem.sum()<20: continue
        Xtr,ytr=Xall[trm],y[trm]; Xte=Xall[tem]; yte=y[tem]
        mu=Xtr.mean(0); sd=Xtr.std(0); sd=np.where(sd>1e-12,sd,1.0)
        sig=mad(ytr)
        if not np.isfinite(sig) or sig<=0: continue
        m=RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
        yh=m.predict((Xte-mu)/sd)*sig
        preds.append((day[tem],yh,yte))
    if not preds: return None
    # per-fold P/S for sign-consistency
    foldPS=[]
    for d,yh,yt in preds:
        if len(yh)>5: foldPS.append((float(pearsonr(yh,yt)[0]),float(spearmanr(yh,yt)[0])))
    allyh=np.concatenate([p[1] for p in preds]); allyt=np.concatenate([p[2] for p in preds])
    P=float(pearsonr(allyh,allyt)[0]); S=float(spearmanr(allyh,allyt)[0])
    return dict(P=P,S=S,n=len(allyh),foldPS=foldPS,preds=preds)

def main():
    t0=time.time()
    # sample ~130 days spread across 20240601-20250930
    btc=np.load(pth.join(CACHE,"bnfbtc.npz"))
    alldays=np.unique(btc["day"])
    alldays=alldays[(alldays>=20240601)&(alldays<=20250930)]
    NSAMP=int(sys.argv[1]) if len(sys.argv)>1 else 130
    idx=np.linspace(0,len(alldays)-1,NSAMP).astype(int); idx=np.unique(idx)
    sample_days=alldays[idx]
    print(f"[F3] sampling {len(sample_days)} days from {sample_days[0]}..{sample_days[-1]}",flush=True)

    blob=pth.join(REPO,"multi_asset/exports/eda/_f3_built.npz")
    if pth.exists(blob) and "--rebuild" not in sys.argv:
        z=np.load(blob,allow_pickle=True)
        feat_names=list(z["feat_names"]); data={}
        for s in SYMS:
            data[s]=dict(X44=z[f"{s}_X44"],y=z[f"{s}_y"],day=z[f"{s}_day"],
                         clean=z[f"{s}_clean"],F3=z[f"{s}_F3"],ts_cache=z[f"{s}_ts"])
        print(f"[F3] loaded cached build {blob}",flush=True)
    else:
        data,feat_names=build_panel_features(sample_days)
        sv={"feat_names":np.array(feat_names,dtype=object)}
        for s in SYMS:
            sv[f"{s}_X44"]=data[s]["X44"]; sv[f"{s}_y"]=data[s]["y"]
            sv[f"{s}_day"]=data[s]["day"]; sv[f"{s}_clean"]=data[s]["clean"]
            sv[f"{s}_F3"]=data[s]["F3"].astype(np.float32); sv[f"{s}_ts"]=data[s]["ts_cache"]
        np.savez_compressed(blob,**sv); print(f"[F3] cached build -> {blob}",flush=True)
    print(f"[F3] built {len(feat_names)} F3 features: {feat_names}",flush=True)
    # GLOBAL day axis (all 487 days) — folds are day-INDICES into this, not the sample.
    uniq=alldays.copy()
    n_sampled=len(np.unique(np.concatenate([data[s]["day"] for s in SYMS])))
    print(f"[F3] global day axis {len(uniq)} days; {n_sampled} sampled days fall in it; build took {time.time()-t0:.0f}s",flush=True)

    # per-asset baseline vs +F3
    rows=[]; base_preds={}; plus_preds={}
    for s in SYMS:
        d=data[s]
        if d["y"].shape[0]<600:
            rows.append((s,None,None)); continue
        b=run_asset(d["X44"],d["F3"],d["y"],d["day"],d["clean"],False,uniq)
        p=run_asset(d["X44"],d["F3"],d["y"],d["day"],d["clean"],True,uniq)
        rows.append((s,b,p))
        if b: base_preds[s]=b["preds"]
        if p: plus_preds[s]=p["preds"]

    # ---- univariate standalone |Spearman| of each F3 feature on clean rows --
    uni=[]
    # pool across assets per-asset-zscored y for comparability
    for j,name in enumerate(feat_names):
        ss=[]
        for s in SYMS:
            d=data[s]
            if d["y"].shape[0]<300: continue
            cl=d["clean"].astype(bool)
            yv=d["y"][cl]; fv=d["F3"][cl,j]
            m=np.isfinite(yv)&np.isfinite(fv)
            if m.sum()<200 or np.std(fv[m])<1e-12: continue
            ss.append(spearmanr(fv[m],yv[m])[0])
        if ss: uni.append((name,float(np.mean(ss)),float(np.mean(np.abs(ss)))))
    uni.sort(key=lambda r:-r[2])

    # ---- cross-sectional rank-IC (per-timestamp Spearman across assets) -----
    def xsec_ic(predmap):
        # gather per (fold) by ts: align test preds across assets
        # build ts->{sym:yh, sym:yt}
        from collections import defaultdict
        # need ts; re-run with ts. We have day only in preds; use index alignment instead:
        return None  # computed separately below
    # We compute rank-IC by re-aligning on cache ts directly.
    ric_base, ric_plus = xsec_rank_ic(data,uniq,feat_names)

    # ---- print + assemble ---------------------------------------------------
    print(f"\n{'asset':9s} {'bP':>7s} {'+P':>7s} {'dP':>7s} {'bS':>7s} {'+S':>7s} {'dS':>7s}  fold-dP-signs",flush=True)
    dPs=[];dSs=[]
    perasset={}
    for s,b,p in rows:
        if not(b and p):
            print(f"{s:9s}  (skip)"); continue
        dP=p["P"]-b["P"]; dS=p["S"]-b["S"]; dPs.append(dP); dSs.append(dS)
        # per-fold dP sign
        signs=[]
        for (bp,bs),(pp,ps) in zip(b["foldPS"],p["foldPS"]):
            signs.append("+" if (pp-bp)>0 else ("-" if (pp-bp)<0 else "0"))
        perasset[s]=dict(bP=round(b["P"],4),pP=round(p["P"],4),dP=round(dP,4),
                         bS=round(b["S"],4),pS=round(p["S"],4),dS=round(dS,4),signs="".join(signs))
        print(f"{s:9s} {b['P']:>+7.4f} {p['P']:>+7.4f} {dP:>+7.4f} {b['S']:>+7.4f} {p['S']:>+7.4f} {dS:>+7.4f}  {''.join(signs)}",flush=True)
    avgdP=float(np.mean(dPs)); avgdS=float(np.mean(dSs))
    avg_bP=float(np.mean([perasset[s]['bP'] for s in perasset]))
    avg_pP=float(np.mean([perasset[s]['pP'] for s in perasset]))
    avg_bS=float(np.mean([perasset[s]['bS'] for s in perasset]))
    avg_pS=float(np.mean([perasset[s]['pS'] for s in perasset]))
    print(f"\nAVG  baseP={avg_bP:+.4f} +P={avg_pP:+.4f} dP={avgdP:+.4f} | baseS={avg_bS:+.4f} +S={avg_pS:+.4f} dS={avgdS:+.4f}",flush=True)
    print(f"rank-IC base={ric_base:+.4f} +F3={ric_plus:+.4f} dRIC={ric_plus-ric_base:+.4f}",flush=True)
    print(f"\nTop univariate |Spearman| F3 features (avg signed S, avg |S|):",flush=True)
    for name,sgn,ab in uni[:14]:
        print(f"  {name:18s} S={sgn:+.4f} |S|={ab:.4f}",flush=True)

    # sign consistency check: fraction of asset-folds where dP>0
    allsigns="".join(perasset[s]['signs'] for s in perasset)
    fpos=allsigns.count('+'); fneg=allsigns.count('-')
    print(f"\nfold-dP sign tally across assets: +{fpos} / -{fneg} (of {len(allsigns)})",flush=True)

    res=dict(family="F3_book_dynamics",n_days=int(len(uniq)),
             feat_names=feat_names,
             avg_baseP=round(avg_bP,4),avg_plusP=round(avg_pP,4),avg_dP=round(avgdP,4),
             avg_baseS=round(avg_bS,4),avg_plusS=round(avg_pS,4),avg_dS=round(avgdS,4),
             rankIC_base=round(ric_base,4),rankIC_plus=round(ric_plus,4),rankIC_d=round(ric_plus-ric_base,4),
             per_asset=perasset,
             top_uni=[(n,round(s,4),round(a,4)) for n,s,a in uni[:14]],
             fold_dP_pos=fpos,fold_dP_neg=fneg)
    outp=pth.join(REPO,"multi_asset/exports/eda/F3_book_dynamics_gate.json")
    json.dump(res,open(outp,"w"),indent=2)
    print(f"\n[F3] wrote {outp}; total {time.time()-t0:.0f}s",flush=True)

def xsec_rank_ic(data,uniq,feat_names):
    """Cross-sectional rank-IC: for each test ts, rank assets' predictions vs
    realized y across the universe, Spearman, then mean. Compare base vs +F3.
    We refit per fold per asset (pooled) then align test preds by exact ts."""
    from collections import defaultdict
    def fit_predict(use_f3):
        # ts -> {sym: (yh,yt)}
        byts=defaultdict(dict)
        for s in SYMS:
            d=data[s]
            if d["y"].shape[0]<600: continue
            Xall=np.concatenate([d["X44"],d["F3"]],1) if use_f3 else d["X44"]
            for f in FOLDS:
                r=folddays(f,uniq)
                if r is None: continue
                trd,ted=r
                trm=np.isin(d["day"],list(trd)); tem=np.isin(d["day"],list(ted))&d["clean"].astype(bool)
                if trm.sum()<500 or tem.sum()<20: continue
                Xtr,ytr=Xall[trm],d["y"][trm]; Xte=Xall[tem]
                mu=Xtr.mean(0);sd=Xtr.std(0);sd=np.where(sd>1e-12,sd,1.0)
                sig=mad(ytr)
                if not np.isfinite(sig) or sig<=0: continue
                m=RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd,ytr/sig)
                yh=m.predict((Xte-mu)/sd)*sig
                # need ts for test rows
                ts_te=d["ts_cache"][tem]
                yt=d["y"][tem]
                for t,h,r_ in zip(ts_te,yh,yt):
                    byts[int(t)][s]=(float(h),float(r_))
        ics=[]
        for t,dd in byts.items():
            if len(dd)<5: continue
            syms=list(dd.keys())
            yh=np.array([dd[s][0] for s in syms]); yt=np.array([dd[s][1] for s in syms])
            if np.std(yh)<1e-12: continue
            ics.append(spearmanr(yh,yt)[0])
        return float(np.mean(ics)) if ics else float('nan')
    return fit_predict(False), fit_predict(True)

if __name__=="__main__":
    main()
