"""0C FINAL VERDICT AUDIT — QIM wide-universe factor (Engine A).
Independent reproduction + decomposition + net-cost + anomaly audit. CPU-only numpy scoring,
NO GPU/training. Writes multi_asset/exports/eda/qim_final_verdict.{json,md}.
"""
import numpy as np, pandas as pd, json, os, glob
from scipy.stats import rankdata, spearmanr

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
TRAIN = ROOT + "/multi_asset/exports/train"
EDA = ROOT + "/multi_asset/exports/eda"
os.makedirs(EDA, exist_ok=True)
RNG = np.random.default_rng(0)


def load_panel(d):
    z = np.load(d + "/panel_ref.npz", allow_pickle=True)
    return dict(ts=z["ts"].astype(np.int64), day=z["day"], symbols=[str(s) for s in z["symbols"]],
                Yraw=z["Yraw"].astype(np.float64), YR=z["YR"].astype(np.float64),
                member=z["member"].astype(bool), CL=z["CL"].astype(bool),
                funding=z["funding"].astype(np.float64), H=int(z["horizon"]))


def fold_files(d):
    return sorted(glob.glob(d + "/fold_*_head_scores.npz"),
                  key=lambda f: int(f.split("fold_")[1].split("_")[0]))


def comp_panel(scores, panel):
    """Build z-mean ensemble composite C[t,i] (NaN off valid), honest caliber. scores (T,N,K)."""
    T, N, K = scores.shape
    C = np.full((T, N), np.nan)
    member, CL, YR = panel["member"], panel["CL"], panel["YR"]
    rows = np.where((member & CL & np.isfinite(YR)).any(1) & np.isfinite(scores).any((1, 2)))[0]
    for t in rows:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            C[t, base] = comp / nk
    return C


def ic_series(C, Ytgt, panel):
    """Per-ts cross-sectional rank-IC of composite C vs Ytgt over valid rows. Returns (rows, ics)."""
    member, CL = panel["member"], panel["CL"]
    rws, ics = [], []
    cand = np.where(np.isfinite(C).any(1))[0]
    for t in cand:
        base = np.where(member[t] & CL[t] & np.isfinite(Ytgt[t]) & np.isfinite(C[t]))[0]
        if base.size < 5:
            continue
        ic = np.corrcoef(rankdata(C[t, base]), rankdata(Ytgt[t, base]))[0, 1]
        if np.isfinite(ic):
            rws.append(t); ics.append(ic)
    return np.array(rws), np.array(ics)


def dyn_static(C, panel, nshuf=25):
    """Dynamic/static decomposition. static = time-shuffle (break timing, keep per-asset tilt).
    Returns total, static_shuffle, static_mean(deterministic), dynamic."""
    member, CL, YR = panel["member"], panel["CL"], panel["YR"]
    rows = np.where(np.isfinite(C).any(1))[0]
    # cache per-row valid idx + target ranks
    idxs, yrank = [], []
    for t in rows:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(C[t]))[0]
        if base.size < 5:
            idxs.append(None); yrank.append(None); continue
        idxs.append(base); yrank.append(rankdata(YR[t, base]))
    valid = [i for i in range(len(rows)) if idxs[i] is not None]
    # total
    tot = []
    for i in valid:
        t = rows[i]; b = idxs[i]
        tot.append(np.corrcoef(rankdata(C[t, b]), yrank[i])[0, 1])
    tot = float(np.nanmean(tot))
    # deterministic static: per-asset time-mean over these rows
    N = C.shape[1]
    mu = np.full(N, np.nan)
    for a in range(N):
        col = C[rows, a]
        col = col[np.isfinite(col)]
        if col.size >= 5:
            mu[a] = col.mean()
    stat_m = []
    for i in valid:
        t = rows[i]; b = idxs[i]
        if np.isfinite(mu[b]).sum() >= 5:
            m2 = np.isfinite(mu[b])
            stat_m.append(np.corrcoef(rankdata(mu[b][m2]), rankdata(YR[t, b][m2]))[0, 1])
    stat_m = float(np.nanmean(stat_m))
    # shuffle static: permute each asset's C across rows, recompute per-t IC, average over reps
    Csub = C[rows]                      # (R,N)
    shuf_ic = []
    for _ in range(nshuf):
        Cs = Csub.copy()
        for a in range(N):
            fin = np.where(np.isfinite(Cs[:, a]))[0]
            if fin.size > 1:
                Cs[fin, a] = Cs[fin[RNG.permutation(fin.size)], a]
        rep = []
        for i in valid:
            b = idxs[i]
            v = np.isfinite(Cs[i, b])
            if v.sum() >= 5:
                rep.append(np.corrcoef(rankdata(Cs[i, b][v]), rankdata(YR[rows[i], b][v]))[0, 1])
        shuf_ic.append(np.nanmean(rep))
    stat_s = float(np.nanmean(shuf_ic))
    return dict(total=tot, static_shuffle=stat_s, static_mean=stat_m,
                dynamic=tot - stat_s, dyn_share=(tot - stat_s) / tot if tot else np.nan)


def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64)
    r = r - r.mean()
    s = np.abs(r).sum()
    return r / s * 2.0 if s > 0 else r


def netcost(C, panel, costs=(0.0, 2.3, 5.0, 9.5)):
    """4h-rebalanced dollar-neutral rank-weighted L/S on RAW forward returns. Full-turnover headline
    + EMA break-even. per_yr from H hours."""
    member, CL, Yraw = panel["member"], panel["CL"], panel["Yraw"]
    H = panel["H"]
    per_yr = 365 * 24 / H; ann = np.sqrt(per_yr)
    rows = np.sort(np.where(np.isfinite(C).any(1))[0])
    S = C.shape[1]
    tw, yv, br = [], [], []
    n_q = 10; qy = [[] for _ in range(n_q)]
    ics = []
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(C[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(S); w[v] = rank_weights(C[t, v])
        tw.append(w); yv.append(np.where(np.isin(np.arange(S), v), Yraw[t], 0.0)); br.append(v.size)
        ics.append(spearmanr(C[t, v], Yraw[t, v]).correlation)
        order = C[t, v].argsort()
        for qi in range(n_q):
            lo = qi * len(order) // n_q; hi = (qi + 1) * len(order) // n_q
            if hi > lo:
                qy[qi].append(Yraw[t, v][order[lo:hi]].mean())
    tw = np.array(tw); yv = np.array(yv); n = len(tw)
    if n < 20:
        return None
    # full turnover series
    def series(alpha):
        held = np.zeros(S); g = np.empty(n); tn = np.empty(n)
        for k in range(n):
            new = alpha * tw[k] + (1 - alpha) * held
            tn[k] = np.abs(new - held).sum(); g[k] = float((new * yv[k]).sum()); held = new
        return g, tn
    g1, t1 = series(1.0)
    res = dict(n_periods=n, gross_bps=float(g1.mean() * 1e4), turnover=float(t1.mean()),
               be_fullturn=float(g1.mean() / t1.mean() * 1e4) if t1.mean() > 0 else np.inf,
               gross_sharpe=float(g1.mean() / g1.std() * ann) if g1.std() > 0 else np.nan,
               mean_rank_ic_raw=float(np.nanmean(ics)), avg_breadth=float(np.mean(br)))
    for c in costs:
        net = g1 - t1 * (c * 1e-4)
        res[f"netSharpe_full_c{c}"] = float(net.mean() / net.std() * ann) if net.std() > 0 else np.nan
        res[f"netAnnBps_full_c{c}"] = float(net.mean() * per_yr * 1e4)
    # best-alpha break-even (turnover-optimised)
    best_be = -1; best = None
    for al in (1.0, 0.5, 0.3, 0.2, 0.1, 0.05):
        g, tn = series(al)
        be = g.mean() / tn.mean() * 1e4 if tn.mean() > 0 else np.inf
        if be > best_be:
            best_be = be
            nets = {f"netSharpe_a{al}_c{c}": (float((g - tn * (c * 1e-4)).mean() /
                    (g - tn * (c * 1e-4)).std() * ann) if (g - tn * (c * 1e-4)).std() > 0 else np.nan)
                    for c in costs}
            best = dict(alpha=al, be=float(be), turnover=float(tn.mean()), **nets)
    res["best_alpha"] = best
    qm = [float(np.mean(b)) if b else np.nan for b in qy]
    res["decile_mean_bps"] = [round(q * 1e4, 3) for q in qm]
    res["decile_monotonicity"] = float(spearmanr(np.arange(n_q), qm).correlation)
    return res


def run_multiyear():
    d = TRAIN + "/wideA_qim_multiyear"
    panel = load_panel(d)
    yr_of = pd.to_datetime(panel["ts"], unit="ms", utc=True).year.to_numpy()
    out = {}
    ff = fold_files(d)
    for f in ff:
        z = np.load(f); scores = z["scores"]; te_rows = z["te_rows"]
        # determine test year from te_rows
        yrs = yr_of[te_rows]
        Y = int(np.bincount(yrs - yrs.min()).argmax() + yrs.min())
        C = comp_panel(scores, panel)
        # restrict composite to this fold's te_rows only (mask others)
        keep = np.zeros(panel["Yraw"].shape[0], bool); keep[te_rows] = True
        C[~keep] = np.nan
        r_res, ic_res = ic_series(C, panel["YR"], panel)
        r_raw, ic_raw = ic_series(C, panel["Yraw"], panel)
        dec = dyn_static(C, panel)
        nc = netcost(C, panel)
        out[str(Y)] = dict(
            year=Y, n_clean_ts=int(len(ic_res)),
            ens_resid_ic=round(float(ic_res.mean()), 4),
            ens_resid_ic_ir=round(float(ic_res.mean() / ic_res.std() * np.sqrt(len(ic_res))), 2),
            ens_raw_ic=round(float(ic_raw.mean()), 4),
            member_per_hr=int(np.median(panel["member"][te_rows].sum(1))),
            decomp={k: (round(v, 4) if isinstance(v, float) and np.isfinite(v) else v)
                    for k, v in dec.items()},
            netcost=nc)
        print(f"[5yr {Y}] resid IC={ic_res.mean():+.4f} (IR {out[str(Y)]['ens_resid_ic_ir']}) "
              f"raw={ic_raw.mean():+.4f} | dyn share={dec['dyn_share']:.2f} "
              f"(tot {dec['total']:.4f} stat_shuf {dec['static_shuffle']:.4f} stat_mean {dec['static_mean']:.4f}) "
              f"| BE={nc['be_fullturn']:.2f} netSh@2.3={nc['netSharpe_full_c2.3']:.2f}", flush=True)
    return out


def recompute_ens(tag):
    """Recompute honest ensemble resid IC per fold for a 3-fold run (verify + mechanism/seed)."""
    d = TRAIN + "/" + tag
    panel = load_panel(d)
    res = []
    for f in fold_files(d):
        z = np.load(f); C = comp_panel(z["scores"], panel)
        keep = np.zeros(panel["Yraw"].shape[0], bool); keep[z["te_rows"]] = True
        C[~keep] = np.nan
        _, ic = ic_series(C, panel["YR"], panel)
        res.append(round(float(ic.mean()), 4))
    return dict(per_fold=res, mean=round(float(np.mean(res)), 4))


def leak_audit():
    d = TRAIN + "/wideA_qim_multiyear"
    panel = load_panel(d)
    T = panel["Yraw"].shape[0]
    # YR orthogonality to funding (residualization sanity)
    member, CL, YR, fund = panel["member"], panel["CL"], panel["YR"], panel["funding"]
    v = member & CL & np.isfinite(YR) & np.isfinite(fund)
    cor_fund = float(np.corrcoef(YR[v], fund[v])[0, 1])
    # member point-in-time: distinct monthly member sets + monotonic growth of universe size early
    day = panel["day"]; month = day // 30
    sizes = [int(member[np.where(month == m)[0][0]].sum()) for m in np.unique(month)]
    n_distinct = len({tuple(np.where(member[np.where(month == m)[0][0]])[0].tolist())
                      for m in np.unique(month)})
    # member never true where Yraw all-nan history (proxy: member implies finite CH-era). Check a coin
    # is not a member before its first finite raw-return appearance.
    firstfin = {}
    for a in range(panel["Yraw"].shape[1]):
        f = np.where(np.isfinite(panel["Yraw"][:, a]))[0]
        firstfin[a] = int(f[0]) if f.size else T
    premember = 0
    for a in range(panel["Yraw"].shape[1]):
        mrows = np.where(member[:, a])[0]
        if mrows.size and mrows[0] < firstfin[a]:
            premember += 1
    return dict(corr_YR_funding=round(cor_fund, 5), monthly_member_sizes=sizes,
                n_distinct_monthly_sets=n_distinct, n_months=len(sizes),
                coins_member_before_first_finite=premember)


def fold_boundary_audit():
    """Reconstruct year_folds day ranges on the 5yr panel; confirm train/test separation + embargo."""
    d = TRAIN + "/wideA_qim_multiyear"
    panel = load_panel(d)
    ts = panel["ts"]; day = panel["day"]
    uniq_days = np.unique(day)
    yr_of_hour = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    day_year = np.array([int(yr_of_hour[day == dd][0]) for dd in uniq_days])
    embargo, val = 8, 30
    rep = []
    ff = fold_files(d)
    fold_te = {}
    for f in ff:
        z = np.load(f)
        fte = np.unique(day[z["te_rows"]])
        yrs = yr_of_hour[z["te_rows"]]
        Y = int(np.bincount(yrs - yrs.min()).argmax() + yrs.min())
        fold_te[Y] = (int(fte.min()), int(fte.max()))
    for Y in sorted(set(day_year.tolist())):
        te = uniq_days[day_year == Y]
        tr_all = uniq_days[day_year < Y]
        if len(te) < 60 or len(tr_all) < 120 + val + embargo:
            continue
        tr_all2 = tr_all[:-embargo]
        tr, va = tr_all2[:-val], tr_all2[-val:]
        gap = te.min() - va.max()   # days between val end and test start
        # cross-check the actual exported te range
        exp = fold_te.get(Y)
        overlap = (exp is not None and not (exp[0] > va.max()))
        rep.append(dict(test_year=Y, train_days=int(len(tr)), val_days=int(len(va)),
                        train_end_day=int(tr[-1]), val_end_day=int(va.max()),
                        test_start_day=int(te.min()), test_end_day=int(te.max()),
                        embargo_gap_days=int(gap),
                        exported_te_range=exp, train_test_overlap=bool(overlap)))
    return rep


if __name__ == "__main__":
    print("=== 1. MULTIYEAR (5yr QIM) reproduce + decomp + netcost ===", flush=True)
    myr = run_multiyear()
    print("\n=== 2. leak audit ===", flush=True)
    leak = leak_audit(); print(json.dumps(leak, indent=2), flush=True)
    print("\n=== 3. fold boundary audit ===", flush=True)
    fb = fold_boundary_audit()
    for r in fb:
        print(f"  te={r['test_year']}: train..d{r['train_end_day']} val..d{r['val_end_day']} "
              f"test d{r['test_start_day']}..d{r['test_end_day']} gap={r['embargo_gap_days']}d "
              f"overlap={r['train_test_overlap']}", flush=True)
    print("\n=== 4. mechanism (3-fold matched ensemble) ===", flush=True)
    mech = {}
    for tag in ["wideA_conformer_ref", "wideA_lamorth0", "wideA_qim"]:
        mech[tag] = recompute_ens(tag)
        print(f"  {tag}: {mech[tag]}", flush=True)
    print("\n=== 5. seed (3-fold matched ensemble) ===", flush=True)
    seed = {}
    for tag in ["wideA_qim", "wideA_qim_seed43", "wideA_qim_seed44"]:
        seed[tag] = recompute_ens(tag)
        print(f"  {tag}: {seed[tag]}", flush=True)
    result = dict(multiyear=myr, leak_audit=leak, fold_boundary=fb, mechanism=mech, seed=seed)
    json.dump(result, open(EDA + "/qim_verdict_audit_raw.json", "w"), indent=2, default=str)
    print("\nSAVED -> " + EDA + "/qim_verdict_audit_raw.json", flush=True)
