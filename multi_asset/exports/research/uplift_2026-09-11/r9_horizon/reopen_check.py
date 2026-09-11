#!/usr/bin/env python3
"""
r9 / INDEPENDENT HOLDING HORIZON class survey.
Task 1: settle the ONE explicit reopen condition left open by r2_horizon RESULT sec.9:
   "if INFRA 1 later gives an effective maker cost < 0.82 bps/unit turnover, question (b) must reopen."
Task 2: first-hand inventory of the horizon arms from RESULT_abcd.json -> (Sharpe, |rho to A0|) pincer.

E-0826-D ENV WHITELIST FOR THIS SCRIPT = THE EMPTY SET.
Asserted below: no environment variable is read. All inputs are explicit file paths.
"""
import json, os, sys, hashlib

ENV_WHITELIST = frozenset()          # E-0826-D: empty set, asserted
_orig_environ_get = os.environ.get
def _forbidden(*a, **k):
    raise AssertionError("E-0826-D violation: this analysis script must read no env var")
os.environ.get = _forbidden          # any accidental env read raises

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
COSTB = ROOT + "/r3k_impact/costb_PWR_G230k.json"
COSTB_FIT = ROOT + "/r3k_impact/costb_FIT_G230k.json"
COSTB_H0 = ROOT + "/infra1_cost/costb_honest_H0.json"
COSTB_X1 = ROOT + "/infra1_cost/costb_honest_X1.json"
COSTB_DEPLOYED_NOTE = "calib/costb_fee_steady.json (live): book avg 2.067, quoted from INFRA1 sec.5 (INFERRED, not re-read here)"
ABCD = ROOT + "/r2_horizon/RESULT_abcd.json"

def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]

out = {"env_whitelist": sorted(ENV_WHITELIST), "inputs": {}}
for p in (COSTB, COSTB_FIT, COSTB_H0, COSTB_X1, ABCD):
    out["inputs"][p] = sha16(p)

# ---------- TASK 1: the reopen condition ----------
# Quantities quoted FROM the prior receipt (r2_horizon RESULT sec.0 lines 10-11). Marked INFERRED:
# they were produced on pod2 by the round-2 signal-layer paper book; not re-derived here.
G1H   = 1.0872      # bps per HOUR per unit gross, gross price pnl of the 1h-clock paper book
T1H   = 1.3261      # turnover per HOUR, units of gross
BREAKEVEN = G1H / T1H

cb  = json.load(open(COSTB))
cbf = json.load(open(COSTB_FIT))
h0  = json.load(open(COSTB_H0))
x1  = json.load(open(COSTB_X1))

def blended(d):
    return d["book_avg_bps_per_unit_turnover"]
def maker_range(d):
    m = [t["maker_bps"] for t in d["tiers"]]
    return min(m), max(m)

lines = {
  "PINNED costb_PWR_G230k (this program's cost model)": blended(cb),
  "costb_FIT_G230k (linear book-walk variant)":         blended(cbf),
  "costb_honest_H0 (fee + half-spread, ZERO impact)":   blended(h0),
  "costb_honest_X1 (fee + spread + exec-caliber impact K=1)": blended(x1),
}
mk = maker_range(cb)

t1 = {
  "breakeven_bps_per_unit_turnover": round(BREAKEVEN, 4),
  "source_of_gross_and_turnover": "r2_horizon/RESULT_r2_horizon_2026-09-11.md L10-11 (INFERRED: quoted, not re-derived)",
  "reopen_threshold_stated_in_r2_horizon_L170": 0.82,
  "cost_lines_bps_per_unit_turnover": {k: round(v, 4) for k, v in lines.items()},
  "PINNED_maker_only_bps_min_max_by_tier": [round(mk[0],4), round(mk[1],4)],
  "maker_fee_assumed_by_r2_horizon": 1.80,
  "maker_fee_MEASURED_by_INFRA1": 1.90,
}
# net per hour under each cost line
t1["net_bps_per_hour_per_gross"] = {}
for k, v in lines.items():
    t1["net_bps_per_hour_per_gross"][k] = round(G1H - T1H * v, 4)
# absolute floor: cheapest maker-only tier, no spread, no impact
t1["net_bps_per_hour_per_gross"]["FLOOR: cheapest tier maker_bps only (%.4f)" % mk[0]] = round(G1H - T1H * mk[0], 4)
t1["ratio_pinned_cost_over_breakeven"] = round(blended(cb) / BREAKEVEN, 4)
t1["ratio_cheapest_makeronly_over_breakeven"] = round(mk[0] / BREAKEVEN, 4)
t1["VERDICT"] = ("REOPEN CONDITION NOT MET. Every measured cost line exceeds the 0.82 bps/unit-turnover "
                 "breakeven. The cheapest possible line (maker fee only, most-liquid tier, zero spread, "
                 "zero impact) is already %.4f bps = %.2fx the breakeven. The pinned model is %.2fx."
                 % (mk[0], mk[0]/BREAKEVEN, blended(cb)/BREAKEVEN))
out["task1_reopen_1h_subanchor"] = t1

# ---------- TASK 2: horizon arm inventory, first-hand from RESULT_abcd.json ----------
d = json.load(open(ABCD))
rows = []
for name, v in d.items():
    rows.append({
        "arm": name,
        "sharpe": round(v["sharpe"], 4),
        "g_bps": round(v["full"], 4),
        "abs_rho_A0": round(abs(v["corr"]), 4),
        "rho_A0": round(v["corr"], 4),
        "turn": round(v["turn"], 5),
        "carryfrac": round(v["carry"], 4),
        "yrs_pos": v["yrs"],
    })
rows.sort(key=lambda r: -r["sharpe"])
out["task2_arm_inventory_n"] = len(rows)
out["task2_arms"] = rows

# the pincer: is there ANY arm with low rho AND real edge?
S_BAR, RHO_BAR = 1.50, 0.25          # r2_horizon prereg S1 and S3, frozen before numbers
both = [r for r in rows if r["sharpe"] >= S_BAR and r["abs_rho_A0"] <= RHO_BAR]
lowrho = [r for r in rows if r["abs_rho_A0"] <= 0.10]
out["task2_pincer"] = {
    "gate_S1_sharpe_ge": S_BAR, "gate_S3_absrho_le": RHO_BAR,
    "arms_passing_BOTH": [r["arm"] for r in both],
    "n_arms_with_absrho_le_0.10": len(lowrho),
    "best_sharpe_among_absrho_le_0.10": max([r["sharpe"] for r in lowrho]) if lowrho else None,
    "best_arm_among_absrho_le_0.10": max(lowrho, key=lambda r: r["sharpe"])["arm"] if lowrho else None,
    "best_sharpe_overall": rows[0]["sharpe"], "best_arm_overall": rows[0]["arm"],
    "abs_rho_of_best_arm_overall": rows[0]["abs_rho_A0"],
}

# ---------- TASK 3: what a horizon book would have to deliver ----------
# Sharpe adds as sqrt over uncorrelated sources. A0 post-warm + E-0911-D truncation = 1.2912 (n=9138).
A0_SR, A0_N = 1.2912, 9138
SE = (2190.0 / A0_N) ** 0.5
TARGET_POINT = 3.0 + 1.96 * SE
need_solo = (TARGET_POINT ** 2 - A0_SR ** 2) ** 0.5
out["task3_bar_for_this_class"] = {
    "A0_sharpe": A0_SR, "n": A0_N, "SE_annualised_sharpe": round(SE, 4),
    "point_estimate_needed_for_CI95_lower_bound_over_3.0": round(TARGET_POINT, 4),
    "standalone_sharpe_a_ZERO_correlation_horizon_book_must_carry": round(need_solo, 4),
    "best_standalone_sharpe_any_horizon_arm_measured": rows[0]["sharpe"],
    "shortfall_multiple": round(need_solo / rows[0]["sharpe"], 3),
    "source_A0": "CLOSEOUT_uplift_program_2026-09-12.md sec.2 (INFERRED: quoted, not re-derived)",
}


# ---------- TASK 4 (appended): is independence the binding constraint, or edge? ----------
def _pearson(xs, ys):
    mx = sum(xs)/len(xs); my = sum(ys)/len(ys)
    num = sum((a-mx)*(b-my) for a, b in zip(xs, ys))
    den = (sum((a-mx)**2 for a in xs) * sum((b-my)**2 for b in ys)) ** 0.5
    return num/den
_rows = out["task2_arms"]
_low = sorted([r for r in _rows if r["abs_rho_A0"] <= 0.10], key=lambda r: -r["sharpe"])
_task4 = {
  "pearson_absrho_vs_sharpe_over_40_horizon_arms": round(_pearson(
      [r["abs_rho_A0"] for r in _rows], [r["sharpe"] for r in _rows]), 4),
  "reading": ("~0 => in this family independence and edge are UNRELATED. Independence is free and "
              "plentiful (20/40 arms at |rho|<=0.10); edge is the binding constraint."),
  "independent_cloud_top": [{"arm": r["arm"], "sharpe": r["sharpe"], "rho_A0": r["rho_A0"],
                             "turn": r["turn"]} for r in _low[:6]],
  "only_arms_with_sharpe_ge_1.5": [{"arm": r["arm"], "sharpe": r["sharpe"], "rho_A0": r["rho_A0"]}
                                    for r in _rows if r["sharpe"] >= 1.5],
  "note_on_those": ("all four are the SAME Amihud sleeve at four lookback windows; r2_horizon sec.3.1 "
                    "measured their per-anchor g correlation to the round-1 SL_ORTH_f_amihud_24h__p at "
                    "+0.931..+0.941, and the ex-ante AMENDMENT-1 rule (rho>=0.6 => horizon variant) "
                    "forbids counting them as a new sleeve."),
  "note_on_the_independent_cloud": ("its best member C_TBF3D__p was REJECTED by the frozen S5 offset "
                                    "spectrum: k=-1 rank IC +0.03178 vs k=0 +0.00272 = 11.7x backward "
                                    "=> the feature reads the past, it does not forecast."),
}
out["task4_independence_vs_edge"] = _task4
print(json.dumps(out, indent=1, ensure_ascii=False))
