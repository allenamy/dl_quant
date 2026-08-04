"""The first book in which EVERY DL leg is certified and both are on ONE funding caliber.

> created 2026-08-04 09:xx UTC | Session: B4-retrain | status: final
> not a deployment proposal — a measurement of a configuration that has never been read.

★ WHAT IS NEW HERE. Every book measured to date mixes at least one of:
    - a king and an s2 on different funding calibers (dbaae69795db vs c6a1f9e9e5a0), or
    - prediction arrays from the hand-rolled forward loop that does not reproduce the frozen scores.
  This one has neither: both legs are `wideA_*_corrfund_v1` (funding `c6a1f9e9e5a0`, verified by
  `panel_ref`), and both prediction arrays came from `TH.predict_scores_wide` behind a 5/5 bitwise
  fidelity gate.

★★ THE PRICE OF THAT IS ANCHOR COUNT, AND IT IS NOT A FREE COMPARISON. s2 natively scores ~1636
   anchors; the densified recipe extends it to ~9821 by handing a daily model an hourly mask it
   never trained under. A sparser anchor set mechanically means fewer rebalances, hence LOWER
   turnover and HIGHER BE — so the certified book's BE is **not** comparable like-for-like against
   the 9821-anchor numbers, and the difference must not be read as an improvement. Both arms are
   run here precisely so the densification's price is measured rather than argued.

★ THE FUNDING LEG comes from the assembly panel (`wide_dl_full_fundfix`) in both arms and is
  unchanged; only the two DL legs move. The funding leg's own caliber question is separate and is
  NOT addressed here.
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
from engine.netting import CrossLegNetting     # noqa: E402

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
KING = "/tmp/vs5_pred_s1f_SERVE.npz"                       # S1F-xattn, corrfund, CERTIFIED
ARMS = {
    "CERTIFIED s2 (native grid)":   "/tmp/vs5_pred_s2c_SERVE.npz",
    "DENSIFIED s2 (uncertified)":   "/tmp/vs4_pred_s2c_SERVE.npz",
}
COSTS = (1.9, 2.504, 3.79)

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.king = np.load(KING)["pred"].astype(np.float64)


class AsymCap(SignalChain):
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k)
        self.lo_pct, self.hi_pct = lo_pct, hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def run(kw):
    A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                          & np.isfinite(src.s2)).any(1))[0])
    if len(A) < 50:
        return None
    yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
    years = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
    r = (1.0 - kw) / 2.0
    W = {"king": kw, "s2": r, "funding": r, "size": 0.0}
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lo_pct=1.0, hi_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N)
    pnl = np.zeros(len(A))
    turn = np.zeros(len(A))
    ics = []
    for i, t in enumerate(A):
        ti = int(t)
        ret = src.Y4[ti]
        if not np.isfinite(ret).any():
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
    G = pnl.sum() / years * 1e4
    TN = turn.sum() / years
    day = (src.ts[A] // (1000 * 3600 * 24)).astype(np.int64)

    def dsh(c):
        dd = pd.DataFrame({"d": day, "p": pnl - turn * c * 1e-4}).groupby("d")["p"].sum().values
        return float(np.mean(dd) / (np.std(dd) + 1e-12) * np.sqrt(365.0)) if len(dd) > 2 else np.nan

    return dict(ic=float(np.nanmean(ics)), gross=G, turn=TN, be=G / TN, n=len(A),
                net={c: G - TN * c for c in COSTS}, sh={c: dsh(c) for c in COSTS})


print("%-30s %-6s %7s %9s %8s %9s %8s %8s"
      % ("arm", "k", "anchors", "IC", "BE", "net@3.79", "turn/yr", "Sh@3.79"))
print("-" * 96)
R = {}
for name, path in ARMS.items():
    src.s2 = np.load(path)["pred"].astype(np.float64)
    for kw in (0.595, 0.2):
        r = run(kw)
        if r is None:
            print("%-30s %-6.3f  too few anchors" % (name, kw))
            continue
        R[(name, kw)] = r
        print("%-30s %-6.3f %7d %+9.5f %8.3f %9.0f %8.0f %8.2f"
              % (name, kw, r["n"], r["ic"], r["be"], r["net"][3.79], r["turn"], r["sh"][3.79]),
              flush=True)

print("\n=== WHAT DENSIFICATION BUYS / COSTS (same king, same weights) ===")
for kw in (0.595, 0.2):
    a = R.get(("CERTIFIED s2 (native grid)", kw))
    b = R.get(("DENSIFIED s2 (uncertified)", kw))
    if not (a and b):
        continue
    print("  k=%.3f | anchors %d -> %d (%.1fx) | turnover %.0f -> %.0f (%.2fx) | "
          "BE %.3f -> %.3f | IC %+.5f -> %+.5f"
          % (kw, a["n"], b["n"], b["n"] / a["n"], a["turn"], b["turn"], b["turn"] / a["turn"],
             a["be"], b["be"], a["ic"], b["ic"]))
print("\n  ★ BE moves mostly through TURNOVER here, not through alpha — a sparser anchor set")
print("    rebalances less. Do NOT read the certified arm's BE as an improvement; read the IC.")
