"""A4 — cost-sensitive leg weights.

Positions never depend on cost (engine/netting.py uses cost_bps only for its savings report), so
per (caliber, weight-vector) ONE book run yields (gross_bps_yr, turn_yr) and then

    net_bps_yr(c) = gross_bps_yr - turn_yr * c        [exact identity, not interpolation]
    breakeven c*  = gross_bps_yr / turn_yr

Sweep: king weight in {0,.2,.4,.595,.8,1} with s2/funding held at .202/.202, plus the two corners
(king_only = 1/0/0, drop_king = 0/.202/.202). Unit-gross normalisation makes the absolute scale of
the weight vector irrelevant, so only ratios matter.
Caliber: SERVE (primary, has action implications) + TRAIN (historical reference).
READ-ONLY; /tmp only.
"""
import sys, json
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

COSTS = [1.9, 2.504, 2.9, 3.79, 5.92]
PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)

CAL = {"SERVE": ("/tmp/vs_pred_king_SERVE.npz", "/tmp/vs_pred_s2_SERVE.npz"),
       "TRAIN": ("/tmp/vs_pred_king_TRAIN.npz", "/tmp/vs_pred_s2_TRAIN.npz")}


def book(W):
    ch = SignalChain(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N); g = tn = 0.0; ics = []; mx = []
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N); w[m] = p
        ok = np.isfinite(ret)
        g += float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        tn += float(np.abs(w - prev).sum()); prev = w
        mx.append(float(np.abs(p).max()))
        v = ok[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    return dict(gross=g / YEARS * 1e4, turn=tn / YEARS, ic=float(np.nanmean(ics)),
                maxw=float(np.mean(mx)))


VARIANTS = [("king_only", {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0})]
for k in (0.0, 0.2, 0.4, 0.595, 0.8, 1.0):
    VARIANTS.append(("k=%.3f" % k, {"king": k, "s2": .202, "funding": .202, "size": 0.0}))

out = {}
for cal, (kp, sp) in CAL.items():
    src.king = np.load(kp)["pred"].astype(np.float64)
    src.s2 = np.load(sp)["pred"].astype(np.float64)
    print("\n" + "=" * 108)
    print("CALIBER %s%s" % (cal, "   <- PRIMARY (what the running book actually receives)" if cal == "SERVE" else "   (historical reference)"))
    print("=" * 108)
    hdr = "%-11s %9s %8s %8s %8s | " % ("weights", "book_IC", "gross", "turn", "BE bps")
    hdr += " ".join("%9s" % ("c=%.3g" % c) for c in COSTS)
    print(hdr)
    out[cal] = {}
    for nm, W in VARIANTS:
        r = book(W)
        be = r["gross"] / r["turn"] if r["turn"] > 0 else float("nan")
        nets = [r["gross"] - r["turn"] * c for c in COSTS]
        print("%-11s %+9.5f %8.0f %8.0f %8.3f | %s"
              % (nm, r["ic"], r["gross"], r["turn"], be, " ".join("%9.0f" % v for v in nets)))
        out[cal][nm] = dict(r, breakeven=be, net_by_cost={str(c): v for c, v in zip(COSTS, nets)})
    print("   (net bps/yr = gross - turn*c, exact; BE = gross/turn)")

json.dump(out, open("/tmp/vs_a4_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_a4_result.json", flush=True)
