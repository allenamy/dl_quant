#!/usr/bin/python3
"""READ-ONLY: pull /fapi/v1/leverageBracket and bind the "$25k needs >=$5,000" constant to its source.

Lives in the scratchpad ON PURPOSE. Adding the endpoint to repo code trips the API_SEMANTICS doc
gate and puts a new call on the arming path 2 hours before the decisive 16:00Z read; the number is
worth having now, the production wiring is not. One signed GET, weight 1, no order path touched.

What it answers:
  1. the REAL tier-1 maintMarginRatio per symbol (we have never once read this)
  2. whether our tier assumption holds — 109 positions of ~230 USDT each, all in tier 1, cum = 0.
     If any symbol's tier-1 notional cap is below our per-name size, the ladder is wrong for it.
  3. the ladder recomputed on measured MMR instead of a plausible range
"""
import json
import os
import sys

REPO = os.path.expanduser("~/dl_quant_live")
for d in ("live", "scheduler", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
_env = os.path.join(REPO, ".env")
if os.path.exists(_env):
    for line in open(_env):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import binance_broker as BB            # noqa: E402
import pilot_log as PL                 # noqa: E402

GROSS = 25000.0
MODE = os.environ.get("LIVE_MODE", "DRY_RUN")


def main():
    print(f"mode={MODE}")
    b = BB.BinanceBroker(mode=MODE)
    rows = b._request("GET", "/fapi/v1/leverageBracket", {}, signed=True) or []
    print(f"leverageBracket: {len(rows)} symbols")
    if not rows:
        print("NO DATA — cannot bind the constant"); return

    # the universe we actually hold, and the size we actually hold it in
    root = os.path.join(REPO, "state/testnet/pilot_log")
    days = PL.available_days(root)
    held = {}
    for d in reversed(days):
        rb = PL.read_day(root, d).get("position_readback", [])
        if rb:
            ats = max(float(r["anchor_ts"]) for r in rb)
            held = {r["symbol"]: abs(float(r["venue_position_notional"]))
                    for r in rb if abs(float(r["anchor_ts"]) - ats) < 0.6}
            if any(v > 0 for v in held.values()):
                break
    tgt = {}
    for d in reversed(days):
        one = PL.read_day(root, d)
        anch = {float(a["anchor_ts"]): float(a["target_gross"]) for a in one.get("anchors", [])}
        if not anch:
            continue
        ats = max(anch)
        tgt = {o["symbol"]: abs(float(o["target_w"])) * anch[ats]
               for o in one.get("orders", [])
               if abs(float(o["anchor_ts"]) - ats) < 0.6 and o.get("target_w") is not None}
        if tgt:
            break
    print(f"universe under test: {len(tgt)} targeted names, "
          f"max intended notional {max(tgt.values()) if tgt else 0:.1f} USDT")

    by_sym = {r["symbol"]: r.get("brackets", []) for r in rows}
    t1, viol, missing = {}, [], []
    for s, size in sorted(tgt.items()):
        br = by_sym.get(s)
        if not br:
            missing.append(s); continue
        b1 = sorted(br, key=lambda x: float(x.get("bracket", 0)))[0]
        mmr = float(b1.get("maintMarginRatio"))
        cap = float(b1.get("notionalCap", 0))
        cum = float(b1.get("cum", 0))
        t1[s] = (mmr, cap, cum)
        if size > cap or cum != 0.0:
            viol.append((s, size, cap, cum))

    mmrs = sorted(v[0] for v in t1.values())
    print(f"\ntier-1 maintMarginRatio over {len(t1)} names: "
          f"min={mmrs[0]:.4f} p50={mmrs[len(mmrs)//2]:.4f} max={mmrs[-1]:.4f}")
    from collections import Counter
    print("  distribution:", dict(sorted(Counter(round(m, 4) for m in mmrs).items())))
    print(f"\n★ TIER ASSUMPTION ('all positions in tier 1, cum=0'): "
          f"{'HOLDS' if not viol else 'VIOLATED for ' + str(len(viol)) + ' name(s)'}")
    for s, size, cap, cum in viol[:6]:
        print(f"    {s}: size {size:.1f} > tier-1 cap {cap:.0f} (or cum {cum} != 0)")
    if missing:
        print(f"  ! {len(missing)} targeted name(s) absent from leverageBracket: {missing[:6]}")

    # the maintenance margin our ACTUAL book requires, name by name, at real MMR
    mm_target = sum(tgt[s] * t1[s][0] for s in tgt if s in t1)
    blended = mm_target / sum(tgt[s] for s in tgt if s in t1)
    print(f"\n★ MEASURED maintenance margin for a {GROSS:.0f} USDT book of THIS universe:")
    print(f"    Σ(notional_i × MMR_i) = {mm_target:.2f} USDT   (blended MMR = {blended:.4%})")
    print(f"    liquidation equity floor      = {mm_target:.0f} USDT  -> {GROSS/mm_target:.1f}x")
    im = GROSS / 20.0
    print(f"    initial-margin floor (20x)    = {im:.0f} USDT  -> 20.0x "
          f"[STRUCTURAL DEATH: below this the book cannot be REBUILT after a flatten]")
    print(f"    declared operating cap 5.0x   = {GROSS/5.0:.0f} USDT")
    json.dump({"mode": MODE, "n_symbols": len(rows), "n_targeted": len(tgt),
               "tier1_mmr_min": mmrs[0], "tier1_mmr_med": mmrs[len(mmrs)//2],
               "tier1_mmr_max": mmrs[-1], "blended_mmr": blended,
               "maintenance_margin_usdt": mm_target,
               "liquidation_equity_floor": mm_target,
               "liquidation_leverage": GROSS / mm_target,
               "initial_margin_floor": im,
               "tier_assumption_holds": not viol, "violations": viol[:20],
               "missing_from_bracket": missing[:20]},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "margin_brackets.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
