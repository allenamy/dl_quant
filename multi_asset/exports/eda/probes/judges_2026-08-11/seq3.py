"""SEQ 3 — per-leg turnover decomposition. Does the book's -32% follow from king alone?

Re-implements the netting accumulation loop using only PUBLIC chain API (leg_positions), so no
shared code is modified. Splits `gross_turn` per leg instead of summing it, which is the only
thing CrossLegNetting does not already expose.
"""
import sys, json
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting, LEG_CADENCE_H

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
CUR = {"king": .595, "s2": .202, "funding": .202, "size": 0.0}
ck = np.load("/tmp/vs_a1_cleanking.npz")


def per_leg(W=CUR):
    """Per-leg weighted turnover (the same quantity CrossLegNetting sums into gross_turn),
    plus the netted book turnover for cross-check against vs_a7."""
    ch = SignalChain(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
    net = CrossLegNetting(ch, W, cost_bps=1.9)
    res = net.run(A, src.ts, year_of=yr)
    held = {k: np.zeros(src.N) for k in W}
    legturn = {k: 0.0 for k in W}
    for i, t in enumerate(A):
        ti = int(t)
        legpos, m = ch.leg_positions(ti)
        for k in W:
            if i == 0 or (ti % LEG_CADENCE_H[k] == 0):
                new = np.zeros(src.N); new[m] = legpos[k]
                legturn[k] += W[k] * float(np.abs(new - held[k]).sum())
                held[k] = new
    out = {k: legturn[k] / YEARS for k in W}
    out["_gross_sum"] = sum(out[k] for k in W)
    out["_gross_from_netting"] = res["gross_turn_ann"]
    out["_net_book"] = res["net_turn_ann"]
    return out


ARMS = [
    ("BASE  dirty king SERVE + dirty s2 SERVE", "/tmp/vs_pred_king_SERVE.npz", "/tmp/vs_pred_s2_SERVE.npz"),
    ("(b)   clean king SERVE + s2 SERVE  [KING ONLY]", "/tmp/vs3_pred_s1x_SERVE.npz", "/tmp/vs_pred_s2_SERVE.npz"),
    ("(c)   dirty king SERVE + s2 CAUSAL [S2 ONLY]", "/tmp/vs_pred_king_SERVE.npz", "/tmp/vs_pred_s2_CAUSAL.npz"),
    ("(a)   clean king CAUSAL + s2 CAUSAL [BOTH]", "CLEAN", "/tmp/vs_pred_s2_CAUSAL.npz"),
]
R = {}
hdr = "%-46s %9s %9s %9s %9s | %10s %10s" % ("arm", "king", "s2", "funding", "size", "gross_sum", "net_book")
print(hdr); print("-" * len(hdr))
for nm, kp, sp in ARMS:
    src.king = ck["xattn"].astype(np.float64) if kp == "CLEAN" else np.load(kp)["pred"].astype(np.float64)
    src.s2 = np.load(sp)["pred"].astype(np.float64)
    r = per_leg(); R[nm] = r
    print("%-46s %9.1f %9.1f %9.1f %9.1f | %10.1f %10.1f" % (
        nm, r["king"], r["s2"], r["funding"], r["size"], r["_gross_sum"], r["_net_book"]))

b = R[ARMS[0][0]]
print("\n=== king's SHARE of gross turnover (baseline) ===")
for k in ("king", "s2", "funding", "size"):
    print("  %-8s %6.1f%%   (weight %.3f, cadence %dh)" % (
        k, 100 * b[k] / b["_gross_sum"], CUR[k], LEG_CADENCE_H[k]))
print("\n=== per-arm deltas vs BASE ===")
for nm, _, _ in ARMS[1:]:
    r = R[nm]
    print("  %-46s king %+6.1f%%   net_book %+6.1f%%" % (
        nm, 100 * (r["king"] / b["king"] - 1), 100 * (r["_net_book"] / b["_net_book"] - 1)))
json.dump(R, open("/tmp/c2_seq3_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/c2_seq3_result.json")
