import sys
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch; torch.backends.mkldnn.enabled = False
from engine.panel_source import PanelSource
src = PanelSource(panel=MA + "/exports/wide_dl_full_fundfix.npz",
                  king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
t0 = pd.to_datetime(int(src.ts[0]), unit="ms", utc=True)
print("panel row 0 = %s  (UTC hour %d)" % (t0.isoformat(), t0.hour))
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
h = pd.to_datetime(src.ts[A], unit="ms", utc=True).hour.to_numpy()
print("anchor UTC hours present:", sorted(set(h.tolist())))
for cad in (4, 8):
    fire = (A % cad == 0)
    hrs = sorted(set(h[fire].tolist()))
    print("cad=%2d -> fires on %5d / %5d anchors (%.1f%%), at UTC hours %s"
          % (cad, fire.sum(), len(A), 100 * fire.mean(), hrs))
