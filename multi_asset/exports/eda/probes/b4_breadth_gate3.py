"""#21 gate 3 — orthogonality sweep. The cheap gate that kills a batch, read PER SLEEVE.

> created 2026-08-04 15:2x UTC | Session: B4-retrain | prereg FROZEN v1 268a8d9a…

★★ READ PER SLEEVE, NOT POOLED — this is the whole point of the pre-check (`f8cf2e5`).
   `YR4` (the king's target) is residualised against `baseline_cols`, and SIX of the fourteen
   candidates ARE baseline columns:  mom_24h mom_72h rev_1h max_ret_24h rvol_24h size_dvol
   For those six the king carries near-zero exposure BY CONSTRUCTION, so a low |rho| vs the king
   says nothing about breadth. Their gate-3 evidence has to come from s2 and funding.
   For the other eight, |rho| vs the king is informative in both directions.

★ WHAT A CANDIDATE BOOK IS HERE: per anchor, cross-sectional rank of the factor over the members,
  centred and L1-normalised — the simplest honest long/short expression, with no shaping knobs to
  tune. Gate 3 asks whether its P&L moves with an existing sleeve; a dressed-up construction would
  make that question about the dressing.

★ SIGN IS NOT A FREE PARAMETER, and this is the one place it could sneak in: the revival scorecard
  found several of these are REVERSAL (mom_* enter with a negative sign). |rho| is sign-invariant,
  so gate 3 is unaffected — but the sign matters for gates 1/2, so it is RECORDED here (from the
  factor's own standalone rank-IC on this panel) rather than chosen later when it would be a
  post-hoc choice.

★ COST CALIBER: net P&L uses 3.63 bps (the point estimate). Gate 3 is a correlation of net series;
  it is insensitive to the level, but the caliber is named so the series is reproducible.
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
COST = 3.63
CAND = ["mom_4h", "mom_8h", "mom_24h", "mom_72h", "mom_168h", "rev_1h", "rev_3h",
        "gtja_046", "a101_044", "max_ret_24h", "rvol_24h", "rvol_72h",
        "lturnover_24h", "size_dvol"]

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.king = np.load("/tmp/vs5_pred_s1f_SERVE.npz")["pred"].astype(np.float64)
src.s2 = np.load("/tmp/vs5_pred_s2c10_SERVE.npz")["pred"].astype(np.float64)

z = np.load(MA + "/exports/wide_dl_full_corrfund_causal_v1.npz", allow_pickle=True)
chn = [str(c) for c in z["ch_names"]]
BASE = set(str(c) for c in z["baseline_cols"])
CH = z["CH"]

A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
YR = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
print("anchors=%d  cost=%.2f  candidates=%d (%d are baseline cols)"
      % (len(A), COST, len(CAND), sum(c in BASE for c in CAND)), flush=True)


def net_series(w_by_anchor, with_cost=True):
    """L1-normalised weights per anchor -> per-anchor P&L, with or without the cost term.

    ★★ WHY BOTH ARE COMPUTED. The candidate books here are unconstrained per-anchor rank books:
    they re-rank every 4h with no inertia, so their turnover is enormous and every candidate's NET
    series is dominated by its own cost term (measured: -1.7k to -14.7k bps/yr). A correlation
    between two cost-dominated series can be reporting shared TURNOVER rather than shared ALPHA —
    which would make gate 3 kill or spare factors for a reason unrelated to breadth.
    ⇒ So rho is reported on BOTH the net series (the prereg's stated quantity) and the GROSS series
      (cost term removed). If they agree, gate 3 is reading alpha co-movement and stands. If they
      diverge, the net-based verdict is an artifact of a construction choice I made, not a finding.
    """
    prev = np.zeros(src.N)
    out = np.zeros(len(A))
    for i, t in enumerate(A):
        ti = int(t)
        w = w_by_anchor.get(ti)
        ret = src.Y4[ti]
        if w is None or not np.isfinite(ret).any():
            out[i] = 0.0
            continue
        ok = np.isfinite(ret)
        g = float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        out[i] = g - (float(np.abs(w - prev).sum()) * COST * 1e-4 if with_cost else 0.0)
        prev = w
    return out


# ---- the three existing sleeves, each ALONE, through the engine's own chain
sleeves, sleeves_gross = {}, {}
for leg in ("king", "s2", "funding"):
    W = {"king": 0.0, "s2": 0.0, "funding": 0.0, "size": 0.0}
    W[leg] = 1.0
    ch = SignalChain(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=YR)
    wb = {}
    for (t, m, p) in res["net_positions"]:
        w = np.zeros(src.N)
        w[m] = p / max(float(np.abs(p).sum()), 1e-12)
        wb[int(t)] = w
    sleeves[leg] = net_series(wb)
    sleeves_gross[leg] = net_series(wb, with_cost=False)
    print("  sleeve %-8s net/yr=%+8.1f bps" % (leg, sleeves[leg].sum() / 4.492 * 1e4), flush=True)

# ---- each candidate as a plain xsec-rank long/short book
print("\n%-15s %-9s %8s %9s | %9s %9s %9s"
      % ("candidate", "baseline?", "IC", "net/yr", "rho_king", "rho_s2", "rho_fund"))
print("-" * 84)
rows = []
for c in CAND:
    j = chn.index(c)
    wb, ics = {}, []
    for t in A:
        ti = int(t)
        m = np.where(src.member[ti] & src.CL4[ti] & np.isfinite(CH[ti, :, j]))[0]
        if m.size < 5:
            continue
        r = rankdata(CH[ti, m, j].astype(np.float64))
        r = r - r.mean()
        s = float(np.abs(r).sum())
        if s < 1e-12:
            continue
        w = np.zeros(src.N)
        w[m] = r / s
        wb[ti] = w
        ret = src.Y4[ti]
        v = np.isfinite(ret[m])
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(CH[ti, m, j][v]), rankdata(ret[m][v]))[0, 1])
    ns = net_series(wb)
    gs = net_series(wb, with_cost=False)
    ic = float(np.nanmean(ics))
    rho = {k: float(np.corrcoef(ns, v)[0, 1]) for k, v in sleeves.items()}
    rho_g = {k: float(np.corrcoef(gs, v)[0, 1]) for k, v in sleeves_gross.items()}
    inb = c in BASE
    rows.append((c, inb, ic, ns.sum() / 4.492 * 1e4, rho, rho_g))
    print("%-15s %-9s %+8.4f %+9.1f | %+9.3f %+9.3f %+9.3f%s"
          % (c, "★BASE" if inb else "-", ic, ns.sum() / 4.492 * 1e4,
             rho["king"], rho["s2"], rho["funding"],
             "   <- rho_king NOT READABLE" if inb else ""), flush=True)

print("\n=== GATE 3 VERDICT (|rho| < 0.3 vs every sleeve whose comparison is READABLE) ===")
print("  %-15s %-10s %-10s %-10s %s" % ("candidate", "|rho|net", "|rho|gross", "verdict", "agree?"))
for c, inb, ic, net, rho, rho_g in rows:
    rd = {k: v for k, v in rho.items() if not (inb and k == "king")}
    rg = {k: v for k, v in rho_g.items() if not (inb and k == "king")}
    wk = max(rd, key=lambda k: abs(rd[k]))
    wkg = max(rg, key=lambda k: abs(rg[k]))
    ok_n, ok_g = abs(rd[wk]) < 0.3, abs(rg[wkg]) < 0.3
    print("  %-15s %-10.3f %-10.3f %-10s %s"
          % (c, abs(rd[wk]), abs(rg[wkg]), "PASS" if ok_n else "KILLED",
             "yes" if ok_n == ok_g else "*** NET AND GROSS DISAGREE — net verdict is suspect ***"))
print("\n★ For the six baseline-column candidates the king comparison is EXCLUDED, not passed —")
print("  their target was projected out of the king's, so a low value there is guaranteed.")
print("★ Sign recorded above as standalone IC; it is NOT chosen later (that would be post-hoc).")
