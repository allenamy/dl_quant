"""Does tonight's headline survive certification? Same model, same book, two forward loops.

> created 2026-08-04 08:xx UTC | Session: B4-retrain | status: final
> dispatch: self, as the follow-through the `vs_infer` finding demands.

★ THE ONE VARIABLE. Both arms use the SAME frozen model (`wideA_lamorth0_xattn_5yr_causal_v1`),
  the same panel, the same s2/funding legs, the same weights and caps. The only difference is which
  code produced the king's composite:

     LEGACY    /tmp/vs3_pred_s1x_SERVE.npz   hand-rolled loop (vs_infer3.py), never gated
     CERTIFIED /tmp/vs5_pred_s1x_SERVE.npz   TH.predict_scores_wide, gate 5/5 bitwise 0.000e+00

  If BE and net move, the headline was reporting the loop as much as the model. If they do not, the
  defect is real but priced at zero here — and that is worth knowing with the same confidence.

★ THE s2 LEG IS UNCERTIFIED IN BOTH ARMS and is deliberately left so: it is held FIXED, which is
  what makes this a controlled comparison of the king's loop. It does NOT mean the s2 leg is fine —
  it cannot be certified at all in its densified form (no frozen artifact covers those rows).
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
S2_PRED = "/tmp/vs_pred_s2_SERVE.npz"
ARMS = {"LEGACY (vs_infer3, ungated)": "/tmp/vs3_pred_s1x_SERVE.npz",
        "CERTIFIED (predict_scores_wide)": "/tmp/vs5_pred_s1x_SERVE.npz"}
ANCHOR = dict(ic=0.05725, be=3.638)      # C3 post-batch (b), LEGACY arm — the gate below
COST = 3.79

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.s2 = np.load(S2_PRED)["pred"].astype(np.float64)

k_leg = np.load(ARMS["LEGACY (vs_infer3, ungated)"])["pred"].astype(np.float64)
k_cer = np.load(ARMS["CERTIFIED (predict_scores_wide)"])["pred"].astype(np.float64)
both = np.isfinite(k_leg) & np.isfinite(k_cer)
print("king composite: cells=%d  max|d|=%.3e  mean|d|=%.3e  corr=%.8f"
      % (both.sum(), np.abs(k_leg[both] - k_cer[both]).max(),
         np.abs(k_leg[both] - k_cer[both]).mean(),
         np.corrcoef(k_leg[both], k_cer[both])[0, 1]), flush=True)
print("nan-pattern-equal=%s\n" % np.array_equal(np.isfinite(k_leg), np.isfinite(k_cer)), flush=True)


class AsymCap(SignalChain):
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k)
        self.lo_pct, self.hi_pct = lo_pct, hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def run(kpred, kw):
    src.king = kpred
    A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                          & np.isfinite(src.s2)).any(1))[0])
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
    return dict(ic=float(np.nanmean(ics)), gross=G, turn=TN, be=G / TN, net=G - TN * COST,
                n=len(A))


print("%-34s %-8s %9s %8s %9s %9s" % ("arm", "k", "IC", "BE", "net@3.79", "anchors"))
print("-" * 84)
R = {}
for name, path in ARMS.items():
    kp = np.load(path)["pred"].astype(np.float64)
    for kw in (0.595, 0.2):
        r = run(kp, kw)
        R[(name, kw)] = r
        print("%-34s %-8.3f %+9.5f %8.3f %9.0f %9d"
              % (name, kw, r["ic"], r["be"], r["net"], r["n"]), flush=True)

g = R[("LEGACY (vs_infer3, ungated)", 0.595)]
ok = abs(g["ic"] - ANCHOR["ic"]) < 5e-5 and abs(g["be"] - ANCHOR["be"]) < 5e-3
print("\n=== GATE (LEGACY k=.595 == C3 post-batch (b)): IC %.5f (%.5f) BE %.3f (%.3f) -> %s"
      % (g["ic"], ANCHOR["ic"], g["be"], ANCHOR["be"], "PASS" if ok else "FAIL"))
if not ok:
    print("gate failed — the comparison is not anchored; read nothing below.")
    sys.exit(1)

print("\n=== WHAT CERTIFICATION COSTS THE HEADLINE ===")
for kw in (0.595, 0.2):
    a = R[("LEGACY (vs_infer3, ungated)", kw)]
    b = R[("CERTIFIED (predict_scores_wide)", kw)]
    print("  k=%.3f | IC %+.5f -> %+.5f (%+.2f%%) | BE %.3f -> %.3f (%+.2f%%) | "
          "net %+.0f -> %+.0f (%+.0f bps)"
          % (kw, a["ic"], b["ic"], 100 * (b["ic"] / a["ic"] - 1),
             a["be"], b["be"], 100 * (b["be"] / a["be"] - 1),
             a["net"], b["net"], b["net"] - a["net"]))
