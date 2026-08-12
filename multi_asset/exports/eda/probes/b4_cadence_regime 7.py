"""Is the cadence retention f=0.68 an average that hides a stress-regime collapse?

Conditioned on LIVE's OWN regime labels (live/regime_classifier.py, pre-registered, NOT re-tuned):
    calm < 7 bps/min | normal 7-18 | stress >= 18   (causal trailing-24h BTC rvol)
Using the sample median here would repeat the partition error that voided the 1.05 bps correction.
"""
import sys
import numpy as np, pandas as pd
from scipy.stats import rankdata
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch; torch.backends.mkldnn.enabled = False
from engine.panel_source import PanelSource

src = PanelSource(panel=MA + "/exports/wide_dl_full_fundfix.npz",
                  king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
P = np.load("/tmp/vs5_pred_s1f_SERVE.npz")["pred"].astype(np.float64)
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(P)).any(1))[0])


def ic(p, r, m):
    v = m & np.isfinite(p) & np.isfinite(r)
    return np.corrcoef(rankdata(p[v]), rankdata(r[v]))[0, 1] if v.sum() >= 5 else np.nan


rows = []
for i in range(len(A) - 1):
    t, tn = int(A[i]), int(A[i + 1])
    if abs((src.ts[tn] - src.ts[t]) / 3.6e6 - 4.0) > 0.5:
        continue
    rv = src.btc_rvol_bps_min(t, window_h=24)
    lab = "unknown" if not np.isfinite(rv) else ("calm" if rv < 7 else "stress" if rv >= 18 else "normal")
    rows.append((lab, ic(P[t], src.Y4[t], src.member[t]), ic(P[t], src.Y4[tn], src.member[tn])))
df = pd.DataFrame(rows, columns=["regime", "fresh", "stale"]).dropna()
print("%-8s %7s %10s %10s %8s %10s" % ("regime", "n", "fresh IC", "stale IC", "f", "SE(stale)"))
print("-" * 60)
for lab in ("calm", "normal", "stress"):
    d = df[df.regime == lab]
    if len(d) < 20:
        print("%-8s %7d  (too few)" % (lab, len(d))); continue
    fm, sm = d.fresh.mean(), d.stale.mean()
    print("%-8s %7d %10.5f %10.5f %8.3f %10.5f"
          % (lab, len(d), fm, sm, sm / fm if fm else np.nan, d.stale.std() / np.sqrt(len(d))))
fm, sm = df.fresh.mean(), df.stale.mean()
print("%-8s %7d %10.5f %10.5f %8.3f" % ("ALL", len(df), fm, sm, sm / fm))
