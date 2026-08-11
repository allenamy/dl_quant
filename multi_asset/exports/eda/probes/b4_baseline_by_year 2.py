"""BASELINE_BY_YEAR for the new generation — computed BOTH ways, because the specified way is
in-sample and the guard's own provenance check cannot see that. (ledger #31)

★★★ THE PROBLEM, stated before any number.
  `BASELINE_BY_YEAR` is what `monitor.py` compares the live rolling IC against; it alarms when
  `rolling < DECAY_FRAC * baseline`. `_baseline_provenance` already guards two things:
     (a) is the baseline a real measurement traceable to the replay artifact?
     (b) is the baseline window DISJOINT IN TIME from the anchors it judges?
  **Neither can see in-sampleness.** A PRODUCTION FOLD trains on everything up to the panel end, so
  its predictions over 2022–2026 are IN-SAMPLE. A baseline built from them is a *fitted* level, it
  passes (a) — it is a genuine measurement — and passes (b) — the panel still ends 2026-06-30.
  It is simply too high. And an inflated baseline makes `DECAY_FRAC * baseline` too high, so the
  guard **fires on a healthy model**.

  ⇒ The production fold's own provenance says its warrant is "recipe certification (the 5
    walk-forward folds) + live shadow as its OOS". By that logic the baseline — a statement about
    what live should deliver — belongs to the 5-fold OOS predictions, not the production fold's
    in-sample ones.

  ⇒ This script computes BOTH and reports the gap. It does NOT choose; the choice changes a live
    alarm threshold and belongs to the ruler.

★ Caliber held fixed across the two arms: same book (k=.595, cap99, funding_mode=rank), same anchor
  grid, same SERVE ch31, same cost-free rank-IC definition (per-anchor cross-sectional rank-IC of
  the netted book positions vs Y4, averaged within calendar year) — only the PREDICTIONS differ.
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
ARMS = {
    "PRODFOLD (IN-SAMPLE — as #31 specifies)":
        ("/tmp/vs_pf_pf_king_SERVE.npz", "/tmp/vs_pf_pf_s2_SERVE.npz"),
    "5-fold walk-forward (OOS — same generation)":
        ("/tmp/vs5_pred_s1f_SERVE.npz", "/tmp/vs5_pred_s2c10_SERVE.npz"),
}
KW, CAP = 0.595, 99.0
CODED = {2022: 0.062, 2023: 0.086, 2024: 0.081, 2025: 0.076, 2026: 0.062}   # current, old generation

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")


class AsymCap(SignalChain):
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k)
        self.lo_pct, self.hi_pct = lo_pct, hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def per_year(kp, sp):
    src.king = np.load(kp)["pred"].astype(np.float64)
    src.s2 = np.load(sp)["pred"].astype(np.float64)
    A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                          & np.isfinite(src.s2)).any(1))[0])
    yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
    r = (1.0 - KW) / 2.0
    W = {"king": KW, "s2": r, "funding": r, "size": 0.0}
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lo_pct=1.0, hi_pct=CAP)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p) for (t, m, p) in res["net_positions"]}
    acc = {}
    for i, t in enumerate(A):
        ti = int(t)
        ret = src.Y4[ti]
        if ti not in bk or not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        v = np.isfinite(ret[m]) & np.isfinite(p)
        if v.sum() >= 5:
            acc.setdefault(int(yr[i]), []).append(
                np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    return {y: float(np.nanmean(v)) for y, v in sorted(acc.items())}, len(A)


out = {}
for nm, (kp, sp) in ARMS.items():
    out[nm], n = per_year(kp, sp)
    print("%-46s anchors=%d  %s" % (nm, n, {y: round(v, 4) for y, v in out[nm].items()}), flush=True)

print("\n%-8s %12s %12s %12s %10s" % ("year", "coded(old)", "PRODFOLD", "5-fold OOS", "PF/OOS"))
print("-" * 60)
A_ = out["PRODFOLD (IN-SAMPLE — as #31 specifies)"]
B_ = out["5-fold walk-forward (OOS — same generation)"]
for y in sorted(set(A_) | set(B_)):
    a, b = A_.get(y), B_.get(y)
    print("%-8d %12s %12s %12s %10s"
          % (y, CODED.get(y, "-"),
             "%.4f" % a if a is not None else "-",
             "%.4f" % b if b is not None else "-",
             "%.2fx" % (a / b) if a and b else "-"))
ratios = [A_[y] / B_[y] for y in set(A_) & set(B_) if B_[y]]
print("\n★ mean PRODFOLD/OOS ratio = %.2fx" % np.mean(ratios))
print("  ⇒ a baseline built from the PRODFOLD arm sits %.0f%% above the OOS one." % (100 * (np.mean(ratios) - 1)))
print("  ⇒ monitor alarms when rolling < DECAY_FRAC(0.5) x baseline, so an inflated baseline")
print("    raises the alarm line and makes the guard fire on a HEALTHY model.")
print("  ⇒ and `_baseline_provenance` CANNOT catch it: (a) it IS a real measurement, (b) the panel")
print("    still ends 2026-06-30 so the time-disjointness check still passes. NOT MY CALL — ruler's.")
