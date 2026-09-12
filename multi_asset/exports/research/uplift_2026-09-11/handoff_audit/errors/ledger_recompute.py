#!/usr/bin/env python3
"""ERROR LEDGER recompute device (handoff audit, 2026-09-12).
ENV WHITELIST = EMPTY SET (asserted below). Read-only. No GPU, no network, no live write.
Every number in ERROR_LEDGER_uplift_2026-09-12.md tagged [RECOMPUTED] comes from this file.
Inputs (all hashed into the receipt):
  r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz   the archived pinned A0 arm
  r3_placebo/MATCH_DIAGNOSTIC.json               the defective-placebo turnover/cost diagnostic
  r3k_impact/{costb_PWR_G230k.json,FITK_v3_shape.json,FITK_v2.json}
  trackA/w10_sleeve.py                           the pinned replay device
"""
import os, json, hashlib, datetime, sys
import numpy as np

_FORBID = [k for k in os.environ
           if k.split("_")[0] in ("CAL","LEGS","PHI","LOOK","SLOW","FPRED","COSTB","UMASK",
                                  "MEMBERS","WRULE","FTRIM","W3FIX","OUT","SLEEVE","KMOD")]
assert _FORBID == [], f"env whitelist is the empty set; found {_FORBID}"

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

ARM  = f"{ROOT}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
MD   = f"{ROOT}/r3_placebo/MATCH_DIAGNOSTIC.json"
CB   = f"{ROOT}/r3k_impact/costb_PWR_G230k.json"
F3   = f"{ROOT}/r3k_impact/FITK_v3_shape.json"
F2   = f"{ROOT}/r3k_impact/FITK_v2.json"
DEV  = f"{ROOT}/trackA/w10_sleeve.py"
out  = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)),
        "utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "env_whitelist": [], "gpu_used": False, "network_used": False, "live_written": False,
        "inputs_sha256": {p.split("/uplift_2026-09-11/")[1]: sha(p) for p in (ARM, MD, CB, F3, F2, DEV)}}

d = np.load(ARM, allow_pickle=True)
cols = [str(c) for c in d["cols"]]; rec = d["rec"]; i = {c: k for k, c in enumerate(cols)}
ts = rec[:, i["ts"]]
CEIL = int(datetime.datetime(2026, 8, 30, 20, tzinfo=datetime.timezone.utc).timestamp())
W_ALPHA = (np.arange(len(ts)) >= 900) & (ts <= CEIL)     # E-0911-A warm drop + E-0911-D ceiling
W_TAIL  = (ts <= CEIL)                                    # no warm drop
def utc(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d %HZ")
def SR(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190))

gA = rec[W_ALPHA, i["net_ex"]] / rec[W_ALPHA, i["gross_total"]]
gT = rec[W_TAIL,  i["net_ex"]] / rec[W_TAIL,  i["gross_total"]]
out["windows"] = {"axis_rows": int(len(ts)), "axis_first": utc(ts[0]), "axis_last": utc(ts[-1]),
                  "W_ALPHA_n": int(W_ALPHA.sum()), "W_TAIL_n": int(W_TAIL.sum()),
                  "W_ALPHA_first": utc(ts[W_ALPHA][0]), "W_ALPHA_last": utc(ts[W_ALPHA][-1])}
out["A0_levels"] = {"W_ALPHA_mean_g": float(gA.mean()), "W_ALPHA_sharpe": SR(gA),
                    "W_ALPHA_SE_sharpe": float(np.sqrt(2190 / W_ALPHA.sum())),
                    "W_TAIL_mean_g": float(gT.mean()), "W_TAIL_sharpe": SR(gT)}

# --- unit trap: three turnover calibers -------------------------------------------------
tu = rec[W_ALPHA, i["turnover"]]; gt = rec[W_ALPHA, i["gross_total"]]
raw = float(tu.mean()); rom = float(tu.mean() / gt.mean()); mor = float(np.mean(tu / gt))
out["turnover_calibers"] = {
    "raw_mean_sum_abs_dw": raw, "mean_gross_total": float(gt.mean()),
    "ratio_of_means_turnover_over_gross": rom, "ratio_of_means_over_raw": rom / raw,
    "mean_of_per_anchor_ratios": mor, "mean_of_ratios_over_raw": mor / raw,
    "note": "the caliber that matches g = net_ex/gross_total is the MEAN OF PER-ANCHOR RATIOS "
            "0.0540270; it is raw x 1.78214, NOT raw x 1.4375. 1.4375 = 1/mean(gross_total) "
            "produces 0.043579, a third number that appears nowhere in the programme.",
    "REV_SHORT_ratio_matched": 1.3178 / mor, "REV_SHORT_ratio_on_raw_0.03032": 1.3178 / raw,
    "REV_SHORT_ratio_on_raw_0.0335": 1.3178 / 0.0335}

# --- accounting identity: which sign does carry_ex carry? --------------------------------
plus  = rec[W_ALPHA, i["net_ex"]] - (rec[W_ALPHA, i["pnl_ex"]] + rec[W_ALPHA, i["carry_ex"]] - rec[W_ALPHA, i["cost_ex"]])
minus = rec[W_ALPHA, i["net_ex"]] - (rec[W_ALPHA, i["pnl_ex"]] - rec[W_ALPHA, i["carry_ex"]] - rec[W_ALPHA, i["cost_ex"]])
out["accounting_identity"] = {
    "net_ex_minus_(pnl_ex_PLUS_carry_ex_minus_cost_ex)_maxabs": float(np.abs(plus).max()),
    "net_ex_minus_(pnl_ex_MINUS_carry_ex_minus_cost_ex)_maxabs": float(np.abs(minus).max()),
    "verdict": "carry_ex is carry PAID and is SUBTRACTED. net_ex = pnl_ex - carry_ex - cost_ex holds "
               "bitwise (maxabs 0.0). Any audit that adds carry_ex reads a spurious -0.7279 residual."}

# --- the dead-leg prefixes, reproduced from the arm itself (no pod2 needed) ---------------
pref = {}
for n in (1110, 3300):
    a, b = gA[:n], gA[n:]
    pref[str(n)] = {"last_ts": utc(ts[W_ALPHA][n - 1]), "dead_mean_g": float(a.mean()), "dead_sharpe": SR(a),
                    "live_mean_g": float(b.mean()), "live_sharpe": SR(b), "share_of_W_ALPHA": n / int(W_ALPHA.sum())}
out["dead_leg_prefixes"] = pref
out["dead_leg_prefixes"]["reading"] = ("prefix 1110 = F10 leg identically zero (E-0911-D left edge, r9); "
    "prefix 3300 = king leg ALSO identically zero (r7-r9 block, pod2). 1110 = every W_ALPHA anchor in 2022; "
    "3300 = 2022 + 2023 exactly. Reproduces RECEIPT_r9_addendum (+0.1586/+0.7000/1.3741) and the "
    "r7_r9 pod2 recomputation (-0.3770/+1.2058/-1.1302/2.1508) from LOCAL data only.")

# --- per-year A0 with the desk's own SE rule ---------------------------------------------
yr = np.array([datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).year for t in ts[W_ALPHA]])
out["A0_by_year_W_ALPHA"] = {}
for y in sorted(set(yr.tolist())):
    s = gA[yr == y]; se = float(np.sqrt(2190 / len(s)))
    out["A0_by_year_W_ALPHA"][str(y)] = {"n": int(len(s)), "mean_g": float(s.mean()), "sharpe": SR(s),
                                         "SE_sharpe": se, "t": SR(s) / se,
                                         "ann_pct_of_gross": float(s.mean() * 2190 / 100)}

# --- defective per-anchor placebo: the real ratio range -----------------------------------
md = json.load(open(MD))
P = {k: v["fam"]["P"] for k, v in md.items() if "P" in v.get("fam", {})}
tr = sorted((round(v["turn_ratio"], 3), k) for k, v in P.items())
cr = sorted((round(v["cost_ratio"], 3), k) for k, v in P.items())
out["defective_placebo_ratios"] = {"n_arms": len(P),
    "turnover_ratio_min": tr[0], "turnover_ratio_max": tr[-1], "turnover_ratios": [list(x) for x in tr],
    "cost_ratio_min": cr[0], "cost_ratio_max": cr[-1],
    "claim_in_six_documents": "2.6-7.7x", "verdict": "WRONG AT BOTH ENDS on its own receipt"}

# --- cost model provenance ----------------------------------------------------------------
cb = json.load(open(CB)); f3 = json.load(open(F3)); f2 = json.load(open(F2))
out["cost_model_provenance"] = {
    "pinned_file_has_K_field": "K" in cb, "pinned_file_has_exponent_field": any("exp" in k for k in cb),
    "pinned_impact_bps_by_tier": cb["impact_bps_by_tier"],
    "FITK_v3_POWER_per_tier_excess": [f3["POWER"]["per_tier"][f"tier{t}"]["excess"] for t in (0, 1, 2)],
    "tiers_identical": cb["impact_bps_by_tier"] == [f3["POWER"]["per_tier"][f"tier{t}"]["excess"] for t in (0, 1, 2)],
    "FITK_v3_POWER_K_excess": f3["POWER"]["K_excess"], "FITK_v3_POWER_K_excess_CI95": f3["POWER"]["K_excess_CI95"],
    "FITK_v3_UNIF_K_excess": f3["UNIF"]["K_excess"],
    "FITK_v3_implied_alpha_1_over_p": f3["implied_impact_exponent_alpha_1_over_p"],
    "FITK_v3_p_exponent_turnwtd": f3["p_exponent_turnwtd"],
    "book_avg_bps_per_unit_turnover": cb["book_avg_bps_per_unit_turnover"],
    "verdict": "K=0.17 IS fitted (POWER branch, with a CI) and the pinned tier impacts are bitwise the "
               "POWER fit's per-tier excess. The documented exponent 0.87 is NOT this file's: it is "
               "FITK_v2's pooled log-vwap-on-log-participation alpha. This file's implied exponent is 0.7826."}
try:
    out["cost_model_provenance"]["FITK_v2_pooled_alpha"] = \
        f2["FINE2026_G230k"]["powerlaw_vwap_vs_participation"]["pooled"]["alpha"]
except Exception as e:
    out["cost_model_provenance"]["FITK_v2_pooled_alpha_lookup_error"] = repr(e)

# --- repricing sensitivity at the disputed 3.2167x ----------------------------------------
cost_ex = float(rec[W_ALPHA, i["cost_ex"]].mean()); g0 = float(gA.mean())
cx_per_gross = float(np.mean(rec[W_ALPHA, i["cost_ex"]] / gt))   # matched caliber, mean of per-anchor ratios
extra_rom = 2.2167 * cost_ex / float(gt.mean())                  # ratio-of-means variant (do not use)
extra = 2.2167 * cx_per_gross                                    # matched
out["repricing_3p2167"] = {"mean_cost_ex_bps_per_anchor_raw": cost_ex, "mean_gross_total": float(gt.mean()),
    "mean_cost_ex_over_gross_matched": cx_per_gross,
    "implied_rate_bps_per_unit_traded_matched": cx_per_gross / mor,
    "extra_cost_matched": extra, "extra_cost_ratio_of_means_variant": extra_rom,
    "extra_cost_via_gap_6.5475_x_matched_turnover": 6.5475 * mor,
    "A0_mean_g_repriced_matched": g0 - extra, "A0_sharpe_repriced_same_vol": SR(gA) * (g0 - extra) / g0,
    "note": "three routes to the same object land at 0.354-0.371 bps/anchor/unit gross, i.e. g 0.634 -> "
            "0.263-0.281 and Sharpe -> 0.54-0.57. The programme's own r11 device reports 0.2717 / 0.5532. "
            "The ratio-of-means variant (0.302) is the 1.4375 unit trap again and is 18% too small."}

print(json.dumps(out, indent=1, ensure_ascii=False))
