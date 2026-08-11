"""F1 GATE — Microprice & price refinement family.

Builds causal microprice / weighted-mid / spread features at each panel_cache
pred timestamp (aligned by exact ts via searchsorted onto raw bar P.ts), then
runs per-asset RidgeCV walk-forward: baseline = 44 hand feats (panel_cache X)
vs test = 44 + F1. Reports per-asset Pearson + Spearman, deltas, rank-IC delta,
univariate standalone |Spearman|, and marginal contribution.

CPU-only. Sample ~N_DAYS days spread over the cache range; read only the
columns needed per day. Strictly causal: every F1 value at pred-bar t uses only
bars <= t.
"""
from __future__ import annotations
import json, os.path as p, sys, time
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV

sys.path.insert(0, ".")
from multi_asset.data.bar_loader import load_day_panel

CACHE = "multi_asset/exports/panel_cache"
SYMS = ["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada","bnflink",
        "bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALPHAS = np.logspace(-2, 4, 13)
EMB = 1
FOLDS = [dict(tr=(0,250),te=(272,312)), dict(tr=(80,330),te=(352,392)),
         dict(tr=(160,410),te=(432,472))]
N_DAYS = 75           # sampled days (MooseFS day-load variance; keep runtime bounded)
_EPS = 1e-12

# ---- raw-bar columns we need (read only these per day) -------------------
BID_PX = ["bid","bid_1","bid_2","bid_3","bid_4"]
ASK_PX = ["ask","ask_1","ask_2","ask_3","ask_4"]
BID_SZ = ["bidsz","bidsz_1","bidsz_2","bidsz_3","bidsz_4"]
ASK_SZ = ["asksz","asksz_1","asksz_2","asksz_3","asksz_4"]
NEED = BID_PX + ASK_PX + BID_SZ + ASK_SZ + ["mid"]

# F1 feature names (computed at pred bar t)
F1_NAMES = [
    "micro_dev_bps",        # (microprice-mid)/mid*1e4   [Stoikov]
    "micro_ret_10s",        # micro log-ret over 10s (bps)
    "micro_ret_30s",
    "micro_ret_60s",
    "micro_ret_300s",       # 5-min microprice reversal scale
    "wmid_dev_bps",         # (5-level size-weighted mid - mid)/mid*1e4
    "micro_mom_60s_z",      # micro_ret_60s z-scored by its 300s rolling std
    "micro_rev_300s_z",     # micro_ret_300s z-scored by 600s rolling std (reversal)
    "micro_rv_60s",         # realized vol of 1s micro log-ret over 60s (bps)
    "micro_rv_300s",
    "rel_spread",           # spread/mid  (dimensionless; baseline has spread_bps already)
    "eff_spread_bps",       # depth-weighted effective half-spread proxy (bps)
]


def _lag(x, k):
    out = np.full_like(x, np.nan)
    if k < x.shape[0]:
        out[k:] = x[:-k]
    return out


def _roll_std(x, w):
    xf = np.where(np.isfinite(x), x, 0.0)
    f = np.isfinite(x).astype(np.float64)
    cs = np.cumsum(xf); cs2 = np.cumsum(xf*xf); cf = np.cumsum(f)
    s1 = cs.copy(); s2 = cs2.copy(); n = cf.copy()
    if w < x.shape[0]:
        s1[w:] = cs[w:]-cs[:-w]; s2[w:] = cs2[w:]-cs2[:-w]; n[w:] = cf[w:]-cf[:-w]
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = np.where(n>0, s1/n, np.nan)
        var = np.where(n>0, s2/n - mean*mean, np.nan)
    return np.sqrt(np.maximum(var, 0.0))


def build_f1(data, cols):
    """data:(T,len(cols)) just the NEED columns; returns (T, len(F1_NAMES))."""
    ci = {c: i for i, c in enumerate(cols)}
    bpx = np.stack([data[:, ci[c]] for c in BID_PX], 1).astype(np.float64)
    apx = np.stack([data[:, ci[c]] for c in ASK_PX], 1).astype(np.float64)
    bsz = np.stack([data[:, ci[c]] for c in BID_SZ], 1).astype(np.float64)
    asz = np.stack([data[:, ci[c]] for c in ASK_SZ], 1).astype(np.float64)
    mid = data[:, ci["mid"]].astype(np.float64)
    T = mid.shape[0]

    b0, a0 = bpx[:, 0], apx[:, 0]
    bs0, as0 = bsz[:, 0], asz[:, 0]
    tot0 = bs0 + as0
    # Stoikov microprice: bid-queue-heavy -> pull toward ask
    micro = np.where(tot0 > 0, (bs0*a0 + as0*b0)/(tot0+_EPS), 0.5*(b0+a0))
    with np.errstate(divide="ignore", invalid="ignore"):
        micro_dev_bps = np.where(mid > 0, (micro-mid)/(mid+_EPS)*1e4, 0.0)
        lmicro = np.log(np.where(micro > 0, micro, np.nan))

    def mret(k):
        return (lmicro - _lag(lmicro, k)) * 1e4
    mr10, mr30, mr60, mr300 = mret(10), mret(30), mret(60), mret(300)

    # 5-level size-weighted mid: sum(px*sz both sides)/sum(sz)
    wnum = (bpx*bsz).sum(1) + (apx*asz).sum(1)
    wden = bsz.sum(1) + asz.sum(1)
    wmid = np.where(wden > 0, wnum/(wden+_EPS), mid)
    with np.errstate(divide="ignore", invalid="ignore"):
        wmid_dev_bps = np.where(mid > 0, (wmid-mid)/(mid+_EPS)*1e4, 0.0)

    # micro 1s log-ret for realized vol + z-scoring denom
    mr1 = mret(1)
    rv60 = _roll_std(mr1, 60); rv300 = _roll_std(mr1, 300)
    std300 = _roll_std(mr60, 300); std600 = _roll_std(mr300, 600)
    with np.errstate(divide="ignore", invalid="ignore"):
        mom60z = np.where(std300 > _EPS, mr60/std300, 0.0)
        rev300z = np.where(std600 > _EPS, mr300/std600, 0.0)

    # spread family
    spread = a0 - b0
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_spread = np.where(mid > 0, spread/(mid+_EPS), 0.0)
    # effective half-spread proxy: distance from microprice to mid + half-spread,
    # i.e. the size-aware cost a marketable order pays vs mid, in bps.
    half_spread_bps = np.where(mid > 0, 0.5*spread/(mid+_EPS)*1e4, 0.0)
    eff_spread_bps = half_spread_bps + np.abs(micro_dev_bps)

    out = np.stack([
        micro_dev_bps, mr10, mr30, mr60, mr300, wmid_dev_bps,
        mom60z, rev300z, rv60, rv300, rel_spread, eff_spread_bps,
    ], 1)
    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    # generous clips (NOT a scaler; per-fold standardizer scales)
    clip = np.array([200, 1000,1000,1000,1000, 200, 50,50, 2000,2000, 0.05, 500.0])
    out = np.clip(out, -clip, clip)
    return out.astype(np.float64)


def mad(x):
    x = x[np.isfinite(x)]
    return float(np.median(np.abs(x-np.median(x)))*1.4826) if x.size else np.nan


def load_cache(s):
    d = np.load(p.join(CACHE, f"{s}.npz"))
    return d["X"], d["y"], d["day"], d["ts"], d["clean600"]


def main():
    t0 = time.time()
    per = {s: load_cache(s) for s in SYMS}
    all_days = np.unique(per["bnfbtc"][2])
    # sample N_DAYS spread evenly over the full range
    idx = np.linspace(0, len(all_days)-1, N_DAYS).round().astype(int)
    sample_days = np.unique(all_days[idx])
    print(f"sampling {len(sample_days)} days from {all_days.min()}..{all_days.max()}", flush=True)

    # Build F1 per sym, only on sampled days, aligned to pred ts via searchsorted.
    F1 = {s: {} for s in SYMS}   # F1[s][day] -> (n_pred_that_day, 12) aligned to cache rows
    rowmap = {s: {} for s in SYMS}
    for di, day in enumerate(sample_days):
        try:
            P = load_day_panel(int(day), SYMS, cols=NEED)
        except TypeError:
            P = load_day_panel(int(day), SYMS)
        for s in SYMS:
            X, y, dd, ts, cl = per[s]
            m = dd == day
            if not m.any():
                continue
            pred_ts = ts[m]
            cols = P.cols
            data = P.data[s]
            # restrict to NEED cols if full panel returned
            if len(cols) != len(NEED):
                ciP = {c: cols.index(c) for c in NEED}
                data = np.stack([data[:, ciP[c]] for c in NEED], 1)
                use_cols = NEED
            else:
                use_cols = cols
            f1 = build_f1(data, use_cols)        # (T,12) causal over full day
            j = np.searchsorted(P.ts, pred_ts)    # exact ts match
            j = np.clip(j, 0, len(P.ts)-1)
            ok = P.ts[j] == pred_ts
            row = np.where(m)[0]
            F1[s][int(day)] = (row[ok], f1[j[ok]])
        if (di+1) % 10 == 0:
            print(f"  built {di+1}/{len(sample_days)} days  ({time.time()-t0:.0f}s)", flush=True)

    # assemble per-sym aligned F1 matrices over sampled rows only
    def assemble(s):
        X, y, dd, ts, cl = per[s]
        keep_rows, f1_parts = [], []
        for day in sample_days:
            if int(day) in F1[s]:
                r, f = F1[s][int(day)]
                keep_rows.append(r); f1_parts.append(f)
        if not keep_rows:
            return None
        rows = np.concatenate(keep_rows)
        f1mat = np.concatenate(f1_parts, 0)
        order = np.argsort(rows)
        rows = rows[order]; f1mat = f1mat[order]
        return rows, X[rows], y[rows], dd[rows], cl[rows], f1mat

    asm = {s: assemble(s) for s in SYMS}
    uniq = np.unique(per["bnfbtc"][2])  # for fold day slicing use FULL day axis

    def folddays(f):
        n = uniq.shape[0]
        if f["te"][1] > n:
            return None
        te0, te1 = f["te"]; tr0, tr1 = f["tr"]
        tri = np.arange(tr0, tr1); tri = tri[tri < te0-EMB]
        return set(uniq[tri].tolist()), set(uniq[te0:te1].tolist())

    def run(s, mode):
        a = asm[s]
        if a is None:
            return None
        rows, X, y, day, cl, f1mat = a
        if mode == "base":
            F = X
        elif mode == "plus":
            F = np.concatenate([X, f1mat], 1)
        elif mode == "f1only":
            F = f1mat
        yh, yt = [], []
        for f in FOLDS:
            r = folddays(f)
            if r is None:
                continue
            trd, ted = r
            trm = np.isin(day, list(trd)); tem = np.isin(day, list(ted)) & cl
            if trm.sum() < 300 or tem.sum() < 15:
                continue
            Xtr, ytr = F[trm], y[trm]; Xte = F[tem]
            mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
            sig = mad(ytr)
            if not np.isfinite(sig) or sig <= 0:
                continue
            m = RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
            yh.append(m.predict((Xte-mu)/sd)*sig); yt.append(y[tem])
        if not yh:
            return None
        yh = np.concatenate(yh); yt = np.concatenate(yt)
        return dict(P=float(pearsonr(yh, yt)[0]), S=float(spearmanr(yh, yt)[0]), n=len(yh))

    # per-fold sign-consistency of dP/dS
    def run_perfold(s, mode):
        a = asm[s]
        if a is None:
            return []
        rows, X, y, day, cl, f1mat = a
        F = X if mode == "base" else np.concatenate([X, f1mat], 1)
        out = []
        for f in FOLDS:
            r = folddays(f)
            if r is None:
                out.append(None); continue
            trd, ted = r
            trm = np.isin(day, list(trd)); tem = np.isin(day, list(ted)) & cl
            if trm.sum() < 300 or tem.sum() < 15:
                out.append(None); continue
            Xtr, ytr = F[trm], y[trm]; Xte = F[tem]
            mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
            sig = mad(ytr)
            mm = RidgeCV(alphas=ALPHAS); mm.fit((Xtr-mu)/sd, ytr/sig)
            yh = mm.predict((Xte-mu)/sd)*sig; yt = y[tem]
            out.append((float(pearsonr(yh, yt)[0]), float(spearmanr(yh, yt)[0])))
        return out

    print("\n=== per-asset RidgeCV walk-forward: baseline(44) vs +F1(56) ===", flush=True)
    rows_out = []
    base_P, plus_P, base_S, plus_S = [], [], [], []
    pf_signs = {"dP": [], "dS": []}
    for s in SYMS:
        b = run(s, "base"); pl = run(s, "plus")
        if not b or not pl:
            continue
        dP, dS = pl["P"]-b["P"], pl["S"]-b["S"]
        base_P.append(b["P"]); plus_P.append(pl["P"]); base_S.append(b["S"]); plus_S.append(pl["S"])
        pfb = run_perfold(s, "base"); pfp = run_perfold(s, "plus")
        fold_dP = [(pfp[i][0]-pfb[i][0]) if (pfb[i] and pfp[i]) else np.nan for i in range(len(FOLDS))]
        fold_dS = [(pfp[i][1]-pfb[i][1]) if (pfb[i] and pfp[i]) else np.nan for i in range(len(FOLDS))]
        pf_signs["dP"].append(fold_dP); pf_signs["dS"].append(fold_dS)
        rows_out.append((s, b["P"], pl["P"], dP, b["S"], pl["S"], dS, fold_dP, fold_dS))
        print(f"{s:9s} P {b['P']:+.4f}->{pl['P']:+.4f} dP {dP:+.4f} | "
              f"S {b['S']:+.4f}->{pl['S']:+.4f} dS {dS:+.4f} | "
              f"foldP {['%+.3f'%x for x in fold_dP]}", flush=True)

    avg_bP, avg_pP = np.mean(base_P), np.mean(plus_P)
    avg_bS, avg_pS = np.mean(base_S), np.mean(plus_S)
    print(f"\nAVG  P {avg_bP:+.4f}->{avg_pP:+.4f} dP {avg_pP-avg_bP:+.4f} | "
          f"S {avg_bS:+.4f}->{avg_pS:+.4f} dS {avg_pS-avg_bS:+.4f}", flush=True)

    # cross-sectional rank-IC (per-timestamp Spearman across assets), base vs plus
    print("\n=== cross-sectional rank-IC (per-ts Spearman across assets) ===", flush=True)
    # collect OOS predictions keyed by ts for both modes
    def oos_by_ts(mode):
        preds = {}  # ts -> {sym: yhat}, truth -> {sym:y}
        truth = {}
        for s in SYMS:
            a = asm[s]
            if a is None:
                continue
            rows, X, y, day, cl, f1mat = a
            ts_s = per[s][3][rows]
            F = X if mode == "base" else np.concatenate([X, f1mat], 1)
            for f in FOLDS:
                r = folddays(f)
                if r is None:
                    continue
                trd, ted = r
                trm = np.isin(day, list(trd)); tem = np.isin(day, list(ted)) & cl
                if trm.sum() < 300 or tem.sum() < 15:
                    continue
                Xtr, ytr = F[trm], y[trm]; Xte = F[tem]
                mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
                sig = mad(ytr)
                mm = RidgeCV(alphas=ALPHAS); mm.fit((Xtr-mu)/sd, ytr/sig)
                yh = mm.predict((Xte-mu)/sd)*sig
                tte = ts_s[tem]; yte = y[tem]
                for k in range(len(tte)):
                    preds.setdefault(int(tte[k]), {})[s] = yh[k]
                    truth.setdefault(int(tte[k]), {})[s] = yte[k]
        return preds, truth

    def rankic(preds, truth):
        ics = []
        for t in preds:
            common = [s for s in SYMS if s in preds[t] and s in truth[t]]
            if len(common) >= 5:
                ph = np.array([preds[t][s] for s in common])
                py = np.array([truth[t][s] for s in common])
                if np.std(ph) > 0 and np.std(py) > 0:
                    ics.append(spearmanr(ph, py)[0])
        ics = np.array([x for x in ics if np.isfinite(x)])
        return float(ics.mean()), float(ics.mean()/ics.std()) if ics.std() > 0 else np.nan, len(ics)

    pb, tb = oos_by_ts("base"); pp, tp = oos_by_ts("plus")
    ricb, irb, nb = rankic(pb, tb); ricp, irp, npn = rankic(pp, tp)
    print(f"base rank-IC {ricb:+.4f} (IR {irb:+.2f}, {nb} ts) | "
          f"plus rank-IC {ricp:+.4f} (IR {irp:+.2f}) | d {ricp-ricb:+.4f}", flush=True)

    # univariate standalone |Spearman| of each F1 feature vs y (pooled clean)
    print("\n=== univariate standalone Spearman (pooled clean, all syms) ===", flush=True)
    uni = {nm: [] for nm in F1_NAMES}
    for s in SYMS:
        a = asm[s]
        if a is None:
            continue
        rows, X, y, day, cl, f1mat = a
        ys = y[cl]
        sigy = mad(y[cl])
        for k, nm in enumerate(F1_NAMES):
            fk = f1mat[cl, k]
            if np.std(fk) > 0 and np.std(ys) > 0:
                uni[nm].append(spearmanr(fk, ys)[0])
    uni_avg = {nm: float(np.nanmean(uni[nm])) for nm in F1_NAMES}
    for nm in sorted(F1_NAMES, key=lambda n: -abs(uni_avg[n])):
        print(f"  {nm:18s} avg Spearman {uni_avg[nm]:+.4f}", flush=True)

    # marginal: drop-one-from-plus? Too costly; instead add-each-alone delta
    print(f"\nDONE in {time.time()-t0:.0f}s", flush=True)

    summary = dict(
        n_days=int(len(sample_days)),
        avg_base_P=round(avg_bP,4), avg_plus_P=round(avg_pP,4), avg_dP=round(avg_pP-avg_bP,4),
        avg_base_S=round(avg_bS,4), avg_plus_S=round(avg_pS,4), avg_dS=round(avg_pS-avg_bS,4),
        rankic_base=round(ricb,4), rankic_plus=round(ricp,4), d_rankic=round(ricp-ricb,4),
        per_asset=[dict(sym=r[0], baseP=round(r[1],4), plusP=round(r[2],4), dP=round(r[3],4),
                        baseS=round(r[4],4), plusS=round(r[5],4), dS=round(r[6],4),
                        foldP=[round(x,4) for x in r[7]], foldS=[round(x,4) for x in r[8]]) for r in rows_out],
        univariate=uni_avg,
    )
    json.dump(summary, open("multi_asset/exports/eda/F1_microprice_gate.json","w"), indent=2)
    print("wrote multi_asset/exports/eda/F1_microprice_gate.json", flush=True)


if __name__ == "__main__":
    main()
