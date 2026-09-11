#!/usr/bin/env python3
"""R11 TOTALS — converts every member to the frozen comparison unit and sums.
ENV WHITELIST = EMPTY SET (asserted, E-0826-D). Pure arithmetic on the three member receipts.
UNIT: g = bps per 4h anchor per unit gross.  NAV%/yr at 2.0x gross = g * 2190 * 2 / 100.
A0 = +0.6342 g, Sharpe 1.2912, n 9138, +27.78% NAV/yr."""
import json, os, hashlib, glob
from datetime import datetime, timezone
from collections import defaultdict
import numpy as np
_real_get = os.environ.get
def _no_env(k, d=None): raise RuntimeError("E-0826-D violation: env read %r; whitelist EMPTY" % k)
os.environ.get = _no_env
B = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_income"
LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()[:16]
NAVYR = lambda g: g * 2190 * 2 / 100.0
A0 = 0.6342
R = {"device": "r11_totals.py", "env_whitelist": [], "gpu_used": False, "network": False,
     "self_sha256": sha16(os.path.abspath(__file__)), "inputs_sha16": {}}
for f in ("receipts/RECEIPT_r11_M1_fee.json", "receipts/RECEIPT_r11_M2_financing.json",
          "receipts/RECEIPT_r11_M3_quoting.json"):
    R["inputs_sha16"][f] = sha16(f"{B}/{f}")
M1 = json.load(open(f"{B}/receipts/RECEIPT_r11_M1_fee.json"))
M2 = json.load(open(f"{B}/receipts/RECEIPT_r11_M2_financing.json"))
M3 = json.load(open(f"{B}/receipts/RECEIPT_r11_M3_quoting.json"))

# ---- trailing-30d traded volume (the fee-tier gate) -------------------------------------------
days = sorted(d for d in os.listdir(LOG) if d.isdigit())
vol = M1["M1_fee"]["traded_notional_by_day"]
d30 = sorted(vol)[-30:]
v30 = sum(vol[d] for d in d30)
R["FEE_TIER_GATE"] = {"trailing_30d_traded_notional_usdt": round(v30, 0),
    "trailing_5d_annualised_30d_equivalent": round(sum(vol[d] for d in sorted(vol)[-5:]) / 5 * 30, 0),
    "current_tier_VERIFIED": "VIP0 (maker 0.0200%, taker 0.0500%) — read off USDT-denominated commission "
        "rows that are EXACTLY 2.0000 and 5.0000 bps of fill notional, n=8317 and n=6818 fills",
    "VIP1_threshold_INFERRED": "Binance USDT-M VIP1 needs ~15,000,000 USD of 30d futures volume "
        "(public schedule, NOT verified from the venue in this session — account-authenticated endpoints "
        "are off-limits here). Desk 30d volume is ~1/10 to ~1/3 of that even at the elevated recent rate.",
    "reading": "the volume-based tier ladder is CLOSED at this book size. The only live fee lever is the "
               "10% BNB discount, which is currently OFF."}
turn = {"current_09-07..09-11": 0.170372, "calm_08-05..09-06": 0.086814, "whole_window": 0.128265}

def line(name, bps_per_unit_traded, T, verified, note):
    g = bps_per_unit_traded * T
    return {"lever": name, "bps_per_unit_traded": round(bps_per_unit_traded, 4), "turnover_used": T,
            "g_bps_per_anchor_per_unit_gross": round(g, 5), "NAV_pct_per_year_at_2x": round(NAVYR(g), 4),
            "pct_of_A0": round(100 * g / A0, 2), "status": verified, "note": note}
R["LINES"] = {}
R["LINES"]["M1a_BNB_discount_restore"] = {
    tname: line("restore the 10% BNB fee discount", 0.3125, T, "VERIFIED",
        "the discount was 100% covered 08-05..09-06 and has been 0% since 2026-09-07; 0.3125 bps = 10% "
        "of the 3.1252 bps all-in fee now being paid entirely in USDT")
    for tname, T in turn.items()}
R["LINES"]["M1b_taker_to_maker_ceiling"] = {
    tname: line("every taker fill executed as maker (CEILING, not a plan)", 0.8726, T, "VERIFIED-ceiling",
        "taker blended 4.9001 vs maker blended 1.9122 bps on 29.2% of window notional. NOT fully "
        "choosable: 15.1pp of that 29.2pp is the 09-09 protective flatten (a risk action) and the rest "
        "is the residual of maker legs that did not fill.")
    for tname, T in turn.items()}
# behind-arm lever, expressed in the comparison unit
itt = M3["ARM_ITT_DIFF_behind_minus_join"]
join_intended = M3["ARM_SUMMARY"]["join"]["intended"]
sum_gross = M1["turnover"]["sum_gross"]
for tag, val in (("point", -itt["point"]), ("CI_lo", -itt["CI95"][1]), ("CI_hi", -itt["CI95"][0])):
    usdt = join_intended * val / 1e4
    g = usdt / sum_gross * 1e4
    R["LINES"].setdefault("M3a_move_join_notional_to_behind", {})[tag] = {
        "saving_bps_per_unit_intended": round(val, 4), "usdt_over_window": round(usdt, 2),
        "g_bps_per_anchor_per_unit_gross": round(g, 5), "NAV_pct_per_year_at_2x": round(NAVYR(g), 4),
        "pct_of_A0": round(100 * g / A0, 2)}
R["LINES"]["M3a_move_join_notional_to_behind"]["status"] = "UNDECIDED — CI95 on the ITT difference "\
    "spans zero ([-3.80, +0.16] bps per unit intended, 31 UTC-day blocks). The point estimate says the "\
    "CURRENT eps=0.50 policy is leaving money by not quoting MORE behind the touch, which is the "\
    "OPPOSITE of what the markout reading alone suggests. Not bankable; it is an upper end."
R["LINES"]["M2_idle_collateral"] = {
    f"safety_{m}_at_{y}pct_yield": {
        "idle_pct_of_NAV": v["genuinely_idle_pct_of_NAV"],
        "NAV_pct_per_year": round(v["genuinely_idle_pct_of_NAV"] / 100.0 * y, 4),
        "g_bps_per_anchor_per_unit_gross": round((v["genuinely_idle_pct_of_NAV"] / 100.0 * y) / 43.8, 5),
        "pct_of_A0": round(100 * ((v["genuinely_idle_pct_of_NAV"] / 100.0 * y) / 43.8) / A0, 2)}
    for m, v in M2["BUFFER"]["by_safety_multiple_on_maxDD"].items() for y in (4.0,)}
R["LINES"]["M2_idle_collateral"]["status"] = "INFERRED. The 90.2% unencumbered-by-IM figure is VERIFIED "\
    "arithmetic (IM = gross/20, asserted by arm() A6). The tail-adequate idle fraction is INFERRED and "\
    "rests on LOWER-BOUND tail inputs. The 4%/yr cash rate is an assumption, not a measurement. And the "\
    "whole line is structurally blocked by constant_leverage_2.00 (see M2 STRUCTURAL_BLOCKER)."

# ---- the honest total -------------------------------------------------------------------------
T = turn["whole_window"]
bankable_g = 0.3125 * T
R["TOTAL"] = {
  "BANKABLE_NOW_no_research_risk": {
    "members": ["M1a BNB discount restore"],
    "g_bps_per_anchor_per_unit_gross": round(bankable_g, 5),
    "NAV_pct_per_year_at_2x": round(NAVYR(bankable_g), 3),
    "pct_of_A0": round(100 * bankable_g / A0, 2),
    "range_over_turnover_regimes_NAV_pct_yr": [round(NAVYR(0.3125 * turn["calm_08-05..09-06"]), 3),
                                               round(NAVYR(0.3125 * turn["current_09-07..09-11"]), 3)]},
  "PLAUSIBLE_needs_a_live_change_and_a_user_ruling": {
    "members": ["M2 idle collateral at 4%/yr, 1.5x safety multiple",
                "M1b a realistic slice of the taker mix (the topup_taker half, not the flatten half)"],
    "M2_g": round((29.43 / 100.0 * 4.0) / 43.8, 5), "M2_NAV_pct_yr": round(29.43 / 100.0 * 4.0, 3),
    "M1b_topup_only_g": round(0.8726 * (216290.4 / 449047.37) * T, 5),
    "M1b_topup_only_NAV_pct_yr": round(NAVYR(0.8726 * (216290.4 / 449047.37) * T), 3)},
  "NOT_BANKABLE_undecided": {"members": ["M3a behind-arm extension"],
    "reason": "CI spans zero; and its own prereg disposition (2026-09-05) is 'eps 0.50, do not expand'"},
}
tot_g = bankable_g + (29.43 / 100.0 * 4.0) / 43.8 + 0.8726 * (216290.4 / 449047.37) * T
R["TOTAL"]["SUM_bankable_plus_plausible"] = {
    "g_bps_per_anchor_per_unit_gross": round(tot_g, 5), "NAV_pct_per_year_at_2x": round(NAVYR(tot_g), 3),
    "pct_of_A0_0.6342": round(100 * tot_g / A0, 2),
    "A0_for_comparison": {"g": A0, "NAV_pct_yr": 27.78}}
json.dump(R, open(f"{B}/receipts/RECEIPT_r11_TOTALS.json", "w"), indent=1)
os.environ.get = _real_get
print(json.dumps(R, indent=1))
