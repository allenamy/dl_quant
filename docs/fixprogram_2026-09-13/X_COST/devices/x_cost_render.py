#!/usr/bin/env python3
"""X-COST renderer: arithmetic over committed receipts only (no ledger read). Written after reading run 1 and A1, so
every allocation rule here is PRESENTATION, not a pre-registered measurement; the pre-registered objects are the
identity (x_cost_decompose.py D4) and the A1 factorisation / counterfactual.

Outputs receipts/x_cost_tables.md and receipts/x_cost_attribution.json.
Log-share allocation for the from_reject factorisation: pp_i = Δshare x ln(ratio_i) / Σ ln(ratio_j).
Fee translation: extra fee of a taker component vs maker = notional x (5.00 - 2.00) bps, the rates measured on USDT
fills in S3 (receipt fee_usdt_by_comp); BNB-era fees are not converted.
"""
import json
import math
import os
import sys

R = sys.argv[1]
P = json.load(open(os.path.join(R, "x_cost_periods.json")))
A = json.load(open(os.path.join(R, "x_cost_a1.json")))
recs = json.load(open(os.path.join(R, "x_cost_per_anchor.json")))
COMPS = ["K2d", "K2q", "K2e", "K2n", "K3ci", "K3co", "K3f", "K3nc", "K3n", "K4", "K5", "K6", "K7"]
SUBS = ["S1a", "S1b", "S2a", "S2b", "S3"]
out = {"source_receipts": {"periods_self_sha256": P["self_sha256"], "a1_self_sha256": A["self_sha256"]}}
L = []


def pct(x, nd=1):
    return "—" if x is None else f"{100 * x:.{nd}f}"


L.append("## T1 Maker share (CHK-03 caliber) by period")
L.append("| period | anchors | halted | rebuild | D (USDT) | maker share | median anchor | min–max anchor | maker share ex-rebuild |")
L.append("|---|---:|---:|---:|---:|---:|---:|---|---:|")
for grp, keys in (("periods", ["P1", "P2", "P3"]), ("subperiods", SUBS)):
    for k in keys:
        o = P[grp][k]; ox = P[grp + "_ex_rebuild"][k]
        L.append(f"| {k} | {o['n_anchors']} | {o['n_halted']} | {o['n_rebuild']} | {o['D']:,.0f} | {pct(o['maker_share'])}% | "
                 f"{pct(o['median_anchor_maker_share'])}% | {pct(o['min_anchor_maker_share'])}–{pct(o['max_anchor_maker_share'])}% | {pct(ox['maker_share'])}% |")
L.append("")
L.append("## T2 Taker components as % of D (non-halted, excluding rebuild anchors); Δ vs S1a in pp")
L.append("| component | " + " | ".join(SUBS) + " | Δ S3−S1a |")
L.append("|---|" + "---:|" * (len(SUBS) + 1))
ex = P["subperiods_ex_rebuild"]
base = ex["S1a"]
rows_t2 = {}
for c in COMPS:
    vals = [ex[s]["component_share"][c] for s in SUBS]
    if all((v or 0) == 0 for v in vals):
        continue
    d = (ex["S3"]["component_share"][c] or 0) - (base["component_share"][c] or 0)
    rows_t2[c] = {"shares": dict(zip(SUBS, vals)), "delta_S3_S1a": d}
    L.append(f"| {c} | " + " | ".join(pct(v, 2) for v in vals) + f" | {100 * d:+.2f} |")
tot = [ex[s]["taker_share"] for s in SUBS]
dT = ex["S3"]["taker_share"] - base["taker_share"]
L.append("| **taker total** | " + " | ".join(pct(v, 2) for v in tot) + f" | **{100 * dT:+.2f}** |")
L.append("")
out["T2_ex_rebuild"] = {"rows": rows_t2, "taker_total": dict(zip(SUBS, tot)), "delta_taker_S3_S1a": dT}

L.append("## T3 Driver indicators (A1: non-halted anchors, excluding rebuild anchors)")
L.append("| indicator | " + " | ".join(SUBS) + " |")
L.append("|---|" + "---:|" * len(SUBS))
a1 = A["subperiods_non_halted_ex_rebuild"]
for key, lab, f in (("first_attempt_5022_rate", "first-attempt −5022 plans / plans", lambda v: pct(v)),
                    ("RI_over_MI", "rejected intent / maker intent (RI/MI)", lambda v: f"{v:.3f}"),
                    ("IOC_FR_over_RI", "from_reject IOC notional / rejected intent", lambda v: f"{v:.3f}"),
                    ("MI_over_D", "maker intent / D", lambda v: f"{v:.3f}"),
                    ("pooled_maker_fill_ratio", "maker-flag maker fills / maker intent", lambda v: f"{v:.3f}")):
    L.append(f"| {lab} | " + " | ".join(("—" if a1[s][key] is None else f(a1[s][key])) for s in SUBS) + " |")
for k, lab in (("skipped_no_chase_arm", "no-chase gap: skipped_no_chase_arm residual / MI"),
               ("skipped_min_notional", "residual below floor / MI"), ("sent", "from_partial residual sent / MI")):
    L.append(f"| {lab} | " + " | ".join(("—" if a1[s]['resid_pool_over_MI'].get(k) is None else f"{a1[s]['resid_pool_over_MI'][k]:.4f}") for s in SUBS) + " |")
L.append("| median target notional per name (USDT) | " + " | ".join(str(P['subperiods'][s]['median_target_notional_per_name']) for s in SUBS) + " |")
L.append("| gross_mult values | " + " | ".join(str(P['subperiods'][s]['gross_mult_values']) for s in SUBS) + " |")
L.append("")

# factorisation S2a(ex-rebuild) -> S3(ex-rebuild), log-share allocation
s0, s1 = a1["S2a"], a1["S3"]
ratios = {"reject_pool RI/MI": s1["RI_over_MI"] / s0["RI_over_MI"], "IOC conversion IOC/RI": s1["IOC_FR_over_RI"] / s0["IOC_FR_over_RI"],
          "intent per fill MI/D": s1["MI_over_D"] / s0["MI_over_D"]}
lnsum = sum(math.log(v) for v in ratios.values())
dshare = s1["share_FR"] - s0["share_FR"]
alloc = {k: dshare * math.log(v) / lnsum for k, v in ratios.items()}
out["T4_factorisation_S2a_to_S3_ex_rebuild"] = {"share_FR_S2a": s0["share_FR"], "share_FR_S3": s1["share_FR"], "ratios": ratios,
                                                 "pp_allocation": alloc}
L.append("## T4 from_reject IOC share: factorisation S2a → S3 (non-halted, ex-rebuild; log-share allocation)")
L.append(f"share_FR {pct(s0['share_FR'], 2)}% → {pct(s1['share_FR'], 2)}% (Δ {100 * dshare:+.2f} pp)")
L.append("| factor | ratio S3/S2a | allocated pp |")
L.append("|---|---:|---:|")
for k in ratios:
    L.append(f"| {k} | {ratios[k]:.3f} | {100 * alloc[k]:+.2f} |")
L.append("")

cf = A["counterfactual_direct_arm"]
L.append("## T5 Requote direct arm: counterfactual (A1, INFERRED)")
L.append("| slice | K2d share | RI_direct/D | attributable (c0 from S2a) | attributable (c0 from S1a) | bounds |")
L.append("|---|---:|---:|---:|---:|---|")
for k in ("S3:ex_rebuild", "S3:all", "S2b:ex_rebuild"):
    v = cf[k]
    L.append(f"| {k} | {pct(v['K2d_share'], 2)}% | {pct(v['RI_direct_over_D'], 2)}% | {pct(v['attributable_direct_share_c0_S2a'], 2)}% | "
             f"{pct(v['attributable_direct_share_c0_S1a'], 2)}% | [{pct(v['bounds_share'][0], 2)}, {pct(v['bounds_share'][1], 2)}]% |")
L.append(f"c0 (S2a ex-rebuild) = {cf['S3:ex_rebuild']['c0_S2a']:.4f}; c0' (S1a) = {cf['S3:ex_rebuild']['c0_S1a']:.4f}")
L.append("")

# attribution of the S1a -> S3 ex-rebuild drop
d_direct = cf["S3:ex_rebuild"]["attributable_direct_share_c0_S2a"]
fr_total = sum((ex["S3"]["component_share"][c] or 0) - (base["component_share"][c] or 0) for c in ("K2d", "K2q", "K2e", "K2n"))
att = {"requote direct arm (counterfactual c0 S2a)": d_direct,
       "other from_reject growth (reject pool, requote-arm and exempt IOC, net of pre-experiment K2n)": fr_total - d_direct,
       "chase arm, in-sample anchors (K3ci)": (ex["S3"]["component_share"]["K3ci"] or 0) - (base["component_share"]["K3ci"] or 0),
       "chase_forced neutrality fills (K3f)": (ex["S3"]["component_share"]["K3f"] or 0) - (base["component_share"]["K3f"] or 0)}
other = dT - sum(att.values())
att["all other components"] = other
Dpa = ex["S3"]["D"] / (ex["S3"]["n_anchors"] - ex["S3"]["n_halted"])
fee = {k: {"pp": v, "extra_fee_usdt_per_anchor": v * Dpa * 3e-4, "extra_fee_usdt_per_day": v * Dpa * 3e-4 * 6} for k, v in att.items()}
out["T6_attribution_S1a_to_S3_ex_rebuild"] = {"delta_taker": dT, "items": fee, "D_per_trading_anchor_S3": Dpa}
L.append("## T6 Attribution of the maker-share drop S1a → S3 (non-halted, ex-rebuild)")
L.append(f"Maker share {pct(1 - base['taker_share'])}% → {pct(1 - ex['S3']['taker_share'])}%; taker share Δ {100 * dT:+.2f} pp; "
         f"D per trading anchor in S3 = {Dpa:,.0f} USDT")
L.append("| item | pp of D | extra fee vs maker, USDT/anchor | USDT/day |")
L.append("|---|---:|---:|---:|")
for k, v in fee.items():
    L.append(f"| {k} | {100 * v['pp']:+.2f} | {v['extra_fee_usdt_per_anchor']:.2f} | {v['extra_fee_usdt_per_day']:.2f} |")
L.append("")
open(os.path.join(R, "x_cost_tables.md"), "w").write("\n".join(L) + "\n")
json.dump(out, open(os.path.join(R, "x_cost_attribution.json"), "w"), indent=1, ensure_ascii=False)
print("SUMMARY x_cost_render rc=0")
