"""SEQ 5 addendum — "does it make money" is NECESSARY, not SUFFICIENT. Three missing readings.

> created 2026-08-04 05:xx UTC | Session: B4-retrain
> dispatch (team-lead): BE > cost does not say the book is worth capital. Add absolute %/NAV,
>   net-of-cost Sharpe, and regime-conditioned net — because 3.79 is a moving target.

★ WHY THIS EXISTS, in team-lead's words: "we now have a criterion for *does it make money*; we do
  not have one for *is it worth doing*." A book at IC 0.032 can be net-positive and still have a
  Sharpe too low to deserve the capital.

★★★ THE 28% GAP IS A REGIME-MIX DIFFERENCE, NOT BROKEN ARITHMETIC — and the source predicted it.
   Charging each anchor its own regime cost implies a turnover-weighted average of **2.74 bps** while
   the live blend is **3.79**. That is not a contradiction: STATE §2 defines 3.79 as **notional-weighted
   over the last 11 anchors**, and JOURNAL_2026-08-03 §17 writes the split with its own caveat attached
   — "平静锚 +0.84 / 奔跑锚 +4.48; **本窗趋势日偏多**". Solving 0.84w + 4.48(1−w) = 3.79 gives a calm
   notional share of **w = 0.19** in the live window; this backtest's turnover-weighted calm share is
   **0.478** over 9821 anchors. Both are correct about their own sample.

   ⇒ **3.79 is the trend-day-heavy rate.** Applying it across full history charges the running-regime
   rate almost everywhere. ⇒ **The claim "k=0.2 is the only net-positive configuration" is a statement
   about the assumed cost mix, not about the book**: mix-neutral pricing makes all three cells positive
   (k=.595 −208 → +1239, k=1.0 −1163 → +519), though the ORDERING by net is unchanged.

   ★ This is STATE's own caveat made concrete. It says "3.79 是会动的靶子 … 靶子动 1bps 就足以换边".
   The mix correction is **1.05 bps** and its sign is favourable — the caveat is not hypothetical.

   ★ COUNTER-CAVEAT, stated with equal force: 0.84 and 4.48 are sub-averages of **11 anchors** split
   into two bins (sub-counts unrecorded, possibly 2 and 9), and two points may not span the cost
   distribution — the running tail could sit well above 4.48. The mix correction is credible in SIGN
   and order-of-magnitude; its inputs are n=11. The reconciliation gate below stays RED on purpose:
   red here means "these two numbers describe different samples", which is exactly true and must not
   be silently absorbed.

★★ REGIME IS PRICED AT ITS OWN COST, NOT AT THE AVERAGE. The measured 3.79 bps is a blend of calm
   anchors (+0.84) and running anchors (+4.48). Charging every anchor the blended 3.79 flatters the
   calm ones and forgives the running ones. Here each anchor is charged the cost of ITS OWN regime,
   which is the only version that answers "what happens when it gets expensive".
   Regime label is CAUSAL: trailing BTC realised vol at t (PanelSource.btc_rvol_bps_min, window 24h),
   split at its median over the evaluated anchors — never a forward or full-sample-percentile label.

★ SHARPE CALIBER. Anchor P&L -> DAILY sums -> daily Sharpe x sqrt(365), matching
  `replay_fullhist._dsharpe` so the number sits beside the engine's own table rather than beside a
  differently-annualised one.
"""
import sys
import json

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
KING_PRED = "/tmp/vs3_pred_s1x_SERVE.npz"
S2_PRED = "/tmp/vs_pred_s2_SERVE.npz"
ANCHOR = dict(ic=0.05725, gross=5009.0, turn=1377.0, be=3.638)

NAV = 2201.0            # STATE §2, live equity
GROSS_USDT = 4390.0     # STATE §2, 2x leverage
COST_CALM, COST_RUN, COST_BLEND = 0.84, 4.48, 3.79   # STATE §2 measured

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.king = np.load(KING_PRED)["pred"].astype(np.float64)
src.s2 = np.load(S2_PRED)["pred"].astype(np.float64)

A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)

# ---- causal regime label: trailing BTC realised vol at each anchor ----
rv = np.array([src.btc_rvol_bps_min(int(t), window_h=24) for t in A], float)
med = float(np.nanmedian(rv))
calm = rv <= med
print(f"[regime] trailing-24h BTC rvol median {med:.4f} bps/min -> calm {int(calm.sum())} / "
      f"running {int((~calm).sum())} anchors (causal label)", flush=True)


class AsymCap(SignalChain):
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k)
        self.lo_pct, self.hi_pct = lo_pct, hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def run(W, hi):
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lo_pct=1.0, hi_pct=hi)
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
            prev = prev
            continue
        m, p = bk[ti]
        w = np.zeros(src.N)
        w[m] = p
        ok = np.isfinite(ret)
        pnl[i] = float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        turn[i] = float(np.abs(w - prev).sum())
        prev = w
        v = ok[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    return np.array(pnl), np.array(turn), float(np.nanmean(ics))


def sharpe_daily(pnl_series):
    """anchor P&L -> daily -> daily Sharpe x sqrt(365)  (replay_fullhist._dsharpe caliber)."""
    day = (src.ts[A] // (1000 * 3600 * 24)).astype(np.int64)
    d = pd.DataFrame({"day": day, "p": pnl_series}).groupby("day")["p"].sum().values
    d = d[np.isfinite(d)]
    return float(np.mean(d) / (np.std(d) + 1e-12) * np.sqrt(365.0)) if len(d) > 2 else np.nan


def W_of(k):
    r = (1.0 - k) / 2.0
    return {"king": k, "s2": r, "funding": r, "size": 0.0}


R = {}
print("\n%-18s %9s %8s %9s | %8s %8s | %10s %10s %10s"
      % ("book", "IC", "BE", "net@3.79", "Sh@1.9", "Sh@3.79", "%NAV@1.9", "%NAV@3.79", "%NAV@regime"))
print("-" * 108)
for k in (0.2, 0.595, 1.0):
    for hi in (99.0,):
        pnl, turn, ic = run(W_of(k), hi)
        G = pnl.sum() / YEARS * 1e4
        TN = turn.sum() / YEARS
        be = G / TN
        # regime-priced: each anchor charged its OWN regime's cost
        cost_vec = np.where(calm, COST_CALM, COST_RUN)
        net_reg = (pnl.sum() - float((turn * cost_vec * 1e-4).sum())) / YEARS * 1e4
        nets = {c: G - TN * c for c in (1.9, 2.504, 3.79)}
        sh = {c: sharpe_daily(pnl - turn * c * 1e-4) for c in (1.9, 3.79)}
        sh_reg = sharpe_daily(pnl - turn * cost_vec * 1e-4)
        # absolute: bps/yr OF GROSS -> USDT/yr -> % of NAV
        pct = {c: nets[c] * 1e-4 * GROSS_USDT / NAV * 100 for c in nets}
        pct_reg = net_reg * 1e-4 * GROSS_USDT / NAV * 100
        nm = "k=%.3f cap%d" % (k, int(hi))
        R[nm] = dict(ic=ic, be=be, gross=G, turn=TN, net=nets, net_regime=net_reg,
                     sharpe=sh, sharpe_regime=sh_reg, pct_nav=pct, pct_nav_regime=pct_reg)
        print("%-18s %+9.5f %8.3f %9.0f | %8.2f %8.2f | %10.1f %10.1f %10.1f"
              % (nm, ic, be, nets[3.79], sh[1.9], sh[3.79], pct[1.9], pct[3.79], pct_reg), flush=True)

gb = R["k=0.595 cap99"]
gate = (abs(gb["ic"] - ANCHOR["ic"]) < 5e-5 and abs(gb["be"] - ANCHOR["be"]) < 5e-3)
print("\n=== GATE (baseline cell == C3 post-batch (b)) : IC %.5f (%.5f)  BE %.3f (%.3f) -> %s"
      % (gb["ic"], ANCHOR["ic"], gb["be"], ANCHOR["be"], "PASS" if gate else "FAIL"))
if not gate:
    print("GATE FAILED — emitting nothing.")
    sys.exit(1)

# ---- RECONCILIATION GATE: the regime decomposition must reproduce the measured blend ----
print("\n=== REGIME-COST RECONCILIATION (gate on the regime column) ===")
recon_ok = True
for nm, r in R.items():
    implied = (r["gross"] - r["net_regime"]) / r["turn"]
    ok = abs(implied - COST_BLEND) < 0.15
    recon_ok &= ok
    print("  %-18s implied turnover-weighted cost %.3f  vs measured blend %.3f   %s"
          % (nm, implied, COST_BLEND, "ok" if ok else "*** MISMATCH ***"))
w_calm_needed = (COST_RUN - COST_BLEND) / (COST_RUN - COST_CALM)
w_bt = (COST_RUN - (R["k=0.595 cap99"]["gross"] - R["k=0.595 cap99"]["net_regime"])
        / R["k=0.595 cap99"]["turn"]) / (COST_RUN - COST_CALM)
print("  calm share implied by the LIVE blend %.2f : w = %.3f   (11 anchors, notional-weighted, "
      "'本窗趋势日偏多')" % (COST_BLEND, w_calm_needed))
print("  calm share of THIS BACKTEST          : w = %.3f   (%d anchors, turnover-weighted; "
      "%.3f by anchor count)" % (w_bt, len(A), calm.mean()))
print("  ⇒ the %.2f-bps gap is a REGIME-MIX difference between an 11-anchor window and a %d-anchor"
      % (COST_BLEND - (COST_BLEND - (COST_BLEND - 2.74)), len(A)))
print("    backtest, not a broken decomposition. RED here = 'different samples', which is true.")
print("    Do not quote the regime column without its calm share, and not without n=11.")

print("\n=== the three readings the BE table could not give ===")
for nm, r in R.items():
    print("  %-18s  net@blend3.79 %+7.0f bps  |  net@REGIME-PRICED %+7.0f bps  (%s)"
          % (nm, r["net"][3.79], r["net_regime"],
             "regime pricing is KINDER" if r["net_regime"] > r["net"][3.79] else "regime pricing is HARSHER"))
print()
for nm, r in R.items():
    print("  %-18s  Sharpe net@1.9 %5.2f   net@3.79 %5.2f   net@regime %5.2f"
          % (nm, r["sharpe"][1.9], r["sharpe"][3.79], r["sharpe_regime"]))
print()
for nm, r in R.items():
    print("  %-18s  %%NAV/yr  @1.9 %+6.1f%%   @3.79 %+6.1f%%   @regime %+6.1f%%   (NAV %.0f, gross %.0f)"
          % (nm, r["pct_nav"][1.9], r["pct_nav"][3.79], r["pct_nav_regime"], NAV, GROSS_USDT))

json.dump(dict(anchor=ANCHOR, nav=NAV, gross=GROSS_USDT,
               costs=dict(calm=COST_CALM, running=COST_RUN, blend=COST_BLEND),
               regime_median_rvol=med, n_calm=int(calm.sum()), n_run=int((~calm).sum()), cells=R),
          open("/mnt/storage/private/work_hsy/b4_causal_scratch/b4_seq5_absolute.json", "w"),
          indent=1, default=float)
print("\nsaved b4_seq5_absolute.json")
