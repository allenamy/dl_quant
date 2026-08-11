import json, numpy as np
EDA = "multi_asset/exports/eda"
r = json.load(open(EDA + "/qim_execution_feasibility_raw.json"))

# maker-fill-failure fraction that flips a year net-negative, from verdict break-evens (per-side bps).
BE = {"2022": 6.51, "2023": 9.21, "2024": 15.91, "2025": 15.97, "2026": 4.92}
flip = {}
for tk in (5.0, 9.5):
    flip[str(tk)] = {y: (round(min(1.0, be / tk), 2)) for y, be in BE.items()}

r["maker_fail_flip_negative"] = dict(
    note=("assuming maker cost ~0 and a fraction phi of volume forced to TAKER at cost tk, effective "
          "per-side = phi*tk; year flips net-negative when phi*tk > break-even. phi_flip = BE/tk "
          "(capped 1.0). Uses verdict per-year BE {6.51,9.21,15.91,15.97,4.92}."),
    breakeven_per_side_bps=BE, phi_flip_at_taker=flip)

r["sizing_recommendation"] = dict(
    start_aum_gross_usd="5-10M",
    rationale=("at x=1% maker participation + 5bps effective cost, $5-10M gross retains ~85-90% of the "
               "frictionless Sharpe (7.8-8.8 vs 8.76 ref); all full-universe years strongly positive."),
    scale_to_usd="25M",
    scale_note=("Sharpe ~5.5 (~63% retention); full-universe years (2023-25) >4, weak partial 2026 near "
                "breakeven. Push to $25-50M only if maker participation x>=2% is achievable."),
    soft_ceiling_usd="50-100M",
    ceiling_note=("Sharpe 1.9-3.5, heavily capacity-diluted; beyond this the small/mid-cap alpha is "
                  "uncapturable and only the large-cap core trades. Never flips negative from capacity "
                  "alone (asymptotes to low-positive)."),
    robustness=("book is ROBUST to small-coin execution failure: 50% fill on bottom size-tercile barely "
                "moves Sharpe (7.94->6.30 in 2024, others flat) because those names are already "
                "capacity-suppressed at scale and the large/mid-cap leg carries the Sharpe."),
    negative_flip_risk=("NOT capacity (dilutes, stays positive). Real risks: (a) taker cost > break-even "
                        "in thin/partial years -- 2022/2026 tolerate only ~50-70% maker-fill failure at "
                        "9.5bps taker before flipping, strong years ~100%; (b) UNMODELED market impact / "
                        "adverse selection / queue position on resting maker orders -- the true binding "
                        "constraint, absent from this notional-participation model."),
    honest_caveat=("this models NOTIONAL-PARTICIPATION capacity ONLY. It assumes we can passively capture "
                   "x% of 4h volume as maker with ~0 impact every period including stressed regimes -- "
                   "optimistic. Treat all AUM figures as UPPER bounds; real deployable AUM is likely lower. "
                   "Recommend a live maker-fill pilot at $2-5M to measure realized fill-rate + slippage "
                   "before scaling."))

json.dump(r, open(EDA + "/qim_execution_feasibility.json", "w"), indent=2, default=str)
print("SAVED", EDA + "/qim_execution_feasibility.json")
print("phi_flip@taker9.5:", flip["9.5"])
print("phi_flip@taker5.0:", flip["5.0"])
