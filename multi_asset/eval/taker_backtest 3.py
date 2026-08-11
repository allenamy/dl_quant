"""Single-asset taker/maker NET-OF-COST backtest on y_600 OOS preds (Run1 / production).
User-authorized; "no logic errors" mandate -> the VERIFICATION BATTERY must PASS before any alpha
number is trusted. Run --battery first; only then read the economic table.

DESIGN (all causal, ≤t_k):
- DECISION GRID: per UTC clean day, greedy stride-600 NON-OVERLAPPING sample of preds -> periods
  k spaced ≥600s so [t_k,t_k+600] never overlaps [t_{k+1},...]. PnL_k = π_k·y_600(t_k) directly.
- SIGNAL: causal decision-demean center c_k = trailing mean of p over W periods (≤t_k) -> deviation
  d_k = p_k − c_k. Magnitude calibration d_k -> ê_k (bps) via OFF-TEST expanding-prior OLS slope
  (fit on PRIOR months only, never the test month's realized y). First month(s): ê=0 (no trades).
- RULE (asymmetric, cost-aware, hysteresis + min-hold): enter long if ê>+ (cost_rt+buf_long), short
  if ê< −(cost_rt+buf_short) with buf_short≤buf_long (H1 short-tail edge); hold until ê crosses a
  LOWER exit band (exit_frac·T); min-hold M periods; π∈{−1,0,+1}. Position CARRIES across days
  (so constant-long pays ONE entry cost — unit-test #4).
- COST: pay per SIDE on |Δπ| (flip=2 sides); hold=0. Grid {0,0.5,1.0,1.7} one-side taker + a
  maker/taker HYBRID (entries/exits=maker, flips=taker).

Run:  python multi_asset/eval/taker_backtest.py --battery
      python multi_asset/eval/taker_backtest.py --preds <csv|dir> --econ
"""
from __future__ import annotations
import numpy as np, pandas as pd, argparse, glob, os

SEC = 1000; HZ = 600 * SEC; DAY = 86400 * SEC
MONTHS = ["2025_08", "2025_09", "2025_10", "2025_11", "2025_12", "2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]


# ------------------------------ data ------------------------------
def load_preds(source):
    """CSV backtest OR dir of wf_*/fold_0/ema_test_preds.npz -> df[ts_ms, p, y_bps, month]."""
    if source.endswith(".csv"):
        d = pd.read_csv(source)
        return pd.DataFrame({"ts": d.timestamp_ms.astype(np.int64), "p": d.y_pred_raw.astype(float),
                             "y": d.y_true_ret_bps.astype(float), "month": d.month})
    rows = []
    for f in sorted(glob.glob(os.path.join(source, "wf_*/fold_0/ema_test_preds.npz"))):
        mk = f.split("wf_")[1][:7]
        z = np.load(f, allow_pickle=True); pr = z["predictions"]
        q = (pr[:, 1] if pr.ndim == 2 else pr).astype(float); y = z["targets"].astype(float)
        ts = z["timestamps"].astype(np.int64); ts = ts // 1000 if ts[0] > 3e12 else ts
        ysig = float(z["y_sigma"]) if "y_sigma" in z.files else 1.0; ymed = float(z["y_median"]) if "y_median" in z.files else 0.0
        m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(y), bool)
        rows.append(pd.DataFrame({"ts": ts[m], "p": q[m], "y": (y[m] * ysig + ymed) * 1e4, "month": mk}))
    return pd.concat(rows, ignore_index=True)


def nonoverlap_grid(df):
    """Per UTC day, greedy ≥600s non-overlap; return time-sorted periods across all days."""
    df = df[df.y != 0].copy()
    ts = df.ts.values.astype(np.int64); order = np.argsort(ts)
    df = df.iloc[order].reset_index(drop=True); ts = df.ts.values.astype(np.int64)
    day = ts // DAY; keep = np.zeros(len(df), bool)
    for d in np.unique(day):
        idx = np.where(day == d)[0]; last = -1 << 62
        for i in idx:
            if ts[i] - last >= HZ:
                keep[i] = True; last = ts[i]
    return df[keep].reset_index(drop=True)


# ------------------------------ signal ------------------------------
def decision_center(p, W):
    """Trailing mean of p over the last W periods INCLUSIVE of current (≤t_k, causal)."""
    c = np.empty_like(p)
    csum = np.concatenate([[0.0], np.cumsum(p)])
    for k in range(len(p)):
        lo = max(0, k - W + 1)
        c[k] = (csum[k + 1] - csum[lo]) / (k - lo + 1)
    return c


def calibrate_offtest(d, y, month):
    """ê_k = slope_prior · d_k, slope from OLS(y~d) on PRIOR months only (never the test month)."""
    ehat = np.zeros(len(d))
    for i, mk in enumerate(MONTHS):
        te = (month == mk)
        if not te.any():
            continue
        tr = np.isin(month, MONTHS[:i])          # strictly prior months
        if tr.sum() < 200 or np.std(d[tr]) < 1e-12:
            continue                              # no calibration yet -> ê stays 0 (no trades)
        slope = np.cov(y[tr], d[tr])[0, 1] / np.var(d[tr])
        ehat[te] = slope * d[te]
    return ehat


# ------------------------------ strategy state machine ------------------------------
def _trans_cost(pi_old, pi_new, cost_side, hybrid, maker, taker):
    dpi = abs(pi_new - pi_old)
    if dpi == 0:
        return 0.0
    if not hybrid:
        return dpi * cost_side
    return 2 * taker if dpi == 2 else maker      # flip=taker(2 sides); entry/exit=maker


def run_strategy(ehat, y, cost_side, buf_long, buf_short, exit_frac, min_hold,
                 hysteresis=True, hybrid=False, maker=0.0, taker=1.7):
    n = len(ehat); cost_rt = 2 * cost_side
    T_long = cost_rt + buf_long; T_short = -(cost_rt + buf_short)
    xl = exit_frac * T_long; xs = exit_frac * T_short       # lower exit bands
    if not hysteresis:                                       # OFF: exit band == entry band, no min-hold
        xl = T_long; xs = T_short; min_hold = 0
    pi = 0; hold = 0
    pnl = np.empty(n); pos = np.empty(n, np.int8); dpis = np.empty(n)
    for k in range(n):
        if pi != 0 and hold < min_hold:
            new = pi                                         # locked by min-hold
        elif pi == 0:
            new = 1 if ehat[k] > T_long else (-1 if ehat[k] < T_short else 0)
        elif pi == 1:
            new = 1 if ehat[k] >= xl else (-1 if ehat[k] < T_short else 0)
        else:  # pi == -1
            new = -1 if ehat[k] <= xs else (1 if ehat[k] > T_long else 0)
        c = _trans_cost(pi, new, cost_side, hybrid, maker, taker)
        pnl[k] = new * y[k] - c; pos[k] = new; dpis[k] = abs(new - pi)
        hold = 0 if new != pi else hold + 1
        pi = new
    return pnl, pos, dpis


def metrics(pnl, pos, dpis, y, ts):
    n = len(pnl); gross = float(np.sum(pos * y)); net = float(np.sum(pnl))
    sides = float(np.sum(dpis)); ntr = int(np.sum(dpis > 0))
    entered = pos != 0
    hit = float(np.mean(np.sign(pos[entered]) == np.sign(y[entered]))) if entered.any() else np.nan
    turn = float(np.mean(dpis > 0))
    yrs = max((ts.max() - ts.min()) / (365.25 * DAY), 1e-9); ppy = n / yrs
    sh = float(np.mean(pnl) / (np.std(pnl) + 1e-12) * np.sqrt(ppy))
    be = gross / sides if sides > 0 else np.inf              # break-even one-side cost (all-taker)
    return dict(net=net, gross=gross, sides=sides, ntrades=ntr, hit=hit, turnover=turn,
                sharpe=sh, breakeven=be, ppy=ppy, exposure=float(np.mean(entered)))


# ------------------------------ verification battery ------------------------------
def battery(df, cfg):
    G = nonoverlap_grid(df); ts = G.ts.values.astype(np.int64); y = G.y.values; p = G.p.values; mon = G.month.values
    print(f"grid: {len(G)} non-overlap periods, {len(np.unique(ts//DAY))} days")
    ok = True

    # (6) NON-OVERLAP: consecutive same-day periods ≥600s apart
    day = ts // DAY; viol = 0
    for d in np.unique(day):
        t = np.sort(ts[day == d]); viol += int(np.any(np.diff(t) < HZ))
    print(f"[6] NON-OVERLAP: {viol} day(s) with <600s spacing  -> {'PASS' if viol == 0 else 'FAIL'}"); ok &= viol == 0

    # (1) CAUSALITY: center uses ≤k; calibration excludes the test month. Assert on a probe.
    c = decision_center(p, cfg["W"]); d = p - c
    # probe: recompute center at a random k using only ≤k, must match
    kk = len(p) // 2; ref = np.mean(p[max(0, kk - cfg["W"] + 1):kk + 1])
    caus_c = abs(c[kk] - ref) < 1e-9
    # probe: calibration slope for a month must not change if that month's y is corrupted
    eh = calibrate_offtest(d, y, mon); ycorr = y.copy(); ycorr[mon == "2026_03"] = 0.0
    eh2 = calibrate_offtest(d, ycorr, mon)
    caus_cal = np.allclose(eh[mon == "2026_03"], eh2[mon == "2026_03"])   # test-month y change must NOT alter its own ê
    print(f"[1] CAUSALITY: center≤t {caus_c} | calib off-test (corrupt test-month y ⇒ same ê) {caus_cal}"
          f"  -> {'PASS' if caus_c and caus_cal else 'FAIL'}"); ok &= caus_c and caus_cal

    # (4) COST-SIGN unit test: constant-long (ê=+inf) => net = Σy − 1·cost_side
    ehL = np.full(len(p), 1e9)
    pnlL, posL, dpL = run_strategy(ehL, y, cost_side=1.0, buf_long=0, buf_short=0, exit_frac=0.3, min_hold=1)
    exp = float(np.sum(y) - 1.0)
    u4 = abs(float(np.sum(pnlL)) - exp) < 1e-6 and int(np.sum(dpL)) == 1
    print(f"[4] COST-SIGN: const-long net={np.sum(pnlL):.4f} vs Σy−1cost={exp:.4f}, sides={int(np.sum(dpL))}"
          f"  -> {'PASS' if u4 else 'FAIL'}"); ok &= u4

    # (5) TURNOVER MONOTONICITY: hysteresis ON < OFF
    a = run_strategy(eh, y, cfg["cost"], cfg["buf_long"], cfg["buf_short"], cfg["exit_frac"], cfg["min_hold"], hysteresis=True)
    b = run_strategy(eh, y, cfg["cost"], cfg["buf_long"], cfg["buf_short"], cfg["exit_frac"], cfg["min_hold"], hysteresis=False)
    ton = float(np.mean(a[2] > 0)); toff = float(np.mean(b[2] > 0))
    u5 = ton <= toff
    print(f"[5] TURNOVER: hysteresis ON {ton:.3f} <= OFF {toff:.3f}  -> {'PASS' if u5 else 'FAIL'}"); ok &= u5

    # (3) ORACLE SANITY: ê = sign(y) big => strongly profitable @0, degrades w/ cost
    eO = np.sign(y) * 1e9
    prof = {}
    for cst in (0.0, 1.0, 1.7):
        pn, po, dp = run_strategy(eO, y, cost_side=cst, buf_long=0, buf_short=0, exit_frac=0.3, min_hold=1)
        prof[cst] = float(np.sum(pn))
    u3 = prof[0.0] > 0 and prof[0.0] > prof[1.0] > prof[1.7]
    print(f"[3] ORACLE sign(y): net @0={prof[0.0]:.0f} @1.0={prof[1.0]:.0f} @1.7={prof[1.7]:.0f} bps"
          f"  -> {'PASS' if u3 else 'FAIL'}"); ok &= u3

    # (2) SHUFFLE-NULL: 50 within-day permutations. TWO reads, decoupled (0B's fix — 5-shuffle was
    #     seed-fragile). (a) ENGINE-UNBIASED = null distribution centered near 0 (|mean| « std) i.e.
    #     no PnL manufactured from noise — THIS is the battery gate. (b) SIGNAL z/percentile of real
    #     gross vs the null (reported, not gated; 0B measured z≈2.0 = marginal, so report honestly).
    rng = np.random.default_rng(0); grosses = []
    NSH = 50
    for _ in range(NSH):
        ps = p.copy()
        for dd in np.unique(day):
            idx = np.where(day == dd)[0]; ps[idx] = p[idx][rng.permutation(len(idx))]
        ds = ps - decision_center(ps, cfg["W"]); ehs = calibrate_offtest(ds, y, mon)
        pn, po, dp = run_strategy(ehs, y, cfg["cost"], cfg["buf_long"], cfg["buf_short"], cfg["exit_frac"], cfg["min_hold"])
        grosses.append(float(np.sum(po * y)))
    grosses = np.asarray(grosses)
    real_gross = float(np.sum(a[1] * y))
    nmean, nstd = float(np.mean(grosses)), float(np.std(grosses) + 1e-12)
    z = (real_gross - nmean) / nstd
    pct = float(np.mean(grosses < real_gross)) * 100.0
    u2 = abs(nmean) < 0.5 * nstd                                 # engine-unbiased gate (not the signal claim)
    print(f"[2] SHUFFLE-NULL ({NSH}x): null mean={nmean:.1f} std={nstd:.1f} (engine unbiased |mean|<0.5std -> "
          f"{'PASS' if u2 else 'FAIL'})  |  real gross={real_gross:.1f}  z={z:.2f}  pct={pct:.0f}%"
          f"  [{'signal>2σ' if z > 2 else 'MARGINAL signal'}]"); ok &= u2

    print(f"\nBATTERY: {'ALL PASS' if ok else 'FAIL — do not trust alpha'}")
    return ok


# ------------------------------ economic table ------------------------------
def econ(df, cfg, label):
    G = nonoverlap_grid(df); ts = G.ts.values.astype(np.int64); y = G.y.values; p = G.p.values; mon = G.month.values
    d = p - decision_center(p, cfg["W"]); eh = calibrate_offtest(d, y, mon)
    print(f"\n=== ECONOMIC TABLE [{label}]  ({len(G)} periods) ===")
    print(f"{'cost(1-side)':>12s} {'net_bps':>9s} {'Sharpe':>7s} {'PnL/trade':>9s} {'turnover':>8s} {'hit':>6s} {'exposure':>8s}")
    for cst in (0.0, 0.5, 1.0, 1.7):
        pn, po, dp = run_strategy(eh, y, cst, cfg["buf_long"], cfg["buf_short"], cfg["exit_frac"], cfg["min_hold"])
        m = metrics(pn, po, dp, y, ts)
        ppt = m["net"] / m["ntrades"] if m["ntrades"] else np.nan
        print(f"{cst:12.2f} {m['net']:9.1f} {m['sharpe']:7.2f} {ppt:9.3f} {m['turnover']:8.3f} {m['hit']:6.3f} {m['exposure']:8.3f}")
    # maker/taker hybrid
    pn, po, dp = run_strategy(eh, y, cfg["cost"], cfg["buf_long"], cfg["buf_short"], cfg["exit_frac"], cfg["min_hold"],
                              hybrid=True, maker=cfg["maker"], taker=cfg["taker"])
    mh = metrics(pn, po, dp, y, ts)
    print(f"HYBRID maker={cfg['maker']}/taker={cfg['taker']}: net={mh['net']:.1f} Sharpe={mh['sharpe']:.2f} "
          f"turnover={mh['turnover']:.3f} hit={mh['hit']:.3f}")
    # break-even headline (gross / sides at the operating point)
    pn0, po0, dp0 = run_strategy(eh, y, 0.0, cfg["buf_long"], cfg["buf_short"], cfg["exit_frac"], cfg["min_hold"])
    m0 = metrics(pn0, po0, dp0, y, ts)
    print(f"★ BREAK-EVEN one-side cost = {m0['breakeven']:.3f} bps (gross {m0['gross']:.1f} / {m0['sides']:.0f} sides)")

    # FIXED-threshold cost-sweep (tune once @0, apply grid to the SAME position path) -> monotone
    print("  fixed-strategy(cost0-thresholds) cost-sweep net_bps (monotone):", end=" ")
    for cst in (0.0, 0.5, 1.0, 1.7):
        print(f"@{cst}={m0['gross'] - cst * m0['sides']:.0f}", end="  ")
    print()

    # per-month break-even (which months carry the alpha), cost-adaptive at cfg cost
    print("  per-month break-even (bps) [gross/sides, hit, turnover]:")
    for mk in MONTHS:
        sel = mon == mk
        if sel.sum() < 50:
            continue
        pn, po, dp = run_strategy(eh[sel], y[sel], 0.0, cfg["buf_long"], cfg["buf_short"], cfg["exit_frac"], cfg["min_hold"])
        mm = metrics(pn, po, dp, y[sel], ts[sel])
        print(f"    {mk}: BE={mm['breakeven']:.3f}  hit={mm['hit']:.3f}  turn={mm['turnover']:.3f}  gross={mm['gross']:.0f}")
    return m0["breakeven"]


# ------------------------------ tail-selectivity sweep ------------------------------
def _dayblock_boot(day_arr, pnl_k, nboot, seed):
    """Day-block bootstrap of total net PnL: resample UTC days w/ replacement (block = a day's trades)."""
    ds = pd.Series(pnl_k).groupby(day_arr).sum().values      # per-day net-PnL sums
    nd = len(ds)
    if nd < 2:
        return np.array([float(ds.sum())])
    rng = np.random.default_rng(seed)
    return np.array([ds[rng.integers(0, nd, nd)].sum() for _ in range(nboot)])


def _tail_stats(sgn, yy, day_arr, mon_arr, taker, yrs, nboot, seed, label):
    """Independent-round-trip stats for a set of tail trades: enter@t_k, exit@t_k+600 (2 sides).
    CONSERVATIVE (never carries -> max cost); carrying same-sign neighbours would only help."""
    n = len(yy); rt = 2 * taker
    if n == 0:
        return dict(n=0, per_side=np.nan, per_trade=np.nan, net=np.nan, sharpe=np.nan,
                    hit=np.nan, clears=False, boot_frac_pos=np.nan, boot_lo=np.nan, boot_hi=np.nan)
    gk = sgn * yy                                            # gross per round-trip (bps)
    gross = float(gk.sum()); per_trade = gross / n; per_side = gross / (2 * n)
    net = gross - rt * n
    pnl_k = gk - rt
    tpy = n / yrs
    sh = float(np.mean(pnl_k) / (np.std(pnl_k) + 1e-12) * np.sqrt(tpy))
    hit = float(np.mean(sgn == np.sign(yy)))
    boots = _dayblock_boot(day_arr, pnl_k, nboot, seed)
    return dict(n=n, per_side=per_side, per_trade=per_trade, net=net, sharpe=sh, hit=hit,
                clears=per_side > taker, boot_frac_pos=float(np.mean(boots > 0)),
                boot_lo=float(np.percentile(boots, 2.5)), boot_hi=float(np.percentile(boots, 97.5)))


def tail_sweep(df, cfg, label, taker=1.7, nboot=3000):
    """Trade ONLY the fat tail of |ê| (off-test calibrated signal-deviation). For each top-f cutoff,
    each selected non-overlap period is an independent round-trip (2 taker sides = 3.4 rt @1.7).
    Answers: is there a cutoff where per-trade edge ROBUSTLY exceeds taker cost, or does it evaporate?"""
    G = nonoverlap_grid(df); ts = G.ts.values.astype(np.int64); y = G.y.values; p = G.p.values; mon = G.month.values
    d = p - decision_center(p, cfg["W"]); eh = calibrate_offtest(d, y, mon)
    cal = eh != 0.0                                          # only calibrated (post-warmup) periods tradeable
    ae = np.abs(eh); day = ts // DAY
    yrs = max((ts.max() - ts.min()) / (365.25 * DAY), 1e-9)
    rt = 2 * taker
    ncal = int(cal.sum())
    print(f"\n=== TAIL-SELECTIVITY SWEEP [{label}]  taker={taker} (round-trip {rt})  ===")
    print(f"grid {len(G)} periods, {ncal} calibrated (tradeable), {len(np.unique(day))} days, {yrs:.2f} yr span")
    print(f"NOTE: threshold = pooled top-f quantile of |ê| among calibrated (mild in-sample peek on the CUTOFF"
          f" LOCATION only; slope calibration stays strictly off-test). Causal expanding-prior sensitivity in last col.")
    print(f"{'top-f':>7s} {'thr(bps)':>8s} {'#tr':>5s} {'per_side':>8s} {'clears1.7':>9s} {'per_trade':>9s} "
          f"{'net_bps':>9s} {'Sharpe':>7s} {'hit':>5s} {'boot>0':>7s} {'boot95%CI':>18s} {'causal_ps':>9s}")
    fracs = (0.10, 0.05, 0.02, 0.01, 0.005)
    rows = {}
    for f in fracs:
        thr = float(np.quantile(ae[cal], 1.0 - f))
        sel = cal & (ae >= thr)
        st = _tail_stats(np.sign(eh[sel]), y[sel], day[sel], mon[sel], taker, yrs, nboot, 0, f)
        # causal sensitivity: threshold from expanding-prior |ê| (prior months only)
        cps_num = cps_den = 0.0
        for i, mk in enumerate(MONTHS):
            te = (mon == mk) & cal
            if not te.any():
                continue
            prior = np.isin(mon, MONTHS[:i]) & cal
            if prior.sum() < 200:
                continue
            tq = float(np.quantile(ae[prior], 1.0 - f))
            s2 = te & (ae >= tq)
            if s2.any():
                cps_num += float((np.sign(eh[s2]) * y[s2]).sum()); cps_den += 2 * int(s2.sum())
        cps = cps_num / cps_den if cps_den > 0 else np.nan
        rows[f] = st
        ci = f"[{st['boot_lo']:.0f},{st['boot_hi']:.0f}]"
        print(f"{f*100:6.1f}% {thr:8.3f} {st['n']:5d} {st['per_side']:8.3f} {'YES' if st['clears'] else 'no':>9s} "
              f"{st['per_trade']:9.3f} {st['net']:9.1f} {st['sharpe']:7.2f} {st['hit']:5.3f} "
              f"{st['boot_frac_pos']:7.2f} {ci:>18s} {cps:9.3f}")

    # long-tail vs short-tail split (H1: short alive in drift, long weaker)
    print(f"\n  LONG vs SHORT tail split (independent round-trips @taker {taker}):")
    print(f"  {'top-f':>7s} {'side':>5s} {'#tr':>5s} {'per_side':>8s} {'clears':>6s} {'net_bps':>9s} {'Sharpe':>7s} {'hit':>5s} {'boot>0':>7s}")
    for f in fracs:
        thr = float(np.quantile(ae[cal], 1.0 - f)); sel = cal & (ae >= thr)
        for nm, m2 in (("long", sel & (eh > 0)), ("short", sel & (eh < 0))):
            st = _tail_stats(np.sign(eh[m2]), y[m2], day[m2], mon[m2], taker, yrs, nboot, 0, nm)
            print(f"  {f*100:6.1f}% {nm:>5s} {st['n']:5d} {st['per_side']:8.3f} {'YES' if st['clears'] else 'no':>6s} "
                  f"{st['net']:9.1f} {st['sharpe']:7.2f} {st['hit']:5.3f} {st['boot_frac_pos']:7.2f}")

    # operating point = most net-positive cutoff; per-month + leave-one-month-out concentration
    op = max(fracs, key=lambda f: (rows[f]["net"] if np.isfinite(rows[f]["net"]) else -1e18))
    thr = float(np.quantile(ae[cal], 1.0 - op)); sel = cal & (ae >= thr)
    sgn = np.sign(eh[sel]); yy = y[sel]; msel = mon[sel]; gk = sgn * yy
    print(f"\n  OPERATING POINT = top {op*100:.1f}% (most net-positive). Concentration check:")
    print(f"  {'month':>8s} {'#tr':>5s} {'net_bps':>9s} {'gross':>8s} {'hit':>5s}  | LOMO net (drop this month):")
    tot_net = float((gk - rt).sum())
    for mk in MONTHS:
        sm = msel == mk
        if sm.sum() == 0:
            continue
        gm = float(gk[sm].sum()); nm_ = int(sm.sum()); netm = gm - rt * nm_
        lomo = tot_net - netm
        print(f"  {mk:>8s} {nm_:5d} {netm:9.1f} {gm:8.1f} {float(np.mean(sgn[sm]==np.sign(yy[sm]))):5.3f}  | drop-{mk}: {lomo:9.1f}")
    lomo_min = min((tot_net - (float(gk[msel==mk].sum()) - rt*int((msel==mk).sum())))
                   for mk in MONTHS if (msel==mk).sum() > 0)
    print(f"  total net={tot_net:.1f}  worst LOMO (drop best month)={lomo_min:.1f}  "
          f"-> {'SURVIVES' if lomo_min > 0 else 'DIES'} leave-one-month-out")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", default="exports/final_l01/y600_backtest_dataset.csv")
    ap.add_argument("--battery", action="store_true"); ap.add_argument("--econ", action="store_true")
    ap.add_argument("--tail", action="store_true")
    ap.add_argument("--label", default="preds")
    a = ap.parse_args()
    cfg = dict(W=12, cost=1.0, buf_long=1.0, buf_short=0.5, exit_frac=0.3, min_hold=1, maker=0.0, taker=1.7)
    df = load_preds(a.preds)
    if a.battery or not (a.econ or a.tail):
        passed = battery(df, cfg)
        if not passed:
            print("BATTERY FAILED — refusing to print alpha."); return
    if a.econ:
        econ(df, cfg, a.label)
    if a.tail:
        tail_sweep(df, cfg, a.label, taker=cfg["taker"])
    print("DONE_TAKER_BACKTEST.")


if __name__ == "__main__":
    main()
