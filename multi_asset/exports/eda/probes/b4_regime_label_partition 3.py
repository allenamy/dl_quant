"""Recompute the backtest's regime mix under LIVE's OWN thresholds, not a sample median.

live/regime_classifier.py (pre-registered, reusing makerfill_deepdive gates, NOT re-tuned):
    calm   < 7 bps/min   |   normal 7-18   |   stress >= 18
    input  = PanelSource.btc_rvol_bps_min()  -- causal trailing 24h

My earlier regime-priced number used a TWO-way split at the sample MEDIAN (5.3714). That is a
different partition from live's THREE-way fixed-threshold one, so the 1.05 bps "mixture correction"
derived from it was comparing two things that are not the same label.
"""
import sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch
torch.backends.mkldnn.enabled = False
from engine.panel_source import PanelSource

src = PanelSource(panel=MA + "/exports/wide_dl_full_fundfix.npz",
                  king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
A = np.sort(np.where((src.member & src.CL4).any(1))[0])
rv = np.array([src.btc_rvol_bps_min(int(t), window_h=24) for t in A], float)
ok = np.isfinite(rv)
print("anchors=%d finite rvol=%d   median=%.4f" % (len(A), ok.sum(), np.nanmedian(rv)))
CALM_MAX, STRESS_MIN = 7.0, 18.0
calm = rv < CALM_MAX
stress = rv >= STRESS_MIN
normal = ok & ~calm & ~stress
print("\n=== LIVE's three-way partition applied to the backtest ===")
for nm, m in (("calm  (<7)", calm & ok), ("normal(7-18)", normal), ("stress(>=18)", stress & ok)):
    print("  %-14s %6d anchors  %5.1f%%" % (nm, m.sum(), 100 * m.sum() / ok.sum()))
print("\n=== my earlier TWO-way median split (what the 1.05 bps used) ===")
med = float(np.nanmedian(rv))
print("  calm (<=%.4f)  %6d  %5.1f%%" % (med, (rv <= med).sum(), 100 * (rv <= med).mean()))
print("  running        %6d  %5.1f%%" % ((rv > med).sum(), 100 * (rv > med).mean()))
print("\n⇒ live calls %.1f%% of these anchors CALM; my median split called 50.0%%." %
      (100 * (calm & ok).sum() / ok.sum()))
print("⇒ the two labels are NOT the same partition, so any mixture correction that pairs")
print("  live's 0.84/4.48 with my median split is comparing two different labels.")
