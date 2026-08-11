"""SEQ 5 — REPRODUCTION GATE. Must reproduce the live book's known baseline with MY OWN
assembly+scoring before any joint-lever number is produced. Fail => report and stop, emit nothing.

Targets (live, known): book rank-IC = 0.04437 , BE = 2.504
"""
import sys
import numpy as np, pandas as pd
from scipy.stats import rankdata
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch
torch.backends.mkldnn.enabled = False          # C3 detour #1
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.king = np.load("/tmp/vs_pred_king_SERVE.npz")["pred"].astype(np.float64)
src.s2 = np.load("/tmp/vs_pred_s2_SERVE.npz")["pred"].astype(np.float64)

A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
W = {"king": .595, "s2": .202, "funding": .202, "size": 0.0}

# --- my own assembly + scoring loop (not vs_a7's function) ---
ch = SignalChain(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
book = {int(t): (m, p) for (t, m, p) in res["net_positions"]}

prev = np.zeros(src.N)
gross_bps = 0.0
turn = 0.0
ics = []
n_scored = 0
for t in A:
    ti = int(t)
    ret = src.Y4[ti]
    if not np.isfinite(ret).any():
        continue
    m, p_raw = book[ti]
    g = float(np.abs(p_raw).sum())
    p = p_raw / g if g > 1e-12 else p_raw          # unit-gross normalisation
    w = np.zeros(src.N); w[m] = p
    fin = np.isfinite(ret)
    gross_bps += float(np.where(fin, w * np.nan_to_num(ret), 0.0).sum())
    turn += float(np.abs(w - prev).sum()); prev = w
    v = fin[m] & np.isfinite(p)
    if v.sum() >= 5:
        ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
        n_scored += 1

IC = float(np.nanmean(ics))
G = gross_bps / YEARS * 1e4
T = turn / YEARS
BE = G / T

print("=== SEQ 5 REPRODUCTION GATE (my own assembly + scoring) ===")
print(f"  anchors used         {len(A)}   scored {n_scored}   years {YEARS:.3f}")
print(f"  book rank-IC         {IC:.6f}     target 0.04437   d={IC-0.04437218703993101:+.2e}")
print(f"  gross bps/yr         {G:.2f}")
print(f"  turnover/yr          {T:.2f}")
print(f"  BE bps               {BE:.6f}     target 2.504     d={BE-2.504332885658508:+.2e}")
ic_ok = abs(IC - 0.04437218703993101) < 1e-6
be_ok = abs(BE - 2.504332885658508) < 1e-6
print()
print(f"  IC reproduced: {'PASS' if ic_ok else 'FAIL'}")
print(f"  BE reproduced: {'PASS' if be_ok else 'FAIL'}")
print()
print("GATE:", "PASS — joint-lever work may proceed" if (ic_ok and be_ok)
      else "FAIL — STOP, emit no joint-lever numbers")
