#!/usr/bin/env python3
"""READ-ONLY part 6: two-factor attribution. MKT = altEW (449 EW alt names). LIQ = EW return of the
bottom-liquidity tercile minus the top-liquidity tercile of the live universe (liquidity = 7d mean
log1p 5m quote-volume, measured strictly BEFORE the anchor). Regress the live book on both."""
import json, os, time, calendar, collections
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
exec(open(f"{OUT}/beta_neutrality_2026-09-11.py").read().split('print(f"== ALIGN')[0])
def T(*x): return calendar.timegm(x + (0,) * (6 - len(x)))
def ols(y, X, names):
    Xm = np.column_stack([np.ones(len(y))] + list(X)); b, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    r = y - Xm @ b; s2 = r @ r / max(len(y) - Xm.shape[1], 1)
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(Xm.T @ Xm)))
    r2 = 1 - r @ r / ((y - y.mean()) @ (y - y.mean()))
    return b, se, r2
LQV = z["data"][:, :, 3].astype(np.float32)
def liq(upto, days=7):
    i1 = TPOS.get(upto)
    if i1 is None: return None
    i0 = max(0, i1 - days * 288)
    with np.errstate(all="ignore"):
        return np.nanmean(LQV[i0:i1 + 1], axis=0)
grid = sorted(set(int(t) for t in PTS if int(t) % H == 0))
FAC = {}
for g in grid:
    pr = panel_ret(g); lq = liq(g)
    if pr is None or lq is None: continue
    ok = np.isfinite(pr) & np.isfinite(lq)
    cols = np.array([c for c in ALT_COLS if ok[c]])
    if len(cols) < 100: continue
    lv = lq[cols]; q1, q2 = np.percentile(lv, [33.3, 66.7])
    lo = cols[lv <= q1]; hi = cols[lv >= q2]
    FAC[g] = dict(mkt=float(np.mean(pr[cols])), liq=float(np.mean(pr[lo]) - np.mean(pr[hi])),
                  nlo=len(lo), nhi=len(hi), brd=float(np.mean(pr[cols] > 0)))
rr = {r["a"]: r for r in rows}
A = [a for a in sorted(rr) if a in FAC]
print("== [14] factor definitions: n anchors=%d ; mean n_low-liq=%d n_high-liq=%d" % (len(A), np.mean([FAC[a]['nlo'] for a in A]), np.mean([FAC[a]['nhi'] for a in A])))
mk = np.array([FAC[a]["mkt"] for a in A]) * 1e4; lq_ = np.array([FAC[a]["liq"] for a in A]) * 1e4
print("   MKT mean %+.2f bps/anchor sd %.1f ; LIQ mean %+.2f bps/anchor sd %.1f ; corr(MKT,LIQ) %+.3f" % (mk.mean(), mk.std(), lq_.mean(), lq_.std(), np.corrcoef(mk, lq_)[0, 1]))
PER = [("whole live", 0, 9e9), ("pre-combo", 0, T(2026, 8, 26, 4)), ("combo era", T(2026, 8, 26, 4), 9e9), ("post-deposit", T(2026, 9, 3, 16), 9e9)]
print("\n%-14s %4s %9s %8s %9s %8s %10s %7s %11s %11s" % ("period", "n", "b_MKT", "t", "b_LIQ", "t", "alpha", "R2", "MKT bps/a", "LIQ bps/a"))
ATTR = {}
for lab, lo, hi in PER:
    S = [a for a in A if lo <= a < hi]
    if len(S) < 12: continue
    y = np.array([rr[a]["bps"] for a in S]); x1 = np.array([FAC[a]["mkt"] for a in S]) * 1e4; x2 = np.array([FAC[a]["liq"] for a in S]) * 1e4
    b, se, r2 = ols(y, [x1, x2], ["mkt", "liq"])
    ATTR[lab] = dict(n=len(S), b_mkt=b[1], b_liq=b[2], t_liq=b[2] / se[2], t_mkt=b[1] / se[1], alpha=b[0], r2=r2,
                     mkt_c=b[1] * x1.mean(), liq_c=b[2] * x2.mean(), book=y.mean(),
                     se_alpha=se[0], mkt_bps=x1.mean(), liq_bps=x2.mean())
    print("%-14s %4d %+9.4f %+8.2f %+9.4f %+8.2f %+10.3f %7.3f %+11.2f %+11.2f" % (lab, len(S), b[1], b[1] / se[1], b[2], b[2] / se[2], b[0], r2, x1.mean(), x2.mean()))
print("\n   attribution of the book's mean return (bps/anchor) = alpha + b_MKT*E[MKT] + b_LIQ*E[LIQ]:")
print("%-14s %11s %11s %11s %11s" % ("period", "book", "MKT part", "LIQ part", "alpha"))
for lab in ATTR:
    d = ATTR[lab]
    print("%-14s %+11.3f %+11.3f %+11.3f %+11.3f  (alpha se %.3f)" % (lab, d["book"], d["mkt_c"], d["liq_c"], d["alpha"], d["se_alpha"]))

print("\n== [15] the book's LIQ loading vs its own position tilt (sanity: does the regression loading match the holdings?)")
for lab, lo, hi in PER:
    S = [a for a in A if lo <= a < hi]
    if len(S) < 12: continue
    dif = []
    for a in S:
        lq2 = liq(a); p = pos[a]
        wl = sum(n for n in p.values() if n > 0); ws = -sum(n for n in p.values() if n < 0)
        if wl <= 0 or ws <= 0: continue
        l = sum(n * lq2[IDX[s]] for s, n in p.items() if n > 0 and s in IDX and np.isfinite(lq2[IDX[s]])) / wl
        sh = -sum(n * lq2[IDX[s]] for s, n in p.items() if n < 0 and s in IDX and np.isfinite(lq2[IDX[s]])) / ws
        dif.append(l - sh)
    dif = np.array(dif)
    print("   %-14s logQV(long)-logQV(short) mean %+.3f ; anchors with long LESS liquid: %.0f%% ; regression b_LIQ %+.4f" % (
        lab, dif.mean(), 100 * np.mean(dif < 0), ATTR[lab]["b_liq"]))

print("\n== [16] conditional book return in broad rallies, controlling for MKT and LIQ (combo era + whole)")
for lab, lo, hi in [("whole live", 0, 9e9), ("combo era", T(2026, 8, 26, 4), 9e9)]:
    S = [a for a in A if lo <= a < hi]
    y = np.array([rr[a]["bps"] for a in S]); x1 = np.array([FAC[a]["mkt"] for a in S]) * 1e4; x2 = np.array([FAC[a]["liq"] for a in S]) * 1e4
    b, se, r2 = ols(y, [x1, x2], ["m", "l"])
    res = y - (b[0] + b[1] * x1 + b[2] * x2)
    br = np.array([FAC[a]["mkt"] > 0.005 and FAC[a]["brd"] > 0.65 for a in S])
    print("   %-11s BROAD RALLY n=%d: raw %+.2f bps ; after MKT+LIQ %+.2f bps (t %+.2f) | non-rally raw %+.2f, after %+.2f" % (
        lab, br.sum(), y[br].mean(), res[br].mean(), res[br].mean() / (res[br].std(ddof=1) / np.sqrt(br.sum())), y[~br].mean(), res[~br].mean()))
json.dump(ATTR, open(f"{OUT}/factor_attribution.json", "w"), indent=1, default=float)
print("DONE_PART6")
