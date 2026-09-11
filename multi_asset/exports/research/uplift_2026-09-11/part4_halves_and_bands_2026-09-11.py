#!/usr/bin/env python3
"""READ-ONLY part 4: half-book alphas (beta-adjusted), rally-bucket beta decomposition,
current-anchor beta exposure, and the neutrality-band calibration test."""
import json, os, time, calendar, collections
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
exec(open(f"{OUT}/beta_neutrality_2026-09-11.py").read().split('print(f"== ALIGN')[0])
def T(*x): return calendar.timegm(x + (0,) * (6 - len(x)))
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X)); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b; s2 = r @ r / max(len(y) - X.shape[1], 1)
    return b, np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
def tt(x):
    x = np.asarray(x, float); return x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))

grid = sorted(set(int(t) for t in PTS if int(t) % H == 0))
ALT = {}; BRD = {}
for g in grid:
    pr = panel_ret(g)
    if pr is None: continue
    ALT[g] = float(np.nanmean(pr[ALT_COLS])); BRD[g] = float(np.nanmean(pr[ALT_COLS] > 0))
rr = {r["a"]: r for r in rows}
CE = [a for a in sorted(rr) if a >= T(2026, 8, 26, 4) and a in ALT]
PRE = [a for a in sorted(rr) if a < T(2026, 8, 26, 4) and a in ALT]
ALLA = [a for a in sorted(rr) if a in ALT]

print("== [8] half-book ALPHA (half return minus its own realised beta x altEW), bps per unit half gross")
print("%-22s %4s %10s %8s %10s %8s %10s %10s %10s %8s" % ("period", "n", "Lraw", "t", "Sraw", "t", "bL", "bS", "Lalpha(t)", "Salpha(t)"))
for lab, S in [("whole live", ALLA), ("pre-combo", PRE), ("combo era", CE),
               ("combo 08-26..09-09 04Z", [a for a in CE if a <= T(2026, 9, 9, 4)]),
               ("combo 09-09 08Z..", [a for a in CE if a > T(2026, 9, 9, 4)])]:
    if len(S) < 6: continue
    yl = np.array([rr[a]["lbps"] for a in S]); ys = np.array([rr[a]["sbps"] for a in S]); x = np.array([ALT[a] for a in S]) * 1e4
    bl, sel = ols(yl, [x]); bs, ses = ols(ys, [x])
    al = yl - bl[1] * x; as_ = ys - bs[1] * x
    ml, tl = tt(yl); ms, ts_ = tt(ys); mal, tal = tt(al); mas, tas = tt(as_)
    print("%-22s %4d %+10.2f %+8.2f %+10.2f %+8.2f %+10.3f %+10.3f %+6.2f(%+.2f) %+6.2f(%+.2f)" % (lab, len(S), ml, tl, ms, ts_, bl[1], bs[1], mal, tal, mas, tas))

print("\n== [9] broad-rally bucket decomposed into beta part and residual (book bps/anchor)")
print("%-22s %5s %11s %11s %11s %11s" % ("period/bucket", "n", "book", "beta part", "residual", "resid t"))
for lab, S in [("whole live", ALLA), ("pre-combo", PRE), ("combo era", CE)]:
    x = np.array([ALT[a] for a in S]) * 1e4; y = np.array([rr[a]["bps"] for a in S])
    b, se = ols(y, [x])                                  # period beta
    for bl_, sel_ in [("  ALL", S), ("  BROAD RALLY", [a for a in S if ALT[a] > 0.005 and BRD[a] > 0.65]),
                      ("  BROAD SELLOFF", [a for a in S if ALT[a] < -0.005 and BRD[a] < 0.35]),
                      ("  quiet", [a for a in S if abs(ALT[a]) <= 0.005])]:
        if len(sel_) < 3: continue
        xs = np.array([ALT[a] for a in sel_]) * 1e4; ys = np.array([rr[a]["bps"] for a in sel_])
        res = ys - b[1] * xs
        print("%-22s %5d %+11.2f %+11.2f %+11.2f %+11.2f" % (lab + bl_, len(sel_), ys.mean(), (b[1] * xs).mean(), res.mean(), res.mean() / (res.std(ddof=1) / np.sqrt(len(res)))))
    print("   period beta b_alt=%+.4f (t %+.2f)" % (b[1], b[1] / se[1]))

print("\n== [10] NEUTRALITY BAND: what the live code actually constrains")
print("   scheduler/anchor_loop.py:20  NEUTRALITY_ALARM_FRAC = 0.03   (alarm only; comment says 'a POLICY NUMBER ... no measurement produced it')")
print("   live/chase_policy.py:149     NEUTRAL_BAND = 0.015           (target for `neutral_only` chase fills, = half the alarm band)")
print("   anchor_loop.py:1695-1700     the neutral NO-TRADE band is SKIPPED for the external book -> combo is not passed through it")
print("   Both quantities are the signed sum of position NOTIONALS. Neither references beta, sector, funding-bucket or any factor.")
ng = np.array([rr[a]["ng"] for a in ALLA])
print("\n   live |net/gross| distribution (venue readback, n=%d): mean %+.3f%% sd %.3f%% p90 %.3f%% max %.3f%%" % (
    len(ng), ng.mean() * 100, ng.std() * 100, np.percentile(np.abs(ng), 90) * 100, np.abs(ng).max() * 100))
for thr in (0.01, 0.015, 0.03, 0.05):
    print("     |dollar net|>%.1f%%: %5.1f%% of anchors (%d)" % (thr * 100, np.mean(np.abs(ng) > thr) * 100, int(np.sum(np.abs(ng) > thr))))
# variance contribution: how much of book return variance does dollar-net explain vs beta-net?
J = json.load(open(f"{OUT}/beta_part2_rows.json"))
J = {int(r["a"]): r for r in J if r.get("dbeta_g") is not None}
S = [a for a in ALLA if a in J]
x = np.array([ALT[a] for a in S]) * 1e4
dn = np.array([rr[a]["ng"] for a in S]); db = np.array([J[a]["dbeta_g"] for a in S]); y = np.array([rr[a]["bps"] for a in S])
print("\n   per-anchor P&L attributable to each exposure (bps/anchor, mean over n=%d):" % len(S))
print("     dollar-net x altEW   : %+7.3f   (this is what the band controls)" % np.mean(dn * x))
print("     beta-net   x altEW   : %+7.3f   (this is what nothing controls)" % np.mean(db * x))
print("     book actual          : %+7.3f" % y.mean())
print("     sd of (beta-net x altEW) %.3f bps vs sd of (dollar-net x altEW) %.3f bps -> beta channel is %.1fx the dollar channel" % (
    (db * x).std(), (dn * x).std(), (db * x).std() / (dn * x).std()))
CEJ = [a for a in CE if a in J]
xc = np.array([ALT[a] for a in CEJ]) * 1e4; dnc = np.array([rr[a]["ng"] for a in CEJ]); dbc = np.array([J[a]["dbeta_g"] for a in CEJ])
print("   combo era only (n=%d): dollar-net x alt %+.3f ; beta-net x alt %+.3f ; sd ratio %.2fx" % (
    len(CEJ), np.mean(dnc * xc), np.mean(dbc * xc), (dbc * xc).std() / (dnc * xc).std()))
print("   combo era |beta-net| p50 %.2f%% p90 %.2f%% max %.2f%% ; |dollar-net| p50 %.2f%% p90 %.2f%% max %.2f%%" % (
    np.percentile(np.abs(dbc), 50) * 100, np.percentile(np.abs(dbc), 90) * 100, np.abs(dbc).max() * 100,
    np.percentile(np.abs(dnc), 50) * 100, np.percentile(np.abs(dnc), 90) * 100, np.abs(dnc).max() * 100))
print("DONE_PART4")
