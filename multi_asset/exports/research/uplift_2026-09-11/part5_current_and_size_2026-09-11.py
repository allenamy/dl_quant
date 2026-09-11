#!/usr/bin/env python3
"""READ-ONLY part 5: current-anchor exposures (incl. 09-11 04Z), size tilt test (is long half large-cap?),
and 09-06 anchor-by-anchor detail."""
import json, os, time, calendar, collections
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
exec(open(f"{OUT}/beta_neutrality_2026-09-11.py").read().split('print(f"== ALIGN')[0])
def T(*x): return calendar.timegm(x + (0,) * (6 - len(x)))
LQV = z["data"][:, :, 3].astype(np.float32)     # log1p(quote volume) per 5m bar = size/liquidity proxy
grid = sorted(set(int(t) for t in PTS if int(t) % H == 0))
ALT = {}
for g in grid:
    pr = panel_ret(g)
    if pr is not None: ALT[g] = float(np.nanmean(pr[ALT_COLS]))
gk = sorted(ALT)
def name_betas(upto, lookback=180):
    ks = [t for t in gk if t < upto][-lookback:]
    if len(ks) < 40: return None
    M = np.array([panel_ret(t) for t in ks]); alt = np.nanmean(M[:, ALT_COLS], axis=1)
    B = np.full(M.shape[1], np.nan)
    for j in range(M.shape[1]):
        c = M[:, j]; ok = np.isfinite(c)
        if ok.sum() < 30: continue
        cc = c[ok] - c[ok].mean(); aa = alt[ok] - alt[ok].mean(); d = float(aa @ aa)
        if d > 0: B[j] = float(cc @ aa) / d
    return B
def size_score(upto, days=7):
    i1 = TPOS.get(upto) or (len(PTS) - 1)
    i0 = max(0, i1 - days * 288)
    return np.nanmean(LQV[i0:i1 + 1], axis=0)          # mean log quote-volume, 7d

print("== [11] CURRENT exposures, last 6 anchors with venue readback")
B = name_betas(T(2026, 9, 11, 0)); SZ = size_score(T(2026, 9, 11, 4))
last = sorted(a for a in pos if a >= T(2026, 9, 9, 8))
for a in last:
    p = pos[a]; g = sum(abs(v) for v in p.values()); net = sum(p.values())
    db = sum(n * B[IDX[s]] for s, n in p.items() if s in IDX and np.isfinite(B[IDX[s]]))
    wl = sum(n for n in p.values() if n > 0); ws = -sum(n for n in p.values() if n < 0)
    bl = sum(n * B[IDX[s]] for s, n in p.items() if n > 0 and s in IDX and np.isfinite(B[IDX[s]])) / wl
    bs = -sum(n * B[IDX[s]] for s, n in p.items() if n < 0 and s in IDX and np.isfinite(B[IDX[s]])) / ws
    szl = sum(n * SZ[IDX[s]] for s, n in p.items() if n > 0 and s in IDX and np.isfinite(SZ[IDX[s]])) / wl
    szs = -sum(n * SZ[IDX[s]] for s, n in p.items() if n < 0 and s in IDX and np.isfinite(SZ[IDX[s]])) / ws
    print("  {} n={:3d} gross {:9,.0f}  dollar-net/gross {:+7.3f}%  BETA-net/gross {:+7.3f}%  betaL {:.3f} betaS {:.3f}  meanLogQV L {:.2f} S {:.2f} (L-S {:+.2f})".format(
        utc(a), len(p), g, net / g * 100, db / g * 100, bl, bs, szl, szs, szl - szs))

print("\n== [12] SIZE TILT: is the long half large-cap and the short half small-cap alt?  (7d mean log1p(5m quote volume))")
hist = []
for a in sorted(pos):
    if a < T(2026, 8, 2, 8): continue
    SZa = size_score(a); Ba = None
    p = pos[a]; wl = sum(n for n in p.values() if n > 0); ws = -sum(n for n in p.values() if n < 0)
    if wl <= 0 or ws <= 0: continue
    szl = sum(n * SZa[IDX[s]] for s, n in p.items() if n > 0 and s in IDX and np.isfinite(SZa[IDX[s]])) / wl
    szs = -sum(n * SZa[IDX[s]] for s, n in p.items() if n < 0 and s in IDX and np.isfinite(SZa[IDX[s]])) / ws
    hist.append((a, szl, szs))
for lab, lo, hi in [("whole live", 0, 9e9), ("pre-combo", 0, T(2026, 8, 26, 4)), ("combo era", T(2026, 8, 26, 4), 9e9), ("post-deposit", T(2026, 9, 3, 16), 9e9)]:
    hs = [h for h in hist if lo <= h[0] < hi]
    if not hs: continue
    d = np.array([h[1] - h[2] for h in hs])
    print("  %-14s n=%3d  logQV long %.3f  short %.3f  diff %+.4f (t %+.2f)  -> long half is %s" % (
        lab, len(hs), np.mean([h[1] for h in hs]), np.mean([h[2] for h in hs]), d.mean(), d.mean() / (d.std(ddof=1) / np.sqrt(len(d))),
        "LARGER-cap" if d.mean() > 0 else "SMALLER-cap"))
print("  (panel-wide reference: mean logQV over live universe = %.3f, sd %.3f)" % (np.nanmean(size_score(T(2026, 9, 11, 4))[LIVE_COLS]), np.nanstd(size_score(T(2026, 9, 11, 4))[LIVE_COLS])))

print("\n== [13] 09-06 anchor by anchor")
for a in sorted(x for x in pos if T(2026, 9, 6, 0) <= x <= T(2026, 9, 6, 20)):
    r = next((q for q in rows if q["a"] == a), None)
    g = sum(abs(v) for v in pos[a].values())
    if r is None:
        print("  {} gross {:9,.0f}  (no forward mid pair -> excluded from price P&L)".format(utc(a), g)); continue
    per = sorted(r["per"], key=lambda t: t[3])
    print("  {} gross {:9,.0f} n={:3d}  P&L {:+8,.0f} ({:+7.1f} bps) L {:+8,.0f} S {:+8,.0f} | altEW {:+6.1f} bps brd {:.2f} | worst: {}".format(
        utc(a), g, r["n"], r["pl"], r["bps"], r["lp"], r["sp"], ALT.get(a, float('nan')) * 1e4, r["breadth"],
        " ".join("{}({},{:+.1f}%,{:+,.0f})".format(s.replace("USDT", ""), "L" if n > 0 else "S", ret * 100, u) for s, n, ret, u in per[:5])))
    nn = [u for s, n, ret, u in r["per"]]
    print("       names losing: %d/%d (%.0f%%) ; top-10 = %.0f%% of gross losses ; long names losing %d/%d, short names losing %d/%d" % (
        sum(1 for u in nn if u < 0), len(nn), 100 * np.mean(np.array(nn) < 0),
        100 * sum(sorted(nn)[:10]) / sum(u for u in nn if u < 0),
        sum(1 for s, n, ret, u in r["per"] if n > 0 and u < 0), sum(1 for s, n, ret, u in r["per"] if n > 0),
        sum(1 for s, n, ret, u in r["per"] if n < 0 and u < 0), sum(1 for s, n, ret, u in r["per"] if n < 0)))
# dispersion comparison: 09-06 vs typical
print("\n  cross-sectional dispersion of live-universe 4h returns (sd of altEW constituents):")
for lab, a in [("09-06 00Z", T(2026, 9, 6, 0)), ("09-06 04Z", T(2026, 9, 6, 4)), ("08-21 avg", None), ("08-24 avg", None)]:
    pass
sds = {}
for a in gk:
    pr = panel_ret(a); sds[a] = float(np.nanstd(pr[ALT_COLS]))
allsd = np.array([sds[a] for a in gk])
for lab, a in [("09-06 00Z", T(2026, 9, 6, 0)), ("09-06 04Z", T(2026, 9, 6, 4)), ("09-06 08Z", T(2026, 9, 6, 8)), ("08-21 12Z", T(2026, 8, 21, 12)), ("08-24 12Z", T(2026, 8, 24, 12))]:
    if a in sds: print("    %s xsec sd %.4f = %.0fth pct of all %d anchors" % (lab, sds[a], 100 * np.mean(allsd < sds[a]), len(allsd)))
print("    median xsec sd %.4f" % np.median(allsd))
print("DONE_PART5")
