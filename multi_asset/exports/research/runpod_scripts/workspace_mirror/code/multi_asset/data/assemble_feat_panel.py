#!/usr/bin/env python3
"""Assemble the FULL tested-factor feature panel for 0C's Stage-1 GBDT interaction probe.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

Horizontal concat of every already-aligned factor group onto the micro-feature grid (_f2_assembled,
61490 dense-180s rows over 130 days — micro features exist only there). All groups share/subset the
panel_ref h3600 ts, so alignment is exact ts-match (searchsorted). Output per 0C's gbdt_probe schema:
  <sym>__X   [N, 94]  = 44 fast micro + 20 F2 micro + 15 slow + 7 funding + 4 oflow + 4 semivar
  <sym>__y   [N]      = y_3600 (from panel_ref h3600, the canonical target — NOT _f2's own y)
  <sym>__ts/__day [N]; <sym>__cl [N] bool (FRESH ≥3600s non-overlap greedy per day)
  <sym>__funding [N]  = funding_ema VALUE per row (for the probe's incremental-over-funding residualization)
  names [94], symbols [14]
All causal / as-of ≤t (each group already leak-safe; this is concat + target + cl). y is forward
[t,t+3600] on the SUPERSET grid, aligned by exact ts — no leak.
Usage: PYTHONPATH=. python multi_asset/data/assemble_feat_panel.py
"""
from __future__ import annotations
import os.path as p
import numpy as np

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
OUT = E + "/eda/feat_panel_h3600.npz"
NS = 1_000_000_000
HZN = 3600
GROUPS = ["slow_factor_cache", "funding_factor_cache", "oflow_factor_cache", "semivar_factor_cache"]


def cl_nonoverlap(ts, day, horizon=HZN):
    """Greedy ≥horizon non-overlap per UTC-day-index (same rule as the h3600 panel CL)."""
    cl = np.zeros(len(ts), bool); Hns = horizon * NS
    for d in np.unique(day):
        r = np.where(day == d)[0]; last = -(1 << 62)
        for i in r:
            if int(ts[i]) - last >= Hns:
                cl[i] = True; last = int(ts[i])
    return cl


def main():
    f2 = np.load(p.join(E, "eda/_f2_assembled.npz"), allow_pickle=True)
    ref = np.load(p.join(E, "eda/panel_ref_fund_h3600.npz"), allow_pickle=True)
    SYMBOLS = [str(x) for x in ref["symbols"]]
    full_ts = ref["ts"].astype(np.int64); full_Y = ref["Y"]
    fidx = {int(t): i for i, t in enumerate(full_ts)}

    # feature names
    f2_names = [str(x) for x in f2["names"]]                          # 20 F2 micro
    micro44 = [f"micro44_{i:02d}" for i in range(44)]                 # panel_cache micro (no name list on disk)
    grp_names, grp_ok = {}, True
    for g in GROUPS:
        z = np.load(p.join(E, g, "bnfbtc.npz"), allow_pickle=True)
        grp_names[g] = [str(x) for x in z["factor_names"]]
    names = micro44 + f2_names + sum((grp_names[g] for g in GROUPS), [])
    print(f"[assemble] {len(names)} features = 44 micro + {len(f2_names)} F2 + "
          f"{sum(len(grp_names[g]) for g in GROUPS)} factor-group", flush=True)

    # reference grid = _f2 ts (shared across assets — verified)
    ts = f2["bnfbtc__ts"].astype(np.int64)
    day = f2["bnfbtc__day"].astype(np.int64)
    pos = np.searchsorted(full_ts, ts)
    assert np.all(full_ts[np.clip(pos, 0, len(full_ts) - 1)] == ts), "f2 ts not a subset of full grid"
    cl = cl_nonoverlap(ts, day)
    print(f"[assemble] grid N={len(ts)} days={len(np.unique(day))} cl(≥3600 nonoverlap)={cl.mean():.3f}", flush=True)

    out = {"names": np.array(names, dtype=object), "symbols": np.array(SYMBOLS, dtype=object)}
    # preload group caches (full grid) once per group
    gcache = {g: {s: np.load(p.join(E, g, f"{s}.npz"), allow_pickle=True)["X"] for s in SYMBOLS} for g in GROUPS}
    fund_col_idx = grp_names["funding_factor_cache"].index("funding_ema")

    for si, s in enumerate(SYMBOLS):
        assert np.array_equal(f2[f"{s}__ts"].astype(np.int64), ts), f"{s} f2 ts differs"
        blocks = [f2[f"{s}__X"], f2[f"{s}__F2"]]                       # 44 + 20 micro (already on _f2 grid)
        for g in GROUPS:
            blocks.append(gcache[g][s][pos])                          # full-grid cache aligned to _f2 ts
        X = np.concatenate(blocks, axis=1).astype(np.float32)
        assert X.shape == (len(ts), len(names)), f"{s} X shape {X.shape} != {(len(ts), len(names))}"
        out[f"{s}__X"] = X
        out[f"{s}__y"] = full_Y[pos, si].astype(np.float32)          # y_3600 from panel_ref (canonical target)
        out[f"{s}__ts"] = ts
        out[f"{s}__day"] = day
        out[f"{s}__cl"] = cl
        out[f"{s}__funding"] = gcache["funding_factor_cache"][s][pos, fund_col_idx].astype(np.float32)

    np.savez(OUT, **out)
    # coverage report
    fin = np.mean([np.isfinite(out[f"{s}__X"]).mean() for s in SYMBOLS])
    yfin = np.mean([np.isfinite(out[f"{s}__y"]).mean() for s in SYMBOLS])
    print(f"[assemble] wrote {OUT}\n  X finite={fin:.3f}  y finite={yfin:.3f}  "
          f"funding finite={np.mean([np.isfinite(out[f'{s}__funding']).mean() for s in SYMBOLS]):.3f}", flush=True)


if __name__ == "__main__":
    main()
