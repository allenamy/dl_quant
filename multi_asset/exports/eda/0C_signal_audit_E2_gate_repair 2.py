#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — item E, part 2: WHICH cohort definition makes the gate discriminate?

E part 1 established: the shipped structural gate evaluates over ZERO coins and therefore passes
every crossed caliber. The obvious repair — drop the `member` restriction — was tested and is
WRONG: it goes red on the CORRECT panel too (dev 1.8e-02). Reporting it as the fix would have
armed a false alarm in place of a blind spot.

The reason: `IH` on the hourly grid is the interval of the LAST SETTLEMENT <= t. A coin can be 4h
on every row of a 45-day window and still carry 8h settlements inside its EMA MEMORY (the EMA runs
over the whole cached settlement series, ~1000 rows / 166+ days). The exact-2x identity is a
property of the EMA's INPUT SERIES, not of the grid.

⇒ correct cohort test: a coin is "pure 4h" iff EVERY SETTLEMENT in its series is 4h.
This script measures all three definitions against one control and three attacks.
"""
import json
import os
import sys

import numpy as np

LIVE = os.path.expanduser("~/dl_quant_live")
for p in (os.path.join(LIVE, "signal"), os.path.join(LIVE, "vendor"), os.path.join(LIVE, "live")):
    sys.path.insert(0, p)

import funding_panel as FP                 # noqa: E402
import live_panel as LP                    # noqa: E402
import panel_build as PB                   # noqa: E402

OUT = os.path.expanduser(
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_E2_gate_repair.json")


def identity_test(A, B, cols8, cols4):
    """The shipped algebra, evaluated over a supplied cohort. Returns (d8, d4, n8, n4)."""
    d8 = float(np.nanmax(np.abs(A[:, cols8] - B[:, cols8]))) if cols8.any() else float("nan")
    d4 = float(np.nanmax(np.abs(B[:, cols4] - 2.0 * A[:, cols4]))) if cols4.any() else float("nan")
    return {"n_coins_8h": int(cols8.sum()), "n_coins_4h": int(cols4.sum()),
            "max_abs_diff_on_8h": d8, "max_abs_dev_from_2x_on_4h": d4,
            "verdict": ("PASS" if ((not cols8.any() or d8 == 0.0)
                                   and (not cols4.any() or d4 <= 1e-12 * max(
                                       float(np.nanmax(np.abs(B[:, cols4]))), 1e-30)))
                        else "FAIL"),
            "evaluated_over_zero_coins": bool(not cols8.any() and not cols4.any())}


def main():
    syms = LP.panel_symbols()
    kc, fc = LP.KlineCache(symbols=syms), LP.FundingCache(symbols=syms)
    ts, C, H, L, V, Q = kc.window(PB.WARMUP_RECOMMENDED_H)
    DV = PB.dvol30_from_qvol(np.asarray(Q, np.float64))
    rows = fc.as_rows(until_ms=int(ts[-1]))
    A_true, IH, _ = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_AS_TRAINED)
    B_true, _, _ = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_NORMFIX)
    member = PB.derive_member(DV, np.asarray(C, np.float64)).astype(bool)

    fin = np.isfinite(A_true) & np.isfinite(B_true) & np.isfinite(IH)

    # ── the three cohort definitions ─────────────────────────────────────────────────────────
    with np.errstate(invalid="ignore"):
        d_shipped_8 = (np.where(fin & member, IH, np.nan) >= 8.0).all(0) & (fin & member).any(0)
        d_shipped_4 = (np.where(fin & member, IH, np.nan) <= 4.0).all(0) & (fin & member).any(0)
        d_grid_8 = (np.where(fin, IH, np.nan) >= 8.0).all(0) & fin.any(0)
        d_grid_4 = (np.where(fin, IH, np.nan) <= 4.0).all(0) & fin.any(0)

    # settlement-series cohort: every settlement the EMA ever consumed shares one interval
    ser8 = np.zeros(len(syms), bool)
    ser4 = np.zeros(len(syms), bool)
    n_settle = np.zeros(len(syms), int)
    for j, s in enumerate(syms):
        r = rows.get(s)
        if not r or len(r.get("fts", ())) < 3:
            continue
        iv = r.get("interval_h")
        iv = np.asarray(iv, float)
        iv = np.where(np.isfinite(iv) & (iv > 0), iv, FP.DEFAULT_INTERVAL_H)
        n_settle[j] = len(iv)
        if fin[:, j].any():
            ser8[j] = bool((iv >= 8.0).all())
            ser4[j] = bool((iv <= 4.0).all())

    defs = {"shipped (member-rows, grid IH)": (d_shipped_8, d_shipped_4),
            "grid-only (drop member restriction)": (d_grid_8, d_grid_4),
            "settlement-series (EMA memory)": (ser8, ser4)}

    cases = {"CONTROL_correct_split_path": (A_true, B_true),
             "ATTACK_A_dl_panel_gets_normfix": (B_true, B_true),
             "ATTACK_B_leg_gets_as_trained": (A_true, A_true),
             "ATTACK_C_swapped": (B_true, A_true)}

    res = {"panel_hours": int(len(ts)), "n_symbols": len(syms),
           "settlements_per_symbol_median": int(np.median(n_settle[n_settle > 0])),
           "cohort_sizes": {k: {"n8": int(v[0].sum()), "n4": int(v[1].sum())}
                            for k, v in defs.items()},
           "results": {}}
    for dname, (c8, c4) in defs.items():
        res["results"][dname] = {cname: identity_test(A, B, c8, c4)
                                 for cname, (A, B) in cases.items()}

    # a cohort definition is USABLE iff control PASSes and every attack FAILs
    res["discriminates"] = {
        dname: {"control_pass": r["CONTROL_correct_split_path"]["verdict"] == "PASS",
                "all_attacks_fail": all(r[c]["verdict"] == "FAIL" for c in cases if c != "CONTROL_correct_split_path"),
                "usable_as_a_gate": (r["CONTROL_correct_split_path"]["verdict"] == "PASS" and
                                     all(r[c]["verdict"] == "FAIL"
                                         for c in cases if c != "CONTROL_correct_split_path"))}
        for dname, r in res["results"].items()}

    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
