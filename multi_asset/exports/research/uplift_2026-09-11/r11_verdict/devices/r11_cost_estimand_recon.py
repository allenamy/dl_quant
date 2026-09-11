import os,json
os.environ.clear() if False else None
# ENV WHITELIST = EMPTY: this script reads no environment variable at all.
R={}
# --- the two instruments, as published -----------------------------------
MODEL      = 2.9537     # costb_PWR_G230k book_avg_bps_per_unit_turnover (recomputed sha 295b4e7b462373e4)
FEE_TB     = 2.399      # trackB combo-epoch fee, bps/unit traded
SLIP_TB    = -2.113     # trackB combo-epoch blended slippage vs ANCHOR MID (negative = book receives)
CASH_TB    = FEE_TB + SLIP_TB
FEE_R11    = 2.7847     # r11 whole-window BNB-converted fee
ADV60_R11  = 3.2026     # r11 balanced-panel 60s adverse selection
ADVSS_R11  = 6.7164     # r11 steady-state plateau
TURN_REPLAY= 0.05402702626085247   # recomputed first-hand from the pinned npz
TURN_LIVE  = 0.10864               # r11 cost receipt, live traded / gross
JUDGE1     = 0.2767                # r6 judge1: realised(fee+timing) - replay cost, bps/anchor
JUDGE1_CI  = [0.075, 0.653]

R["estimand_A_vs_decision_price"] = {
  "what_the_replay_needs": "fill price vs ANCHOR MID, plus fee  (device w10_sleeve.py L313 trade=sm-HB, L323 cbps, L324/L329 pnl_raw=sum(sm*y4[i]) marks anchor->anchor)",
  "trackB_measured_bps_per_unit_traded": round(CASH_TB,4),
  "model_charges": MODEL,
  "model_overcharge_bps_per_unit_traded": round(MODEL-CASH_TB,4),
}
R["estimand_B_vs_fill_price"] = {
  "what_r11_measured": "mid(fill+D) vs FILL PRICE, a post-fill path quantity",
  "fee_plus_adverse_60s": round(FEE_R11+ADV60_R11,4),
  "fee_plus_adverse_steady": round(FEE_R11+ADVSS_R11,4),
  "why_it_is_not_chargeable": "the interval [fill, fill+D] lies INSIDE [anchor_i, anchor_i+1]; the replay's own mark sm*y4[i] already carries that price path. Charging it again double-counts.",
}
# --- triangulation: does the corrected estimand reproduce judge1? ---------
over = MODEL - CASH_TB
R["triangulation"] = {
  "model_overcharge_bps_per_unit_traded": round(over,4),
  "x_LIVE_turnover_per_gross": round(over*TURN_LIVE,4),
  "judge1_measured_bps_per_anchor": JUDGE1,
  "judge1_CI95": JUDGE1_CI,
  "agreement_pct": round(100*abs(over*TURN_LIVE-JUDGE1)/JUDGE1,2),
  "x_REPLAY_turnover_per_gross": round(over*TURN_REPLAY,4),
  "reading": "using the LIVE turnover reproduces judge1 to ~5%; using the REPLAY turnover gives half, and the factor between them is exactly the 2.01x live/replay turnover gap. Two independent instruments reconcile once the turnover caliber is matched.",
}
# --- what the r11 repricing would have done, for contrast ----------------
GAP_SS = 6.547452
R["withdrawn_repricing"] = {
  "r11_delta_g_bps_per_anchor": 0.3625,
  "sign": "CHARGE (reduces g)",
  "corrected_delta_g_bps_per_anchor_on_replay_turnover": round(-over*TURN_REPLAY,4),
  "sign2": "CREDIT (raises g) - opposite sign",
  "spread_between_the_two_readings_bps_per_anchor": round(0.3625+over*TURN_REPLAY,4),
}
# --- planning number -----------------------------------------------------
A1X = {"mean_g":0.6602,"CI95":[0.1673,1.1472],"sharpe":1.2857,"n":9199}
A1X_S2027={"mean_g":0.6828,"CI95":[0.1911,1.1717],"sharpe":1.3288}
import math
R["planning_number"] = {
  "arm":"A1x_ext_s42 (v4-native, coverage ceiling CLOSED, upper bound 2026-09-10 00Z)",
  **A1X,
  "SE_sharpe": round(math.sqrt(2190/9199),4),
  "sharpe_in_SE_from_zero": round(A1X["sharpe"]/math.sqrt(2190/9199),3),
  "NAV_pct_yr_at_2x": round(A1X["mean_g"]*2190*2/100,3),
  "NAV_pct_yr_CI95_at_2x": [round(A1X["CI95"][0]*2190*2/100,2), round(A1X["CI95"][1]*2190*2/100,2)],
  "second_seed_s2027": A1X_S2027,
  "cost_repricing_applied": False,
}
# --- the class whose value scales with the cost wall ---------------------
lad = {"ZEROISH":(0.11506,0.01057),"PWR230k":(0.16817,0.01444),"PWR2300k":(0.30162,0.02307)}
xs=[v[0] for v in lad.values()]; ys=[v[1] for v in lad.values()]
sl=(ys[2]-ys[0])/(xs[2]-xs[0])
R["build1_cost_sensitivity"] = {
  "ladder_A0cost_to_marginal_dg": lad,
  "slope_dg_per_unit_A0cost": round(sl,5),
  "at_r11_repriced_wall_A0cost_0.5409": round(ys[0]+sl*(0.5409-xs[0]),5),
  "at_corrected_lower_wall": "moves DOWN toward the ZEROISH rung +0.01057",
  "reading": "BUILD 1 basis-in-book is the ONLY family whose value RISES with the cost wall (it reduces turnover -5.13%). Under the r11 repricing its marginal dg would have roughly tripled. Under the CORRECTED (cheaper) wall it shrinks. Closed harder, not reopened.",
}
R["trackB_prior_sensitivity"] = {
  "prereg_prior_quoted":"A0_dyn frozen-window cost_ex = 0.1201 bps/anchor/gross; cost-to-zero ceiling +0.120 < G2 resolution 0.23 => the pure cost channel cannot produce a measurable improvement",
  "under_r11_repricing_ceiling": round(0.1201*3.216695,4),
  "vs_G2_gate": 0.23,
  "would_have_reopened": 0.1201*3.216695 > 0.23,
  "under_corrected_cheaper_wall": "ceiling SHRINKS below 0.120 => axis stays closed, more firmly",
}
print(json.dumps(R,indent=1))
json.dump(R,open('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_verdict/receipts/RECEIPT_r11_cost_estimand_reconciliation.json','w'),indent=1)
