#!/usr/bin/env python3
# r12 VERDICT device. Read-only. Recomputes every number carried in
# RESULT_r12_verdict_2026-09-12.md from the three upstream rounds' machine receipts.
#
# E-0826-D ENV WHITELIST: this device consumes ZERO environment variables.
# It is asserted below: no env key changes any branch. All inputs are absolute paths.
# Upstream env whitelists are read out of the upstream receipts and re-printed, not re-set.
import json, os, hashlib, sys

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
OUT  = f"{ROOT}/r12_verdict/receipts"

# ---- ENV ASSERTION (constraint 7) -------------------------------------------------
ENV_WHITELIST = []          # declared: empty
_FORBIDDEN = ["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ",
              "SLOW_NPY","FSEED","FPRED","COSTB_JSON","OUT_TAG","CEM_Q","CEM_MODE","BYP_STATE",
              "BYP_Q","BYP_A","SMA","SBAND","AUX12","JUDGE_HC","EXPORT_PANEL","EMA_STATE_JSON"]
_present = [k for k in _FORBIDDEN if k in os.environ]
assert not _present, f"device reads no env; these are set and must not be: {_present}"

def sha(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<20), b""): h.update(b)
    return h.hexdigest()

def J(p): return json.load(open(p))

IN = {
 "regime_table":   f"{ROOT}/r12_regime/receipts/RECEIPT_r12_regime_table.json",
 "regime_stage3":  f"{ROOT}/r12_regime/receipts/RECEIPT_r12_stage3_beta.json",
 "smooth_grid":    f"{ROOT}/r12_smoothing/receipts/RESULT_R12.json",
 "smooth_cond":    f"{ROOT}/r12_smoothing/receipts/RESULT_R12C.json",
 "smooth_lag":     f"{ROOT}/r12_smoothing/receipts/LAG12B.json",
 "smooth_bite":    f"{ROOT}/r12_smoothing/receipts/BITE12.json",
 "smooth_lev":     f"{ROOT}/r12_smoothing/receipts/LEV12.json",
 "smooth_g1":      f"{ROOT}/r12_smoothing/receipts/GATE_G1.json",
 "interv_batt":    f"{ROOT}/r12_intervene/receipts/BATTERY_r12.json",
 "interv_null":    f"{ROOT}/r12_intervene/receipts/NULLJUDGE.json",
 "interv_dec":     f"{ROOT}/r12_intervene/receipts/DECISIVE.json",
 "interv_env":     f"{ROOT}/r12_intervene/receipts/RUN_ENV_r12.json",
 "r11_ladder":     f"{ROOT}/r11_verdict/receipts/RECEIPT_r11_verdict_arith.json",
}
SH = {k: sha(v) for k,v in IN.items()}
D  = {k: J(v) for k,v in IN.items()}

R = {"device_env_whitelist": ENV_WHITELIST, "inputs_sha256": SH}

# ---- Q1: cells clearing 3.0 --------------------------------------------------------
cells = D["regime_table"]["cells"]
inc = {"n_cells": len(cells),
       "point_gt3": [(c["cell"], round(c["sharpe"],4), c["n"]) for c in cells if c["sharpe"]>3.0],
       "cilo_gt3":  [(c["cell"], round(c["sharpe_lo"],4)) for c in cells if c["sharpe_lo"]>3.0],
       "ci_g_excl0": sum(1 for c in cells if c["ci_lo"]>0),
       "neg_point": [(c["cell"], round(c["mean_g"],4)) for c in cells if c["mean_g"]<0],
       "se_ge_085": sum(1 for c in cells if c["sharpe_se"]>=0.85)}
R["Q1_incumbent_regime_round"] = inc

G = D["smooth_grid"]
keys = list(G["S_a010_b25e4_s42"]["regime"].keys())
def count(cell):
    reg = G[cell]["regime"]
    p3 = [k for k in keys if reg[k]["sharpe"]>3.0]
    c3 = [k for k in keys if reg[k]["sharpe"]-1.96*reg[k]["se_sharpe"]>3.0]
    a  = G[cell]["alpha"]
    return {"n_cells":len(keys),"point_gt3":p3,"cilo_gt3":c3,
            "pooled_g":a["mean_g"],"pooled_sharpe":a["sharpe"],
            "pooled_ci":a["ci95_k0"],"turn_matched":a["turn_matched_meanratio"],
            "cost_over_gross":a["cost_over_gross"]}
R["Q1_sidebyside"] = {c: count(c) for c in
    ["S_a010_b25e4_s42","S_a010_b50e4_s42","S_a005_b25e4_s42","S_a030_b25e4_s42","S_a100_b00_s42"]}
R["Q1_percell"] = {k: {c: {"sharpe":G[c]["regime"][k]["sharpe"],
                           "lo":G[c]["regime"][k]["sharpe"]-1.96*G[c]["regime"][k]["se_sharpe"],
                           "n":G[c]["regime"][k]["n"]}
                       for c in ["S_a010_b25e4_s42","S_a005_b25e4_s42"]} for k in keys}

# ---- Q2: interventions ------------------------------------------------------------
B = D["interv_batt"]["arms"]
def arm(a):
    x = B[a]
    return {"dg":x["dg"], "ci95":x["dg_k0"]["ci95"], "bonf29":x["dg_k0"]["ci_bonf29"],
            "dturn_pct":x["dturn_frac_pct"], "fire_pct":x["fire_rate_pct"], "fire_n":x["fire_n"],
            "worst_2x":x["tail_2.0x"]["worst_day_pct"], "le4_per_yr":x["tail_2.0x"]["le4.00"]["per_yr"],
            "le4_n":x["tail_2.0x"]["le4.00"]["n"], "maxDD":x["tail_2.0x"]["maxDD_pct"],
            "le4_281":x["tail_2.81x"]["le4.00"]["per_yr"], "rho":x["rho_to_A0"],
            "by_year":x["by_year_dg"], "dpnl":x["dpnl"], "dcarry":x["dcarry"], "dcost":x["dcost"]}
R["Q2_arms"] = {a: arm(a) for a in ["R12_CEM_99_neutral_s42","R12_CEM_95_neutral_s42",
                "R12_ICO_L24_th0228_lam00","R12_BYP_either_90_a100_s42","R12_IAS_th200_phi00"]}
A0 = D["interv_batt"]["A0"]
R["Q2_A0"] = {k:A0[k] for k in A0 if not isinstance(A0[k],(dict,list))}
R["Q2_A0_tail"] = A0.get("tail_2.0x")
# marginal turnover: min over all 29 arms (the round-8 -5.13% did NOT replicate)
R["Q2_min_marginal_turnover_pct"] = min(B[a]["dturn_frac_pct"] for a in B)
R["Q2_n_arms"] = len(B)
R["Q2_nulls_CEM"] = D["interv_null"]["nulls"]["R12_CEM_99_neutral_s42"]
R["Q2_nulls_BYP"] = D["interv_null"]["nulls"]["R12_BYP_either_90_a100_s42"]
R["Q2_seed2"]     = D["interv_null"]["second_seed"]["R12_CEM_99_neutral"]

# state-conditional acceleration (smoothing round) + its repricing
C = D["smooth_cond"]
base_a = G["S_a010_b25e4_s42"]["alpha"]
MULT = D["interv_batt"]["reprice_multiple"] - 1.0
def reprice(a): return a["mean_g"] - MULT*a["cost_over_gross"]
gb = reprice(base_a)
R["Q2_altsurge"] = {}
for k in ["C_AS_med_a010","C_AS_fast_a010","C_AS_fast_a005"]:
    a = C[k]["alpha"]; t = C[k]["tail"]["live_vol"]
    R["Q2_altsurge"][k] = {
        "dg": a["dg_vs_deployed"], "ci95": a["dg_ci95_k0"], "p_ge0": a.get("dg_p_ge0_k0"),
        "turn": a["turn_matched_meanratio"],
        "dturn_pct": 100*(a["turn_matched_meanratio"]/base_a["turn_matched_meanratio"]-1),
        "worst_livevol": t["worst_day_pct"], "halt_per_yr_livevol": t["halt_per_yr"],
        "maxdd_livevol": t["maxdd_pct"],
        "dg_repriced": reprice(a)-gb}
R["Q2_altsurge_nulls"] = {k: C[k]["alpha"]["mean_g"]-base_a["mean_g"]
                          for k in ["C_NULL101_a010","C_NULL503_a010","C_NULL1009_a010"]}
R["Q2_reprice_corners"] = {c: reprice(G[c]["alpha"])-gb for c in
    ["S_a010_b50e4_s42","S_a005_b25e4_s42","S_a100_b00_s42","S_a030_b25e4_s42"]}
R["Q2_reprice_multiple"] = D["interv_batt"]["reprice_multiple"]

# ---- Q3: lag + drawdown-aware optimum ----------------------------------------------
L = D["smooth_lag"]; BI = D["smooth_bite"]
R["Q3_lag"] = {k: {"SMA":L[k]["SMA"],"SBAND":L[k]["SBAND"],
                   "b_over_a": (L[k]["SBAND"]/L[k]["SMA"]) if L[k]["SMA"] else None,
                   "eff_lag_anchors":L[k]["eff_lag_kernel_K60"],
                   "eff_lag_hours":4*L[k]["eff_lag_kernel_K60"],
                   "theory_noband":L[k]["theory_lag_truncK60_noband"],
                   "R2":L[k]["kernel_R2"],"phi_0":L[k]["phi_h"][0],"phi_30":L[k]["phi_terminal"],
                   "frozen_given_want":BI[k]["frac_member_names_frozen_given_want"]}
               for k in ["S_a010_b00_s42","S_a010_b25e4_s42","S_a010_b50e4_s42",
                         "S_a005_b25e4_s42","S_a005_b50e4_s42","S_a030_b25e4_s42","S_a100_b00_s42"]}
R["Q3_band_share_of_lag"] = (L["S_a010_b25e4_s42"]["eff_lag_kernel_K60"]
                             - L["S_a010_b00_s42"]["eff_lag_kernel_K60"])
R["Q3_deadzone_vs_meanw"] = {"b_over_alpha":base_a["deadzone_b_over_alpha"],
                             "mean_abs_w":base_a["mean_abs_w"],
                             "ratio":base_a["deadzone_b_over_alpha"]/base_a["mean_abs_w"]}
# lag cost in the two named states
R["Q3_named_states"] = {}
for st in ["POSTCRASH","BROADRALLY","POSTCRASH_NOT","BROADRALLY_NOT","ALTSURGE","DEEPNEG_SHORT"]:
    R["Q3_named_states"][st] = {c: {kk: G[c]["regime"][st][kk] for kk in
        ["n","mean_g","sharpe","pnl_over_gross","carry_over_gross","cost_over_gross","turn_matched"]}
        for c in ["S_a010_b25e4_s42","S_a100_b00_s42","S_a005_b25e4_s42","S_a010_b50e4_s42"]}
    d_ = G["S_a010_b25e4_s42"]["regime"][st]; i_ = G["S_a100_b00_s42"]["regime"][st]
    R["Q3_named_states"][st]["lag_gives_up_gross"] = d_["pnl_over_gross"]-i_["pnl_over_gross"]
    R["Q3_named_states"][st]["lag_buys_back_cost"] = i_["cost_over_gross"]-d_["cost_over_gross"]
    R["Q3_named_states"][st]["ratio"] = ((i_["cost_over_gross"]-d_["cost_over_gross"]) /
                                          abs(d_["pnl_over_gross"]-i_["pnl_over_gross"]))
# contour check: is b/alpha really the governing parameter?
cont = {}
for k,c in G.items():
    if k=="_meta": continue
    if c["SMA"]==0: continue
    ba = round(c["SBAND"]/c["SMA"],5)
    cont.setdefault(ba,[]).append((k, c["alpha"]["mean_g"]))
R["Q3_contour"] = {str(k): {"cells":v, "mean":sum(x[1] for x in v)/len(v),
                            "spread": (max(x[1] for x in v)-min(x[1] for x in v))}
                   for k,v in sorted(cont.items()) if len(v)>1}
# leverage feasibility
LV = D["smooth_lev"]
grid = [0.25+0.125*i for i in range(15)]
R["Q3_lev"] = {}
for k in ["S_a010_b25e4_s42","S_a010_b50e4_s42","S_a005_b25e4_s42"]:
    rows = LV[k]["rows"]
    rows = rows if isinstance(rows,list) else [rows[q] for q in sorted(rows,key=float)]
    R["Q3_lev"][k] = {"max_feasible_L":LV[k]["max_feasible_leverage"],
                      "cagr_at_L":LV[k]["median_1y_cagr_at_feasible_pct"],
                      "at_L": {f"{grid[i]:.3f}": rows[i] for i in range(len(rows))}}
R["Q3_tail_blocks"] = {k: G[k]["tail"] for k in
                       ["S_a010_b25e4_s42","S_a010_b50e4_s42","S_a005_b25e4_s42"]}

# ---- two-instrument reconciliation on tail risk -------------------------------------
r11 = D["r11_ladder"]
R["RECON_tailrisk"] = {
  "r11_n_utc_days": r11["n_utc_days"], "r11_n_anchors": r11["n_anchors"],
  "r11_2.00x": r11["leverage_table"]["A_pinned"]["2.00x"],
  "r11_1.25x_P": r11["leverage_table"]["A_pinned"]["1.25x"]["P_1y_maxDD_ge_25pct"],
  "r12smooth_2.00x_replay": G["S_a010_b25e4_s42"]["tail"]["replay"],
  "r12smooth_2.00x_livevol": G["S_a010_b25e4_s42"]["tail"]["live_vol"],
  "r12interv_2.00x": D["interv_dec"]["A0_leverage_ladder"]["2.00"],
  "note": ("r11 ladder is POST-WARM (1523 d) so it EXCLUDES 2022-06-07 -11.1714% and the 2022H1 "
           "drawdown; r12 uses W_TAIL (1673/1683 d). Both differences push the same way: r11 "
           "understates tail risk. Estimator also differs (bootstrap 1y windows vs 1323 "
           "overlapping path windows).")}
R["DECISIVE_ladder"] = D["interv_dec"]["A0_leverage_ladder"]
R["DECISIVE_matched"] = D["interv_dec"]["matched_cost_delever"]

# ---- gates ---------------------------------------------------------------------------
R["GATES"] = {"smooth_G1": D["smooth_g1"]["G1_a010_b250_aux0"],
              "smooth_G1b": D["smooth_g1"]["G1b_aux0_vs_aux1"],
              "interv_GATE_P2": D["interv_null"]["GATE_P2"],
              "regime_selfcheck": D["regime_table"]["selfcheck"],
              "regime_prereg_sha": D["regime_table"]["prereg_sha256"],
              "interv_prereg_sha": D["interv_batt"]["prereg_sha256"],
              "pinned_device_sha": D["interv_batt"]["pinned_sha256"]}
R["UPSTREAM_ENV_WHITELIST_interv"] = D["interv_env"]["env_whitelist"]
R["UPSTREAM_COMMON_ENV_interv"] = D["interv_env"]["common_env"]

# ---- receipt-vs-prose discrepancies found by this stage -------------------------------
R["DISCREPANCIES"] = {
  "halt_per_yr_prose_vs_receipt": {
     "DEEPNEG_MKT": {"receipt": [c["halt4_per_yr"] for c in cells if c["cell"].startswith("DEEPNEG_MKT")][0],
                     "prose_r12_regime": 6.12},
     "BREADTH_T1": {"receipt": [c["halt4_per_yr"] for c in cells if c["cell"]=="T1 narrowest"][0],
                    "prose_r12_regime": 3.49},
     "POSTCRASH":  {"receipt": [c["halt4_per_yr"] for c in cells if c["cell"].startswith("POSTCRASH")][0],
                    "prose_r12_regime": 3.56}},
  "empty_env_whitelist_fields": ["r12_intervene/receipts/BATTERY_r12.json",
                                 "r12_intervene/receipts/NULLJUDGE.json",
                                 "r12_intervene/receipts/DECISIVE.json",
                                 "r11_verdict/receipts/RECEIPT_r11_verdict_arith.json"],
  "note_env": ("the real whitelist for r12_intervene IS enumerated in RUN_ENV_r12.json; the "
               "BATTERY/NULLJUDGE/DECISIVE copies are unpopulated. r11's ladder receipt has none.")}

os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/RECEIPT_r12_verdict.json","w") as f:
    json.dump(R,f,indent=1,sort_keys=False)
me = os.path.abspath(__file__)
print("SELF_SHA256", sha(me))
print("OUT", f"{OUT}/RECEIPT_r12_verdict.json", sha(f"{OUT}/RECEIPT_r12_verdict.json"))
for k,v in SH.items(): print(f"  IN {k:16s} {v}")
print()
print("Q1 incumbent (regime instrument, 34 cells): point>3", len(inc["point_gt3"]), inc["point_gt3"],
      "| CIlo>3", len(inc["cilo_gt3"]))
for c,v in R["Q1_sidebyside"].items():
    print(f"Q1 {c:20s} point>3 {len(v['point_gt3'])} {v['point_gt3']}  CIlo>3 {len(v['cilo_gt3'])}  g {v['pooled_g']:+.4f} Sh {v['pooled_sharpe']:.4f}")
print()
print("Q2 min marginal turnover over", R["Q2_n_arms"], "arms:", round(R["Q2_min_marginal_turnover_pct"],4), "%")
print("Q2 ALTSURGE repriced:", {k:round(v["dg_repriced"],4) for k,v in R["Q2_altsurge"].items()})
print("Q2 corners repriced  :", {k:round(v,4) for k,v in R["Q2_reprice_corners"].items()})
print()
print("Q3 deployed eff lag", round(R["Q3_lag"]["S_a010_b25e4_s42"]["eff_lag_anchors"],3), "anchors =",
      round(R["Q3_lag"]["S_a010_b25e4_s42"]["eff_lag_hours"],1), "h; band adds",
      round(R["Q3_band_share_of_lag"],3))
print("Q3 deadzone/mean|w|", round(R["Q3_deadzone_vs_meanw"]["ratio"],4))
for k,v in R["Q3_contour"].items():
    print(f"Q3 contour b/a={k}: mean {v['mean']:+.4f} spread {v['spread']:.4f} n={len(v['cells'])}")
print()
print("RECON r11 days", R["RECON_tailrisk"]["r11_n_utc_days"], "P25@2.0x", R["RECON_tailrisk"]["r11_2.00x"]["P_1y_maxDD_ge_25pct"],
      "| r12 replay", R["RECON_tailrisk"]["r12smooth_2.00x_replay"]["p_1y_dd_ge25"],
      "| r12 livevol", R["RECON_tailrisk"]["r12smooth_2.00x_livevol"]["p_1y_dd_ge25"])
print("DONE")
