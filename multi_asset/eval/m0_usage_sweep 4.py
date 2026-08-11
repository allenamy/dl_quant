"""USAGE-LAYER sweep on the saved M0 fullhist preds — can trading DESIGN rescue M0's 2023/24 net-cost?

> Pre-registered (2026-07-10, lead+user). M0 is IC-real all years (z11-15), mono 0.9+, tails richest,
> but net-cost tradeable ONLY 2025 under ONE usage (z-weighted full book + EMA-hold): its 2023/24
> signal is fast (weight-autocorr 0.18-0.27) → cost-killed. Test whether alternative USAGES rescue it.

Three designs, per test year (2023/24/25), raw-caliber (panel_ref y_3600, >=3600 CL — same Y as the
replay baselines so variants are apples-to-apples):
  1. TAIL-GATED M0 book: {decile, quintile} × hold {none, flip, opp_tail, minhold N h}. Tails have
     the richest per-trade edge + holding collapses turnover. Baseline = M0 full-book (2023/24/25
     net-Sh@5 -2.05/-1.77/+1.37) AND the net-cost floor (>0).
  2. FUNDING-FILTER/TILT: funding = WHAT to hold; M0 only modulates (sign-agreement filter / confidence
     tilt). Near-zero added turnover. Baseline = funding-alone (+0.40/+0.85/+2.25 net-Sh-opt caliber).
  3. REBALANCE-TIMING: funding = WHAT, M0 = WHEN (rebalance funding only when M0 signals change).
     Turnover-neutral/reducing. Baseline = funding fixed-schedule.

★ ACCEPTANCE (LOCKED before results): a variant ACCEPTS iff it beats its baseline on >=2 of 3 years
  AND is per-year sign-consistent (no year worse-signed). Design-1 also must clear net-cost floor
  (net-Sh@5 > 0) on >=2/3. Single-seed-42.
★ KNOWN DEAD-END (excluded): post-hoc EMA smoothing of the M0 PREDS (= the caliber that killed it;
  the info lives in the fast component). Tail-gating/filter/timing are legit usages; EMA-of-preds is not.

Usage: PYTHONPATH=. python multi_asset/eval/m0_usage_sweep.py
"""
from __future__ import annotations
import sys, os.path as op, datetime as dt, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel
from multi_asset.eval.backtest_longshort import rank_weights

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
MIN = 5
ANN = np.sqrt(365 * 24 * 3600 / 3600)
YEARS = [2023, 2024, 2025]
BASE_M0 = {2023: -2.05, 2024: -1.77, 2025: 1.37}       # replay M0 full-book net-Sh@5 (net-Sh-opt caliber)
BASE_FUND = {2023: 0.40, 2024: 0.85, 2025: 2.25}       # replay funding-alone net-Sh@5


def _pnl(W, Yr, cost_bps=5.0):
    """W (n,S) target weights per clean step; Yr (n,S) fwd returns. Returns net-Sh + BE + turnover."""
    n = len(W)
    g = np.array([np.nansum(W[k] * np.nan_to_num(Yr[k])) for k in range(n)])
    tn = np.array([np.abs(W[k] - (W[k - 1] if k else 0.0)).sum() for k in range(n)])
    c = cost_bps * 1e-4
    net = g - tn * c
    nsh = float(net.mean() / net.std() * ANN) if net.std() > 0 else np.nan
    gsh = float(g.mean() / g.std() * ANN) if g.std() > 0 else np.nan
    be = float(g.mean() / tn.mean() * 1e4) if tn.mean() > 1e-12 else np.nan
    return dict(net_sh=nsh, gross_sh=gsh, be=be, turn=float(tn.mean()))


def _dollar_neutral(pos):
    """pos (S,) in {-1,0,+1} (or continuous) -> dollar-neutral weights, gross ~1."""
    w = pos.astype(float).copy()
    lp, sp = w > 0, w < 0
    if lp.any():
        w[lp] = w[lp] / (2.0 * w[lp].sum())
    if sp.any():
        w[sp] = w[sp] / (2.0 * np.abs(w[sp]).sum())
    return w


def _clean_seq(sig, Y, CL, rows):
    out = []
    for t in rows:
        v = CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN and np.std(sig[t, v]) > 1e-12:
            out.append(t)
    return np.array(out, int)


# ---------------- Design 1: tail-gated M0 book ----------------
def design1(M0, Y, CL, rows, q, hold, minhold_n=4):
    ts = _clean_seq(M0, Y, CL, rows); S = Y.shape[1]
    W = np.zeros((len(ts), S)); Yr = np.zeros((len(ts), S))
    pos = np.zeros(S); entry = np.full(S, -10 ** 9)
    for k, t in enumerate(ts):
        v = np.where(CL[t] & np.isfinite(M0[t]) & np.isfinite(Y[t]))[0]
        s = M0[t, v]
        lo, hi = np.quantile(s, q), np.quantile(s, 1 - q)
        side = np.zeros(S); side[v[s >= hi]] = 1.0; side[v[s <= lo]] = -1.0
        if hold == "none":
            pos = side
        elif hold == "flip":                                   # hold until raw M0 sign flips vs pos
            newpos = pos.copy()
            for a in v:
                sgn = np.sign(M0[t, a])
                if pos[a] == 0 and side[a] != 0:
                    newpos[a] = side[a]; entry[a] = k
                elif pos[a] != 0 and sgn == -pos[a]:
                    newpos[a] = 0.0
            pos = newpos
        elif hold == "opp_tail":                               # hold through neutral; flip at opposite tail
            pos = np.where(side != 0, side, pos)
        elif hold == "minhold":                                # refresh tail but lock N steps after entry
            newpos = pos.copy()
            for a in range(S):
                if pos[a] == 0 and side[a] != 0:
                    newpos[a] = side[a]; entry[a] = k
                elif pos[a] != 0 and (k - entry[a]) >= minhold_n:
                    if side[a] == 0 or side[a] == -pos[a]:
                        newpos[a] = side[a]; entry[a] = k if side[a] != 0 else entry[a]
            pos = newpos
        W[k] = _dollar_neutral(pos)
        Yr[k, v] = Y[t, v]
    return W, Yr


# ---------------- Design 2: funding book, M0 modulates ----------------
def design2(M0, FU, Y, CL, rows, mode):
    ts = _clean_seq(FU, Y, CL, rows); S = Y.shape[1]
    W = np.zeros((len(ts), S)); Yr = np.zeros((len(ts), S))
    for k, t in enumerate(ts):
        v = np.where(CL[t] & np.isfinite(FU[t]) & np.isfinite(Y[t]) & np.isfinite(M0[t]))[0]
        wf = np.zeros(S); wf[v] = rank_weights(FU[t, v])       # funding base book (WHAT to hold)
        m = M0[t, v]
        mult = np.ones(S)
        if mode == "sign_zero":                                # keep funding only where M0 agrees in sign
            mult[v] = (np.sign(m) == np.sign(wf[v])).astype(float)
        elif mode == "sign_half":
            mult[v] = np.where(np.sign(m) == np.sign(wf[v]), 1.0, 0.5)
        elif mode == "tilt":                                   # scale by M0 percentile agreement [0.5..1.5]
            pr = (np.argsort(np.argsort(m)) + 0.5) / len(m)    # percentile 0..1
            agree = np.where(np.sign(m) == np.sign(wf[v]), pr, 1 - pr)
            mult[v] = 0.5 + agree
        w = wf * mult
        W[k] = _dollar_neutral(np.sign(w) * np.abs(w))         # renormalize dollar-neutral
        Yr[k, v] = Y[t, v]
    return W, Yr


# ---------------- Design 3: funding=WHAT, M0=WHEN (rebalance timing) ----------------
def design3(M0, FU, Y, CL, rows, thr):
    ts = _clean_seq(FU, Y, CL, rows); S = Y.shape[1]
    W = np.zeros((len(ts), S)); Yr = np.zeros((len(ts), S)); held = np.zeros(S); prev_m = None
    for k, t in enumerate(ts):
        v = np.where(CL[t] & np.isfinite(FU[t]) & np.isfinite(Y[t]) & np.isfinite(M0[t]))[0]
        wf = np.zeros(S); wf[v] = rank_weights(FU[t, v])
        mvec = np.zeros(S); mvec[v] = M0[t, v]
        # M0 "signals a change" when its xsec pattern shifts > thr (cosine distance from last rebalance)
        rebal = (prev_m is None)
        if prev_m is not None:
            a, b = mvec, prev_m
            d = 1.0 - (a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
            rebal = d > thr
        if rebal:
            held = _dollar_neutral(wf); prev_m = mvec.copy()
        W[k] = held
        Yr[k, v] = Y[t, v]
    return W, Yr


def _fund_baseline(FU, Y, CL, rows):
    """funding fixed-schedule (rebalance every step) — the design-3 baseline."""
    ts = _clean_seq(FU, Y, CL, rows); S = Y.shape[1]
    W = np.zeros((len(ts), S)); Yr = np.zeros((len(ts), S))
    for k, t in enumerate(ts):
        v = np.where(CL[t] & np.isfinite(FU[t]) & np.isfinite(Y[t]))[0]
        wf = np.zeros(S); wf[v] = rank_weights(FU[t, v]); W[k] = _dollar_neutral(wf); Yr[k, v] = Y[t, v]
    return W, Yr


def main():
    M = load_panel("m0_fullhist_wf", E); F = load_panel("fund_ema_fullhist", E)
    Y, CL, ts = M["Y"], M["CL"].astype(bool), M["ts"].astype(np.int64)
    M0, FU = M["pred"], F["pred"]
    u = 1e9 if ts[0] > 1e17 else (1e6 if ts[0] > 1e14 else 1e3)
    yr = np.array([dt.datetime.utcfromtimestamp(int(t) / u).year for t in ts])
    ry = {y: np.where(yr == y)[0] for y in YEARS}

    def run(label, fn, base):
        res = {}
        for y in YEARS:
            W, Yr = fn(ry[y]); res[y] = _pnl(W, Yr)
        n5 = {y: res[y]["net_sh"] for y in YEARS}
        beat = sum(1 for y in YEARS if n5[y] > base[y]); pos = sum(1 for y in YEARS if n5[y] > 0)
        signcons = all(np.sign(n5[y]) >= np.sign(base[y]) or n5[y] > base[y] for y in YEARS)
        print(f"  {label:38s} net-Sh@5 {[round(n5[y],2) for y in YEARS]} | "
              f"turn {[round(res[y]['turn'],3) for y in YEARS]} | BE {[round(res[y]['be'],1) for y in YEARS]} | "
              f"beat-base {beat}/3 pos {pos}/3")
        return dict(n5=n5, beat=beat, pos=pos, signcons=signcons)

    print("=" * 100)
    print(f"DESIGN 1 — TAIL-GATED M0 BOOK   (baseline M0 full-book net-Sh@5 {BASE_M0}; floor >0)")
    d1 = {}
    for q, qn in [(0.1, "decile"), (0.2, "quintile")]:
        for hold in ["none", "flip", "opp_tail", "minhold"]:
            lab = f"{qn} × {hold}"
            d1[lab] = run(lab, lambda rows, q=q, hold=hold: design1(M0, Y, CL, rows, q, hold), BASE_M0)
    print("=" * 100)
    print(f"DESIGN 2 — FUNDING-FILTER/TILT  (baseline funding-alone net-Sh@5 {BASE_FUND})")
    d2 = {}
    for mode in ["sign_zero", "sign_half", "tilt"]:
        d2[mode] = run(f"funding × M0-{mode}", lambda rows, mode=mode: design2(M0, FU, Y, CL, rows, mode), BASE_FUND)
    print("=" * 100)
    print(f"DESIGN 3 — REBALANCE-TIMING (M0=WHEN)  (baseline funding fixed-schedule)")
    fb = {y: _pnl(*_fund_baseline(FU, Y, CL, ry[y])) for y in YEARS}
    base3 = {y: fb[y]["net_sh"] for y in YEARS}
    print(f"  {'funding fixed-schedule (BASELINE)':38s} net-Sh@5 {[round(base3[y],2) for y in YEARS]} | "
          f"turn {[round(fb[y]['turn'],3) for y in YEARS]}")
    d3 = {}
    for thr in [0.05, 0.15, 0.30]:
        d3[f"thr{thr}"] = run(f"funding rebal on M0-shift>{thr}", lambda rows, thr=thr: design3(M0, FU, Y, CL, rows, thr), base3)

    print("=" * 100)
    print("PRE-REGISTERED ACCEPT (>=2/3 beat baseline AND per-year sign-consistent; D1 also floor>0 >=2/3):")
    for name, d in list(d1.items()):
        acc = d["beat"] >= 2 and d["pos"] >= 2 and d["signcons"]
        print(f"  D1 {name:32s} {'ACCEPT' if acc else 'reject'} (beat {d['beat']}/3, pos {d['pos']}/3)")
    for name, d in list(d2.items()) + list(d3.items()):
        acc = d["beat"] >= 2 and d["signcons"]
        print(f"  {name:35s} {'ACCEPT' if acc else 'reject'} (beat {d['beat']}/3)")
    print("DONE_USAGE_SWEEP")


if __name__ == "__main__":
    main()
