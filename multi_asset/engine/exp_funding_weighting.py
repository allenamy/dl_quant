"""Engine v1 correction 2: funding-leg z-weighting vs rank-weighting, C5 on vs off (2x2).

0C non-blocker: the funding leg z + L1 weighting is UNBOUNDED -> single-name L1 concentration up to
0.49 -> heavily reliant on C5 winsor to be tradeable. RANK weighting is naturally bounded. If the
rank version is stable WITHOUT C5, C5 demotes from "necessary hygiene" to "insurance" and the
architecture is cleaner. This runs the 2x2 and reports, per cell: funding single-name concentration,
FTX funding-leg max-abs, hedge, and per-year + avg net-of-cost Sharpe.
"""
import sys, json, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.replay_fullhist import run_replay

OUT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/engine_funding_weighting_2x2.json"

cells = {}
rows = []
for mode in ["z", "rank"]:
    for c5 in [True, False]:
        key = f"{mode}_{'C5on' if c5 else 'C5off'}"
        print(f"\n===== {key} =====", flush=True)
        out = run_replay(funding_mode=mode, use_c5=c5, shaping="cap", verbose=True)   # canonical caliber
        cells[key] = out
        yrs = sorted(out["per_year"].keys())
        rows.append({
            "cell": key, "mode": mode, "c5": c5,
            "conc_mean": out["funding_concentration"]["mean"],
            "conc_p99": out["funding_concentration"]["p99"],
            "conc_max": out["funding_concentration"]["max"],
            "ftx_max_abs": out["ftx_funding_tail"]["funding_leg_max_abs_withRC"],
            "hedge_pct": round(out["netting"]["hedge_rate"] * 100, 1),
            "disp_gated": out["ftx_funding_tail"]["disp_gated_days"],
            "net_sharpe_by_year": [out["per_year"][y]["net_of_cost_sharpe"] for y in yrs],
            "avg_net_sharpe": out["avg_net_of_cost_sharpe"],
        })

print("\n\n================ 2x2 SUMMARY ================")
hdr = "%-14s %8s %8s %8s %9s %7s %8s   %s" % (
    "cell", "conc_mn", "conc_p99", "conc_max", "ftx|max|", "hedge%", "avgSh", "net Sharpe by year")
print(hdr); print("-" * len(hdr))
for r in rows:
    print("%-14s %8.3f %8.3f %8.3f %9.3f %7.1f %8.2f   %s" % (
        r["cell"], r["conc_mean"], r["conc_p99"], r["conc_max"], r["ftx_max_abs"],
        r["hedge_pct"], r["avg_net_sharpe"], r["net_sharpe_by_year"]))

json.dump({"rows": rows, "cells": cells}, open(OUT, "w"), indent=1)
print("\n[written]", OUT)
