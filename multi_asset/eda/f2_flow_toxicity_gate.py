"""F2 GATE — Order-flow toxicity & price impact (multi-asset y_600).

Builds a family of strictly-causal flow/toxicity/impact features at each
panel_cache pred bar, aligned by exact ts onto the raw 1s bar grid via
searchsorted. Then runs per-asset RidgeCV walk-forward: baseline = the 44 hand
features (panel_cache X) vs +F2 family. Reports per-asset Pearson + Spearman
deltas, cross-sectional rank-IC delta, and univariate |Spearman| of each F2
feature. CPU-only, sampled days.

FAMILY (all scale-invariant ratios / regression slopes, so cross-asset QTY
multiplier cancels):
  Dollar-flow imbalance     (tdQtyPxBuy-Sell)/(sum)         30/60/300s
  Trade-count imbalance     (tdCntBuy-Sell)/(sum)           30/60/300s
  Trade-size asymmetry      (avgBuySize-avgSellSize)/(sum)  60/300s
  Avg trade size (log)      log(totQty/totCnt)              60/300s   (regime)
  VPIN (qty)                sum|buy-sell|/sum(tot)          60/300s
  VPIN (dollar)             sum|$buy-$sell|/sum($tot)       60/300s
  Kyle lambda               rolling OLS slope dMid~signed$flow  300/600s
  Kyle lambda |.|           |slope| magnitude               300/600s
  Flow autocorr (persist)   corr(flow_t, flow_{t-30}) win   300s
  Flow-return toxicity      corr(signed$flow, dMid) win     300s
"""
from __future__ import annotations
import os, sys, json
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.bar_loader import load_day_panel  # noqa: E402

CACHE = os.path.join(REPO, "multi_asset/exports/panel_cache")
SYMS = ["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada",
        "bnflink","bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALPHAS = np.logspace(-2, 4, 13)
EMB = 1
FOLDS = [dict(tr=(0,250),te=(272,312)), dict(tr=(80,330),te=(352,392)),
         dict(tr=(160,410),te=(432,472))]
EPS = 1e-9

# ---------------- causal primitives ----------------
def roll_sum(x, w):
    xf = np.where(np.isfinite(x), x, 0.0)
    cs = np.cumsum(xf); out = cs.copy()
    if w < x.shape[0]: out[w:] = cs[w:] - cs[:-w]
    return out

def lag(x, k):
    out = np.full_like(x, np.nan)
    if k < x.shape[0]: out[k:] = x[:-k]
    return out

def imb(a, b):
    d = a + b
    return np.where(np.abs(d) > EPS, (a - b) / d, 0.0)

def roll_cov_slope(yv, xv, w):
    """Rolling OLS slope of yv on xv over trailing window w (causal).
    slope = cov(x,y)/var(x). Returns array length T."""
    n = float(w)
    sx = roll_sum(xv, w); sy = roll_sum(yv, w)
    sxx = roll_sum(xv*xv, w); sxy = roll_sum(xv*yv, w)
    cov = sxy/n - (sx/n)*(sy/n)
    var = sxx/n - (sx/n)**2
    return np.where(var > EPS, cov/var, 0.0), cov, var

def roll_corr(yv, xv, w):
    n = float(w)
    sx = roll_sum(xv, w); sy = roll_sum(yv, w)
    sxx = roll_sum(xv*xv, w); syy = roll_sum(yv*yv, w); sxy = roll_sum(xv*yv, w)
    cov = sxy/n - (sx/n)*(sy/n)
    vx = np.maximum(sxx/n - (sx/n)**2, 0.0)
    vy = np.maximum(syy/n - (sy/n)**2, 0.0)
    den = np.sqrt(vx*vy)
    return np.where(den > EPS, cov/den, 0.0)

# ---------------- F2 family builder ----------------
def build_f2(P, sym):
    """Returns (F (T, k) full-grid causal features, names)."""
    ci = {c: i for i, c in enumerate(P.cols)}
    d = P.data[sym]
    col = lambda c: d[:, ci[c]].astype(np.float64)
    mid = col("mid")
    qb, qs = col("tdQtyBuy"), col("tdQtySell")
    pxb, pxs = col("tdQtyPxBuy"), col("tdQtyPxSell")
    cb, cs = col("tdCntBuy"), col("tdCntSell")

    with np.errstate(divide="ignore", invalid="ignore"):
        lm = np.log(np.maximum(mid, EPS))
    dmid = lm - lag(lm, 1)            # 1s mid log-ret
    dmid = np.nan_to_num(dmid, nan=0.0) * 1e4   # bps

    signed_dollar = pxb - pxs        # signed taker notional (per bar)
    signed_qty = qb - qs
    tot_dollar = pxb + pxs
    tot_qty = qb + qs
    tot_cnt = cb + cs

    feats, names = [], []
    def add(nm, v): feats.append(np.asarray(v, np.float64)); names.append(nm)

    # 1) dollar-flow imbalance 30/60/300
    for w in (30, 60, 300):
        add(f"f2_dollimb_{w}s", imb(roll_sum(pxb, w), roll_sum(pxs, w)))
    # 2) trade-count imbalance 30/60/300
    for w in (30, 60, 300):
        add(f"f2_cntimb_{w}s", imb(roll_sum(cb, w), roll_sum(cs, w)))
    # 3) trade-size asymmetry: avg buy size vs avg sell size, normalized
    for w in (60, 300):
        avg_b = roll_sum(qb, w) / (roll_sum(cb, w) + EPS)
        avg_s = roll_sum(qs, w) / (roll_sum(cs, w) + EPS)
        add(f"f2_sizeasym_{w}s", imb(avg_b, avg_s))
    # 4) avg trade size (log) — regime conditioner
    for w in (60, 300):
        avg_sz = roll_sum(tot_qty, w) / (roll_sum(tot_cnt, w) + EPS)
        add(f"f2_logtsize_{w}s", np.log(np.maximum(avg_sz, EPS)))
    # 5) VPIN (qty) 60/300
    for w in (60, 300):
        num = roll_sum(np.abs(signed_qty), w); den = roll_sum(tot_qty, w)
        add(f"f2_vpin_qty_{w}s", np.where(den > EPS, num/den, 0.0))
    # 6) VPIN (dollar) 60/300
    for w in (60, 300):
        num = roll_sum(np.abs(signed_dollar), w); den = roll_sum(tot_dollar, w)
        add(f"f2_vpin_doll_{w}s", np.where(den > EPS, num/den, 0.0))
    # 7) Kyle lambda: rolling OLS slope of dmid on signed_dollar 300/600
    #    scale signed_dollar to a stable unit via its own rolling RMS so slope is
    #    cross-asset comparable (slope of bps-return per RMS-unit of flow).
    for w in (300, 600):
        rms = np.sqrt(roll_sum(signed_dollar*signed_dollar, w)/float(w)) + EPS
        x_unit = signed_dollar / rms     # ~unit variance flow
        slope, _, _ = roll_cov_slope(dmid, x_unit, w)
        add(f"f2_kyle_{w}s", slope)
        add(f"f2_kyle_abs_{w}s", np.abs(slope))
    # 8) flow autocorrelation / persistence: corr(signed_dollar_t, lag30) win300
    sd_lag = lag(signed_dollar, 30)
    add("f2_flowac_300s", roll_corr(signed_dollar, sd_lag, 300))
    # 9) flow-return toxicity: corr(signed_dollar, dmid) win300  (contemporaneous
    #    impact alignment — high = flow moves price = toxic/informed)
    add("f2_flowtox_300s", roll_corr(signed_dollar, dmid, 300))

    F = np.stack(feats, axis=1)
    F = np.nan_to_num(F, nan=0.0, posinf=0.0, neginf=0.0)
    return F.astype(np.float32), names

# ---------------- load panel_cache ----------------
def load_cache(s):
    z = np.load(os.path.join(CACHE, f"{s}.npz"))
    return z["X"], z["y"], z["day"], z["ts"], z["clean600"]

CACHE_F2 = os.path.join(REPO, "multi_asset/exports/eda/_f2_assembled.npz")

def main():
    np.random.seed(0)
    per = {s: load_cache(s) for s in SYMS}
    # FULL cache day axis (defines the fold index layout, ~487 days)
    cache_days = np.unique(per["bnfbtc"][2])
    # sample ~130 days spread across the full range
    n_sample = 130
    if cache_days.shape[0] > n_sample:
        idx = np.linspace(0, cache_days.shape[0]-1, n_sample).round().astype(int)
        sample_days = np.unique(cache_days[idx])
    else:
        sample_days = cache_days
    print(f"[F2] sampling {sample_days.shape[0]} days "
          f"({sample_days.min()}..{sample_days.max()})", flush=True)

    asm = {}
    names_ref = None
    if os.path.exists(CACHE_F2) and os.environ.get("F2_REBUILD", "0") != "1":
        z = np.load(CACHE_F2, allow_pickle=True)
        names_ref = list(z["names"])
        for s in SYMS:
            if f"{s}__X" in z:
                asm[s] = dict(X=z[f"{s}__X"], y=z[f"{s}__y"], day=z[f"{s}__day"],
                              cl=z[f"{s}__cl"], ts=z[f"{s}__ts"], F2=z[f"{s}__F2"])
        print(f"[F2] loaded cached assembled arrays ({len(asm)} assets)", flush=True)
    else:
        # build per-asset F2 arrays aligned to cache rows, only for sampled days
        f2_rows = {s: {} for s in SYMS}   # day -> (cache_row_idx, F2 (m,k))
        for di, day in enumerate(sample_days):
            day = int(day)
            try:
                P = load_day_panel(day, SYMS)
            except Exception as e:
                print(f"  skip {day}: {e}", flush=True); continue
            Pts = P.ts
            for s in SYMS:
                X, y, cday, cts, cl = per[s]
                sel = np.where(cday == day)[0]
                if sel.size == 0: continue
                tsel = cts[sel]
                pos = np.searchsorted(Pts, tsel)
                ok = (pos < Pts.shape[0])
                pos_ok = np.clip(pos, 0, Pts.shape[0]-1)
                exact = ok & (Pts[pos_ok] == tsel)
                if exact.sum() == 0: continue
                F, nm = build_f2(P, s)
                if names_ref is None: names_ref = nm
                rows = sel[exact]
                f2sel = F[pos_ok[exact]]
                f2_rows[s][day] = (rows, f2sel)
            if (di+1) % 25 == 0:
                print(f"  ..{di+1}/{sample_days.shape[0]} days built", flush=True)

        for s in SYMS:
            days = sorted(f2_rows[s].keys())
            if not days: continue
            rowidx = np.concatenate([f2_rows[s][d][0] for d in days])
            F2 = np.concatenate([f2_rows[s][d][1] for d in days], axis=0)
            X, y, cday, cts, cl = per[s]
            asm[s] = dict(X=X[rowidx], y=y[rowidx], day=cday[rowidx],
                          cl=cl[rowidx], ts=cts[rowidx], F2=F2)
        # persist assembled arrays for fast re-gate
        save = dict(names=np.array(names_ref, dtype=object))
        for s in asm:
            for k in ("X", "y", "day", "cl", "ts", "F2"):
                save[f"{s}__{k}"] = asm[s][k]
        np.savez(CACHE_F2, **save)
        print(f"[F2] saved assembled arrays -> {CACHE_F2}", flush=True)

    K = len(names_ref)
    print(f"[F2] assembled. K={K} features. "
          f"rows/asset e.g. btc={asm['bnfbtc']['X'].shape[0]}", flush=True)

    # ---------- per-asset RidgeCV walk-forward ----------
    def mad(x):
        x = x[np.isfinite(x)]
        return float(np.median(np.abs(x-np.median(x)))*1.4826) if x.size else np.nan

    # Fold index ranges are defined against the FULL cache day axis (~487 days),
    # NOT the sampled subset. We build the train/test day-SETS from cache_days,
    # then mask the assembled (sampled) rows by membership — sampled days that
    # fall in a fold window participate; others are skipped. 1-day embargo.
    FULL_DAYS = cache_days

    def folddays(f):
        n = FULL_DAYS.shape[0]
        if f["te"][1] > n: return None
        te0, te1 = f["te"]; tr0, tr1 = f["tr"]
        tri = np.arange(tr0, tr1); tri = tri[tri < te0-EMB]
        return set(FULL_DAYS[tri].tolist()), set(FULL_DAYS[te0:te1].tolist())

    def run(s, with_f2):
        a = asm[s]; X, y, day, cl, F2 = a["X"], a["y"], a["day"], a["cl"], a["F2"]
        Fmat = np.concatenate([X, F2], axis=1) if with_f2 else X
        yh, yt, idxh = [], [], []
        for f in FOLDS:
            r = folddays(f)
            if r is None: continue
            trd, ted = r
            trm = np.isin(day, list(trd)); tem = np.isin(day, list(ted)) & cl
            if trm.sum() < 300 or tem.sum() < 20: continue
            Xtr, ytr = Fmat[trm], y[trm]; Xte = Fmat[tem]
            mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
            sig = mad(ytr)
            if not np.isfinite(sig) or sig <= 0: continue
            m = RidgeCV(alphas=ALPHAS)
            m.fit((Xtr-mu)/sd, ytr/sig)
            pred = m.predict((Xte-mu)/sd)*sig
            yh.append(pred); yt.append(y[tem]); idxh.append(np.where(tem)[0])
        if not yh: return None
        yh = np.concatenate(yh); yt = np.concatenate(yt)
        return dict(P=float(pearsonr(yh, yt)[0]), S=float(spearmanr(yh, yt)[0]),
                    n=len(yh))

    def run_perfold(s, with_f2):
        """return list of per-fold (P,S) for sign-consistency check."""
        a = asm[s]; X, y, day, cl, F2 = a["X"], a["y"], a["day"], a["cl"], a["F2"]
        Fmat = np.concatenate([X, F2], axis=1) if with_f2 else X
        out = []
        for f in FOLDS:
            r = folddays(f)
            if r is None: out.append(None); continue
            trd, ted = r
            trm = np.isin(day, list(trd)); tem = np.isin(day, list(ted)) & cl
            if trm.sum() < 300 or tem.sum() < 20: out.append(None); continue
            Xtr, ytr = Fmat[trm], y[trm]; Xte = Fmat[tem]
            mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
            sig = mad(ytr)
            if not np.isfinite(sig) or sig <= 0: out.append(None); continue
            m = RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
            pred = m.predict((Xte-mu)/sd)*sig
            out.append((float(pearsonr(pred, y[tem])[0]),
                        float(spearmanr(pred, y[tem])[0])))
        return out

    res = {}
    pf_base, pf_plus = {}, {}
    for s in SYMS:
        if s not in asm: continue
        b = run(s, False); p = run(s, True)
        res[s] = dict(base=b, plus=p,
                      dP=(p["P"]-b["P"]) if b and p else None,
                      dS=(p["S"]-b["S"]) if b and p else None)
        pf_base[s] = run_perfold(s, False); pf_plus[s] = run_perfold(s, True)

    ok = [s for s in SYMS if s in res and res[s]["base"] and res[s]["plus"]]
    avgP_b = np.mean([res[s]["base"]["P"] for s in ok])
    avgP_p = np.mean([res[s]["plus"]["P"] for s in ok])
    avgS_b = np.mean([res[s]["base"]["S"] for s in ok])
    avgS_p = np.mean([res[s]["plus"]["S"] for s in ok])

    print("\n=== PER-ASSET BASELINE vs +F2 ===", flush=True)
    print(f"{'asset':9s} {'Pb':>8s} {'Pp':>8s} {'dP':>8s} {'Sb':>8s} {'Sp':>8s} {'dS':>8s}")
    for s in ok:
        r = res[s]
        print(f"{s:9s} {r['base']['P']:>+8.4f} {r['plus']['P']:>+8.4f} {r['dP']:>+8.4f} "
              f"{r['base']['S']:>+8.4f} {r['plus']['S']:>+8.4f} {r['dS']:>+8.4f}")
    print(f"{'AVG':9s} {avgP_b:>+8.4f} {avgP_p:>+8.4f} {avgP_p-avgP_b:>+8.4f} "
          f"{avgS_b:>+8.4f} {avgS_p:>+8.4f} {avgS_p-avgS_b:>+8.4f}")

    # per-fold sign consistency of dP
    print("\n=== per-fold dP (sign consistency) ===", flush=True)
    fold_dP = [[] for _ in FOLDS]
    for s in ok:
        for fi in range(len(FOLDS)):
            b = pf_base[s][fi]; p = pf_plus[s][fi]
            if b and p: fold_dP[fi].append(p[0]-b[0])
    for fi in range(len(FOLDS)):
        arr = np.array(fold_dP[fi])
        print(f"  fold{fi}: mean dP={arr.mean():+.4f}  n_assets={arr.size}  "
              f"frac_pos={(arr>0).mean():.2f}")

    # ---------- cross-sectional rank-IC delta ----------
    def xsec_rankic(with_f2):
        # predict per-asset (walk-forward), then per-timestamp rank corr across
        # assets. Build pred arrays keyed by ts.
        preds = {}; ys = {}
        for s in ok:
            a = asm[s]; X, y, day, cl, F2, ts = (a["X"], a["y"], a["day"],
                                                 a["cl"], a["F2"], a["ts"])
            Fmat = np.concatenate([X, F2], axis=1) if with_f2 else X
            for f in FOLDS:
                r = folddays(f)
                if r is None: continue
                trd, ted = r
                trm = np.isin(day, list(trd)); tem = np.isin(day, list(ted)) & cl
                if trm.sum() < 300 or tem.sum() < 20: continue
                Xtr, ytr = Fmat[trm], y[trm]; Xte = Fmat[tem]
                mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
                sig = mad(ytr)
                if not np.isfinite(sig) or sig <= 0: continue
                m = RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
                pred = m.predict((Xte-mu)/sd)*sig
                tsv = ts[tem]; yv = y[tem]
                for t, pv, yvv in zip(tsv, pred, yv):
                    preds.setdefault(int(t), {})[s] = pv
                    ys.setdefault(int(t), {})[s] = yvv
        ics = []
        for t in preds:
            common = [s for s in preds[t] if s in ys[t]]
            if len(common) < 5: continue
            pv = np.array([preds[t][s] for s in common])
            yv = np.array([ys[t][s] for s in common])
            if np.std(pv) < 1e-12 or np.std(yv) < 1e-12: continue
            ics.append(spearmanr(pv, yv)[0])
        ics = np.array([i for i in ics if np.isfinite(i)])
        return float(ics.mean()), float(ics.mean()/(ics.std()+EPS)), ics.size

    ric_b, ir_b, nb = xsec_rankic(False)
    ric_p, ir_p, npp = xsec_rankic(True)
    print(f"\n=== cross-sectional rank-IC ===", flush=True)
    print(f"  baseline rank-IC={ric_b:+.4f} (IR={ir_b:+.2f}, n_ts={nb})")
    print(f"  +F2      rank-IC={ric_p:+.4f} (IR={ir_p:+.2f}, n_ts={npp})")
    print(f"  delta rank-IC = {ric_p-ric_b:+.4f}")

    # ---------- univariate |Spearman| of each F2 feature vs y ----------
    print("\n=== univariate F2 |Spearman| vs y (pooled over assets, clean rows) ===",
          flush=True)
    uni = []
    for k in range(K):
        sps = []
        for s in ok:
            a = asm[s]
            m = a["cl"]
            fv = a["F2"][m, k]; yv = a["y"][m]
            good = np.isfinite(fv) & np.isfinite(yv)
            if good.sum() < 200 or np.std(fv[good]) < 1e-12: continue
            sps.append(spearmanr(fv[good], yv[good])[0])
        if sps:
            uni.append((names_ref[k], float(np.mean(sps))))
    uni.sort(key=lambda z: -abs(z[1]))
    for nm, sp in uni:
        print(f"  {nm:22s} avg-Spearman={sp:+.4f}")

    out = dict(family="F2_flow_toxicity",
               n_days=int(sample_days.shape[0]),
               K=K, names=names_ref,
               avgP_base=round(avgP_b,4), avgP_plus=round(avgP_p,4),
               avg_dP=round(avgP_p-avgP_b,4),
               avgS_base=round(avgS_b,4), avgS_plus=round(avgS_p,4),
               avg_dS=round(avgS_p-avgS_b,4),
               rankIC_base=round(ric_b,4), rankIC_plus=round(ric_p,4),
               rankIC_delta=round(ric_p-ric_b,4),
               per_asset={s: dict(Pb=res[s]["base"]["P"], Pp=res[s]["plus"]["P"],
                                  dP=res[s]["dP"], Sb=res[s]["base"]["S"],
                                  Sp=res[s]["plus"]["S"], dS=res[s]["dS"])
                          for s in ok},
               fold_dP_mean=[float(np.mean(fold_dP[fi])) for fi in range(len(FOLDS))],
               fold_dP_fracpos=[float((np.array(fold_dP[fi])>0).mean()) for fi in range(len(FOLDS))],
               univariate=uni)
    os.makedirs(os.path.join(REPO, "multi_asset/exports/eda"), exist_ok=True)
    json.dump(out, open(os.path.join(REPO, "multi_asset/exports/eda/F2_flow_toxicity.json"), "w"), indent=2)
    print("\n[F2] wrote exports/eda/F2_flow_toxicity.json", flush=True)


def _days_of(per):
    return per["bnfbtc"][2]


if __name__ == "__main__":
    main()
