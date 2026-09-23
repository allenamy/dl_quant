#!/usr/bin/env python3
"""m3_rules.py — the FROZEN operational definitions of M3's criteria (prereg docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md, 24c3f803f,
§3–§4), written and committed BEFORE any M3 number (feasibility rows included). Pure functions (numpy only); imported by m3_exec_path.py,
m3_feasibility.py and m3_readout.py so that the gate is computed by one piece of code. Nothing here is tuned; each item is the literal reading.

Windows      MAIN = [2026-01-01T00Z, 2026-09-18T20Z] (the last anchor whose 4h window the certified price table x0918r covers: the grid
             ends 2026-09-19T00Z); AUX = [2023-06-30T04Z, 2025-12-31T20Z] (M2's PRE2026 = the full-recipe start → end of 2025).
Series       the certified main reading (bt_tables.series_from_path, UA-FREEZE-EXCLUDE) per path; the MEAN PATH = bt_tables.series_mean over
             the 32 paths (per-window mean return). Criteria are evaluated on the mean path (M2's convention); the 32-path distribution is
             reported next to it.
Daily        complete UTC days only (all six anchors 00Z…20Z inside the window): r_d = Π(1 + r_w) − 1 over the day's six windows. In MAIN
             every day 2026-01-01 … 2026-09-18 is complete (261 days).
BTC daily    r_BTC,d = exp(LP[d + 1 day] − LP[d]) − 1, BTCUSDT column of the certified price_full_raw_x0918r table = BTC's return over the
             same 24 hours [d 00:00Z, d+1 00:00Z] the book's day spans (M2's definition).
R1           realised daily beta = OLS slope WITH intercept of r_d(book + hedge) on r_BTC,d over MAIN's complete days; PASS iff it lies in
             [−0.10, +0.10] (closed).
R2           "days whose BTC 24h return exceeds +2 %" = MAIN complete days with r_BTC,d > 0.02 (strict; the 24 h are the day's own 24 h, the
             hours the hedge is meant to cover — "BTC 涨超 2% 日少亏"); PASS iff mean over those days of r_d(M3) > mean of r_d(base)
             (strict; mean paths). Every such day is listed with both returns. Fewer than 1 such day ⇒ UNDECIDED.
R3           flat-book delivery on the executor's own code path (m3_exec_path.py: the certified HistSim31 with the M3 hook, one anchor from a
             flat book, NAV0, decision only): per MAIN published anchor that reaches the decision in both arms,
               intended_A = −β_exec(A)                       (gross units; the hook's own β_exec in the control arm)
               move_A     = β(planned book, overlay) − β(planned book, control)   (planned book = Σ over plan rows WITH a quantity of
                                                             qty × mid, i.e. what plan() actually orders after rounding / min-notional /
                                                             UA-frozen skips; flat ⇒ no position term)
             D = Σ_A move_A·sign(intended_A) / Σ_A |intended_A|   (delivered share of the intended |move|; a skipped anchor delivers 0)
             m = median over anchors with |intended_A| > 0.01 of move_A / intended_A
             PASS iff D ∈ [0.95, 1.05] AND m ∈ [0.95, 1.05]. Anchors that do not reach the decision are excluded and COUNTED by name.
R4           report only: hedge-leg cost = (BTCUSDT fees + BTCUSDT funding paid) in the M3 run MINUS the same in the zero-hedge control run
             (bitwise the base), per path per complete day, in bps of the day's opening simulator NAV (nav0 of the day's first window, each
             arm its own), averaged over days then over the 32 paths (and the path 2.5/97.5 %); plus Sharpe / total return / maxDD (5m) /
             worst day of both arms and their differences in MAIN and AUX (mean path; per-path distribution alongside).
Verdict      per base: PASS iff R1, R2, R3 all PASS ⇒ "M3 may be submitted to the user as a risk policy (with R4 as its price)"; any FAIL
             ⇒ FAIL (listed); any criterion not computable ⇒ UNDECIDED. The verdict never depends on R4.
Feasibility  (a) daily-beta standard error on the BASE mean path in MAIN: classical OLS SE and Newey–West (Bartlett, lag 5) SE;
             (b) = R3 above; (c) the base's ex-ante executed-book beta in MAIN: flat-book β_exec (m3_exec_path) and in-path β_exec from the
             zero-hedge control's sidecar (seed 0), each with mean / quantiles / share < 0, next to the pre-reshape (published) beta.
Empty inputs raise (unknown is not zero); every aggregate prints its n.
"""
import calendar, math, time

import numpy as np

DAY = 86400; H4 = 14400
R1_BAND = (-0.10, 0.10)
R3_BAND = (0.95, 1.05)
R3_MEDIAN_MIN_ABS_INTENDED = 0.01
BTC_UP = 0.02
NW_LAG = 5


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


MAIN = (ts("2026-01-01T00:00:00Z"), ts("2026-09-18T20:00:00Z"))
AUX = (ts("2023-06-30T04:00:00Z"), ts("2025-12-31T20:00:00Z"))
WINDOWS = {"MAIN_2026-01-01_to_2026-09-18T20Z": MAIN, "AUX_2023-06-30T04Z_to_2025-12-31T20Z": AUX}


class Empty(Exception):
    pass


def complete_days(A, r, a0, a1):
    A = np.asarray(A, np.int64); r = np.asarray(r, float)
    m = (A >= a0) & (A <= a1)
    A = A[m]; r = r[m]
    if len(A) == 0: raise Empty(f"no anchors in [{a0}, {a1}]")
    d = (A // DAY) * DAY
    ud, inv, cnt = np.unique(d, return_inverse=True, return_counts=True)
    out = np.ones(len(ud)); np.multiply.at(out, inv, 1.0 + r)
    keep = cnt == 6
    if not keep.any(): raise Empty("no complete day")
    return ud[keep], out[keep] - 1.0, int(len(ud) - keep.sum())


def ols(y, x):
    """slope, intercept, classical SE of the slope, Newey–West (Bartlett, NW_LAG) SE of the slope, n"""
    y = np.asarray(y, float); x = np.asarray(x, float); n = len(y)
    if n < 3 or len(x) != n: raise Empty(f"ols needs >= 3 paired points, got {n}")
    dx = x - x.mean(); sxx = float((dx * dx).sum())
    if not sxx > 0: raise Empty("zero variance in x")
    b = float((dx * (y - y.mean())).sum() / sxx); a = float(y.mean() - b * x.mean())
    e = y - a - b * x
    se = math.sqrt(float((e * e).sum()) / (n - 2) / sxx)
    u = dx * e; S = float((u * u).sum())
    for L in range(1, NW_LAG + 1):
        S += 2.0 * (1.0 - L / (NW_LAG + 1.0)) * float((u[L:] * u[:-L]).sum())
    se_nw = math.sqrt(max(S, 0.0)) / sxx
    return {"slope": b, "intercept": a, "se_classical": se, "se_newey_west_lag5": se_nw, "n": n}


def r1(beta):
    return {"measured": beta, "gate": list(R1_BAND), "pass": bool(R1_BAND[0] <= beta <= R1_BAND[1])}


def r2(days, rd_m3, rd_base, rb):
    days = np.asarray(days); rb = np.asarray(rb, float)
    up = rb > BTC_UP
    if not up.any(): return {"undecided": "no day with BTC 24h return > +2 % in the window", "pass": None, "n_days": 0}
    mm, mb = float(np.mean(np.asarray(rd_m3)[up])), float(np.mean(np.asarray(rd_base)[up]))
    rows = [[time.strftime("%Y-%m-%d", time.gmtime(int(d))), float(b), float(x), float(y), float(x - y)]
            for d, b, x, y in zip(days[up], rb[up], np.asarray(rd_m3)[up], np.asarray(rd_base)[up])]
    return {"n_days": int(up.sum()), "mean_m3": mm, "mean_base": mb, "diff": mm - mb, "n_days_m3_better": int(np.sum(np.asarray(rd_m3)[up] > np.asarray(rd_base)[up])),
            "rows[date, r_btc, r_m3, r_base, diff]": rows, "gate": "mean_m3 > mean_base", "pass": bool(mm > mb)}


def r3(intended, move):
    intended = np.asarray(intended, float); move = np.asarray(move, float)
    if len(intended) == 0 or len(move) != len(intended): raise Empty("R3: no anchors")
    if not (np.all(np.isfinite(intended)) and np.all(np.isfinite(move))): raise Empty("R3: non-finite intended / move")
    den = float(np.abs(intended).sum())
    if not den > 0: raise Empty("R3: zero intended hedge everywhere")
    D = float((move * np.sign(intended)).sum() / den)
    big = np.abs(intended) > R3_MEDIAN_MIN_ABS_INTENDED
    if not big.any(): raise Empty("R3: no anchor with |intended| > 0.01")
    ratio = move[big] / intended[big]
    med = float(np.median(ratio))
    inband = (ratio >= R3_BAND[0]) & (ratio <= R3_BAND[1])
    return {"D_delivered_share": D, "median_ratio(|intended|>0.01)": med, "n_anchors": int(len(intended)), "n_for_median": int(big.sum()),
            "share_anchors_ratio_in_band": float(inband.mean()), "ratio_p05": float(np.percentile(ratio, 5)), "ratio_p95": float(np.percentile(ratio, 95)),
            "n_anchors_zero_move_with_intended": int(np.sum((move == 0.0) & (intended != 0.0))), "gate": list(R3_BAND),
            "pass": bool(R3_BAND[0] <= D <= R3_BAND[1] and R3_BAND[0] <= med <= R3_BAND[1])}


def dist(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0: raise Empty("empty distribution")
    return {"n": int(len(x)), "mean": float(x.mean()), **{f"p{q}": float(np.percentile(x, q)) for q in (5, 25, 50, 75, 95)}, "share_negative": float((x < 0).mean())}
