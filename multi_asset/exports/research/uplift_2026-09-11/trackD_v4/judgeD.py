"""Track D judge (exploratory; judge_v4's frozen g/window/bootstrap definitions, NOT its eligibility gate).
g = net_ex/gross_total [bps/anchor/gross]. UTC-day block bootstrap 2000, base seed 20260905, substream [20260905,k]."""
import numpy as np, json, calendar, time, os, glob, sys
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c:i for i,c in enumerate(COLS)}; APY = 2190
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
FROZEN = (T(2025,3,1), T(2026,8,10,20)+1)
FULL   = (T(2022,1,1), T(2026,8,10,20)+1)
W24    = (T(2024,1,1), T(2026,8,10,20)+1)
YRS = {"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
       "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
def load(p, key="rec"):
    A = np.load(p, allow_pickle=True)
    R = A[key] if key in A.files else A["d30_n2_c42_rec"]
    ts = np.round(np.asarray(R[:,0],float)).astype(np.int64)
    g = R[:,C["net_ex"]]/R[:,C["gross_total"]]
    return ts, g, R
def boot(v, days, k):
    rng = np.random.default_rng([20260905, k])
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)), float(np.percentile(mn,97.5)), float((mn>0).mean()), mn
def stats(ts, g, R, lo, hi):
    m = (ts>=lo)&(ts<hi)
    if m.sum() < 3: return None
    v = g[m]; c = np.concatenate([[0.0], np.cumsum(v)])
    return {"n":int(m.sum()), "mean":float(v.mean()),
            "sharpe": float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if v.std(ddof=1)>0 else float("nan"),
            "se_sharpe": float(np.sqrt(2190.0/m.sum())),
            "maxdd": float(np.max(np.maximum.accumulate(c)-c)),
            "turnover": float(R[m,C["turnover"]].mean()),
            "cost_bps": float((R[m,C["cost_ex"]]/R[m,C["gross_total"]]).mean()),
            "carry_bps": float((R[m,C["carry_ex"]]/R[m,C["gross_total"]]).mean()),
            "gross_mean": float(R[m,C["gross_total"]].mean())}
if __name__ == "__main__":
    A0P = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
    A0P2= "/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz"
    t0,g0,R0 = load(A0P, "d30_n2_c42_rec"); t0b,g0b,R0b = load(A0P2,"d30_n2_c42_rec")
    files = sorted(glob.glob("/workspace/uplift_2026-09-11/trackD_v4/SL_*.npz"))
    out = {"baseline": {}, "arms": {}, "meta": {"n_arms": len(files), "device_sha": "8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d"}}
    for w,(lo,hi) in [("frozen",FROZEN),("full",FULL),("2024on",W24)]+list(YRS.items()):
        out["baseline"][w] = stats(t0,g0,R0,lo,hi)
    d0 = t0//86400
    mf = (t0>=FULL[0])&(t0<FULL[1])
    lo_,hi_,p_,_ = boot(g0[mf], d0[mf], 0)
    out["baseline"]["full_ci"] = [lo_,hi_,p_]
    k = 1
    for f in files:
        tag = os.path.basename(f)[:-4]
        ts,g,R = load(f, "rec")
        # anchor-set identity with A0 on the frozen window
        fa = ts[(ts>=FROZEN[0])&(ts<FROZEN[1])]; f0 = t0[(t0>=FROZEN[0])&(t0<FROZEN[1])]
        same = bool(len(fa)==len(f0) and (fa==f0).all())
        e = {"anchor_axis_equals_A0_frozen": same}
        for w,(lo,hi) in [("frozen",FROZEN),("full",FULL),("2024on",W24)]+list(YRS.items()):
            e[w] = stats(ts,g,R,lo,hi)
        m = (ts>=FULL[0])&(ts<FULL[1])
        lo_,hi_,p_,_ = boot(g[m], ts[m]//86400, k); k+=1
        e["full_ci"] = [lo_,hi_,p_]
        # correlation to A0 (common anchors)
        for w,(lo,hi),nm in [(0,FROZEN,"corr_frozen"),(0,W24,"corr_2024on"),(0,FULL,"corr_full")]:
            ca, ia, ib = np.intersect1d(ts, t0, return_indices=True)
            sel = (ca>=lo)&(ca<hi)
            e[nm] = float(np.corrcoef(g[ia[sel]], g0[ib[sel]])[0,1]) if sel.sum()>10 else None
        # 50/50 blend with A0 (equal gross)
        ca, ia, ib = np.intersect1d(ts, t0, return_indices=True)
        gb = 0.5*g[ia] + 0.5*g0[ib]
        e["blend50"] = {}
        for w,(lo,hi) in [("frozen",FROZEN),("full",FULL)]+list(YRS.items()):
            sel = (ca>=lo)&(ca<hi)
            if sel.sum()>3:
                v = gb[sel]
                e["blend50"][w] = {"mean":float(v.mean()),"sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(APY))}
        out["arms"][tag] = e
    # A0 blend reference: A0 alone on common set already in baseline
    json.dump(out, open("/workspace/uplift_2026-09-11/trackD_v4/JUDGE_trackD.json","w"), indent=1)
    print("arms judged:", len(files))
