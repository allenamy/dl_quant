#!/usr/bin/env python3
"""READ-ONLY part 3: regime conditioning (broad rally / post-crash reversal), daily P&L reconciliation,
current-anchor beta exposure. Same instruments and alignment as part 1/2."""
import json, glob, os, time, collections, calendar
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
exec(open(f"{OUT}/beta_neutrality_2026-09-11.py").read().split('print(f"== ALIGN')[0])
def T(*x): return calendar.timegm(x + (0,) * (6 - len(x)))
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X)); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b; s2 = r @ r / max(len(y) - X.shape[1], 1)
    return b, np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
def mci(x):
    x = np.asarray(x, float); m = x.mean(); s = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan
    return m, s, m - 1.96 * s, m + 1.96 * s

# ---- panel history for index (regime definitions use the panel, not the book) ----
grid = sorted(set(int(t) for t in PTS if int(t) % H == 0))
ALT = {}; BTCR = {}; BRD = {}
for g in grid:
    pr = panel_ret(g)
    if pr is None: continue
    ALT[g] = float(np.nanmean(pr[ALT_COLS])); BRD[g] = float(np.nanmean(pr[ALT_COLS] > 0)); BTCR[g] = float(pr[BTC])
gk = sorted(ALT)
def cum(t, k):   # trailing k anchors of altEW ending at t (exclusive of the anchor's own fwd window)
    ks = [x for x in gk if x < t][-k:]
    return float(np.sum([ALT[x] for x in ks])) if len(ks) == k else None

rr = {r["a"]: r for r in rows}
A = [a for a in rr if a in ALT]
print(f"== [6] regime conditioning, live anchors n={len(A)} ({utc(min(A))}..{utc(max(A))}); regimes defined on altEW (449 alt names, EW)")
qs = np.percentile([ALT[a] for a in A], [20, 40, 60, 80])
print(f"   altEW quintile cuts (bps/4h): {[round(q*1e4,1) for q in qs]}")
print("%-34s %5s %11s %11s %11s %11s %11s" % ("bucket", "n", "book bps/a", "95%CI lo", "95%CI hi", "altEW bps", "breadth"))
def show(lab, sel):
    if len(sel) < 3: print("%-34s %5d  (too few)" % (lab, len(sel))); return None
    y = np.array([rr[a]["bps"] for a in sel]); m, s, lo, hi = mci(y)
    print("%-34s %5d %+11.3f %+11.3f %+11.3f %+11.2f %11.2f" % (lab, len(sel), m, lo, hi, np.mean([ALT[a] for a in sel]) * 1e4, np.mean([BRD[a] for a in sel])))
    return y
for i, (lo_, hi_) in enumerate(zip([-9e9] + list(qs), list(qs) + [9e9])):
    show(f"altEW quintile Q{i+1}", [a for a in A if lo_ <= ALT[a] < hi_])
print()
BR = [a for a in A if ALT[a] > 0.005 and BRD[a] > 0.65]                       # broad rally: >+50bps AND >65% up
NB = [a for a in A if ALT[a] > 0.005 and BRD[a] <= 0.65]
SEL = [a for a in A if ALT[a] < -0.005 and BRD[a] < 0.35]                     # broad selloff
yBR = show("BROAD RALLY (alt>+50bp, brd>65%)", BR)
show("narrow rally (alt>+50bp, brd<=65%)", NB)
show("BROAD SELLOFF (alt<-50bp, brd<35%)", SEL)
show("quiet (|alt|<=50bp)", [a for a in A if abs(ALT[a]) <= 0.005])
print()
# post-crash reversal: trailing 6 anchors (24h) alt <= -2%, current anchor alt > 0
PCR = [a for a in A if (cum(a, 6) is not None and cum(a, 6) <= -0.02 and ALT[a] > 0)]
PCR2 = [a for a in A if (cum(a, 6) is not None and cum(a, 6) <= -0.02)]
PCD = [a for a in A if (cum(a, 6) is not None and cum(a, 6) <= -0.02 and ALT[a] <= 0)]
show("POST-CRASH 24h<=-2% (all)", PCR2)
show("POST-CRASH REVERSAL (then alt>0)", PCR)
show("POST-CRASH continuation (alt<=0)", PCD)
show("after 24h rally >=+2%", [a for a in A if (cum(a, 6) is not None and cum(a, 6) >= 0.02)])
print()
print("   share-of-loss accounting (price P&L USDT, whole live window):")
tot = sum(rr[a]["pl"] for a in A)
for lab, sel in [("broad rally", BR), ("narrow rally", NB), ("broad selloff", SEL), ("quiet", [a for a in A if abs(ALT[a]) <= 0.005]),
                 ("post-crash reversal", PCR), ("post-crash 24h<=-2% all", PCR2)]:
    s = sum(rr[a]["pl"] for a in sel); g = sum(rr[a]["gross"] for a in sel)
    print("     {:<26s} n={:3d}  P&L {:+9,.0f} USDT  ({:+.2f} bps/anchor of its own gross)".format(lab, len(sel), s, s / g * 1e4 if g else 0))
print("     {:<26s} n={:3d}  P&L {:+9,.0f} USDT".format("ALL", len(A), tot))
# combo era only
CE = [a for a in A if a >= T(2026, 8, 26, 4)]
print("\n   combo era only (n=%d):" % len(CE))
print("%-34s %5s %11s %11s %11s %11s %11s" % ("bucket", "n", "book bps/a", "95%CI lo", "95%CI hi", "altEW bps", "breadth"))
show("  BROAD RALLY", [a for a in CE if a in BR]); show("  BROAD SELLOFF", [a for a in CE if a in SEL])
show("  POST-CRASH REVERSAL", [a for a in CE if a in PCR]); show("  quiet", [a for a in CE if abs(ALT[a]) <= 0.005])

# ---- daily reconciliation and long/short shares ----
print("\n== [7] daily: price P&L by half, vs ledger ΔNAV (flow-adjusted)")
nav = {}
for p in sorted(glob.glob(f"{LIVE}/pilot_log/2026*/daily_nav.jsonl")):
    rs = jl(p)
    if rs: nav[os.path.basename(os.path.dirname(p))] = rs[-1]
days = sorted(set(time.strftime("%Y%m%d", time.gmtime(r["a"])) for r in rows))
prev = None; tab = []
print("%-10s %4s %10s %10s %10s %9s %9s %9s %9s" % ("day", "n", "price P&L", "long", "short", "fund", "comm", "dNAV-flow", "altEW bps"))
for d in days:
    rs = [r for r in rows if time.strftime("%Y%m%d", time.gmtime(r["a"])) == d]
    nv = nav.get(d)
    dn = None
    if nv and prev is not None:
        dn = float(nv["nav"]) - prev - float(nv.get("external_flow_usdt") or 0.0)
    bt = (nv or {}).get("realised_by_type") or {}
    alt = sum(ALT.get(r["a"], 0.0) for r in rs) * 1e4
    print("{:<10s} {:4d} {:+10,.0f} {:+10,.0f} {:+10,.0f} {:+9,.0f} {:+9,.0f} {:>9s} {:+9.0f}".format(d, len(rs), sum(r["pl"] for r in rs), sum(r["lp"] for r in rs), sum(r["sp"] for r in rs),
          float(bt.get("FUNDING_FEE") or 0), float(bt.get("COMMISSION") or 0), ("{:+,.0f}".format(dn)) if dn is not None else "-", alt))
    if nv: prev = float(nv["nav"])
    tab.append(dict(day=d, pl=sum(r["pl"] for r in rs), lp=sum(r["lp"] for r in rs), sp=sum(r["sp"] for r in rs), dnav=dn, alt=alt))
L = sum(r["lp"] for r in rows); S = sum(r["sp"] for r in rows)
CEr = [r for r in rows if r["a"] >= T(2026, 8, 26, 4)]
print("\n   whole live: long {:+,.0f}  short {:+,.0f}   short share of net loss: {}".format(L, S, "n/a" if L + S >= 0 else "{:.0f}%".format(S / (L + S) * 100)))
print("   combo era : long {:+,.0f}  short {:+,.0f}   short share of net loss: {:.0f}%".format(sum(r["lp"] for r in CEr), sum(r["sp"] for r in CEr), sum(r["sp"] for r in CEr) / sum(r["pl"] for r in CEr) * 100))
neg = sum(min(r["lp"], 0) + min(r["sp"], 0) for r in CEr)
print("   combo era gross-loss share (sum of negative half-anchors): long {:.0f}% short {:.0f}%".format(
    sum(min(r["lp"], 0) for r in CEr) / neg * 100, sum(min(r["sp"], 0) for r in CEr) / neg * 100))
json.dump(tab, open(f"{OUT}/daily_pl_rows.json", "w"), indent=0, default=float)
print("DONE_PART3")
