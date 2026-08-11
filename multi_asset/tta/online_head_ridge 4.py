"""E1: causal online ridge re-fit of the head on the FROZEN Conformer embedding.
Diagnosis: choppy val->test drift is a CONCEPT/joint-weight shift (signal present
on test, mapping doesn't transfer). Fix = recency: cache the 32-d pre-head
embedding (model.encode) over a recent contiguous period, then walk-forward fit a
shrunk ridge [z->y] on a trailing W-day window of MATURED samples (ts+600s<=block
start, strictly causal), eval on choppy 2026. Zero GPU training. Compare to frozen q50."""
import sys, os, glob, json
import numpy as np, torch
REPO="/mnt/storage/private/work_hsy/quant_research_multi_asset"; sys.path.insert(0, REPO); os.chdir(REPO)
from scipy.stats import pearsonr, spearmanr

EXP=f"{REPO}/experiments/perp_consolidation/reg_arch_spot_choppy/fold_0"
SP=f"{REPO}/data/npz_spot"

def cache_embeddings():
    from run_pipeline_v3 import build_model
    from src.training.dataset import LOBDatasetV2
    from torch.utils.data import DataLoader
    mcfg=json.load(open("configs/v5push/singh_alpha0_huber_track_reg_arch_spot_choppy.json"))["model"]
    ck=torch.load(f"{EXP}/best_model.pt", map_location="cpu", weights_only=False)
    model=build_model("V3",64,20,mcfg); model.load_state_dict(ck["state"]); model.eval()
    dev="cuda" if torch.cuda.is_available() else "cpu"; model.to(dev)
    npz=np.load(f"{EXP}/norm_params.npz"); xm=npz["x_mean"]; xs=npz["x_std"]; ymed=float(npz["y_median"]); ysig=float(npz["y_sigma"])
    days=sorted(os.path.basename(f)[:-4] for f in glob.glob(SP+"/*.npz") if ".tmp." not in f)
    days=[d for d in days if "2025-09-01"<=d<="2026-04-30"]
    ds=LOBDatasetV2(SP, days, normalize=True, x_mean=xm, x_std=xs, y_norm=(ymed,ysig,5.0), horizons=["y_600"])
    ts=ds.get_all_timestamps().astype(np.int64)
    dl=DataLoader(ds, batch_size=1024, shuffle=False, num_workers=0)
    Z=[]; Q=[]; Y=[]; M=[]
    with torch.no_grad():
        for batch in dl:
            if len(batch)==5: xf,xr,rp,y,m=batch; rp=rp.to(dev)
            else: xf,xr,y,m=batch; rp=None
            xf=xf.to(dev); xr=xr.to(dev)
            z=model.encode(xf,xr,regime_prior=rp)
            out=model(xf,xr,regime_prior=rp); q=out["quantiles"][:,1]
            Z.append(z.cpu().numpy()); Q.append(q.cpu().numpy())
            Y.append(np.asarray(y).reshape(len(y),-1)[:,0]); M.append(np.asarray(m).reshape(len(m),-1)[:,0])
    Z=np.concatenate(Z); Q=np.concatenate(Q); Y=np.concatenate(Y); M=np.concatenate(M).astype(bool)
    sec=(ts//1_000_000).astype(np.int64)
    np.savez(f"{EXP}/embed_cache.npz", Z=Z, Q=Q, Y=Y, M=M, sec=sec)
    print(f"cached Z{Z.shape} Q{Q.shape} sec[{sec.min()},{sec.max()}]", flush=True)
    return Z,Q,Y,M,sec

def walk_forward(Z,Q,Y,M,sec, W_days, lam, blend, test_lo, test_hi):
    W=W_days*86400; K=7*86400
    order=np.argsort(sec); Z,Q,Y,M,sec=Z[order],Q[order],Y[order],M[order],sec[order]
    val=M & (Y>-1e3)
    import datetime as dt
    def mon(s): return dt.datetime.utcfromtimestamp(s).strftime('%Y-%m')
    test_mask = val & (sec>= int(dt.datetime.strptime(test_lo,'%Y-%m-%d').timestamp())) & (sec< int(dt.datetime.strptime(test_hi,'%Y-%m-%d').timestamp()))
    # build per-block ridge
    test_idx=np.where(test_mask)[0]
    if len(test_idx)==0: return None
    preds=np.full(len(sec), np.nan)
    t0=sec[test_idx[0]]; 
    # mean-center z; ridge with L2 lam
    blocks={}
    for i in test_idx:
        b=(sec[i]-t0)//K
        if b not in blocks:
            Tstart=t0+b*K
            fitm = val & (sec+600 <= Tstart) & (sec >= Tstart-W)
            if fitm.sum()<2000: blocks[b]=None; continue
            Xf=Z[fitm]; yf=Y[fitm]; mu=Xf.mean(0); A=Xf-mu
            w=np.linalg.solve(A.T@A + lam*np.eye(A.shape[1]), A.T@(yf-yf.mean()))
            blocks[b]=(mu,w,yf.mean())
        bk=blocks[b]
        if bk is None: continue
        mu,w,yb=bk; preds[i]=(Z[i]-mu)@w + yb
    ok=~np.isnan(preds) & test_mask
    yh=preds[ok]; yy=Y[ok]; qf=Q[ok]; ss=sec[ok]
    if blend>0:
        z=lambda a:(a-a.mean())/(a.std()+1e-9)
        yh=(1-blend)*z(yh)+blend*z(qf)
    res={"P":pearsonr(yh,yy)[0],"S":spearmanr(yh,yy)[0],"sr":yh.std()/(yy.std()+1e-9),"n":len(yy),
         "frozenP":pearsonr(qf,yy)[0]}
    # per-month
    pm={}
    for u in sorted(set(mon(s) for s in ss)):
        sm=np.array([mon(s)==u for s in ss])
        if sm.sum()>200: pm[u]=round(pearsonr(yh[sm],yy[sm])[0],4)
    res["per_month"]=pm
    return res

if __name__=="__main__":
    if os.path.exists(f"{EXP}/embed_cache.npz"):
        d=np.load(f"{EXP}/embed_cache.npz"); Z,Q,Y,M,sec=d["Z"],d["Q"],d["Y"],d["M"].astype(bool),d["sec"]
        print("loaded cache",Z.shape,flush=True)
    else:
        Z,Q,Y,M,sec=cache_embeddings()
    print("\n=== FROZEN baseline (choppy 2026-02/03/04) ===",flush=True)
    base=walk_forward(Z,Q,Y,M,sec, 25, 1e9, 1.0, "2026-02-01","2026-05-01")  # blend=1 -> frozen only
    print(f"  frozen q50: P={base['frozenP']:+.4f}",flush=True)
    print("\n=== E1 online head-ridge sweep (W, lam) ===",flush=True)
    for W in [20,30]:
        for lam in [30.0,100.0,300.0,1000.0]:
            r=walk_forward(Z,Q,Y,M,sec, W, lam, 0.0, "2026-02-01","2026-05-01")
            if r: print(f"  W={W}d lam={lam:6.0f}: P={r['P']:+.4f} S={r['S']:+.4f} sr={r['sr']:.3f} | frozen {r['frozenP']:+.4f} | {r['per_month']}",flush=True)
    print("\n=== E1 + frozen blend (W=25,lam=300) ===",flush=True)
    for bl in [0.0,0.3,0.5]:
        r=walk_forward(Z,Q,Y,M,sec, 25, 300.0, bl, "2026-02-01","2026-05-01")
        if r: print(f"  blend={bl}: P={r['P']:+.4f} S={r['S']:+.4f} {r['per_month']}",flush=True)
