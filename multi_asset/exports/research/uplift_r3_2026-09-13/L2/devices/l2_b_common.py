"""l2_b_common.py — PREREG_L2 (sha pinned below) shared Stage B definitions: prereg / freeze assertion, inputs, metrics data-time map (§5),
features (§5) and targets (§4) as PURE functions of the arrays passed in (the G-SF guard re-evaluates exactly these on perturbed copies),
model family (§6), statistics and the frozen reading (§7, §9). Imported by every Stage B device; never run alone."""
import os, sys, json, time, calendar, math
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C

PREREG = os.path.join(C.L2, "PREREG_L2_squeeze_direction_2026-09-13.md")
FREEZE = os.path.join(C.L2, "receipts", "PREREG_FREEZE_sha.txt")
PREREG_SHA = "44b5baa119ca134eb5183ecea0d6e8e1c3027f5d958451401369f66d46a600dd"   # frozen 2026-09-13T12:57:17Z
DAY = 86400; SWITCH_DAY = calendar.timegm((2024, 3, 4, 0, 0, 0)) // DAY
TEST_YEARS = (2023, 2024, 2025, 2026)
FEATS = ["DOI1H", "DOI24H", "LSDIV", "TKR24", "R3D", "DD7", "AGE", "FZ", "RN8", "DRN8"]
FSETS = {"FULL": list(range(10)), "BASE": [7, 8, 9], "DESC": [4, 5, 6, 7, 8, 9]}
TARGETS = ("A", "B"); MODELS = ("R", "L")
GATE_CELLS = [(m, t) for m in MODELS for t in TARGETS]
MIN_ANCHOR = 10; NB = 2000; NNULL = 500
BLOCK_DAYS = {"A": 1, "B": 3}   # bootstrap block length per target (pre-freeze synthetic calibration: B with 1-day blocks SE 2.4–3.1 vs true 3.73; 3-day 3.99)
FIRST_TEST_DAY = calendar.timegm((2023, 1, 1, 0, 0, 0)) // 86400
SHIFT_A = [-3, -2, -1, 0, 1, 2, 3]; SHIFT_B = [-18, -12, -6, 0, 6, 12, 18]
LGB_PARAMS = dict(objective="regression", learning_rate=0.02, num_leaves=7, max_depth=3, min_data_in_leaf=200, feature_fraction=0.8,
                  bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0, max_bin=63, seed=20260913, deterministic=True, force_row_wise=True,
                  num_threads=8, verbosity=-1)
LGB_ROUNDS = 300
LISTING = os.path.join(C.L2, "out", "L2_A_listing.json")
METDIR = os.path.join(C.L2, "out", "metrics")
PULL_RECEIPT = os.path.join(C.L2, "receipts", "RECEIPT_L2_B_pull.json")
POP_FILES = {"42": (os.path.join(C.L2, "out", "L2_A_population_s42.npz"), "f4fb937d175ce2dfc0c611b301e87ab7b8657ce19e6119c6129a4bcb153d8f3f"),
             "2027": (os.path.join(C.L2, "out", "L2_A_population_s2027.npz"), "122fc6245c226a973b328e8711856cd9488f7f49ee7b43610caa9765edcc91ac")}


def check_prereg():
    s = C.sha256(PREREG); fr = open(FREEZE).read()
    assert s == PREREG_SHA, ("PREREG_L2 sha changed", s)
    assert PREREG_SHA in fr, "freeze receipt does not carry the frozen sha"
    return dict(prereg=s, freeze_receipt=C.sha256(FREEZE))


def year_of_ts(ts):
    return np.array([time.gmtime(int(t)).tm_year for t in ts], np.int64)


# ------------------------------------------------------------------ inputs
def load_core():
    """META y4, PANEL funding / fund-ema / taker fields, listing first dates. Returns dict (float64 copies)."""
    M = np.load(C.INPUTS["META"][0], allow_pickle=False); P = np.load(C.INPUTS["PANEL"][0], allow_pickle=True)
    U = np.load(C.INPUTS["UMASK"][0], allow_pickle=True)
    D = {}
    D["SYM"] = [str(x) for x in P["symbols"]]; assert D["SYM"] == [str(x) for x in U["symbols"]] and len(D["SYM"]) == C.NW
    D["PTS"] = P["ts"].astype(np.int64); assert D["PTS"].shape == (C.N_REC,) and np.array_equal(D["PTS"], U["ts"].astype(np.int64))
    D["E_TS"] = M["E_ts"].astype(np.int64); assert np.array_equal(D["E_TS"][C.META_OFF:C.META_OFF + C.N_REC], D["PTS"])
    D["Y"] = np.asarray(M["y4"], np.float64); assert D["Y"].shape == (10182, C.NW)
    D["FN"] = np.asarray(P["f_fund_now"], np.float64); D["IV"] = np.asarray(P["f_fund_iv"], np.float64)
    D["FE"] = np.asarray(P["f_fund_ema_v1"], np.float64); D["TB24"] = np.asarray(P["f_tbf_24h"], np.float64)
    lj = json.load(open(LISTING))
    D["FIRST_DAY"] = np.array([calendar.timegm(time.strptime(lj[s]["zip_dates"][0], "%Y-%m-%d")) if (s in lj and lj[s]["zip_dates"]) else np.nan
                               for s in D["SYM"]], np.float64)
    return D


def load_metrics(syms):
    """Per symbol: data-time-sorted arrays dt (int64), OIQ, TOP (sum_toptrader_long_short_ratio), GLB (count_long_short_ratio), TKR (taker ratio).
    Data time τ(L) = L before 2024-03-04 (window END labels), L + 300 from 2024-03-04 (window START labels). First occurrence kept."""
    MET = {}; rep = dict(duplicates=0, dup_max_abs_diff=0.0, symbols=0, rows=0)
    for s in syms:
        p = os.path.join(METDIR, s + ".npz")
        if not os.path.exists(p):
            continue
        Z = np.load(p, allow_pickle=False); L = Z["labels"].astype(np.int64); X = Z["X"].astype(np.float64)
        cols = [str(c) for c in Z["cols"]]
        tau = L + 300 * ((L // DAY) >= SWITCH_DAY)
        o = np.argsort(tau, kind="stable"); tau = tau[o]; X = X[o]
        keep = np.ones(tau.size, bool); keep[1:] = tau[1:] != tau[:-1]
        if (~keep).any():
            rep["duplicates"] += int((~keep).sum())
            prev = np.nonzero(~keep)[0]
            rep["dup_max_abs_diff"] = max(rep["dup_max_abs_diff"], float(np.nanmax(np.abs(X[prev] - X[prev - 1]))) if prev.size else 0.0)
        tau = tau[keep]; X = X[keep]
        MET[s] = dict(dt=tau, OIQ=X[:, cols.index("sum_open_interest")], TOP=X[:, cols.index("sum_toptrader_long_short_ratio")],
                      GLB=X[:, cols.index("count_long_short_ratio")], TKR=X[:, cols.index("sum_taker_long_short_vol_ratio")])
        rep["symbols"] += 1; rep["rows"] += int(tau.size)
    return MET, rep


def lookup(dt, val, t):
    """Exact data-time lookup: val at dt == t, else NaN (vectorised over t)."""
    k = np.searchsorted(dt, t)
    out = np.full(t.shape, np.nan)
    ok = (k < dt.size)
    ok[ok] = dt[k[ok]] == t[ok]
    out[ok] = val[k[ok]]
    return out


# ------------------------------------------------------------------ features (§5) and targets (§4): pure functions
def xz_row(v):
    """A0 device xz: rank of finite values / (n_finite − 1) − 0.5; NaN elsewhere; NaN row if < 10 finite."""
    ok = np.isfinite(v); out = np.full(v.shape, np.nan)
    if ok.sum() >= 10:
        out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out


def rn8_bp(FN, IV, j):
    iv = IV[j]
    with np.errstate(invalid="ignore"):
        r = FN[j] * (8.0 / np.where(iv > 0, iv, 8.0))
    return 1e4 * np.where(np.isfinite(r), r, 0.0)


def features_rows(i, n, E, Y, FN, IV, FE, TB24, FIRST_DAY, MET, SYM):
    """10 features for population rows (i: rec row, n: column, E: anchor ts). Reads Y rows <= k-1, panel row j and j-6 only,
    metrics data times <= E-600 only, FIRST_DAY (non-return listing fact)."""
    i = np.asarray(i, np.int64); n = np.asarray(n, np.int64); E = np.asarray(E, np.int64)
    R = i.size; F = np.full((R, 10), np.nan)
    k = i + C.META_OFF; j = i
    # R3D (18 closed 4h returns) and DD7 (42)
    q18 = np.arange(1, 19); blk = Y[k[:, None] - q18[None, :], n[:, None]]
    fin = np.isfinite(blk).all(axis=1)
    F[fin, 4] = np.prod(1.0 + blk[fin], axis=1) - 1.0
    q42 = np.arange(1, 43); blk = Y[k[:, None] - q42[None, :], n[:, None]]
    fin = np.isfinite(blk).all(axis=1)
    cp = np.cumprod(1.0 + blk[fin], axis=1)            # P_q = Π_{r=k-q..k-1}(1+y), q = 1..42
    mx = np.maximum(1.0, (1.0 / cp).max(axis=1))       # max_{q=0..42} C_q, C_0 = 1
    F[fin, 5] = 1.0 / mx - 1.0
    # AGE
    d = (E - FIRST_DAY[n]) / DAY
    ok = np.isfinite(d) & (d >= 0)
    F[ok, 6] = np.log1p(np.minimum(d[ok], 180.0))
    # FZ, RN8, DRN8, TKR24 (panel rows j, j-6); rows grouped by j through one stable argsort
    oj = np.argsort(j, kind="stable"); uj, st_j, ct_j = np.unique(j[oj], return_index=True, return_counts=True)
    for jj, a0, c0 in zip(uj, st_j, ct_j):
        sel = oj[a0:a0 + c0]; nsel = n[sel]
        z = xz_row(FE[jj]); F[sel, 7] = z[nsel]
        r = rn8_bp(FN, IV, jj); F[sel, 8] = r[nsel]
        if jj >= 6:
            r6 = rn8_bp(FN, IV, jj - 6); F[sel, 9] = r[nsel] - r6[nsel]
        F[sel, 3] = TB24[jj, nsel] - 0.5
    # metrics (data time <= E - 600); rows grouped by column
    t0 = E - 600
    on = np.argsort(n, kind="stable"); un, st_n, ct_n = np.unique(n[on], return_index=True, return_counts=True)
    for nn, a0, c0 in zip(un, st_n, ct_n):
        sel = on[a0:a0 + c0]; m = MET.get(SYM[nn])
        if m is None:
            continue
        oq0 = lookup(m["dt"], m["OIQ"], t0[sel]); oq1 = lookup(m["dt"], m["OIQ"], t0[sel] - 3600); oq24 = lookup(m["dt"], m["OIQ"], t0[sel] - 86400)
        with np.errstate(divide="ignore", invalid="ignore"):
            lo0 = np.where(oq0 > 0, np.log(oq0), np.nan); lo1 = np.where(oq1 > 0, np.log(oq1), np.nan); lo24 = np.where(oq24 > 0, np.log(oq24), np.nan)
        F[sel, 0] = lo0 - lo1; F[sel, 1] = lo0 - lo24
        acc = np.zeros(sel.size); cnt = np.zeros(sel.size)
        for q in range(12):
            tt = t0[sel] - 300 * q
            a = lookup(m["dt"], m["TOP"], tt); b = lookup(m["dt"], m["GLB"], tt)
            good = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
            acc[good] += np.log(a[good]) - np.log(b[good]); cnt[good] += 1
        okc = cnt >= 6
        F[sel[okc], 2] = acc[okc] / cnt[okc]
    return F


def targets_rows(i, n, Y):
    """r_A = y4[k,n] (4h from E); r_B = Π_{q=0..5}(1+y4[k+q,n]) − 1 (NaN unless all 6 finite)."""
    k = np.asarray(i, np.int64) + C.META_OFF; n = np.asarray(n, np.int64)
    rA = Y[k, n]
    blk = np.stack([Y[np.minimum(k + q, Y.shape[0] - 1), n] for q in range(6)], axis=1)
    beyond = (k + 5) >= Y.shape[0]
    fin = np.isfinite(blk).all(axis=1) & ~beyond
    rB = np.full(k.size, np.nan); rB[fin] = np.prod(1.0 + blk[fin], axis=1) - 1.0
    return rA, rB


def shifted_returns(i, n, Y):
    """C6 spectra inputs: A shifts y4[k+h] (h in SHIFT_A); B shifts r_B starting at k+h (h in SHIFT_B)."""
    k = np.asarray(i, np.int64) + C.META_OFF; n = np.asarray(n, np.int64); T = Y.shape[0]
    SA = np.full((k.size, len(SHIFT_A)), np.nan); SB = np.full((k.size, len(SHIFT_B)), np.nan)
    for c, h in enumerate(SHIFT_A):
        kk = k + h; ok = (kk >= 0) & (kk < T)
        SA[ok, c] = Y[kk[ok], n[ok]]
    for c, h in enumerate(SHIFT_B):
        kk = k + h; ok = (kk >= 0) & (kk + 5 < T)
        blk = np.stack([Y[np.clip(kk + q, 0, T - 1), n] for q in range(6)], axis=1)
        fin = ok & np.isfinite(blk).all(axis=1)
        SB[fin, c] = np.prod(1.0 + blk[fin], axis=1) - 1.0
    return SA, SB


# ------------------------------------------------------------------ model family (§6)
class Prep:
    def __init__(self, Xtr, Xte):
        med = np.nanmedian(Xtr, axis=0); med = np.where(np.isfinite(med), med, 0.0)
        self.n_imp_train = [int(x) for x in (~np.isfinite(Xtr)).sum(axis=0)]; self.n_imp_test = [int(x) for x in (~np.isfinite(Xte)).sum(axis=0)]
        Xtr = np.where(np.isfinite(Xtr), Xtr, med[None, :]); Xte = np.where(np.isfinite(Xte), Xte, med[None, :])
        lo = np.quantile(Xtr, 0.005, axis=0); hi = np.quantile(Xtr, 0.995, axis=0)
        Xtr = np.clip(Xtr, lo, hi); Xte = np.clip(Xte, lo, hi)
        mu = Xtr.mean(axis=0); sd = Xtr.std(axis=0); zero = sd < 1e-12; sds = np.where(zero, 1.0, sd)
        Xtr = (Xtr - mu) / sds; Xte = (Xte - mu) / sds; Xtr[:, zero] = 0.0; Xte[:, zero] = 0.0
        self.Xtr, self.Xte = Xtr, Xte; self.median = med; self.lo = lo; self.hi = hi; self.zero = [int(x) for x in np.nonzero(zero)[0]]


def clip_train_target(y):
    lo, hi = np.quantile(y, [0.005, 0.995])
    return np.clip(y, lo, hi), [float(lo), float(hi)]


def fit_predict(model, Xtr, ytr, Xte):
    P = Prep(Xtr, Xte); yc, yclip = clip_train_target(ytr)
    info = dict(n_train=int(Xtr.shape[0]), n_test=int(Xte.shape[0]), target_clip=yclip, imputed_train=P.n_imp_train, imputed_test=P.n_imp_test, zero_sd=P.zero)
    if model == "R":
        yb = float(yc.mean()); a = float(Xtr.shape[0])
        beta = np.linalg.solve(P.Xtr.T @ P.Xtr + a * np.eye(P.Xtr.shape[1]), P.Xtr.T @ (yc - yb))
        info.update(beta=[float(x) for x in beta], intercept=yb, alpha=a)
        return yb + P.Xte @ beta, info
    import lightgbm as lgb
    bst = lgb.train(dict(LGB_PARAMS), lgb.Dataset(P.Xtr, label=yc), num_boost_round=LGB_ROUNDS)
    info.update(gain=[float(x) for x in bst.feature_importance(importance_type="gain")], num_trees=int(bst.num_trees()))
    return bst.predict(P.Xte), info


# ------------------------------------------------------------------ statistics (§7) and reading (§9)
def anchor_index(i_rows, ok):
    """Group rows (with ok) by rec row i; returns (a: anchor id per ok-row, starts, sizes, uniq i, ok-row indices) sorted by (i, original order)."""
    idx = np.nonzero(ok)[0]
    ii = i_rows[idx]
    o = np.lexsort((idx, ii)); idx = idx[o]; ii = ii[o]
    uniq, a, sizes = np.unique(ii, return_inverse=True, return_counts=True)
    return idx, a, sizes, uniq


def decile_sets(p, a, sizes, col):
    """Top / bottom ceil(0.1 n) rows per anchor by score p (ties: lower column index first). Inputs are aligned to the ok-row order."""
    m = np.ceil(0.1 * sizes).astype(np.int64)
    o_top = np.lexsort((col, -p, a))       # within anchor: p descending, then column ascending
    o_bot = np.lexsort((col, p, a))        # p ascending, then column ascending
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    rank_top = np.empty(a.size, np.int64); rank_top[o_top] = np.arange(a.size) - np.repeat(starts, sizes)
    rank_bot = np.empty(a.size, np.int64); rank_bot[o_bot] = np.arange(a.size) - np.repeat(starts, sizes)
    return rank_top < m[a], rank_bot < m[a], m


def anchor_stats(s, a, sizes, top, bot):
    """Per anchor D_i and H_i (s = short P&L bps)."""
    na = sizes.size
    pop = np.bincount(a, s, na) / sizes
    m = np.bincount(a, top.astype(np.float64), na)
    D = np.bincount(a, s * top, na) / m - pop
    H = np.bincount(a, s * bot, na) / m - pop
    return D, H


def group_median(v, g, ng):
    """Median of v per group id g (0..ng-1); NaN for empty groups. Average of the two middle values for even sizes."""
    o = np.lexsort((v, g)); vs = v[o]; gs = g[o]
    cnt = np.bincount(gs, minlength=ng); st = np.concatenate([[0], np.cumsum(cnt)[:-1]])
    out = np.full(ng, np.nan); ok = cnt > 0
    lo = st[ok] + (cnt[ok] - 1) // 2; hi = st[ok] + cnt[ok] // 2
    out[ok] = 0.5 * (vs[lo] + vs[hi])
    return out


def anchor_median_stat(s, a, sizes, top):
    """M_i = median_{Q_i} s − median_{all} s."""
    na = sizes.size
    med_all = group_median(s, a, na)
    t = np.nonzero(top)[0]
    med_top = group_median(s[t], a[t], na)
    return med_top - med_all


def block_ids(day_a, T):
    """Bootstrap block id per anchor: floor((UTC day − 2023-01-01) / BLOCK_DAYS[T]); returns (unique blocks, inverse)."""
    b = (np.asarray(day_a, np.int64) - FIRST_TEST_DAY) // BLOCK_DAYS[T]
    return np.unique(b, return_inverse=True)


def draw_counts(nd, base=0):
    Cm = np.zeros((NB, nd))
    for b in range(NB):
        Cm[b] = np.bincount(np.random.default_rng([20260905, base + b]).integers(0, nd, nd), minlength=nd)
    return Cm


def boot_ci(Cm, day_sum, day_cnt):
    v = (Cm @ day_sum) / (Cm @ day_cnt)
    lo, hi = np.percentile(v, [2.5, 97.5])
    return [float(lo), float(hi)]


def reading(cell):
    """§9.1 per seed: cell dict with G, G_ci, G_years{Y}, dG, dG_ci, TB_ci, H_ci, G_med, z, q05, shift_peak_forward_is_0. Returns (conds, first_fail)."""
    c1 = cell["G"] < 0 and cell["G_ci"][1] < 0
    c2 = all(cell["G_years"][str(y)] is not None and cell["G_years"][str(y)] < 0 for y in TEST_YEARS)
    c3 = cell["dG"] < 0 and cell["dG_ci"][1] < 0
    c4 = cell["TB_ci"][1] < 0 and cell["H_ci"][1] >= 0 and cell["G_med"] < 0
    c5 = cell.get("z") is not None and cell.get("q05") is not None and cell["z"] <= cell["q05"]
    c6 = bool(cell.get("shift_peak_forward_is_0"))
    conds = dict(C1=bool(c1), C2=bool(c2), C3=bool(c3), C4=bool(c4), C5=bool(c5), C6=c6)
    labels = dict(C1="DIRECTION-ABSENT", C2="UNSTABLE", C3="NOT-BEYOND-FUNDING", C4="VARIANCE", C5="NULL", C6="SHIFT")
    first = next((labels[k] for k in ("C1", "C2", "C3", "C4", "C5", "C6") if not conds[k]), None)
    return conds, first
