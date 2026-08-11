"""Live shadow — THIRD track: champion weights on the CORRECTED funding factor.

WHY A SEPARATE TRACK: champion and challenger both run on the BROKEN funding factor, so they
answer the WEIGHT question. This track holds the weights fixed at champion and swaps only the
factor, so it answers the FACTOR-FIX question. The two questions are orthogonal and get
independent clocks -- the challenger's 60-day counter does NOT reset because of this.

WHY IT IS NEEDED AT ALL: the evidence that the fix helps (paired ΔIC t=+7.79, 0C's independent
reproduction) is entirely IN-SAMPLE. We just learned that lesson on the challenger track, where
reporting the frozen-panel slice as confirmation would have been circular. In-sample evidence
cannot close an in-sample gap, so the fix gets its own out-of-sample clock like anything else.

  champion            = king .30/s2 .10/funding .30/size .30  on wide_dl_live.npz          (broken)
  champion_fixfunding = SAME weights                          on wide_dl_live_fundfix.npz  (fixed)

*** ADDITIVE and NON-FATAL: does not touch canonical, the pilot defaults, or the champion/
    challenger tracks. Wired into run_daily.sh so a failure here cannot break anything else. ***

Pre-registered criteria: exports/live/fixfunding/README.md — frozen before data accumulates.

Out: exports/live/fixfunding/{positions/, pnl_daily.csv, compare.json, daily_report.md}
"""
import json, os, sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")

OUT = MA + "/exports/live/fixfunding"
POS = OUT + "/positions"
LIVE_PANEL = MA + "/exports/live/wide_dl_live.npz"
LIVE_FIXED = MA + "/exports/live/wide_dl_live_fundfix.npz"
FILL = 0.51
COST_CALM, COST_STRESS = 1.9, 2.9
RVOL_STRESS = 18.0
WEIGHTS = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}


def _src(panel):
    from engine.panel_source import PanelSource
    return PanelSource(panel=panel,
                       king=MA + "/exports/live/king_pred_live.npz",
                       s2=MA + "/exports/live/s2_pred_live.npz")


def run(verbose=True):
    os.makedirs(POS, exist_ok=True)
    from data.apply_funding_fix import apply_to_panel
    from challenger import _positions_w, _leg_only
    from engine.ic_monitor import xsec_rank_ic

    apply_to_panel(LIVE_PANEL, LIVE_FIXED, verbose=verbose)   # refresh the corrected live panel

    src_b = _src(LIVE_PANEL)
    src_f = _src(LIVE_FIXED)
    anchors = np.sort(np.where((src_b.member & src_b.CL4 & np.isfinite(src_b.king)
                                & np.isfinite(src_b.s2)).any(1))[0])
    frozen_end = int(np.load(MA + "/exports/eda/king_pred_panel.npz",
                             allow_pickle=True)["ts"].max())

    book_b = _positions_w(src_b, anchors, WEIGHTS)
    book_f = _positions_w(src_f, anchors, WEIGHTS)
    fund_b = _leg_only(src_b, anchors, "funding")
    fund_f = _leg_only(src_f, anchors, "funding")

    syms = np.array(src_f.symbols)
    for t in anchors[src_f.ts[anchors] > frozen_end]:
        ti = int(t); d = pd.to_datetime(src_f.ts[ti], unit="ms", utc=True)
        m, p = book_f[ti]
        json.dump({"anchor_ts_ms": int(src_f.ts[ti]), "anchor_utc": d.isoformat(), "horizon_h": 4,
                   "track": "champion_fixfunding", "weights": WEIGHTS,
                   "factor_version": "funding_ema_normfix (settlement-interval corrected)",
                   "positions": {syms[j]: round(float(w), 8) for j, w in zip(m, p)}},
                  open(f"{POS}/positions_{d.strftime('%Y%m%d_%H')}.json", "w"), indent=1)

    rows = []
    prev = {"broken": np.zeros(src_b.N), "fixed": np.zeros(src_b.N)}
    for t in anchors:
        ti = int(t)
        ret = src_b.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        rvol = src_b.btc_rvol_bps_min(ti)
        stress = bool(np.isfinite(rvol) and rvol > RVOL_STRESS)
        cost = COST_STRESS if stress else COST_CALM
        d = pd.to_datetime(src_b.ts[ti], unit="ms", utc=True)
        row = {"day": d.strftime("%Y-%m-%d"), "regime": "stress" if stress else "calm",
               "is_shadow": bool(int(src_b.ts[ti]) > frozen_end)}
        for name, book, fleg in (("broken", book_b, fund_b), ("fixed", book_f, fund_f)):
            m, p = book[ti]
            w = np.zeros(src_b.N); w[m] = p
            ok = np.isfinite(ret)
            g = float(np.nansum(w[ok] * ret[ok]))
            turn = float(np.abs(w - prev[name]).sum()); prev[name] = w
            row[f"{name}_net"] = FILL * (g - turn * cost * 1e-4)
            row[f"{name}_ic"] = xsec_rank_ic(p, ret[m])
            mF, pF = fleg[ti]
            row[f"{name}_fundleg_pnl"] = float(np.nansum(
                pF * np.where(np.isfinite(ret[mF]), ret[mF], 0.0)))
            row[f"{name}_fundleg_ic"] = xsec_rank_ic(pF, ret[mF])
        rows.append(row)

    df_all = pd.DataFrame(rows)
    df = df_all[df_all.is_shadow].copy()
    shadow_only = len(df) > 0
    if not shadow_only:
        df = df_all.copy()
    df["d_net"] = df["fixed_net"] - df["broken_net"]
    df["d_ic"] = df["fixed_ic"] - df["broken_ic"]
    df["d_fundleg_ic"] = df["fixed_fundleg_ic"] - df["broken_fundleg_ic"]
    daily = df.groupby("day").agg(broken_net=("broken_net", "sum"),
                                  fixed_net=("fixed_net", "sum"),
                                  d_net=("d_net", "sum")).reset_index()
    daily["cum_broken"] = daily["broken_net"].cumsum()
    daily["cum_fixed"] = daily["fixed_net"].cumsum()
    daily.to_csv(OUT + "/pnl_daily.csv", index=False)

    def t_of(s):
        s = s.dropna()
        return round(float(s.mean() / (s.std() + 1e-12) * np.sqrt(len(s))), 2) if len(s) > 2 else None

    stress = df[df.regime == "stress"]
    cmp_ = {
        "question": "does the funding settlement-interval FIX help OUT OF SAMPLE?",
        "weights_held_fixed_at": WEIGHTS,
        "★_scope": ("SHADOW slice only (anchors after the frozen panel) -- the only out-of-sample "
                    "evidence. The in-sample evidence (paired ΔIC t=+7.79) is what this track "
                    "exists to corroborate, so quoting it here would be circular."
                    if shadow_only else
                    "NO shadow anchors matured yet -- BACKTEST slice, NOT evidence. Plumbing check."),
        "is_shadow_evidence": bool(shadow_only),
        "n_anchors": int(len(df)), "n_days": int(len(daily)),
        "criterion_a_book_ic": {"mean_ic_broken": round(float(df["broken_ic"].mean(skipna=True)), 5),
                                "mean_ic_fixed": round(float(df["fixed_ic"].mean(skipna=True)), 5),
                                "mean_d_ic": round(float(df["d_ic"].mean(skipna=True)), 5),
                                "t_stat": t_of(df["d_ic"])},
        "criterion_b_funding_leg_ic": {
            "mean_ic_broken": round(float(df["broken_fundleg_ic"].mean(skipna=True)), 5),
            "mean_ic_fixed": round(float(df["fixed_fundleg_ic"].mean(skipna=True)), 5),
            "mean_d_ic": round(float(df["d_fundleg_ic"].mean(skipna=True)), 5),
            "t_stat": t_of(df["d_fundleg_ic"]),
            "note": "the leg the fix actually touches -- the sharpest read on the fix itself"},
        "criterion_c_stress_anchors": {
            "n": int(len(stress)),
            "d_net": round(float(stress["d_net"].sum()), 6) if len(stress) else None},
        "pnl": {"cum_broken": round(float(daily["cum_broken"].iloc[-1]), 6),
                "cum_fixed": round(float(daily["cum_fixed"].iloc[-1]), 6),
                "days_fixed_better": int((daily["d_net"] > 0).sum()),
                "days_total": int(len(daily))},
        "expected_direction_from_backtest": {
            "price_only_book_net_sharpe": "12.21 -> 12.37 (+0.16)",
            "price_only_funding_leg_ic": "-0.0093 -> -0.0035 (+0.0058)",
            "carry_inclusive_0C": "funding leg net +8.48%/yr, solo Sharpe 0.83",
            "note": "shadow should agree in DIRECTION with these; magnitudes will differ"},
        "caliber": ("shadow paper P&L, price-only (carry not credited), conservative maker-fill; "
                    "NOT a fund net return. Both tracks share everything except the factor."),
    }
    json.dump(cmp_, open(OUT + "/compare.json", "w"), indent=1)
    a, b = cmp_["criterion_a_book_ic"], cmp_["criterion_b_funding_leg_ic"]
    with open(OUT + "/daily_report.md", "w") as f:
        f.write(f"# champion_fixfunding — {daily['day'].iloc[-1]}\n\n")
        f.write(("**Scope: SHADOW (out-of-sample) anchors only.**\n\n" if shadow_only else
                 "**⚠ No shadow anchors matured yet — BACKTEST slice, not evidence.**\n\n"))
        f.write(f"- **(a) book rank-IC**: {a['mean_ic_fixed']:.5f} vs {a['mean_ic_broken']:.5f} "
                f"(Δ {a['mean_d_ic']:+.5f}, t {a['t_stat']})\n")
        f.write(f"- **(b) funding-leg rank-IC**: {b['mean_ic_fixed']:.5f} vs "
                f"{b['mean_ic_broken']:.5f} (Δ {b['mean_d_ic']:+.5f}, t {b['t_stat']})\n")
        f.write(f"- **(c) P&L**: fixed better on {cmp_['pnl']['days_fixed_better']}/"
                f"{cmp_['pnl']['days_total']} days; cum {cmp_['pnl']['cum_fixed']:.5f} vs "
                f"{cmp_['pnl']['cum_broken']:.5f}\n\n")
        f.write("> Price-only caliber (carry not credited) — the funding leg is a carry "
                "harvester, so this understates it by construction. Pre-registered criteria in "
                "README.md.\n")
    if verbose:
        print(f"[fixfunding] {len(df)} anchors / {len(daily)} days | book ΔIC "
              f"{a['mean_d_ic']:+.5f} (t {a['t_stat']}) | fundleg ΔIC {b['mean_d_ic']:+.5f} "
              f"(t {b['t_stat']})", flush=True)
        print(f"[fixfunding] -> {OUT}/", flush=True)


if __name__ == "__main__":
    run()
