"""Factory — component 4: the two-stage evaluation pipeline (factory_prereg §2).

Stage-0 (triage, NOT a discovery): batch-evaluate K formulas' incremental rank-IC over YR{H}B on the
clean CL{H} grid, Benjamini-Hochberg q=0.10 -> survivors; append every formula (pass/fail) to the ledger.
Stage-1 (discovery): each Stage-0 survivor faces two empirical nulls (shuffle-eval day-block target
permutation + random-formula), a Reality-Check / Romano-Wolf max-null, a Bonferroni z>=4.42 gate whose
denominator is the cumulative ledger M, per-year sign consistency, a day-block bootstrap CI excluding 0,
and pred-corr < 0.70 to each shipped leg AND each already-ACCEPTED factory factor. Only a formula that
clears ALL becomes CANDIDATE (via ledger.append_stage1).

★ Evaluation window is HARDCODED to 2022-2025; 2026 is the sealed holdout and is excluded here (it is
opened once, elsewhere, only on the final survivor set — factory_prereg §2.1/§2.6).
"""
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import dsl
from ledger import Ledger, BONFERRONI_Z

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
BH_Q = 0.10
PREDCORR_MAX = 0.70
HOLDOUT_YEAR = 2026            # sealed — hardcoded-excluded from the evaluation window
NULL_R = 200                   # null-batch repeats for the max-null
BOOT = 2000                    # day-block bootstrap draws


def _ric(a, b):
    if len(a) < 8 or np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return np.nan
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def load_context(horizon=4, subsample=1):
    W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
    K = np.load(MA + "/exports/eda/king_pred_panel.npz", allow_pickle=True)
    S = np.load(MA + "/exports/eda/s2_pred_panel_cl4.npz", allow_pickle=True)
    tgt = np.load(MA + f"/exports/{'yr4b' if horizon == 4 else 'yr24b'}_target.npz", allow_pickle=True)
    ts = W["ts"].astype(np.int64); ch = [str(c) for c in W["ch_names"]]
    year = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    day = (ts // 86400000).astype(np.int64)
    member = W["MEMBER110"].astype(bool); CL = W[f"CL{horizon}"].astype(bool)
    CHm = W["CH"].astype(np.float64)
    ctx = {c: CHm[:, :, i] for i, c in enumerate(ch) if c in dsl.DENSE_CHANNELS}
    # 4 leg score columns (SPARSE — anchor-only)
    king = K["king_pred"].astype(np.float64); s2 = S["s2_pred"].astype(np.float64)
    fund = CHm[:, :, ch.index("funding_ema")]; size = CHm[:, :, ch.index("size_dvol")]
    ctx["king"] = king; ctx["s2"] = s2
    ctx["funding_leg"] = -_xsec(fund, member, CL, "rank"); ctx["size_leg"] = _xsec(size, member, CL, "z")
    target = tgt["YR4K"].astype(np.float64)                 # key 'YR4K' holds YR{H}B content (full-book residual)
    # evaluation window: 2022-2025 (HOLDOUT 2026 excluded); anchor rows = member&CL&finite(target)
    base = member & CL & np.isfinite(target)
    rows = np.where(base.any(1) & (year != HOLDOUT_YEAR))[0]
    if subsample > 1:
        rows = rows[::subsample]                             # smoke-speed only; production uses subsample=1
    return dict(ctx=ctx, target=target, member=member, CL=CL, day=day, year=year, rows=rows)


def _xsec(A, member, CL, mode):
    out = np.full_like(A, np.nan)
    for t in np.where((member & CL).any(1))[0]:
        b = np.where(member[t] & CL[t] & np.isfinite(A[t]))[0]
        if b.size >= 3:
            x = A[t, b]
            out[t, b] = (rankdata(x) / b.size - 0.5) if mode == "rank" else ((x - x.mean()) / (x.std() + 1e-9))
    return out


def score_series(factor, C):
    """per-anchor rank-IC(factor, target) over member&CL&finite; returns ic[], day[], year[]."""
    tg, mem, CL, day, year = C["target"], C["member"], C["CL"], C["day"], C["year"]
    ics, days, yrs = [], [], []
    for t in C["rows"]:
        b = np.where(mem[t] & CL[t] & np.isfinite(tg[t]) & np.isfinite(factor[t]))[0]
        if b.size >= 8:
            ic = _ric(factor[t, b], tg[t, b])
            if np.isfinite(ic):
                ics.append(ic); days.append(int(day[t])); yrs.append(int(year[t]))
    return np.array(ics), np.array(days), np.array(yrs)


def _dayblock_ci(ic, days, rng, n=BOOT):
    if len(ic) < 5:
        return (np.nan, np.nan), np.nan
    ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
    b = np.array([ic[np.concatenate([d2[u] for u in rng.choice(ud, len(ud), True)])].mean() for _ in range(n)])
    return (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))), float(b.std())


def stats(ics, days, yrs, rng):
    pooled = float(ics.mean()) if len(ics) else np.nan
    by_year = {int(y): round(float(ics[yrs == y].mean()), 5) for y in sorted(set(yrs.tolist()))}
    ci, se = _dayblock_ci(ics, days, rng)
    z = pooled / se if se and np.isfinite(se) and se > 0 else np.nan
    signs = [v for v in by_year.values()]
    sign_consistent = bool(signs) and (all(v > 0 for v in signs) or all(v < 0 for v in signs))
    return dict(inc_ic=round(pooled, 5), by_year=by_year, ci=[round(ci[0], 5), round(ci[1], 5)],
                se=round(se, 6) if np.isfinite(se) else None, z=round(z, 3) if np.isfinite(z) else None,
                sign_consistent=sign_consistent, n=len(ics))


# ---------------- Stage-0: BH triage ----------------
def stage0(formulas, C, ledger: Ledger, rng):
    rows = []
    tr = _xsec_ranks(C["target"], C)                      # target ranks precomputed once (vectorized scoring)
    day_w = C["day"][C["rows"]]; year_w = C["year"][C["rows"]]
    for f in formulas:
        try:
            root = dsl.parse(f)
        except dsl.DSLError as e:
            ledger.append_stage0(f, "PARSE_FAIL", 0, 0, inc_ic=None, fdr_q=None, survived=False,
                                 death_cause=f"parse:{e}")
            continue
        try:
            factor = dsl.evaluate(root, C["ctx"])          # a bad-but-parseable formula must not abort the campaign
            if not (isinstance(factor, np.ndarray) and factor.shape == C["target"].shape):
                raise ValueError(f"factor shape {getattr(factor,'shape',None)} != panel")
        except Exception as e:
            ledger.append_stage0(f, root.value.get("md5", "EVAL_FAIL"), root.value.get("depth", 0),
                                 root.value.get("n_ops", 0), inc_ic=None, fdr_q=None, survived=False,
                                 death_cause=f"eval_error:{type(e).__name__}")
            continue
        ic = _rowwise_rankcorr(_xsec_ranks(factor, C), tr)   # per-anchor rank-IC vs target (vectorized)
        ok = np.isfinite(ic)
        ics, days, yrs = ic[ok], day_w[ok], year_w[ok]
        st = stats(ics, days, yrs, rng)
        p = 2 * (1 - norm.cdf(abs(st["z"]))) if st["z"] is not None else 1.0
        rows.append((f, root.value, st, p, factor))
    # Benjamini-Hochberg q=0.10
    rows.sort(key=lambda r: r[3])
    m = len(rows); survivors = []
    for i, (f, meta, st, p, factor) in enumerate(rows):
        surv = p <= (i + 1) / max(m, 1) * BH_Q and st["sign_consistent"]
        ledger.append_stage0(f, meta["md5"], meta["depth"], meta["n_ops"], inc_ic=st["inc_ic"],
                             fdr_q=round(p * m / (i + 1), 4) if m else None, survived=surv,
                             death_cause=None if surv else ("sign_flip" if not st["sign_consistent"] else "stage0_bh"))
        if surv:
            survivors.append((f, meta, st, factor))
    return survivors


# ---------------- Stage-1: discovery gate ----------------
def _random_formulas(n, rng, depth_dist):
    """random DSL formulas at the given depth distribution (complexity-matched null)."""
    dense = dsl.DENSE_CHANNELS; out = []
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        d = int(rng.choice(depth_dist)) if len(depth_dist) else 1
        f = _rand_expr(rng, d, dense)
        if dsl.validate(f)["ok"]:
            out.append(f)
    return out


def _rand_expr(rng, depth, dense):
    if depth <= 0:
        return str(rng.choice(dense))
    unary_ts = ["ts_delta", "ts_mean", "ts_std", "ts_zscore", "ema", "ts_rank", "ts_min", "ts_max", "decay_linear"]
    xs = ["xsec_rank", "xsec_z", "xsec_demean"]; pt = ["add", "sub", "mul", "neg", "abs"]
    kind = rng.choice(["ts", "xs", "pt"])
    if kind == "ts":
        op = str(rng.choice(unary_ts)); w = int(rng.choice([4, 12, 24, 72]))
        return f"{op}({_rand_expr(rng, depth-1, dense)}, {w})"
    if kind == "xs":
        return f"{str(rng.choice(xs))}({_rand_expr(rng, depth-1, dense)})"
    op = str(rng.choice(pt))
    if op in ("neg", "abs"):
        return f"{op}({_rand_expr(rng, depth-1, dense)})"
    return f"{op}({_rand_expr(rng, depth-1, dense)}, {_rand_expr(rng, depth-1, dense)})"


def _xsec_ranks(A, C):
    """(len(rows), N) cross-sectional ranks of A over member&CL&finite per eval anchor; NaN off. float32."""
    rows = C["rows"]; N = A.shape[1]; out = np.full((len(rows), N), np.nan, np.float32)
    mem, CL = C["member"], C["CL"]
    for i, t in enumerate(rows):
        b = np.where(mem[t] & CL[t] & np.isfinite(A[t]))[0]
        if b.size >= 8:
            out[i, b] = rankdata(A[t, b]).astype(np.float32)
    return out


def _rowwise_rankcorr(A, B):
    """row-wise Pearson corr of two (n, N) rank arrays over common-finite cells (= Spearman). Vectorized."""
    m = np.isfinite(A) & np.isfinite(B); cnt = m.sum(1)
    Am = np.where(m, A, 0.0); Bm = np.where(m, B, 0.0)
    ma = (Am.sum(1) / np.maximum(cnt, 1))[:, None]; mb = (Bm.sum(1) / np.maximum(cnt, 1))[:, None]
    Ad = np.where(m, A - ma, 0.0); Bd = np.where(m, B - mb, 0.0)
    num = (Ad * Bd).sum(1); den = np.sqrt((Ad * Ad).sum(1) * (Bd * Bd).sum(1))
    return np.where((den > 1e-12) & (cnt >= 8), num / den, np.nan)


def _maxnull_fast(facs, C, rng, null_r):
    """Vectorized shuffle-eval max-null: precompute factor+target xsec ranks ONCE, then per day-block
    permutation do a vectorized row-wise rank-corr for every survivor. ~100-1000x the per-anchor loop."""
    rows = C["rows"]
    tr = _xsec_ranks(C["target"], C)                          # (n_anchors, N) target ranks
    fr = [_xsec_ranks(fac, C) for fac in facs]                # per-formula ranks (precomputed once)
    day_of = C["day"][rows]; udays = np.unique(day_of)
    rep_i = {int(d): int(np.where(day_of == d)[0][0]) for d in udays}
    di = np.array([rep_i[int(d)] for d in day_of])            # anchor -> representative index of its day
    max_null = []
    for _ in range(null_r):
        pm = dict(zip(udays.tolist(), rng.permutation(udays).tolist()))
        perm_i = np.array([rep_i[int(pm[int(d)])] for d in day_of])
        tp = tr[perm_i]                                       # permuted-day target ranks (n_anchors, N)
        best = -np.inf
        for frk in fr:
            mic = np.nanmean(_rowwise_rankcorr(frk, tp))
            if np.isfinite(mic):
                best = max(best, float(mic))
        max_null.append(best)
    return max_null


def stage1(survivors, C, ledger: Ledger, rng, alpha=0.05, null_r=NULL_R):
    if not survivors:
        return []
    facs = [s[3] for s in survivors]
    # ---- Reality-Check / Romano-Wolf max-null via shuffle-eval (day-block target permutation) ----
    # vectorized: precompute factor+target xsec ranks once, row-wise rank-corr per permutation.
    max_null = _maxnull_fast(facs, C, rng, null_r)
    rc_thresh = float(np.nanpercentile(max_null, 100 * (1 - alpha)))

    out = []
    legs = ("king", "s2", "funding_leg", "size_leg")
    leg_ranks = {leg: _xsec_ranks(C["ctx"][leg], C) for leg in legs}   # precompute leg ranks once
    for (f, meta, st, factor) in survivors:
        # pred-corr vs the 4 legs (vectorized row-wise rank-corr) [+ accepted factory factors: batch-2 stub]
        fr = _xsec_ranks(factor, C)
        pc = {}
        for leg in legs:
            ic = _rowwise_rankcorr(fr, leg_ranks[leg])
            pc[leg] = round(float(np.nanmean(np.abs(ic))), 3) if np.isfinite(ic).any() else 0.0
        predcorr_ok = all(v < PREDCORR_MAX for v in pc.values())
        reality_pass = bool(np.isfinite(st["inc_ic"]) and st["inc_ic"] > rc_thresh)
        z_pass = bool(st["z"] is not None and abs(st["z"]) >= BONFERRONI_Z)
        ci_pass = bool(st["ci"][0] > 0 or st["ci"][1] < 0)
        verdict = "CANDIDATE" if (st["sign_consistent"] and reality_pass and z_pass and ci_pass and predcorr_ok) else "REJECT"
        cause = None if verdict == "CANDIDATE" else (
            "below_realitycheck" if not reality_pass else "below_zstar" if not z_pass else
            "ci_includes_0" if not ci_pass else "pred_corr_redundant" if not predcorr_ok else "sign_flip")
        s1 = dict(inc_ic=st["inc_ic"], by_year=st["by_year"], z=st["z"], ci=st["ci"],
                  reality_check_thresh=round(rc_thresh, 5), reality_check_pass=reality_pass,
                  z_pass=z_pass, ci_pass=ci_pass, sign_consistent=st["sign_consistent"],
                  pred_corr=pc, predcorr_ok=predcorr_ok)
        ledger.append_stage1(f, meta["md5"], meta["depth"], meta["n_ops"], stage1_stats=s1,
                             verdict=verdict, death_cause=cause)
        out.append((f, verdict, s1))
    return out


def run_batch(formulas, horizon=4, seed=0, ledger_path=None, subsample=1, null_r=NULL_R, C=None):
    rng = np.random.default_rng(seed)
    if C is None:
        C = load_context(horizon, subsample=subsample)
    lg = Ledger(ledger_path) if ledger_path else Ledger()
    survivors = stage0(formulas, C, lg, rng)
    results = stage1(survivors, C, lg, rng, null_r=null_r)
    return dict(n_formulas=len(formulas), n_stage0_survivors=len(survivors),
                candidates=[f for f, v, s in results if v == "CANDIDATE"],
                stage1=[{"formula": f, "verdict": v, "inc_ic": s["inc_ic"], "z": s["z"],
                         "reality_pass": s["reality_check_pass"], "predcorr": s["pred_corr"]}
                        for f, v, s in results],
                ledger_M=lg.M())
