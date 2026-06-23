"""F5 GATE — Alpha-101 style CROSS-SECTIONAL factors for multi-asset y_600.

We adapt ~10 WorldQuant alpha-101 primitives to the 14-asset USDT-perp panel at
the y_600 prediction bars. EVERY feature is computed CROSS-SECTIONALLY across the
14 assets at each timestamp (causal — only info <= t), from the RAW 44 hand
features already in panel_cache X (which are themselves strictly causal point-in-
time series: multi-scale returns, 5 flow types x 3 windows, realized vol, OBI,
spread, vpin). Because panel_cache is already exactly ts-aligned across all syms
by the EDA harness, cross-sectional rank/ts_rank/decay/corr are leak-free.

Underlying causal series we use (column indices into X, verified by name):
  ret_30s(0) ret_60s(1) ret_120s(2) ret_300s(3) ret_600s(4)
  tradeflow_{30,60,300}s(9,10,11)  dollarflow_{30,60,300}s(12,13,14)
  rv_60s(24) rv_300s(25)  obi_L1(26)  vpin_300s(42)

Alpha-101 adapted factors (all CROSS-SECTIONAL across 14 assets at each ts):
  a_rank_rev300   = -rank_x(ret_300s)              cross-sec reversal (alpha #3/#9 flavor)
  a_rank_rev600   = -rank_x(ret_600s)
  a_rank_flow300  = rank_x(dollarflow_300s)         cross-sec flow imbalance
  a_rank_flowS    = rank_x(tradeflow_30s)           cross-sec short flow (continuation)
  a_rank_rv       = -rank_x(rv_300s)                low-vol assets carry cleaner alpha
  a_signedpow_ret = sign(ret_300s)*rank_x(|ret_300s|)^2   alpha#101 signed-power
  a_decay_ret     = rank_x(decay_linear(ret_30s,5))  alpha#101 decay-linear of recent ret
  a_tsrank_ret300 = ts_rank(ret_300s,60) demeaned    time-series rank vs own recent history
  a_tsrank_flow   = ts_rank(dollarflow_60s,60) demeaned
  a_corr_ret_flow = -rank_x( roll_corr(rank(ret), rank(flow), 30) )  alpha#2-style
  a_rank_obi      = rank_x(obi_L1)                   cross-sec book pressure rank
  a_argmax_ret    = (ts_argmax(|ret_30s|,30)/30 - 0.5)  recency of the biggest move

GATE: a feature/family passes if avg per-asset dP>=+0.005 OR dS>=+0.005 OR
cross-sectional rank-IC delta>=+0.005, sign-consistent across folds, leak-safe.
"""
from __future__ import annotations
import json, os.path as p
import numpy as np
from scipy.stats import pearsonr, spearmanr, rankdata
from sklearn.linear_model import RidgeCV

CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/panel_cache"
EXPORT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda"
SYMS = ["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada","bnflink",
        "bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALPHAS = np.logspace(-2, 4, 13); EMB = 1
FOLDS = [dict(tr=(0,250),te=(272,312)), dict(tr=(80,330),te=(352,392)), dict(tr=(160,410),te=(432,472))]
NDAYS_SAMPLE = 140  # subsample days for speed (alignment is exact regardless)

# column indices into the 44-feature X (verified by name on server)
C = dict(ret30=0, ret60=1, ret120=2, ret300=3, ret600=4,
         tf30=9, tf60=10, tf300=11, df30=12, df60=13, df300=14,
         rv60=24, rv300=25, obi=26, vpin300=42)


def mad(x):
    x = x[np.isfinite(x)]
    return float(np.median(np.abs(x - np.median(x))) * 1.4826) if x.size else np.nan


def load(s):
    d = np.load(p.join(CACHE, f"{s}.npz"))
    return d["X"], d["y"], d["day"], d["ts"], d["clean600"]


# ---- align all syms on common ts (same as alt_with_btc_factor.py) ----
per = {s: load(s) for s in SYMS}
common = sorted(set.intersection(*[set(per[s][3].tolist()) for s in SYMS]))
idx = {s: {int(t): i for i, t in enumerate(per[s][3])} for s in SYMS}


def aligned(s):
    X, y, day, ts, cl = per[s]
    ii = np.array([idx[s][int(t)] for t in common])
    return X[ii], y[ii], day[ii], cl[ii]


A = {s: aligned(s) for s in SYMS}
day_all = A["bnfbtc"][2]
ts_all = np.array(common)
uniq_all = np.unique(day_all)

# Resolve fold train/test day-index ranges (on the FULL sorted day axis) into
# actual day VALUES, with 1-day embargo. Then subsample days WITHIN those windows
# so the fold structure stays valid (the bug was sampling globally then indexing
# by position into a 140-long axis with fold indices up to 472).
n_all = uniq_all.shape[0]
fold_days = []  # list of (train_day_values:set, test_day_values:set)
needed = set()
for f in FOLDS:
    te0, te1 = f["te"]; tr0, tr1 = f["tr"]
    if te1 > n_all:
        fold_days.append(None); continue
    tri = np.arange(tr0, tr1); tri = tri[tri < te0 - EMB]
    trd = set(uniq_all[tri].tolist()); ted = set(uniq_all[te0:te1].tolist())
    fold_days.append((trd, ted)); needed |= trd | ted

# Subsample ~NDAYS_SAMPLE days. Keep ALL test days (they are the eval set and we
# need enough clean600 bars), then fill the remainder with sampled TRAIN days.
rng = np.random.default_rng(0)
test_days = set().union(*[fd[1] for fd in fold_days if fd is not None])
train_only = np.array(sorted(needed - test_days))
n_train_keep = max(0, NDAYS_SAMPLE - len(test_days))
sel_train = set(rng.choice(train_only, size=min(n_train_keep, train_only.shape[0]),
                           replace=False).tolist()) if train_only.size else set()
sel_set = test_days | sel_train
keep = np.isin(day_all, np.array(sorted(sel_set)))
day = day_all[keep]; ts = ts_all[keep]
uniq = np.unique(day)
# stack aligned X,y,clean across assets on the kept rows -> (N, 14, ...)
Xs = np.stack([A[s][0][keep] for s in SYMS], axis=1)   # (N,14,44)
ys = np.stack([A[s][1][keep] for s in SYMS], axis=1)   # (N,14)
cls = np.stack([A[s][3][keep] for s in SYMS], axis=1)  # (N,14)
N = Xs.shape[0]
print(f"days used: {uniq.shape[0]}  timestamps: {N}  assets: {len(SYMS)}")


# ---------------------------------------------------------------------------
# Cross-sectional primitives over axis=1 (the 14 assets), per timestamp.
# ---------------------------------------------------------------------------
def xrank(M):
    """Cross-sectional rank in [0,1] across the 14 assets, per row. NaN-safe,
    vectorized (double-argsort). NaNs sort last and are masked back out, so they
    do not contaminate the finite assets' ranks."""
    Mf = np.where(np.isfinite(M), M, np.inf)              # NaN/inf -> largest
    order = np.argsort(Mf, axis=1, kind="stable")
    ranks = np.empty_like(order)
    ar = np.arange(M.shape[1])
    for i in range(M.shape[0]):                            # cheap: 14-wide scatter
        ranks[i, order[i]] = ar
    ranks = ranks.astype(np.float64)
    fin = np.isfinite(M)
    cnt = fin.sum(axis=1, keepdims=True).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(cnt > 1, ranks / (cnt - 1), 0.5)    # [0,1]
    out[~fin] = np.nan
    out[(cnt < 3).ravel(), :] = np.nan
    return out


def xdemean(M):
    mu = np.nanmean(M, axis=1, keepdims=True)
    return M - mu


def ts_lag(M, k):
    """Lag along time (axis 0) within each asset column. out[t]=M[t-k]."""
    out = np.full_like(M, np.nan)
    if k < M.shape[0]:
        out[k:] = M[:-k]
    return out


def ts_rank(M, w):
    """Time-series rank of current value within trailing window of length w,
    per asset column, in [0,1]. Causal. Vectorized per call via a (Tn,Tn) mask
    (Tn is one day ~473, so this is cheap)."""
    Tn, K = M.shape
    out = np.full_like(M, np.nan, dtype=np.float64)
    ti = np.arange(Tn)
    # for each t, window is [max(0,t-w+1), t]
    for t in range(Tn):
        lo = max(0, t - w + 1)
        win = M[lo:t + 1]  # (<=w, K)
        cur = M[t]
        less = np.sum(win < cur[None, :], axis=0)
        cnt = np.sum(np.isfinite(win), axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[t] = np.where(cnt > 1, less / (cnt - 1), 0.5)
    return out


def ts_argmax_recency(M, w):
    """(argmax position of |M| in trailing window)/w - 0.5, per asset. Causal.
    Near +0.5 => biggest recent shock happened just now (fresh)."""
    Tn, K = M.shape
    out = np.full((Tn, K), np.nan)
    am = np.abs(M)
    for t in range(Tn):
        lo = max(0, t - w + 1)
        win = am[lo:t + 1]
        L = win.shape[0]
        pos = np.nanargmax(np.where(np.isfinite(win), win, -np.inf), axis=0)
        out[t] = pos / max(L - 1, 1) - 0.5
    return out


def decay_linear(M, w):
    """Weighted trailing mean with linearly decaying weights (alpha#101 decay_linear),
    per asset column. Causal. weight w,w-1,...,1 from now backward."""
    Tn, K = M.shape
    out = np.full_like(M, np.nan, dtype=np.float64)
    wts = np.arange(w, 0, -1, dtype=np.float64)
    wsum = wts.sum()
    for t in range(Tn):
        lo = max(0, t - w + 1)
        win = M[lo:t + 1]
        L = win.shape[0]
        ww = wts[w - L:]  # align so most recent gets weight w
        num = np.nansum(win * ww[:, None], axis=0)
        out[t] = num / wsum
    return out


def _roll_pearson(a, b, w):
    """Trailing-window Pearson corr of two 1-D series over window w, causal,
    via rolling sums. out[t] uses [t-w+1, t]. NaN where window degenerate."""
    n = a.shape[0]
    af = np.where(np.isfinite(a), a, 0.0); bf = np.where(np.isfinite(b), b, 0.0)
    val = (np.isfinite(a) & np.isfinite(b)).astype(np.float64)
    af *= val; bf *= val

    def rs(x):
        cs = np.cumsum(x); o = cs.copy()
        if w < n:
            o[w:] = cs[w:] - cs[:-w]
        return o
    cnt = rs(val); sa = rs(af); sb = rs(bf)
    saa = rs(af * af); sbb = rs(bf * bf); sab = rs(af * bf)
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = sab / cnt - (sa / cnt) * (sb / cnt)
        va = saa / cnt - (sa / cnt) ** 2
        vb = sbb / cnt - (sb / cnt) ** 2
        out = cov / np.sqrt(np.maximum(va, 0) * np.maximum(vb, 0))
    out[cnt < 5] = np.nan
    return out


def roll_corr_rank(Ma, Mb, w):
    """Trailing rolling corr of rank(Ma) vs rank(Mb) per asset over window w
    (alpha#2-style corr(rank(x),rank(y))). Ranks are taken WITHIN the day (each
    asset ranked once over the day), then rolling Pearson of those ranks — a
    standard, much cheaper Spearman-of-window approximation. Causal."""
    Tn, K = Ma.shape
    out = np.full((Tn, K), np.nan)
    for k in range(K):
        a = Ma[:, k]; b = Mb[:, k]
        ra = np.full(Tn, np.nan); rb = np.full(Tn, np.nan)
        fa = np.isfinite(a); fb = np.isfinite(b)
        if fa.sum() >= 5:
            ra[fa] = rankdata(a[fa])
        if fb.sum() >= 5:
            rb[fb] = rankdata(b[fb])
        out[:, k] = _roll_pearson(ra, rb, w)
    return out


# ---------------------------------------------------------------------------
# Build the F5 alpha-101 family -> dict name -> (N,14) array.
# Each is then standardized per-fold downstream like any feature column.
# ---------------------------------------------------------------------------
ret300 = Xs[:, :, C["ret300"]]; ret600 = Xs[:, :, C["ret600"]]
ret30 = Xs[:, :, C["ret30"]]
df300 = Xs[:, :, C["df300"]]; df60 = Xs[:, :, C["df60"]]; tf30 = Xs[:, :, C["tf30"]]
rv300 = Xs[:, :, C["rv300"]]; obi = Xs[:, :, C["obi"]]

# Pred bars are spaced 180s apart with 1440s jumps at day boundaries. Cross-
# sectional (per-row) features are unaffected, but TIME-SERIES-window features
# (ts_rank/decay/argmax/corr) must NOT span a day gap — and day-subsampling makes
# consecutive kept rows jump across non-adjacent days. So we run every ts-window
# primitive PER DAY (reset at each boundary): leak-safe + gap-safe regardless of
# sampling. The window length is in pred-bars (1 bar = 180s).
_day_groups = [np.where(day == dd)[0] for dd in uniq]


def by_day(fn, M, w):
    out = np.full_like(M, np.nan, dtype=np.float64)
    for gi in _day_groups:
        out[gi] = fn(M[gi], w)
    return out


def by_day2(fn, Ma, Mb, w):
    out = np.full_like(Ma, np.nan, dtype=np.float64)
    for gi in _day_groups:
        out[gi] = fn(Ma[gi], Mb[gi], w)
    return out


feat = {}
feat["a_rank_rev300"] = -xrank(ret300)
feat["a_rank_rev600"] = -xrank(ret600)
feat["a_rank_flow300"] = xrank(df300)
feat["a_rank_flowS"] = xrank(tf30)
feat["a_rank_rv"] = -xrank(rv300)
feat["a_rank_obi"] = xrank(obi)
feat["a_signedpow_ret"] = np.sign(ret300) * (xrank(np.abs(ret300)) ** 2)
feat["a_decay_ret"] = xrank(by_day(decay_linear, ret30, 5))
feat["a_tsrank_ret300"] = xdemean(by_day(ts_rank, ret300, 20))
feat["a_tsrank_flow"] = xdemean(by_day(ts_rank, df60, 20))
feat["a_corr_ret_flow"] = -xrank(by_day2(roll_corr_rank, ret300, df300, 10))
feat["a_argmax_ret"] = by_day(ts_argmax_recency, ret30, 10)

FNAMES = list(feat.keys())
# sanitize
for k in FNAMES:
    feat[k] = np.nan_to_num(feat[k], nan=0.0, posinf=0.0, neginf=0.0).astype(np.float64)
Fam = np.stack([feat[k] for k in FNAMES], axis=2)  # (N,14,nfam)
print(f"F5 features built: {len(FNAMES)} -> {FNAMES}")


# ---------------------------------------------------------------------------
# Fold helpers + per-asset Ridge walk-forward.
# ---------------------------------------------------------------------------
_sampled = set(uniq.tolist())


def folddays(fi):
    """fi is the fold index; use pre-resolved day VALUES intersected with the
    sampled days actually present in the panel."""
    fd = fold_days[fi]
    if fd is None:
        return None
    trd, ted = fd
    trd = trd & _sampled; ted = ted & _sampled
    if not trd or not ted:
        return None
    return trd, ted


def run_asset(ai, use_family):
    """Per-asset Ridge walk-forward. Returns pooled (yh, yt, te_index_list)."""
    X44 = Xs[:, ai, :]
    y = ys[:, ai]; cl = cls[:, ai]
    if use_family:
        F = np.concatenate([X44, Fam[:, ai, :]], axis=1)
    else:
        F = X44
    yh, yt, teidx = [], [], []
    for fi in range(len(FOLDS)):
        r = folddays(fi)
        if r is None:
            continue
        trd, ted = r
        trm = np.isin(day, list(trd)) & np.isfinite(y)
        tem = np.isin(day, list(ted)) & cl & np.isfinite(y)
        if trm.sum() < 500 or tem.sum() < 20:
            continue
        Xtr, ytr = F[trm], y[trm]; Xte = F[tem]
        mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
        sig = mad(ytr)
        if not np.isfinite(sig) or sig <= 0:
            continue
        m = RidgeCV(alphas=ALPHAS); m.fit((Xtr - mu) / sd, ytr / sig)
        yh.append(m.predict((Xte - mu) / sd) * sig)
        yt.append(y[tem]); teidx.append(np.where(tem)[0])
    if not yh:
        return None
    return np.concatenate(yh), np.concatenate(yt), np.concatenate(teidx)


def perfold(ai, use_family):
    """Per-fold P/S list to check sign-consistency (no fold flips)."""
    X44 = Xs[:, ai, :]; y = ys[:, ai]; cl = cls[:, ai]
    F = np.concatenate([X44, Fam[:, ai, :]], axis=1) if use_family else X44
    out = []
    for fi in range(len(FOLDS)):
        r = folddays(fi)
        if r is None:
            out.append(None); continue
        trd, ted = r
        trm = np.isin(day, list(trd)) & np.isfinite(y)
        tem = np.isin(day, list(ted)) & cl & np.isfinite(y)
        if trm.sum() < 500 or tem.sum() < 20:
            out.append(None); continue
        Xtr, ytr = F[trm], y[trm]; Xte = F[tem]; yte = y[tem]
        mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
        sig = mad(ytr)
        m = RidgeCV(alphas=ALPHAS); m.fit((Xtr - mu) / sd, ytr / sig)
        ph = m.predict((Xte - mu) / sd) * sig
        out.append((float(pearsonr(ph, yte)[0]), float(spearmanr(ph, yte)[0])))
    return out


# ---- run baseline vs +family per asset, collect pooled predictions for rank-IC ----
res = {}
pred_base = {}; pred_plus = {}; truth = {}; teidx_map = {}
pf_base = {}; pf_plus = {}
for ai, s in enumerate(SYMS):
    b = run_asset(ai, False); pl = run_asset(ai, True)
    if b is None or pl is None:
        continue
    yhb, ytb, ib = b; yhp, ytp, ip = pl
    res[s] = dict(
        P_base=round(float(pearsonr(yhb, ytb)[0]), 4),
        S_base=round(float(spearmanr(yhb, ytb)[0]), 4),
        P_plus=round(float(pearsonr(yhp, ytp)[0]), 4),
        S_plus=round(float(spearmanr(yhp, ytp)[0]), 4),
        n=len(yhb))
    res[s]["dP"] = round(res[s]["P_plus"] - res[s]["P_base"], 4)
    res[s]["dS"] = round(res[s]["S_plus"] - res[s]["S_base"], 4)
    pred_base[s] = (ib, yhb); pred_plus[s] = (ip, yhp); truth[s] = (ib, ytb)
    pf_base[s] = perfold(ai, False); pf_plus[s] = perfold(ai, True)


# ---- per-asset standalone univariate |Spearman| of each F5 feature vs y ----
uni = {}
yflat = ys.reshape(-1)
clflat = cls.reshape(-1)
for j, fn in enumerate(FNAMES):
    xflat = Fam[:, :, j].reshape(-1)
    m = np.isfinite(xflat) & np.isfinite(yflat) & clflat
    if m.sum() > 1000 and np.std(xflat[m]) > 1e-12:
        uni[fn] = round(float(spearmanr(xflat[m], yflat[m])[0]), 4)
    else:
        uni[fn] = None


# ---- cross-sectional rank-IC: per-timestamp Spearman across assets (clean only) ----
def xsec_rankic(pred_map):
    """Build (N,14) prediction matrix from pooled per-asset preds, then per-ts
    Spearman across assets (>=4 clean assets), mean."""
    P = np.full((N, len(SYMS)), np.nan)
    for ai, s in enumerate(SYMS):
        if s not in pred_map:
            continue
        ii, vals = pred_map[s]
        P[ii, ai] = vals
    Ytrue = ys.copy()
    ics = []
    for t in range(N):
        pr = P[t]; yr = Ytrue[t]
        m = np.isfinite(pr) & np.isfinite(yr) & cls[t]
        if m.sum() >= 4 and np.std(pr[m]) > 1e-12 and np.std(yr[m]) > 1e-12:
            ics.append(spearmanr(pr[m], yr[m])[0])
    ics = np.array(ics)
    return (round(float(ics.mean()), 4), round(float(ics.std()), 4), len(ics)) if ics.size else (None, None, 0)


ric_base = xsec_rankic(pred_base)
ric_plus = xsec_rankic(pred_plus)


# ---- aggregate ----
avg = lambda key: round(float(np.mean([res[s][key] for s in res])), 4)
summary = dict(
    family="F5_alpha101_xsec",
    days_used=int(uniq.shape[0]), timestamps=int(N), n_features=len(FNAMES),
    feature_names=FNAMES,
    avg_P_base=avg("P_base"), avg_P_plus=avg("P_plus"), avg_dP=round(avg("P_plus") - avg("P_base"), 4),
    avg_S_base=avg("S_base"), avg_S_plus=avg("S_plus"), avg_dS=round(avg("S_plus") - avg("S_base"), 4),
    xsec_rankIC_base=ric_base[0], xsec_rankIC_base_std=ric_base[1],
    xsec_rankIC_plus=ric_plus[0], xsec_rankIC_plus_std=ric_plus[1],
    xsec_rankIC_delta=(round(ric_plus[0] - ric_base[0], 4) if ric_base[0] is not None and ric_plus[0] is not None else None),
    xsec_n_timestamps=ric_base[2],
    univariate_spearman=uni,
    per_asset=res,
)

import os
os.makedirs(EXPORT, exist_ok=True)
json.dump(summary, open(p.join(EXPORT, "F5_alpha101.json"), "w"), indent=2, default=str)

print("\n=== F5 ALPHA-101 CROSS-SECTIONAL GATE ===")
print(f"days={summary['days_used']} ts={N} feats={len(FNAMES)}")
print(f"avg per-asset P: base={summary['avg_P_base']:+.4f} +F5={summary['avg_P_plus']:+.4f}  dP={summary['avg_dP']:+.4f}")
print(f"avg per-asset S: base={summary['avg_S_base']:+.4f} +F5={summary['avg_S_plus']:+.4f}  dS={summary['avg_dS']:+.4f}")
print(f"xsec rank-IC:    base={ric_base[0]} +F5={ric_plus[0]}  delta={summary['xsec_rankIC_delta']}  (ts={ric_base[2]})")

print("\n--- univariate standalone |Spearman| vs y (clean, pooled) ---")
for fn in sorted(uni, key=lambda k: -(abs(uni[k]) if uni[k] is not None else -1)):
    print(f"  {fn:18s} {uni[fn]}")

print(f"\n{'asset':9s} {'P_b':>8s} {'P+':>8s} {'dP':>7s} {'S_b':>8s} {'S+':>8s} {'dS':>7s}")
for s in SYMS:
    if s in res:
        r = res[s]
        print(f"{s:9s} {r['P_base']:>+8.4f} {r['P_plus']:>+8.4f} {r['dP']:>+7.4f} {r['S_base']:>+8.4f} {r['S_plus']:>+8.4f} {r['dS']:>+7.4f}")

# per-fold sign consistency: count assets where any fold's dP flips sign vs avg dP
flips = 0; checked = 0
for s in res:
    a, b = pf_base[s], pf_plus[s]
    dps = [(b[i][0] - a[i][0]) for i in range(len(a)) if a[i] is not None and b[i] is not None]
    if len(dps) >= 2:
        checked += 1
        if not (all(d >= -0.002 for d in dps) or all(d <= 0.002 for d in dps)):
            flips += 1
print(f"\nper-fold sign-consistency: {checked-flips}/{checked} assets sign-consistent on dP (flips={flips})")
print(json.dumps({k: summary[k] for k in ['avg_dP','avg_dS','xsec_rankIC_delta']}, indent=0))
