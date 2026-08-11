"""Reconcile: my `net_turn_ann` vs vs_a7's `turn`. Reproduce vs_a7's exact definition."""
import sys
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting
PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
CUR = {"king": .595, "s2": .202, "funding": .202, "size": 0.0}
src.king = np.load("/tmp/vs_pred_king_SERVE.npz")["pred"].astype(np.float64)
src.s2 = np.load("/tmp/vs_pred_s2_SERVE.npz")["pred"].astype(np.float64)
ch = SignalChain(src, weights=CUR, funding_mode="rank", pos_cap_pct=99.0)
res = CrossLegNetting(ch, CUR, cost_bps=1.9).run(A, src.ts, year_of=yr)
# vs_a7's definition: RE-NORMALISE each anchor's net book to unit gross, then |w - prev|
bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
prev = np.zeros(src.N); tn = 0.0
for t in A:
    ti = int(t)
    if not np.isfinite(src.Y4[ti]).any():
        continue
    m, p = bk[ti]; w = np.zeros(src.N); w[m] = p
    tn += float(np.abs(w - prev).sum()); prev = w
print("vs_a7 definition (renormalised unit-gross book) :", round(tn / YEARS, 1), " [vs_a7 reported 2059.2]")
print("netting's own net_turn_ann (un-renormalised)    :", round(res["net_turn_ann"], 1))
print("netting's own gross_turn_ann (sum of legs)      :", round(res["gross_turn_ann"], 1))
