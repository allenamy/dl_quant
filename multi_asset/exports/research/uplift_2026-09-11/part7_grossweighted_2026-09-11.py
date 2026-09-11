#!/usr/bin/env python3
"""READ-ONLY part 7: everything restated GROSS-WEIGHTED (sum USDT / sum gross x 1e4), the caliber the
lead uses ('bps of gross per anchor'), so beta/factor attribution is comparable to the headline gap."""
import json, os, glob, time, calendar
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
exec(open(f"{OUT}/beta_neutrality_2026-09-11.py").read().split('print(f"== ALIGN')[0])
def T(*x): return calendar.timegm(x + (0,) * (6 - len(x)))
LQV = z["data"][:, :, 3].astype(np.float32)
def liqv(upto, days=7):
    i1 = TPOS.get(upto)
    if i1 is None: return None
    with np.errstate(all="ignore"): return np.nanmean(LQV[max(0, i1 - days * 288):i1 + 1], axis=0)
grid = sorted(set(int(t) for t in PTS if int(t) % H == 0))
RET = {}
for g in grid:
    pr = panel_ret(g)
    if pr is not None: RET[g] = pr
gk = sorted(RET)
FAC = {}
for g in gk:
    pr = RET[g]; lq = liqv(g)
    if lq is None: continue
    ok = np.isfinite(pr) & np.isfinite(lq); cols = np.array([c for c in ALT_COLS if ok[c]])
    if len(cols) < 100: continue
    lv = lq[cols]; q1, q2 = np.percentile(lv, [33.3, 66.7])
    FAC[g] = dict(mkt=float(np.mean(pr[cols])), liq=float(np.mean(pr[cols[lv <= q1]]) - np.mean(pr[cols[lv >= q2]])),
                  brd=float(np.mean(pr[cols] > 0)))
def nbetas(upto, lookback=180):
    ks = [t for t in gk if t < upto][-lookback:]
    if len(ks) < 40: return None
    M = np.array([RET[t] for t in ks]); alt = np.nanmean(M[:, ALT_COLS], axis=1)
    B = np.full(M.shape[1], np.nan)
    for j in range(M.shape[1]):
        c = M[:, j]; ok = np.isfinite(c)
        if ok.sum() < 30: continue
        cc = c[ok] - c[ok].mean(); aa = alt[ok] - alt[ok].mean(); d = float(aa @ aa)
        if d > 0: B[j] = float(cc @ aa) / d
    return B
BC = {}
rr = {r["a"]: r for r in rows}
for r in rows:
    d = int(r["a"]) // 86400 * 86400
    if d not in BC: BC[d] = nbetas(d)
    B = BC[d]
    if B is None or r["a"] not in FAC: continue
    r["dbeta_g"] = sum(n * B[IDX[s]] for s, n in pos[r["a"]].items() if s in IDX and np.isfinite(B[IDX[s]])) / r["gross"]
A = [r for r in rows if r.get("dbeta_g") is not None]
print("== [17] GROSS-WEIGHTED attribution (sum USDT / sum gross x 1e4 = bps of gross per anchor)")
print("%-24s %4s %10s %11s %11s %11s %11s" % ("period", "n", "grossSum", "book", "beta part", "residual", "beta share"))
for lab, lo, hi in [("whole live", 0, 9e9), ("pre-combo", 0, T(2026, 8, 26, 4)), ("combo era", T(2026, 8, 26, 4), 9e9),
                    ("post-deposit 09-03 16Z", T(2026, 9, 3, 16), 9e9), ("last 7d 09-04..09-10", T(2026, 9, 4, 0), 9e9)]:
    S = [r for r in A if lo <= r["a"] < hi]
    if len(S) < 6: continue
    G = sum(r["gross"] for r in S)
    pl = sum(r["pl"] for r in S)
    bp = sum(r["dbeta_g"] * FAC[r["a"]]["mkt"] * r["gross"] for r in S)
    print("{:<24s} {:4d} {:10,.0f} {:+11.3f} {:+11.3f} {:+11.3f} {:10.0f}%".format(lab, len(S), G, pl / G * 1e4, bp / G * 1e4, (pl - bp) / G * 1e4, 100 * bp / pl if pl else 0))
print("\n== [18] GROSS-WEIGHTED by regime bucket (combo era and whole live)")
print("%-38s %4s %11s %11s %11s %11s" % ("bucket", "n", "book bps/a", "beta part", "residual", "USDT"))
def show(lab, S):
    if len(S) < 3: return
    G = sum(r["gross"] for r in S); pl = sum(r["pl"] for r in S)
    bp = sum(r["dbeta_g"] * FAC[r["a"]]["mkt"] * r["gross"] for r in S)
    print("{:<38s} {:4d} {:+11.3f} {:+11.3f} {:+11.3f} {:+11,.0f}".format(lab, len(S), pl / G * 1e4, bp / G * 1e4, (pl - bp) / G * 1e4, pl))
for tag, lo in [("whole ", 0), ("combo ", T(2026, 8, 26, 4))]:
    S = [r for r in A if r["a"] >= lo]
    show(tag + "ALL", S)
    show(tag + "BROAD RALLY (alt>+50bp,brd>65%)", [r for r in S if FAC[r["a"]]["mkt"] > 0.005 and FAC[r["a"]]["brd"] > 0.65])
    show(tag + "BROAD SELLOFF (alt<-50bp,brd<35%)", [r for r in S if FAC[r["a"]]["mkt"] < -0.005 and FAC[r["a"]]["brd"] < 0.35])
    show(tag + "quiet (|alt|<=50bp)", [r for r in S if abs(FAC[r["a"]]["mkt"]) <= 0.005])
    # post-crash reversal
    def cum6(t):
        ks = [x for x in gk if x < t][-6:]
        return float(np.sum([FAC[x]["mkt"] for x in ks if x in FAC])) if len(ks) == 6 else None
    show(tag + "POST-CRASH REVERSAL (24h<=-2%,alt>0)", [r for r in S if (cum6(r["a"]) is not None and cum6(r["a"]) <= -0.02 and FAC[r["a"]]["mkt"] > 0)])
    print()
print("== [19] 09-06 in the same caliber")
S = [r for r in A if T(2026, 9, 6, 0) <= r["a"] <= T(2026, 9, 6, 20)]
G = sum(r["gross"] for r in S); pl = sum(r["pl"] for r in S)
bp = sum(r["dbeta_g"] * FAC[r["a"]]["mkt"] * r["gross"] for r in S)
print("   3 anchors, gross sum {:,.0f}: price P&L {:+,.0f} ({:+.1f} bps of gross per anchor); beta part {:+,.0f} ({:+.1f} bps); residual {:+,.0f}".format(G, pl, pl / G * 1e4, bp, bp / G * 1e4, pl - bp))
print("DONE_PART7")
