"""king cadence 4h -> 8h: the one cheap measurement that decides whether the lever exists at all.

> created 2026-08-04 08:xx UTC | Session: B4-retrain | status: final
> ledger #10. Prior-art check done first (below); this is the pre-gate, not the experiment.

★ PRIOR-ART CHECK (protocol section 7: "has this been rejected before, and on WHICH panel?").
  `prereg_turnover_cost_frontier.md` section 1 enumerates the three families it covers:
      1. band family (no-trade band x per-name cost threshold x position inertia)  -- tested
      2. neutral-priority top-up policy                                            -- NOT testable (no fill model)
      3. per-name cost downweighting                                               -- tested, as a band sub-axis
  **Cadence is none of them.** Grepping both the prereg and the result doc for
  cadence/frequency/4h/8h/rebalance-interval returns ZERO hits. It was not rejected; it was never
  considered. And the three families all act at ONE layer -- `shaped -> net` inside
  `CrossLegNetting.run()`, i.e. how to modify a target vector. **Cadence acts a layer up: how often a
  target vector is computed at all.** That is why the frontier's conclusions cannot speak to it.
  (Panel caliber: the study is 2026-07-26, before the ch31 lookahead was found and before the funding
  fix, so it is dirty-caliber throughout -- an independent reason its rejections carry a "?".)

★★ THE MECHANISM THAT KILLED THE BAND AXIS IS THE ARGUMENT FOR CADENCE.
   The frontier's finding: "band up to 0.5x mean|w| cuts turnover only 9.6% -- **this book's turnover
   is NOT made of small adjustments; nothing for a band to suppress.**"
   ⇒ the turnover is made of LARGE position changes
   ⇒ a band suppresses small ones            -> dead, as measured
   ⇒ cadence removes whole rebalances        -> acts on exactly the large ones that constitute it
   The very result that killed one lever is the mechanistic case for the other.

★★★ BUT THE HONEST COUNTER-ARGUMENT, WHICH IS WHAT THIS SCRIPT MEASURES.
   The king's target horizon IS 4h and its cadence IS 4h -- they match by construction. Moving to 8h
   means the second 4h block is traded on a signal whose forecast period has **already elapsed**.
   Whether that is survivable is not a matter of opinion: it is
        IC( pred(t) , return over [t+4h, t+8h] )   vs   IC( pred(t) , return over [t, t+4h] )
   If the stale half retains a fraction f, then 8h cadence buys ~-50% turnover for ~(1+f)/2 of the
   per-anchor alpha. f is the whole lever. Everything else about cadence is downstream of it.

   Pre-registered reading, written before the run:
       f >= 0.7  -> lever is real, worth a full experiment (alpha cost ~15% for ~45% turnover cut)
       0.4-0.7   -> marginal; only interesting if the gap to clear is small (it is: 4.1%)
       f <  0.4  -> lever is dead as a naive halving; would need a signal built FOR 8h instead
   ★ f < 0 would mean the stale signal is actively wrong, which would kill it outright.
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

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
ARMS = {
    "king S1F-xattn (certified, corrfund)": "/tmp/vs5_pred_s1f_SERVE.npz",
    "king causal_v1 (certified)":           "/tmp/vs5_pred_s1x_SERVE.npz",
}

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")


def xsec_ic(pred_row, ret_row, member_row):
    v = member_row & np.isfinite(pred_row) & np.isfinite(ret_row)
    if v.sum() < 5:
        return np.nan
    return np.corrcoef(rankdata(pred_row[v]), rankdata(ret_row[v]))[0, 1]


for name, path in ARMS.items():
    P = np.load(path)["pred"].astype(np.float64)
    A = np.sort(np.where((src.member & src.CL4 & np.isfinite(P)).any(1))[0])
    dt_h = np.diff(src.ts[A]) / (1000 * 3600.0)
    step = float(np.median(dt_h))
    fresh, stale = [], []
    for i in range(len(A) - 1):
        t, tn = int(A[i]), int(A[i + 1])
        if abs((src.ts[tn] - src.ts[t]) / (1000 * 3600.0) - step) > 0.5:
            continue                                   # skip gaps: not a clean consecutive pair
        fresh.append(xsec_ic(P[t], src.Y4[t], src.member[t]))       # pred(t) vs its own window
        stale.append(xsec_ic(P[t], src.Y4[tn], src.member[tn]))     # pred(t) held one more anchor
    fresh, stale = np.array(fresh, float), np.array(stale, float)
    ok = np.isfinite(fresh) & np.isfinite(stale)
    f_m, s_m = np.nanmean(fresh[ok]), np.nanmean(stale[ok])
    n = int(ok.sum())
    se_s = np.nanstd(stale[ok]) / np.sqrt(n)
    frac = s_m / f_m if f_m else np.nan
    print("\n=== %s ===" % name)
    print("  anchor spacing (median) = %.1f h   usable consecutive pairs = %d" % (step, n))
    print("  fresh  IC( pred(t), ret[t, t+%.0fh] )      = %+.5f" % (step, f_m))
    print("  stale  IC( pred(t), ret[t+%.0fh, t+%.0fh] ) = %+.5f  (SE %.5f)"
          % (step, 2 * step, s_m, se_s))
    print("  ★ retention f = stale/fresh = %.3f" % frac)
    blended = (1 + frac) / 2
    print("  ⇒ an %.0fh cadence would deliver ~%.0f%% of per-anchor alpha for ~50%% of king turnover"
          % (2 * step, 100 * blended))
    verdict = ("REAL — worth a full experiment" if frac >= 0.7 else
               "MARGINAL — only interesting because the gap to clear is 4.1%" if frac >= 0.4 else
               "DEAD as a naive halving" if frac >= 0 else
               "ACTIVELY WRONG — stale signal has the wrong sign")
    print("  ⇒ pre-registered verdict: %s" % verdict)
