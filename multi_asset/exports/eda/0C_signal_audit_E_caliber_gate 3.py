#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — item E: is the split-caliber boundary actually GUARDED?

The boundary (DL panel = as_trained/broken, funding leg = normfix) has exactly one BLOCKING
guard: assert_funding_dim.check_structural, an algebraic identity test —
    8h-settled coins : the two calibers must be BIT-IDENTICAL   (scale 8/8 = 1)
    4h-settled coins : normfix must be EXACTLY 2x as_trained    (scale 8/4 = 2)

This script asks the only question that matters about a guard: WOULD IT GO RED IF THE THING IT
GUARDS AGAINST HAPPENED? It runs the shipped gate, verbatim, on the real live panel cache, and
then feeds it three CROSSED calibers that the boundary exists to prevent.

Read-only: uses ~/dl_quant_live/state/panel_cache/*.npz, writes nothing back there.
"""
import json
import os
import sys

import numpy as np

LIVE = os.path.expanduser("~/dl_quant_live")
sys.path.insert(0, os.path.join(LIVE, "signal"))
sys.path.insert(0, os.path.join(LIVE, "vendor"))
sys.path.insert(0, os.path.join(LIVE, "live"))

import assert_funding_dim as AFD           # noqa: E402
import funding_panel as FP                 # noqa: E402
import live_panel as LP                    # noqa: E402
import panel_build as PB                   # noqa: E402

OUT = os.path.expanduser(
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_E_caliber_gate.json")


def main():
    syms = LP.panel_symbols()
    kc = LP.KlineCache(symbols=syms)
    fc = LP.FundingCache(symbols=syms)
    hours = PB.WARMUP_RECOMMENDED_H
    ts, C, H, L, V, Q = kc.window(hours)
    DV = PB.dvol30_from_qvol(np.asarray(Q, np.float64))
    rows = fc.as_rows(until_ms=int(ts[-1]))

    FUND_AT, IH, prov_at = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_AS_TRAINED)
    FUND_FX, _, _ = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_NORMFIX)
    member = PB.derive_member(DV, np.asarray(C, np.float64))

    res = {"panel": {"hours": int(len(ts)), "n_symbols": len(syms),
                     "anchor_ts_ms": int(ts[-1]),
                     "n_members_at_anchor": int(member[-1].sum())}}

    # ── 1. the gate exactly as shipped (build_dl_panel calls this) ───────────────────────────
    shipped = AFD.check_structural(FUND_AT, FUND_FX, IH, member, raise_on_fail=False)
    res["as_shipped"] = shipped

    # ── 2. WHY the two algebraic tests have no rows: `coin_all8` requires the coin to be a
    #      MEMBER on every one of the T rows, not merely 8h-settled on every row it exists.
    fin = np.isfinite(FUND_AT) & np.isfinite(FUND_FX) & np.isfinite(IH)
    mem = np.asarray(member, bool)
    with np.errstate(invalid="ignore"):
        all8_memberwise = (np.where(fin & mem, IH, np.nan) >= 8.0).all(0) & (fin & mem).any(0)
        all4_memberwise = (np.where(fin & mem, IH, np.nan) <= 4.0).all(0) & (fin & mem).any(0)
        all8_finonly = (np.where(fin, IH, np.nan) >= 8.0).all(0) & fin.any(0)
        all4_finonly = (np.where(fin, IH, np.nan) <= 4.0).all(0) & fin.any(0)
    memfrac = (fin & mem).sum(0) / max(len(ts), 1)
    res["why_vacuous"] = {
        "coins_all8_memberwise(shipped)": int(all8_memberwise.sum()),
        "coins_all4_memberwise(shipped)": int(all4_memberwise.sum()),
        "coins_all8_if_member_restriction_dropped": int(all8_finonly.sum()),
        "coins_all4_if_member_restriction_dropped": int(all4_finonly.sum()),
        "n_coins_member_on_100pct_of_rows": int((memfrac >= 1.0).sum()),
        "max_member_row_fraction_over_coins": float(memfrac.max()),
        "note": "a coin needs member==True on ALL T rows to qualify; membership is top-110 of "
                "140 by a churning DVOL30 rank, so the set is empty and BOTH algebraic tests "
                "evaluate over zero coins.",
    }

    # ── 3. the decisive test: does the shipped gate go RED on a crossed caliber? ─────────────
    attacks = {
        "A_dl_panel_silently_gets_normfix": (FUND_FX, FUND_FX),   # both paths corrected
        "B_funding_leg_silently_gets_as_trained": (FUND_AT, FUND_AT),  # both paths broken
        "C_calibers_swapped": (FUND_FX, FUND_AT),                 # crossed
    }
    res["attacks"] = {}
    for name, (A, B) in attacks.items():
        shipped_v = AFD.check_structural(A, B, IH, member, raise_on_fail=False)
        fixed_v = AFD.check_structural(A, B, IH, None, raise_on_fail=False)   # member=None
        res["attacks"][name] = {
            "shipped_gate_verdict": shipped_v["verdict"],
            "shipped_gate_failed": shipped_v["failed"],
            "shipped_n_coins_all8": shipped_v["n_coins_all8"],
            "shipped_n_coins_all4": shipped_v["n_coins_all4"],
            "same_gate_without_member_restriction_verdict": fixed_v["verdict"],
            "same_gate_without_member_restriction_failed": fixed_v["failed"],
            "without_member_n_coins_all8": fixed_v["n_coins_all8"],
            "without_member_n_coins_all4": fixed_v["n_coins_all4"],
        }

    # control: the honest panel must stay green under both variants
    ctrl = AFD.check_structural(FUND_AT, FUND_FX, IH, None, raise_on_fail=False)
    res["control_correct_panel_without_member_restriction"] = {
        "verdict": ctrl["verdict"], "failed": ctrl["failed"],
        "n_coins_all8": ctrl["n_coins_all8"], "n_coins_all4": ctrl["n_coins_all4"],
        "max_abs_diff_on_8h_coins": ctrl["max_abs_diff_on_8h_coins"],
        "max_abs_dev_from_2x_on_4h_coins": ctrl["max_abs_dev_from_2x_on_4h_coins"]}

    # ── 4. what the crossed panel would do to the composite (is it a big error or a small one?)
    from scipy.stats import rankdata
    a = member[-1].astype(bool)
    x_at, x_fx = FUND_AT[-1, a], FUND_FX[-1, a]
    f = np.isfinite(x_at) & np.isfinite(x_fx)
    r_at = rankdata(x_at[f]) / f.sum()
    r_fx = rankdata(x_fx[f]) / f.sum()
    res["consequence_at_anchor"] = {
        "n_members_scored": int(f.sum()),
        "spearman_between_calibers": float(np.corrcoef(r_at, r_fx)[0, 1]),
        "mean_abs_rank_shift_frac_of_universe": float(np.abs(r_at - r_fx).mean()),
        "max_abs_rank_shift_frac_of_universe": float(np.abs(r_at - r_fx).max()),
        "note": "the funding leg is rank-based, so this is the leg-weight error a crossed "
                "caliber would ship on THIS anchor (funding carries w=0.30)."}

    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
