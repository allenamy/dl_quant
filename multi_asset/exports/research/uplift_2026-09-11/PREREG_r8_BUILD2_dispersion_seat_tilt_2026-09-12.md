> **创建:** 2026-09-12 | **Session:** b9646a9e (round 8, BUILD 2) | **状态:** FROZEN BEFORE ANY NUMBER | **作废条件:** 若 GATE P 不逐位通过, 或 pinned caliber 变更

# PREREG — BUILD 2: condition the leg weight on the one mechanism-identified dispersion relationship

## 0. Why this is not a closed axis (explicit)
- NOT gross timing (refuted 3x, 396 variants, OOS mean dSharpe -0.0502, 1-sided 95% UB -0.0398): gross is
  untouched. The book's L1 is renormalised to 1.0 at every anchor exactly as in A0; only the *composition*
  of the cross-sectional score changes.
- NOT regime-conditional FORM on binary labels (in-sample oracle earns 0.09 Sharpe LESS than on permuted
  labels): no label, binary or otherwise, is used. The conditioning variable is a contemporaneous
  cross-sectional state (funding dispersion), not a realised outcome.
- NOT the leg-weight LOOKBACK (msharpe_look=900 receipted optimal, plateau [380,1200]): LOOK stays 900.
- What IS untested: the msharpe seat weights on TRAILING realised leg Sharpe over 900 anchors. Round 7
  measured corr(sigma_fund, w3_fund) = -0.0361 and decile-1 w3_fund = 0.683 -> the seat does not
  de-weight the fund leg when the fuel is gone; it weights it slightly MORE. The tilt is a
  contemporaneous correction to a lagging seat.

## 1. Pinned caliber (inherited, unchanged)
CAL=log, CRYPTO m1 mask, MEMBERS_TOPN=829, LEGS=101, PHI=0.45, LOOK=900, WRULE=msharpe, FTRIM=zero,
SLOW_NPY=SLOW_v3_on_v4axis.npy, FPRED=f10_A0_s{seed}.npy.
COST = fitted /workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json (sha 295b4e7b462373e4).
GATE P runs at the ARCHIVE cost (health_check/calib/costb_fee_steady.json) because that is what the
archived A0 artifacts were produced at.
Reading rule E-0911-A: drop first LOOK=900 anchors. Coverage ceiling E-0911-D: cut at 2026-08-30 20:00Z
for every PHI>0 arm. Post-warm n = 9138 to that cut.
Metric: g = net_ex / gross_total, bps per 4h anchor per unit gross (book layer, executor caliber).

## 2. Device
/workspace/uplift_2026-09-11/r8b2/w10_sleeve_tilt.py, sha256 7dd6324acd361081...
= pinned w10_sleeve.py (sha b88e35a46b93d712) + {TILT, TILT_TAU, TILT_K, TILT_LO, TILT_HI}, all unset =>
bitwise-unchanged rec AND W. Built by r8b2/mk_tilt.py from the pinned source; diff is 5 hunks.

## 3. The construction (smallest parameterisation)
At each anchor, AFTER the msharpe seat returns w3 = (w_king, w_rev24, w_fund):
    w_fund <- w_fund * f(sigma_i);  w3 <- w3 / sum(w3)   [LEGS=101 => the freed weight goes to king]
sigma_i = 1e4 * population sd (ddof=0) of the finite 8h-equivalent SETTLED funding rates
rn8 = f_fund_now * 8 / f_fund_iv over the SAME masked member set the book ranks at anchor i.
f_fund_now[j] is the last settled rate at or before the anchor (pod_panel_ext.py L153-155) => strictly
causal, no lookahead. Definition copied from r7f1/r7_sigma2.py "LIVE" variant.
tau = 4.75 bp is INHERITED from round 7's profiled step threshold. It is NOT a free parameter of this
round; it was selected in-sample by round 7 and that is recorded as a hole.

## 4. DECLARED ARM GRID — K = 9. Frozen. No arm may be added after any number is seen.
f monotone non-decreasing in sigma in every arm.
  Family S (step):  f = TILT_K  if sigma < 4.75 else 1.0
      S00 TILT_K=0.00   S25 TILT_K=0.25   S50 TILT_K=0.50   S75 TILT_K=0.75
  Family R (ramp, floored):  f = clip(sigma/4.75, TILT_K, 1.0)
      R00 TILT_K=0.00   R25 TILT_K=0.25   R50 TILT_K=0.50
  Family P (power, active at every sigma):  f = clip((sigma/4.75)**TILT_K, 0.25, 2.0)
      P05 TILT_K=0.50   P10 TILT_K=1.00
Bonferroni: alpha = 0.05/9 = 0.005556 => two-sided 99.44% day-block bootstrap CI for the primary gate.
Seeds: the full grid runs at s42. The single best arm (by primary metric) is replicated at s2027.
Seeds are replication, not additional hypotheses; they do not enter K.

## 5. The three deciding tests (frozen)
Let d_i = g_tilt,i - g_A0,i, paired on identical anchors, same cost, post-warm, cut 2026-08-30 20Z.
(a) WITHIN-YEAR. Primary. Year fixed effects: theta = unweighted mean over calendar years of the
    per-year mean(d). PASS requires theta > 0 with the Bonferroni-corrected (99.44%) day-block
    bootstrap CI excluding zero, AND >= 4 of the 5 years with mean(d) > 0.
(b) HELD OUT. Fit TILT_K on anchors <= 2026-08-10 20Z (the pinned state cut) by maximising in-sample
    theta within each family; predict mean(d) on 2026-08-11..08-30 20Z (n=120) and report the
    realisation. PASS requires the realised mean(d) to have the predicted sign.
(c) GIVEBACK. mean(d) on 2026-08-19 00Z .. 2026-08-21 20Z (n=18), where A0 read Sharpe -29.61.
    PASS requires mean(d) >= 0 (must not make the giveback worse; XIB_LAG50 read -5.690 here and died).
Additional non-negotiables:
(d) TURNOVER-MATCHED NULLS. The winning arm must beat SHIFT101 / SHIFT503 / SHIFT1009 of the sigma
    series and 3 circular rotations (ROT1-3), all of which preserve the tilt's per-anchor multiplier
    distribution and lag-1 persistence exactly (hence its turnover), and destroy time alignment.
    Both pnl_ex (gross) and g (net) reported for every null.
(e) COST OF THE TILT. Report leg-reweighting turnover at the fitted cost and the alpha given up in
    sigma >= 4.75 (the regimes where the fund leg is the winner).
Failing (a), (b) or (c) = the construction fails. No post-hoc variant rescue. Every arm run is reported.

## 6. Pre-registered structural risk (written BEFORE any arm was run)
Measured coverage of the tilt-active region (VERIFIED, sigma_variants.npz LIVE gauge x A0_PWR230k_s42
post-warm to the cut): n(sigma<4.75) by year = 2022:730/1110, 2023:1596/2190, 2024:1747/2196,
2025:521/2190, 2026:66/1452. HELD-OUT window 2026-08-11..08-30 20Z: 3 of 120 anchors below 4.75.
GIVEBACK window: 2 of 18. Therefore families S and R are near-inert in exactly the two windows that
tests (b) and (c) interrogate, and those tests will have almost no power for them. Family P was declared
in this same grid specifically because it is active at every sigma. This is stated up front so that a
near-zero (b)/(c) reading for S/R is reported as LOW POWER, not as a pass.
