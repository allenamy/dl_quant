#!/usr/bin/env python3
"""r11 STEP 5 — RECONCILE the realized cost against the pinned model, and REPRICE.

CALIBER NOTE THAT CHANGES THE ANSWER (verified first-hand on pod2 from the arm artifact
/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz, device w10_sleeve.py sha b88e35a46b93d712):
  the replay's weights are NOT normalised to gross 1 — mean gross_total = 0.69565.
  COLS[17] 'turnover' is the RAW sum |dw| (mean 0.03032); COLS[21] 'cost_ex' divided by gross_total
  is what enters g (0.16747 bps). Turnover in the SAME per-unit-gross caliber as g is
      turnover / gross_total = 0.05402,  NOT 0.03032.
  Dividing a per-unit-gross cost by a raw turnover mixes two calibers by a factor 1/0.69565 = 1.4375.
  Independent check: cost(col4)/gross_total / (turnover/gross_total) = 0.16266/0.05402 = 3.011 bps
  per unit turnover, which reproduces the pinned model's book average 2.9537 to 1.9%. The matched
  pair reproduces the model; the mismatched pair does not.

ENV WHITELIST: {} (empty) — asserted (E-0826-D).
"""
import json, os
import numpy as np

_FORBID = ("CAL","JUDGE","PANEL","EXPORT_PANEL","EMA_STATE_JSON","W10_","POD_","DLW_","KING_","SEAT_","UMASK")
assert not sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID)), "ENV WHITELIST VIOLATION"

OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_costtruth/out"
dec = json.load(open(f"{OUT}/r11_decisive.json"))
fee = json.load(open(f"{OUT}/r11_fee_side.json"))

# ---- VERIFIED replay constants (read from the arm artifact, not from a receipt field) ----
GROSS_TOTAL = 0.69565          # mean gross_total, A0_PWR230k_s42, post-warm
TURN_RAW    = 0.03032          # COLS[17] mean
TURN_PER_G  = 0.05402          # turnover / gross_total  <- the caliber that matches g
COST_EX_G   = 0.16747          # cost_ex / gross_total, bps per anchor per unit gross
MODEL_RATE  = 2.9537           # costb_PWR_G230k book_avg_bps_per_unit_turnover, sha 295b4e7b462373e4
A0_G, A0_SR, A0_N = 0.6342, 1.2912, 9138
ANCHORS_YR, GROSS_MULT = 2190.0, 2.0

fee_bps = fee["fee_bps"]                       # 2.7847, BNB-converted (E-0911-C)
adv_60  = -dec["confound"]["60"]["markout"]     # cost sign
adv_ss  = -dec["plateau_mean"]                  # steady state, +5m..+4h

print("=" * 92); print("A. REALIZED COST PER UNIT TRADED (one side), live fills 2026-08-01..09-11"); print("=" * 92)
for lbl, adv in (("using the desk's recorded +60s proxy", adv_60), ("using the STEADY-STATE plateau (+5m..+4h)", adv_ss)):
    print(f"  {lbl}")
    print(f"    fee (BNB-converted)      {fee_bps:8.4f} bps")
    print(f"    adverse selection        {adv:8.4f} bps")
    print(f"    ALL-IN                   {fee_bps+adv:8.4f} bps   vs pinned model {MODEL_RATE:.4f}"
          f"   ratio {(fee_bps+adv)/MODEL_RATE:.4f}x   gap {fee_bps+adv-MODEL_RATE:+.4f}")
print()

print("=" * 92); print("B. REPRICING A0 — the two turnover calibers, side by side"); print("=" * 92)
rows = []
for lbl, adv in (("60s proxy (what the critic priced)", adv_60), ("STEADY STATE (this measurement)", adv_ss)):
    gap = fee_bps + adv - MODEL_RATE
    ratio = (fee_bps + adv) / MODEL_RATE
    for tlbl, turn in (("WRONG caliber: raw turnover 0.03032", TURN_RAW),
                       ("CORRECT: turnover/gross_total 0.05402", TURN_PER_G)):
        d = gap * turn
        g2 = A0_G - d
        sr2 = A0_SR * g2 / A0_G
        nav = d * ANCHORS_YR * GROSS_MULT / 100.0
        rows.append((lbl, tlbl, gap, d, g2, sr2, nav))
        print(f"  {lbl:<34} | {tlbl:<38}")
        print(f"      gap {gap:+7.4f} bps/unit traded -> dg {d:+7.4f} bps/anchor -> "
              f"mean g {g2:+7.4f}  Sharpe {sr2:6.4f}  NAV/yr lost {nav:5.2f} %")
    # ratio method cross-check (independent of any turnover number)
    d_ratio = COST_EX_G * (ratio - 1.0)
    print(f"      [ratio cross-check, no turnover used: cost_ex {COST_EX_G} x ({ratio:.4f}-1) = "
          f"{d_ratio:+.4f} bps/anchor -> g {A0_G-d_ratio:+.4f}, Sharpe {A0_SR*(A0_G-d_ratio)/A0_G:.4f}]")
    print()

gap_ss = fee_bps + adv_ss - MODEL_RATE
ratio_ss = (fee_bps + adv_ss) / MODEL_RATE
D_ADD = gap_ss * TURN_PER_G
D_RAT = COST_EX_G * (ratio_ss - 1.0)
D_USE = float(np.mean([D_ADD, D_RAT]))
G_NEW = A0_G - D_USE; SR_NEW = A0_SR * G_NEW / A0_G
SE_SR = np.sqrt(2190.0 / A0_N)
print("=" * 92); print("C. HEADLINE REPRICED PLANNING NUMBER"); print("=" * 92)
print(f"  additive (correct turnover) dg = {D_ADD:+.4f} ; ratio method dg = {D_RAT:+.4f} ; used = {D_USE:+.4f}")
print(f"  A0 mean g   {A0_G:.4f}  ->  {G_NEW:.4f} bps/anchor/unit gross   ({(1-G_NEW/A0_G)*100:.1f}% haircut)")
print(f"  A0 Sharpe   {A0_SR:.4f}  ->  {SR_NEW:.4f}   (SE(annualised Sharpe) = sqrt(2190/{A0_N}) = {SE_SR:.4f})")
print(f"  Sharpe in SE units: {SR_NEW/SE_SR:.3f}  -> {'INDISTINGUISHABLE FROM ZERO' if SR_NEW < 2*SE_SR else 'still > 2 SE'}")
print(f"  NAV/yr at {GROSS_MULT}x gross: lost {D_USE*ANCHORS_YR*GROSS_MULT/100:.2f} %/yr; "
      f"remaining {G_NEW*ANCHORS_YR*GROSS_MULT/100:.2f} %/yr (was {A0_G*ANCHORS_YR*GROSS_MULT/100:.2f} %/yr)")
print()

print("=" * 92); print("D. CANDIDATES WHOSE COST-SURVIVAL MARGIN THE REPRICING FLIPS"); print("=" * 92)
print("   (cost scales by the ratio; arms are listed with their OWN receipted gross/cost/turnover)")
CAND = [
    ("A0 (incumbent)",        None,      COST_EX_G, A0_G + COST_EX_G, TURN_PER_G),
    ("TSMOM_DIR",             "r10",     0.42736,   0.81814,          0.14330),
    ("VRP_DELTA1",            "r10",     0.18757,   0.27711,          0.06292),
    ("SLOW_CLOCK",            "r10",     0.63750,   0.36590,          None),
    ("COINT_PAIR",            "r10",     0.39430,   0.26100,          None),
    ("CMUM_CARRY",            "r10",     1.30520,   0.26040,          0.05400),
    ("REV_SHORT",             "r9",      3.86830,   1.15850,          1.31780),
]
print(f"   {'arm':<20} {'gross':>8} {'cost@model':>11} {'net@model':>10} | {'cost@real':>10} {'net@real':>10}  verdict")
FLIP = []
for nm, src, cost, gross, turn in CAND:
    net0 = gross - cost
    cost1 = cost * ratio_ss
    net1 = gross - cost1
    verd = ("FLIPS: survived -> dead" if (net0 > 0 and net1 <= 0) else
            ("still alive" if net1 > 0 else "was already dead, deeper"))
    if net0 > 0 and net1 <= 0: FLIP.append(nm)
    print(f"   {nm:<20} {gross:>8.4f} {cost:>11.4f} {net0:>10.4f} | {cost1:>10.4f} {net1:>10.4f}  {verd}")
print(f"\n   FLIPPED BY THE REPRICING: {FLIP if FLIP else 'none'}")
print()

print("=" * 92); print("E. FEE SIDE — the actionable number"); print("=" * 92)
print(f"  account tier (inferred from exact realized USDT rates): {fee['inferred_tier']} "
      f"(maker {fee['tier_schedule'][0]:.2f} / taker {fee['tier_schedule'][1]:.2f} bps)")
print(f"  BNB coverage, share of NOTIONAL : {fee['bnb_notional_share']*100:.2f} %   "
      f"(row-count share {fee['bnb_rowcount_share']*100:.2f} %)")
print(f"  realized all-in fee/unit traded : {fee['fee_bps']:.4f} bps")
print(f"  full BNB coverage would save    : {fee['full_bnb_saving_bps_per_unit_traded']:.4f} bps/unit traded")
sav = fee["full_bnb_saving_bps_per_unit_traded"]
dg_sav = sav * TURN_PER_G
print(f"    -> dg  +{dg_sav:.4f} bps/anchor/unit gross")
print(f"    -> NAV +{dg_sav*ANCHORS_YR*GROSS_MULT/100:.3f} %/yr at {GROSS_MULT}x gross")
print(f"    -> recovers {dg_sav/D_USE*100:.1f} % of the cost-repricing haircut")

json.dump(dict(fee_bps=fee_bps, adv_60=adv_60, adv_steady=adv_ss,
               allin_60=fee_bps+adv_60, allin_steady=fee_bps+adv_ss,
               model_rate=MODEL_RATE, ratio_60=(fee_bps+adv_60)/MODEL_RATE, ratio_steady=ratio_ss,
               gap_steady=gap_ss, turnover_raw=TURN_RAW, turnover_per_gross=TURN_PER_G,
               gross_total=GROSS_TOTAL, cost_ex_per_gross=COST_EX_G,
               dg_additive=D_ADD, dg_ratio=D_RAT, dg_used=D_USE,
               A0_g_repriced=G_NEW, A0_sharpe_repriced=SR_NEW, SE_sharpe=float(SE_SR),
               flipped=FLIP, bnb_saving_dg=dg_sav),
          open(f"{OUT}/r11_reprice.json", "w"), indent=1, default=float)
print(f"\nwrote {OUT}/r11_reprice.json")
