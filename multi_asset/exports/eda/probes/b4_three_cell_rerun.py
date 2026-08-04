"""甲 三格重跑 — as a single-variable LADDER, with dual-target gaps and both embargos. (ledger #20)

> created 2026-08-04 09:2x UTC | Session: B4-retrain | status: final

★ WHY A LADDER AND NOT THREE CELLS. The dispatch is ① old anchor (proves the instrument) → ②
  new anchor (S1F) → ③ swap in the clean s2. But ① and ② differ in TWO things at once — the king's
  identity AND whether its predictions came from the certified inference. So the ladder inserts ①b:

     ①   vs3 king (legacy hand-rolled loop) + dirty s2   -> MUST reproduce C3's 3.638/3.639
                                                             third-party number == instrument OK
     ①b  vs5 causal_v1 king (certified)     + dirty s2   -> isolates CERTIFICATION alone
     ②   vs5 S1F king (certified, corrfund) + dirty s2   -> isolates KING IDENTITY -> NEW ANCHOR
     ③a  vs5 S1F king + clean s2 (emb=8)                 -> isolates the s2 swap
     ③b  vs5 S1F king + clean s2 (emb=10)                -> 主判 (ledger #14 ruling)

  ①→①b→②→③ each move ONE thing. Without ①b, "S1F is worth X" would silently include the
  certification delta, which is a different quantity and was separately measured at +0.3-0.6% BE.

★★ THE s2 LEG IN ①/①b/② IS THE UNCERTIFIED HAND-ROLLED ONE, ON PURPOSE — it is held FIXED so the
   king comparisons are single-variable. It is NOT a claim that leg is fine. ③ is where it moves.

★ DUAL TARGET (prereg v1 §4, after the 2026-08-04 cost rebuild). 3.79/0.84/4.48 are RETIRED.
     point  3.63 bps        -> gap must be reported
     gate   5.8 (CI upper)  -> DEPLOYMENT gate; clearing only the point bets on an n=16 estimate
   Both columns always; the gate column is the one that decides.
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
from engine.netting import CrossLegNetting, LEG_CADENCE_H   # noqa: E402

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
COST_PT, COST_GATE = 3.63, 5.8
NAV, GROSS_USDT = 2201.0, 4390.0
ANCHOR_C3 = 3.638          # C3 post-batch (b), third-party

LADDER = [
    ("(1)  legacy king + dirty s2", "/tmp/vs3_pred_s1x_SERVE.npz", "/tmp/vs_pred_s2_SERVE.npz"),
    ("(1b) certified causal_v1 + dirty s2", "/tmp/vs5_pred_s1x_SERVE.npz", "/tmp/vs_pred_s2_SERVE.npz"),
    ("(2)  certified S1F + dirty s2", "/tmp/vs5_pred_s1f_SERVE.npz", "/tmp/vs_pred_s2_SERVE.npz"),
    ("(3a) certified S1F + clean s2 emb8", "/tmp/vs5_pred_s1f_SERVE.npz", "/tmp/vs5_pred_s2c_SERVE.npz"),
    ("(3b) certified S1F + clean s2 emb10", "/tmp/vs5_pred_s1f_SERVE.npz", "/tmp/vs5_pred_s2c10_SERVE.npz"),
]
KW, CAP = 0.595, 99.0

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")


class AsymCap(SignalChain):
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k)
        self.lo_pct, self.hi_pct = lo_pct, hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def run(kp, sp, cad_king=4):
    src.king = np.load(kp)["pred"].astype(np.float64)
    src.s2 = np.load(sp)["pred"].astype(np.float64)
    A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                          & np.isfinite(src.s2)).any(1))[0])
    yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
    years = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
    r = (1.0 - KW) / 2.0
    W = {"king": KW, "s2": r, "funding": r, "size": 0.0}
    cad = dict(LEG_CADENCE_H); cad["king"] = cad_king
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lo_pct=1.0, hi_pct=CAP)
    res = CrossLegNetting(ch, W, cost_bps=1.9, cadence=cad).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N); pnl = np.zeros(len(A)); turn = np.zeros(len(A)); ics = []
    for i, t in enumerate(A):
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any() or ti not in bk:
            continue
        m, p = bk[ti]; w = np.zeros(src.N); w[m] = p
        okm = np.isfinite(ret)
        pnl[i] = float(np.where(okm, w * np.nan_to_num(ret), 0.0).sum())
        turn[i] = float(np.abs(w - prev).sum()); prev = w
        v = okm[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    G = pnl.sum() / years * 1e4; TN = turn.sum() / years; be = G / TN
    day = (src.ts[A] // (1000 * 3600 * 24)).astype(np.int64)
    dd = pd.DataFrame({"d": day, "p": pnl - turn * COST_PT * 1e-4}).groupby("d")["p"].sum().values
    sh = float(np.mean(dd) / (np.std(dd) + 1e-12) * np.sqrt(365.0))
    net = G - TN * COST_PT
    return dict(n=len(A), ic=float(np.nanmean(ics)), be=be, turn=TN, gross=G, net=net,
                gap_pt=(COST_PT - be) / COST_PT, gap_gate=(COST_GATE - be) / COST_GATE,
                sh=sh, pct=net * 1e-4 * GROSS_USDT / NAV * 100)


for cad in (4, 8):
    print("\n" + "=" * 108)
    print("=== king cadence = %dh   (k=%.3f, cap%d)   cost: point %.2f / GATE %.2f ==="
          % (cad, KW, int(CAP), COST_PT, COST_GATE))
    print("%-38s %7s %9s %8s %9s %9s %10s %7s %8s"
          % ("cell", "anchors", "IC", "BE", "gap@3.63", "gap@5.8", "net@3.63", "Sh", "%NAV"))
    print("-" * 108)
    R = {}
    for name, kp, sp in LADDER:
        r = run(kp, sp, cad_king=cad)
        R[name] = r
        flag = "  <= CLEARS GATE" if r["gap_gate"] <= 0 else ""
        print("%-38s %7d %+9.5f %8.3f %8.1f%% %8.1f%% %10.0f %7.2f %7.1f%%%s"
              % (name, r["n"], r["ic"], r["be"], 100 * r["gap_pt"], 100 * r["gap_gate"],
                 r["net"], r["sh"], r["pct"], flag), flush=True)
    if cad == 4:
        g = R["(1)  legacy king + dirty s2"]
        ok = abs(g["be"] - ANCHOR_C3) < 5e-3
        print("\n  ★ INSTRUMENT CHECK (cell 1 vs C3's third-party %.3f): BE %.3f -> %s"
              % (ANCHOR_C3, g["be"], "PASS" if ok else "FAIL — read nothing below"))
        if not ok:
            sys.exit(1)
        print("  ★ NEW ANCHOR (cell 2, self-built by an instrument cell 1 just validated): BE %.3f"
              % R["(2)  certified S1F + dirty s2"]["be"])
        base = R["(1)  legacy king + dirty s2"]["be"]
        for nm in ("(1b) certified causal_v1 + dirty s2", "(2)  certified S1F + dirty s2"):
            print("     %-38s BE %.3f  (%+.2f%% vs cell 1)" % (nm, R[nm]["be"],
                                                              100 * (R[nm]["be"] / base - 1)))
        a, b = R["(3a) certified S1F + clean s2 emb8"], R["(3b) certified S1F + clean s2 emb10"]
        print("  ★ EMBARGO SENSITIVITY at book level: emb8 BE %.3f vs emb10 BE %.3f (%+.2f%%) | "
              "IC %+.5f vs %+.5f (%+.2f%%)"
              % (a["be"], b["be"], 100 * (b["be"] / a["be"] - 1), a["ic"], b["ic"],
                 100 * (b["ic"] / a["ic"] - 1)))
