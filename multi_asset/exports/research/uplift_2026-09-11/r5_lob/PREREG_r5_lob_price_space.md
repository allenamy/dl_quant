# PREREG — R5 NEW DATA 4: the ORDER BOOK IN PRICE SPACE (not depth level, not depth shape)
Frozen 2026-09-11 BEFORE any arm number was computed. Device w10_sleeve.py sha b88e35a46b93d712.
GATE P: PASS bitwise 4/4 (rec + W) vs archived V4_A0_{dyn,fix}_s{42,2027} — GATE_P_receipt.json.

## 0. WHAT ROUND 2 ALREADY TESTED (read from its own code, not its report)
/workspace/uplift_2026-09-11/build_lob.py      -> LOBIMB1(+-1%), LOBIMB5(+-5%), LOBSLOPE(log S5/S1), LOBDEPTH(log S1), LOBIMB1D
/workspace/uplift_2026-09-11/r2/build_lob2.py  -> LDVOL, LIVOL, LSLASY, LDTREND, LCONVX, LDINNOV, LIMBINN, LDVOLR, _R1MEAN
So the brief.s list of "untested" candidates is WRONG on three of four counts:
  convexity / near-to-far ratio / how fast depth falls away  -> TESTED (LCONVX, LOBSLOPE, LSLASY)
  bid-vs-ask asymmetry at matched distances                  -> TESTED (LOBIMB1, LOBIMB5, LSLASY, LIMBINN)
  time dynamics of depth                                     -> TESTED (LDVOL, LDVOLR, LDTREND, LDINNOV); only
                                                                replenishment-conditional-on-a-trade is untested
  microprice / depth-weighted mid vs trade price             -> GENUINELY UNTESTED. This prereg.
I will NOT re-run any of the tested ones.

## 1. THE HOLE, AND WHY IT IS A HOLE
r2/build_lob2.py line 2 states: "Only lnot is used (ldep = lnot - log(price), redundant)."
That sentence is the reason half of the dataset was never searched, and it is false as a research claim:
ldep is redundant for QUANTITY features, but lnot - ldep IS the depth-weighted price of the cumulative book
out to each band. Round 2 therefore threw away the entire PRICE-SPACE half of the order book.
Exact inversion (log1p is undone exactly, so no 1/Q bias that would masquerade as an illiquidity proxy):
   p_band = log(expm1(lnot_band)) - log(expm1(ldep_band))

## 2. MECHANISM (stated before measurement)
Quantity-space depth says HOW MUCH patient liquidity is resting. Price-space says WHERE it is resting.
The two dissociate: doubling every resting order changes depth level (and Amihud) and leaves every feature
below exactly unchanged. That scale-invariance is the mechanical reason these cannot be Amihud re-spelled.
  BTILT  = mean[ m1 - m5 ],  m_k = (p_bid_k + p_ask_k)/2.  Bid mass packed nearer the mid than ask mass
           lifts the near book.s centre of mass relative to the far book.s => excess patient DEMAND.
  PSKEW  = mean[ 2(m1-m5)/(p1a-p1b) ] — the same tilt normalised by the near book.s own price width.
  PCURVA = mean[ (p5a-p1a) - (p1b-p5b) ] — how much farther ask mass extends when the window widens 1%->5%;
           high = patient supply is reluctant to stand near => positive expected return.
  BLEAD  = d4h(book price centre) - realised 4h trade return. The only feature that joins the two data
           sources: when the resting book reprices further than trades did, patient liquidity led.
Mechanism-predicted sign is POSITIVE (arm __p) for all four. The __m mirror is declared and counted in K.

## 3. WHAT IS DELIBERATELY EXCLUDED
The +-0.2% touch bands (idx 5,6) exist only from 2026-01 (verified, diag2.py: every sampled symbol reads
0.00 finite through 2025-12 and 1.00 from 2026-04). Any arm built on them would live inside one regime cell.
Excluded — and this is why r3k fitted the cost constant on "2026 anchors" only.

## 4. K AND THE BAR — DECLARED BEFORE LOOKING
K = 16 = {BTILT, PSKEW, PCURVA, BLEAD} x {RAW, ORTH-vs-fund-rank} x {__p, __m}.
Bonferroni 95%/16: lower bound at percentile 100*(0.05/16)/2 = 0.15625.
ADMIT requires ALL of:
  (a) standalone Sharpe >= 1.5 on the COMMON span (all arms + A0 live, identical anchors);
  (b) |rho| <= 0.25 to A0 AND to the ORTH_amihud sleeve, on per-anchor g over the COMMON span;
  (c) BONF16 CI95 lower bound on g > 0 (UTC-day block bootstrap 2000, rng default_rng([20260905,k]));
  (d) beats all four turnover-matched nulls (SHIFT101/SHIFT503/SHIFT1009/RELAB), on pnl_ex AND g;
  (e) tail concentration no worse than the live fund-leg control (top20 share 11.09%, ex-top20 Sharpe +6.71).
Cost model: the FITTED /workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json (sha 295b4e7b462373e4).
Statistic g = net_ex/gross_total, bps per anchor per unit gross.
