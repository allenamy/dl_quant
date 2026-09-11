#!/usr/bin/env python3
"""READ-ONLY part 2: per-period ex-ante beta, beta-neutral counterfactual, day attribution, regime conditioning.
Reuses the loaders of beta_neutrality_2026-09-11.py (same instrument, same +6-bar alignment)."""
import json, glob, os, time, collections, sys, calendar
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
src = open(f"{OUT}/beta_neutrality_2026-09-11.py").read()
head = src.split('print(f"== ALIGN')[0]
exec(head)                                     # gives: rows, pos, mid, anch, IDX, ALT_COLS, panel_ret, allret-free
def T(*x): return calendar.timegm(x + (0,) * (6 - len(x)))
def utcd(t): return time.strftime("%Y-%m-%d", time.gmtime(int(t)))
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X)); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b; dof = max(len(y) - X.shape[1], 1); s2 = resid @ resid / dof
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
    return b, se

# ---- panel 4h grid + per-name trailing betas (causal: strictly prior to the day start) ----
grid = sorted(set(int(t) for t in PTS if int(t) % H == 0))
allret = {}
for g in grid:
    pr = panel_ret(g)
    if pr is not None: allret[g] = pr
gk = sorted(allret)
def name_betas(upto, lookback=180, minobs=30):
    ks = [t for t in gk if t < upto][-lookback:]
    if len(ks) < 40: return None
    M = np.array([allret[t] for t in ks]); alt = np.nanmean(M[:, ALT_COLS], axis=1)
    B = np.full(M.shape[1], np.nan)
    for j in range(M.shape[1]):
        col = M[:, j]; ok = np.isfinite(col)
        if ok.sum() < minobs: continue
        c = col[ok] - col[ok].mean(); aa = alt[ok] - alt[ok].mean(); d = float(aa @ aa)
        if d > 0: B[j] = float(c @ aa) / d
    return B
BC = {}
for r in rows:
    day = int(r["a"]) // 86400 * 86400
    if day not in BC: BC[day] = name_betas(day)
    B = BC[day]
    if B is None: r["dbeta_g"] = None; continue
    db = bl = bs = 0.0; wl = ws = 0.0
    for s, n in pos[r["a"]].items():
        j = IDX.get(s)
        if j is None or not np.isfinite(B[j]): continue
        db += n * B[j]
        if n > 0: bl += n * B[j]; wl += n
        else: bs += n * B[j]; ws += -n
    r["dbeta_g"] = db / r["gross"]; r["betaL"] = bl / wl if wl else np.nan; r["betaS"] = -bs / ws if ws else np.nan
R = [r for r in rows if r.get("dbeta_g") is not None]
PER = [("whole (beta-est) 08-09..09-10", R[0]["a"], R[-1]["a"]),
       ("pre-combo ..08-26 00Z", R[0]["a"], T(2026, 8, 26, 0)),
       ("combo era 08-26 04Z..", T(2026, 8, 26, 4), R[-1]["a"]),
       ("post-deposit 09-03 16Z..", T(2026, 9, 3, 16), R[-1]["a"])]
print("== [4b] ex-ante beta per period (beta to altEW; dollar-net for contrast)")
print("%-30s %4s %9s %9s %9s %9s %9s %9s %9s" % ("period", "n", "betaNet%g", "sd", "betaL", "betaS", "dollarNet%", "altEWbps", "betaPnL"))
for lab, lo, hi in PER:
    rs = [r for r in R if lo <= r["a"] <= hi]
    if len(rs) < 5: continue
    db = np.array([r["dbeta_g"] for r in rs]); al = np.array([r["alt"] for r in rs]) * 1e4
    print("%-30s %4d %+9.3f %9.3f %9.3f %9.3f %+10.3f %+9.2f %+9.3f" % (lab, len(rs), db.mean() * 100, db.std() * 100,
          np.nanmean([r["betaL"] for r in rs]), np.nanmean([r["betaS"] for r in rs]), np.mean([r["ng"] for r in rs]) * 100, al.mean(), np.mean(db * al)))
print("\n== [4c] beta-neutral counterfactual (subtract ex-ante beta x altEW from each anchor's book return)")
print("%-30s %4s %11s %11s %11s %11s" % ("period", "n", "book bps/a", "betaPnL", "residual", "resid t"))
for lab, lo, hi in PER:
    rs = [r for r in R if lo <= r["a"] <= hi]
    if len(rs) < 5: continue
    y = np.array([r["bps"] for r in rs]); db = np.array([r["dbeta_g"] for r in rs]); al = np.array([r["alt"] for r in rs]) * 1e4
    res = y - db * al
    print("%-30s %4d %+11.3f %+11.3f %+11.3f %+11.2f" % (lab, len(rs), y.mean(), np.mean(db * al), res.mean(), res.mean() / (res.std(ddof=1) / np.sqrt(len(res)))))
    if lab.startswith("whole"):
        print("      book t-stat {:+.2f} ; USDT: book {:+,.0f}, betaPnL {:+,.0f}, residual {:+,.0f}".format(*(
            y.mean() / (y.std(ddof=1) / np.sqrt(len(y))), np.sum(y * np.array([r["gross"] for r in rs]) / 1e4),
            np.sum(db * al * np.array([r["gross"] for r in rs]) / 1e4), np.sum(res * np.array([r["gross"] for r in rs]) / 1e4))))

# ---- day attribution ----
print("\n== [5] worst-day name-level attribution (price P&L, positions x mid->mid, same UTC day)")
BADDAYS = ["2026-09-06", "2026-08-21", "2026-08-24", "2026-09-04", "2026-09-05", "2026-09-10"]
for dstr in BADDAYS:
    d0 = calendar.timegm(time.strptime(dstr, "%Y-%m-%d")); rs = [r for r in rows if d0 <= r["a"] < d0 + 86400]
    if not rs: print(f"  {dstr}: no anchors"); continue
    nm = collections.defaultdict(float); side = collections.defaultdict(float); tot = 0.0
    for r in rs:
        for s, n, ret, u in r["per"]:
            nm[s] += u; side["L" if n > 0 else "S"] += u; tot += u
    srt = sorted(nm.items(), key=lambda x: x[1]); neg = sum(v for v in nm.values() if v < 0)
    gross = np.mean([r["gross"] for r in rs])
    alt = sum(r["alt"] for r in rs) * 1e4; btc = sum(r["btc"] for r in rs) * 1e4
    print(f"\n  {dstr}  anchors={len(rs)} gross~{gross:,.0f}  priceP&L {tot:+,.0f} ({tot/gross*1e4:+.1f} bps of gross)  L {side['L']:+,.0f} / S {side['S']:+,.0f}  | altEW day {alt:+.0f} bps, BTC {btc:+.0f} bps, breadth {np.mean([r['breadth'] for r in rs]):.2f}")
    print(f"    top-5 losers = {sum(v for _,v in srt[:5]):+,.0f} ({sum(v for _,v in srt[:5])/neg*100:.0f}% of gross losses); top-15 = {sum(v for _,v in srt[:15]):+,.0f} ({sum(v for _,v in srt[:15])/neg*100:.0f}%)")
    det = []
    for s, v in srt[:10]:
        sd = "L" if sum(n for r in rs for ss, n, _, _ in r["per"] if ss == s) > 0 else "S"
        rr = np.prod([1 + ret for r in rs for ss, n, ret, u in r["per"] if ss == s]) - 1
        det.append(f"{s.replace('USDT','')}({sd},{rr*100:+.1f}%,{v:+,.0f})")
    print("    worst10: " + " ".join(det))
    dbe = [r["dbeta_g"] for r in rs if r.get("dbeta_g") is not None]
    if dbe: print(f"    ex-ante betaNet/gross {np.mean(dbe)*100:+.2f}% -> beta P&L {np.sum([r['dbeta_g']*r['alt']*r['gross'] for r in rs if r.get('dbeta_g') is not None]):+,.0f} USDT of the {tot:+,.0f}")
json.dump([{k: v for k, v in r.items() if k != "per"} for r in R], open(f"{OUT}/beta_part2_rows.json", "w"), indent=0, default=float)
print("DONE_PART2")
