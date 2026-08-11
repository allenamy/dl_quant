import sys, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS
EDA = "multi_asset/exports/eda/"; WPF = "multi_asset/exports/wide_panel_full.npz"

grid, syms, CLOSE, FUND = build_panel()
print("funding panel: grid", grid.shape, "syms", list(syms))
print("  grid span", pd.to_datetime(grid[0], unit="ms", utc=True).date(), "->", pd.to_datetime(grid[-1], unit="ms", utc=True).date(), "step-mode(ms)", int(np.median(np.diff(grid))))

z = np.load(WPF, allow_pickle=True)
print("\nwide_panel_full keys:", list(z.files))
wsyms = z["symbols"] if "symbols" in z.files else None
print("wide symbols n=", None if wsyms is None else len(wsyms), "first10", None if wsyms is None else list(wsyms[:10]))
print("wide ts", z["ts"].shape, "span", pd.to_datetime(z["ts"][0], unit="ms", utc=True).date(), "->", pd.to_datetime(z["ts"][-1], unit="ms", utc=True).date())

kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
print("\nking_pred_panel keys:", list(kp.files), "has symbols:", "symbols" in kp.files)

# BTC index in funding syms
bl = [s for s in syms]
print("\nBTC in funding syms idx:", [i for i, s in enumerate(bl) if "BTC" in str(s)])
