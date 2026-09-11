#!/usr/bin/env python3
"""r11 STEP 6 — THE FEE SIDE, priced from the live fills.

E-0911-C: commission rows denominated in BNB are in BNB UNITS. Summing `commission` naively mixes
BNB with USDT and understates the bill. Every BNB row is converted at the BNB mid recorded in the
SAME anchor's `mid_at_anchor_vector` (the desk's own price at the moment of the fill), never a
later or global price.

Reports: realized all-in fee per unit traded; the fee TIER implied by the realized maker/taker rates;
BNB coverage measured as a share of NOTIONAL (not of row count); and the value of taking BNB
coverage from its realized level to 100%.

ENV WHITELIST: {} (empty) — asserted (E-0826-D).
"""
import json, os, hashlib
import numpy as np
from collections import defaultdict

_FORBID = ("CAL","JUDGE","PANEL","EXPORT_PANEL","EMA_STATE_JSON","W10_","POD_","DLW_","KING_","SEAT_","UMASK")
assert not sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID)), "ENV WHITELIST VIOLATION"

OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_costtruth/out"
inp = json.load(open(f"{OUT}/r11_fills_input.json"))
bnbtab = json.load(open(f"{OUT}/r11_anchor_bnb.json"))
rows = inp["rows"]
print(f"input sha16 = {hashlib.sha256(open(f'{OUT}/r11_fills_input.json','rb').read()).hexdigest()[:16]}")
print(f"fills {len(rows)}  days {inp['days']}\n")

ats = sorted(float(k) for k in bnbtab)
def bnb_at(ts):
    """BNB mid at the anchor nearest `ts` that HAS one (mirrors trackB's bnb_mid)."""
    cand = [t for t in ats if bnbtab[repr(t)]["bnb"] if repr(t) in bnbtab] if False else \
           [t for t in ats if (bnbtab.get(f"{t}") or bnbtab.get(repr(t)) or {}).get("bnb")]
    if not cand: return None
    t = min(cand, key=lambda t: abs(t - ts))
    return (bnbtab.get(f"{t}") or bnbtab.get(repr(t)))["bnb"]

# cache: one lookup per anchor
_cache = {}
def bnb_for(ts):
    if ts not in _cache: _cache[ts] = bnb_at(ts)
    return _cache[ts]

# ---------------- realized fee ----------------
agg = defaultdict(lambda: dict(notional=0.0, fee_usdt=0.0, n=0))
tot = dict(notional=0.0, fee_usdt=0.0, fee_naive=0.0, n=0,
           bnb_notional=0.0, usdt_notional=0.0, bnb_fee_usdt=0.0, usdt_fee_usdt=0.0,
           bnb_n=0, usdt_n=0, zerofee_notional=0.0, zerofee_n=0)
per_day = defaultdict(lambda: dict(notional=0.0, bnb_notional=0.0, fee=0.0))
missing_bnb = 0
for r in rows:
    nz = r["notional"]; c = r["commission"]; ca = r["commission_asset"]
    mk = bool(r["venue_maker_flag"]) if r["venue_maker_flag"] is not None else (r["order_type"] == "maker")
    if ca == "BNB":
        px = bnb_for(r["anchor_ts"])
        if px is None: missing_bnb += 1; cu = c
        else: cu = c * px
        tot["bnb_notional"] += nz; tot["bnb_fee_usdt"] += cu; tot["bnb_n"] += 1
        per_day[r["day"]]["bnb_notional"] += nz
    else:
        cu = c
        tot["usdt_notional"] += nz; tot["usdt_fee_usdt"] += cu; tot["usdt_n"] += 1
    if c == 0.0:
        tot["zerofee_notional"] += nz; tot["zerofee_n"] += 1
    tot["notional"] += nz; tot["fee_usdt"] += cu; tot["fee_naive"] += c; tot["n"] += 1
    per_day[r["day"]]["notional"] += nz; per_day[r["day"]]["fee"] += cu
    k = ("maker" if mk else "taker", ca)
    agg[k]["notional"] += nz; agg[k]["fee_usdt"] += cu; agg[k]["n"] += 1
    agg[("ALL_" + ("maker" if mk else "taker"), "*")]["notional"] += nz
    agg[("ALL_" + ("maker" if mk else "taker"), "*")]["fee_usdt"] += cu
    agg[("ALL_" + ("maker" if mk else "taker"), "*")]["n"] += 1

T = tot["notional"]
print("=" * 78)
print("REALIZED FEE BILL  (window %s .. %s)" % (inp["days"][0], inp["days"][1]))
print("=" * 78)
print(f"  traded notional (one side)      : ${T:,.0f}")
print(f"  fee bill, BNB converted at mid  : ${tot['fee_usdt']:,.2f}   = {tot['fee_usdt']/T*1e4:.4f} bps/unit traded")
print(f"  fee bill, NAIVE sum (E-0911-C)  : ${tot['fee_naive']:,.2f}   = {tot['fee_naive']/T*1e4:.4f} bps  <-- WRONG, mixes BNB units")
print(f"  understatement from naive sum   : {(1-tot['fee_naive']/tot['fee_usdt'])*100:.1f}% of the true bill")
print(f"  rows with no BNB mid available  : {missing_bnb}")
print()
print("  BNB COVERAGE (share of NOTIONAL, which is what matters, not row count):")
print(f"    notional paid in BNB          : ${tot['bnb_notional']:,.0f}  = {tot['bnb_notional']/T*100:.2f} %   ({tot['bnb_n']} fills)")
print(f"    notional paid in USDT         : ${tot['usdt_notional']:,.0f}  = {tot['usdt_notional']/T*100:.2f} %   ({tot['usdt_n']} fills)")
print(f"    (row-count share paid in BNB  : {tot['bnb_n']/tot['n']*100:.2f} %)")
print(f"    zero-commission notional      : ${tot['zerofee_notional']:,.0f} = {tot['zerofee_notional']/T*100:.2f}% ({tot['zerofee_n']} fills)")
print()
print("  UNIT RATES BY LIQUIDITY ROLE x COMMISSION ASSET (bps of notional):")
for k in sorted(agg, key=lambda k: (k[0], k[1])):
    a = agg[k]
    if a["notional"] <= 0: continue
    print(f"    {k[0]:<12} {k[1]:<5}  n={a['n']:>6}  notional=${a['notional']:>12,.0f}  rate={a['fee_usdt']/a['notional']*1e4:+8.4f} bps")

# ---------------- tier inference ----------------
mk_bnb = agg.get(("maker","BNB")); mk_usdt = agg.get(("maker","USDT"))
tk_bnb = agg.get(("taker","BNB")); tk_usdt = agg.get(("taker","USDT"))
r_mk_usdt = mk_usdt["fee_usdt"]/mk_usdt["notional"]*1e4 if mk_usdt and mk_usdt["notional"]>0 else float("nan")
r_tk_usdt = tk_usdt["fee_usdt"]/tk_usdt["notional"]*1e4 if tk_usdt and tk_usdt["notional"]>0 else float("nan")
r_mk_bnb  = mk_bnb["fee_usdt"]/mk_bnb["notional"]*1e4 if mk_bnb and mk_bnb["notional"]>0 else float("nan")
r_tk_bnb  = tk_bnb["fee_usdt"]/tk_bnb["notional"]*1e4 if tk_bnb and tk_bnb["notional"]>0 else float("nan")
print()
print("=" * 78)
print("FEE TIER — inferred from the realized USDT-paid rates (the undiscounted schedule)")
print("=" * 78)
# Binance USDT-M futures VIP schedule (maker/taker, bps)
TIERS = {"VIP0":(2.00,5.00),"VIP1":(1.60,4.00),"VIP2":(1.40,3.50),"VIP3":(1.20,3.00),
         "VIP4":(1.00,2.70),"VIP5":(0.80,2.50),"VIP6":(0.60,2.40),"VIP7":(0.40,2.20),
         "VIP8":(0.20,2.00),"VIP9":(0.00,1.70)}
print(f"  realized maker rate, USDT-paid  : {r_mk_usdt:.4f} bps")
print(f"  realized taker rate, USDT-paid  : {r_tk_usdt:.4f} bps")
best = min(TIERS, key=lambda t: abs(TIERS[t][0]-r_mk_usdt)+abs(TIERS[t][1]-r_tk_usdt))
print(f"  closest published tier          : {best}  (maker {TIERS[best][0]:.2f} / taker {TIERS[best][1]:.2f} bps)")
print(f"  realized maker rate, BNB-paid   : {r_mk_bnb:.4f} bps   -> discount vs USDT-paid maker: {(1-r_mk_bnb/r_mk_usdt)*100:.2f}%")
print(f"  realized taker rate, BNB-paid   : {r_tk_bnb:.4f} bps   -> discount vs USDT-paid taker: {(1-r_tk_bnb/r_tk_usdt)*100:.2f}%")

# ---------------- value of full BNB coverage ----------------
print()
print("=" * 78)
print("VALUE OF TAKING BNB COVERAGE TO 100%")
print("=" * 78)
# counterfactual: every USDT-paid fill instead paid in BNB at that role's realized BNB rate
cf = 0.0
for role, rate_bnb in (("maker", r_mk_bnb), ("taker", r_tk_bnb)):
    a = agg.get((role, "USDT"))
    if a and a["notional"] > 0 and rate_bnb == rate_bnb:
        cf += a["notional"] * rate_bnb / 1e4
saved = (tot["usdt_fee_usdt"] - cf)
print(f"  fee actually paid on USDT-settled notional : ${tot['usdt_fee_usdt']:,.2f}")
print(f"  same notional at the realized BNB rates    : ${cf:,.2f}")
print(f"  SAVING over the window                     : ${saved:,.2f}")
print(f"  per unit traded notional                   : {saved/T*1e4:.4f} bps   (on ALL traded notional)")
new_rate = (tot["fee_usdt"] - saved) / T * 1e4
print(f"  all-in fee/unit: {tot['fee_usdt']/T*1e4:.4f} bps  ->  {new_rate:.4f} bps")
out = dict(window=inp["days"], traded_notional=T, fee_usdt=tot["fee_usdt"], fee_naive=tot["fee_naive"],
           fee_bps=tot["fee_usdt"]/T*1e4, fee_bps_naive=tot["fee_naive"]/T*1e4,
           bnb_notional_share=tot["bnb_notional"]/T, bnb_rowcount_share=tot["bnb_n"]/tot["n"],
           maker_rate_usdt_bps=r_mk_usdt, taker_rate_usdt_bps=r_tk_usdt,
           maker_rate_bnb_bps=r_mk_bnb, taker_rate_bnb_bps=r_tk_bnb,
           inferred_tier=best, tier_schedule=TIERS[best],
           full_bnb_saving_usdt=saved, full_bnb_saving_bps_per_unit_traded=saved/T*1e4,
           fee_bps_after_full_bnb=new_rate,
           n_fills=tot["n"], zerofee_notional_share=tot["zerofee_notional"]/T)
json.dump(out, open(f"{OUT}/r11_fee_side.json","w"), indent=1)
print(f"\nwrote {OUT}/r11_fee_side.json")
