"""SEQ 5 — the CLEAN book across king-weight x cap_hi. Does clean + low-k cross 3.79 bps?

> created 2026-08-04 05:xx UTC | Session: B4-retrain | handed over from C2 (budget exhausted)
> instrument: C2's /tmp/c2_seq5probe.py, reused verbatim except the two caliber lines and the gate
>             anchor. Spec: HANDOFF_seq5_joint_instrument_2026-08-04.md (SHA 298bb355…)

THE QUESTION. On the DIRTY book C2 measured d(BE)/d(k) = +1.17 (dominant) vs d(BE)/d(cap) = +0.11,
and the best of six cells reached BE 3.759 against a measured comparable cost of 3.79 — short by
0.8%. The clean book already starts at BE 3.638 with k=.595. So: does clean x low-k cross 3.79?

★ WHICH ARM, AND WHY SERVE. C3's post-batch has two: (a) causal panel BE 3.647, (b) SERVE panel
  BE 3.638. This uses (b), because the deployment batch CUT the panel-causal change (the caliber
  mismatch was measured at ~0), so live keeps the SERVE tail-13 construction. (b) is the book that
  will actually run. Feeding (a) and anchoring on (b), or vice versa, is the error this comment
  exists to prevent.

★★ THE GATE IS WELDED IN AND ITS ANCHOR IS RE-AIMED. C2's version asserted the baseline cell equals
  the LIVE (dirty) book — correct for its run, and it would now go red for an entirely CORRECT
  change of book. A gate that stops the right person is worse than no gate, because the next reader
  routes around it. So the gate is KEPT and re-anchored to C3's post-batch (b):

        IC 0.05725 | gross 5009 | turn 1377 | BE 3.638     (RESULT_fusion_doc_checks_A1A3 §3-septies)

  Fail => exit(1), emit nothing. This is the check C2's first table lacked: it built a NEW script
  and lost the caliber lines, producing the dirty book wearing the live book's label.

★ REPORT BE **AND** book rank-IC TOGETHER. Lowering k buys cost tolerance BY SPENDING IC — on the
  dirty book 0.0444 -> 0.0279 (−37%). Reporting BE alone would read a crossing as free.

★ FLOOR BY NOTIONAL, NOT BY COUNT (HANDOFF §2). Count both overstates today's risk (1/3 vs 1.9%)
  and can miss real deterioration: if a tighter cap flattens weights, what drops below the floor
  turns from dust into real positions while the COUNT barely moves. Both are printed; notional is
  the criterion.

★ TURNOVER DEFINITION. Three exist on disk differing by up to 45% (2059.2 re-normalised net book /
  1416.0 net_turn_ann / 1536.1 gross_turn_ann) — a definition difference, confirmed bitwise, not a
  bug. This reports the FIRST (re-normalised net book, the `vs_a7::book()` convention), which is
  C2's, so the two tables can sit side by side.
"""
import sys
import json

import numpy as np
import pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch  # noqa: E402

torch.backends.mkldnn.enabled = False          # C3 detour #1: else "could not create a primitive"
from engine.panel_source import PanelSource    # noqa: E402
from engine.signal_chain import SignalChain    # noqa: E402
from engine.netting import CrossLegNetting     # noqa: E402

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
KING_PRED = "/tmp/vs3_pred_s1x_SERVE.npz"      # CLEAN king (S1 xattn) on the SERVE panel
S2_PRED = "/tmp/vs_pred_s2_SERVE.npz"          # s2 stays DIRTY — the slow leg, unchanged

# C3 post-batch (b): clean king + dirty s2, SERVE panel. The gate's anchor.
ANCHOR = dict(ic=0.05725, gross=5009.0, turn=1377.0, be=3.638)

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
# ★★ THE CALIBER LINES. Without them PanelSource keeps its raw pred panels and every number below
#    is a different book wearing this one's label. C2's first table died exactly here.
src.king = np.load(KING_PRED)["pred"].astype(np.float64)
src.s2 = np.load(S2_PRED)["pred"].astype(np.float64)

A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
GROSS_USDT = 4285.0
MN = json.load(open("/tmp/mn_map.json"))
syms = [str(s) for s in src.symbols]
floor = np.array([float(MN.get(s, {}).get("min_notional", 5.0)) for s in syms])


class AsymCap(SignalChain):                    # C3's, verbatim (one class, not three)
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k)
        self.lo_pct = lo_pct
        self.hi_pct = hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def book(W, lo, hi):
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lo_pct=lo, hi_pct=hi)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N)
    g = tn = 0.0
    ics, nfl, nsh, nlong = [], [], [], []
    for t in A:
        ti = int(t)
        ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N)
        w[m] = p
        ok = np.isfinite(ret)
        g += float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        tn += float(np.abs(w - prev).sum())
        prev = w
        nlong.append(float((p > 0).sum()) / len(p))
        notional = np.abs(p) * GROSS_USDT
        below = notional < floor[m]
        nfl.append(int(below.sum()))
        nsh.append(float(notional[below].sum()) / max(float(notional.sum()), 1e-12))
        v = ok[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    G = g / YEARS * 1e4
    TN = tn / YEARS
    return dict(ic=float(np.nanmean(ics)), gross=G, turn=TN, be=G / TN,
                net19=G - TN * 1.9, net2504=G - TN * 2.504, net379=G - TN * 3.79,
                n_floor=float(np.mean(nfl)), notional_sh=float(np.mean(nsh)) * 100,
                longfrac=float(np.mean(nlong)))


def W_of(k):
    r = (1.0 - k) / 2.0
    return {"king": k, "s2": r, "funding": r, "size": 0.0}


R = {}
hdr = ("%-22s %9s %8s %8s %7s %9s %9s %9s | %8s %10s %7s" %
       ("book (CLEAN king)", "IC", "gross", "turn", "BE", "net@1.9", "net@2.5", "net@3.79",
        "n_floor", "notion_sh%", "long%"))
print(hdr)
print("-" * len(hdr))
for k in (0.2, 0.595, 1.0):
    for hi in (99.0, 85.0):
        nm = "k=%.3f cap_hi=%d" % (k, int(hi))
        r = book(W_of(k), 1.0, hi)
        R[nm] = r
        print("%-22s %+9.5f %8.0f %8.0f %7.3f %9.0f %9.0f %9.0f | %8.2f %10.3f %7.3f" %
              (nm, r["ic"], r["gross"], r["turn"], r["be"], r["net19"], r["net2504"],
               r["net379"], r["n_floor"], r["notional_sh"], r["longfrac"]), flush=True)

# ---- GATE, INSIDE the emitting instrument, anchored on C3 post-batch (b) ----
gb = R["k=0.595 cap_hi=99"]
gate = (abs(gb["ic"] - ANCHOR["ic"]) < 5e-5 and abs(gb["be"] - ANCHOR["be"]) < 5e-3
        and abs(gb["gross"] - ANCHOR["gross"]) < 5 and abs(gb["turn"] - ANCHOR["turn"]) < 5)
print("\n=== IN-INSTRUMENT GATE (baseline cell == C3 post-batch (b), clean king + SERVE panel) ===")
print("   IC %.5f (%.5f)  gross %.0f (%.0f)  turn %.0f (%.0f)  BE %.3f (%.3f)  -> %s"
      % (gb["ic"], ANCHOR["ic"], gb["gross"], ANCHOR["gross"], gb["turn"], ANCHOR["turn"],
         gb["be"], ANCHOR["be"], "PASS" if gate else "FAIL"))
if not gate:
    print("GATE FAILED -- emitting nothing, per the standing rule.")
    sys.exit(1)
json.dump(dict(anchor=ANCHOR, king_pred=KING_PRED, s2_pred=S2_PRED, panel=PANEL, cells=R),
          open("/mnt/storage/private/work_hsy/b4_causal_scratch/b4_seq5_cleanbook.json", "w"),
          indent=1, default=float)

print("\n=== THE QUESTION: does any clean cell cross the measured comparable cost 3.79 bps? ===")
best = max(R.items(), key=lambda kv: kv[1]["be"])
for nm, r in sorted(R.items(), key=lambda kv: -kv[1]["be"]):
    print("  %-22s BE %6.3f   net@3.79 %+8.0f   IC %+.5f   %s"
          % (nm, r["be"], r["net379"], r["ic"], "CROSSES" if r["be"] > 3.79 else "below"))
print("\n  best cell: %s  BE %.3f  vs cost 3.79  ->  %s"
      % (best[0], best[1]["be"], "CROSSES" if best[1]["be"] > 3.79 else
         "still below by %.2f%%" % (100 * (3.79 - best[1]["be"]) / 3.79)))
print("\n  ★ IC cost of the k lever (clean book): %+.5f -> %+.5f  (%.1f%%)"
      % (R["k=0.595 cap_hi=99"]["ic"], R["k=0.200 cap_hi=99"]["ic"],
         100 * (R["k=0.200 cap_hi=99"]["ic"] / R["k=0.595 cap_hi=99"]["ic"] - 1)))
print("\nsaved b4_seq5_cleanbook.json")
