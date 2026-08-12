"""king cadence 4h -> 8h at the BOOK level, on fully certified single-caliber legs.

> created 2026-08-04 09:xx UTC | Session: B4-retrain | status: final
> follows the pre-gate (`b4_cadence_pregate.py`, f = 0.680 / 0.672 on two independent kings)

★ THE GOAL IS NOT "FIND THE BEST k". team-lead's redirect: the user said 效果不能牺牲, and
  `k=.595` sits only **4.1%** under the cost line (BE 3.639 vs 3.79). Dropping to k=0.2 clears the
  line but throws away 43.5% of the book's IC — an over-reaction to a 4.1% gap. So the question is
  **which combinations push the gap to <= 0 while keeping k HIGH**, and high-k rows are therefore
  the interesting ones here, not the low-k ones.

  Reported per cell: `gap_to_clear = (cost - BE) / cost`   (negative = already clears)
  Chosen over net@3.79 because net is a large number that moves ~1000 bps/yr per 1 bps of assumed
  cost, whereas the gap is a ratio and says directly how far there is left to go.

★ BOTH DL LEGS ARE CERTIFIED AND ON ONE CALIBER — the first time this is true for a cadence test.
  king = wideA_lamorth0_xattn_5yr_corrfund_v1, s2 = wideA_s2_y24_5yr_corrfund_v1, both funding
  `c6a1f9e9e5a0`, both scored through `TH.predict_scores_wide` behind a 5/5 bitwise fidelity gate,
  both densified via `d.CL = member` (the mask production actually uses, priced at 0.6% from live).

★ WHAT THIS CANNOT SHOW. Cadence is a NAIVE halving: skip every other king anchor, keep the same
  model. It does not retrain the king for an 8h horizon, and the pre-gate's f = 0.68 is exactly the
  price of that naivety. A king trained FOR 8h is a different (untested) proposition.
"""
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch  # noqa: E402

torch.backends.mkldnn.enabled = False
from engine.panel_source import PanelSource    # noqa: E402
from engine.signal_chain import SignalChain    # noqa: E402
from engine.netting import CrossLegNetting, LEG_CADENCE_H   # noqa: E402

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
KING = "/tmp/vs5_pred_s1f_SERVE.npz"
S2 = "/tmp/vs5_pred_s2c_SERVE.npz"
COST = 3.79
NAV, GROSS_USDT = 2201.0, 4390.0

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.king = np.load(KING)["pred"].astype(np.float64)
src.s2 = np.load(S2)["pred"].astype(np.float64)
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
YR = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
print("baseline cadence = %s | anchors=%d | years=%.2f" % (LEG_CADENCE_H, len(A), YEARS), flush=True)


class AsymCap(SignalChain):
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k)
        self.lo_pct, self.hi_pct = lo_pct, hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def run(kw, king_cad):
    r = (1.0 - kw) / 2.0
    W = {"king": kw, "s2": r, "funding": r, "size": 0.0}
    cad = dict(LEG_CADENCE_H)
    cad["king"] = king_cad
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lo_pct=1.0, hi_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=1.9, cadence=cad).run(A, src.ts, year_of=YR)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N)
    pnl = np.zeros(len(A))
    turn = np.zeros(len(A))
    ics = []
    for i, t in enumerate(A):
        ti = int(t)
        ret = src.Y4[ti]
        if not np.isfinite(ret).any() or ti not in bk:
            continue
        m, p = bk[ti]
        w = np.zeros(src.N)
        w[m] = p
        okm = np.isfinite(ret)
        pnl[i] = float(np.where(okm, w * np.nan_to_num(ret), 0.0).sum())
        turn[i] = float(np.abs(w - prev).sum())
        prev = w
        v = okm[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    G = pnl.sum() / YEARS * 1e4
    TN = turn.sum() / YEARS
    day = (src.ts[A] // (1000 * 3600 * 24)).astype(np.int64)
    dd = pd.DataFrame({"d": day, "p": pnl - turn * COST * 1e-4}).groupby("d")["p"].sum().values
    sh = float(np.mean(dd) / (np.std(dd) + 1e-12) * np.sqrt(365.0)) if len(dd) > 2 else np.nan
    be = G / TN if TN else np.nan
    net = G - TN * COST
    return dict(ic=float(np.nanmean(ics)), gross=G, turn=TN, be=be, net=net,
                gap=(COST - be) / COST, sh=sh, pct=net * 1e-4 * GROSS_USDT / NAV * 100)


print("\n%-6s %-7s %9s %8s %9s %10s %9s %8s %9s"
      % ("k", "kingCad", "IC", "BE", "turn/yr", "gap_clear", "net@3.79", "Sh", "%NAV"))
print("-" * 92)
R = {}
for kw in (0.2, 0.595, 0.8, 1.0):
    for cad in (4, 8):
        r = run(kw, cad)
        R[(kw, cad)] = r
        flag = "  <= CLEARS" if r["gap"] <= 0 else ""
        print("%-6.3f %-7d %+9.5f %8.3f %9.0f %9.1f%% %9.0f %8.2f %8.1f%%%s"
              % (kw, cad, r["ic"], r["be"], r["turn"], 100 * r["gap"], r["net"], r["sh"],
                 r["pct"], flag), flush=True)

print("\n=== WHAT CADENCE 8h BUYS, AT EACH k (same legs, same weights, one variable) ===")
for kw in (0.2, 0.595, 0.8, 1.0):
    a, b = R[(kw, 4)], R[(kw, 8)]
    print("  k=%.3f | turnover %.0f -> %.0f (%.2fx) | IC %+.5f -> %+.5f (%+.1f%%) | "
          "BE %.3f -> %.3f | gap %+.1f%% -> %+.1f%%"
          % (kw, a["turn"], b["turn"], b["turn"] / a["turn"], a["ic"], b["ic"],
             100 * (b["ic"] / a["ic"] - 1), a["be"], b["be"], 100 * a["gap"], 100 * b["gap"]))
print("\n★ the redirect's question is the LAST column at HIGH k: does anything clear the line")
print("  without paying the IC that dropping to k=0.2 costs?")
