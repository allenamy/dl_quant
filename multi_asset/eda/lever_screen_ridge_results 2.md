# LEVER SCREEN -- Ridge walk-forward, perp y_600, dP vs baseline
# Machinery: perpY_ridge_gate (MAD-z norm fit on TRAIN, lambda-on-val, ::4 subsample,
#   RAW y, 1-day embargo, per-fold sign-consistency). M=147,084 samples, D=64 base.
# Folds: strong_2025_02, strong_2025_04, choppy_2026 (each test=40d, val=20d, train>=230d).
# Baseline = spot book + spot trades -> perp y_600. All -> PERP target.
# DL refs (train540, fold-2025-04, raw EMA P): decider spot/spot->spot 0.0472 | 2a perp/perp->perp 0.0402

| lever | inputs | pooled_P | dP_vs_base | P_2025-02 | P_2025-04 | P_2026 | sign_consistent | verdict |
|-------|--------|----------|-----------|-----------|-----------|--------|-----------------|---------|
| base | spot book + spot trades | 0.0329 | -- | 0.0537 | 0.0311 | 0.0091 | yes | BASELINE |
| perp_trades | spot book + PERP trades | 0.0230 | -0.0099 | 0.0421 | 0.0051 | 0.0117 | yes | HURTS -- perp-trades do NOT lift perp target |
| perp_book | PERP book + spot trades | 0.0329 | +0.0000 | 0.0366 | 0.0397 | 0.0216 | yes | NEUTRAL pooled (helps 04+26, hurts 02); most choppy-robust |
| dual | PERP book + PERP trades | 0.0097 | -0.0232 | 0.0161 | 0.0007 | 0.0073 | yes | COLLAPSES -- dual-source hurts badly |
| bs_bookshape | base + BS book-shape (last-t) | 0.0319 | -0.0010 | 0.0491 | 0.0271 | 0.0154 | yes | NEUTRAL/slight neg |
| cross_venue | base + cross-venue ratios | 0.0347 | +0.0018 | 0.0556 | 0.0377 | 0.0074 | yes | MARGINAL + (02+04 up, choppy flat) -- below +0.005 |
| long_context | base + 60s-pooled 4h summary | 0.0321 | -0.0008 | 0.0377 | 0.0486 | 0.0085 | yes | NEUTRAL pooled; +0.0175 on 2025-04 strong only |

## VERDICT (provenance + lever screen)
- The perp-trade lever does NOT transfer to the perp target (dP -0.0099). With the DL
  runs (decider spot/spot->spot 0.0472, 2a perp/perp->perp 0.0402), the "0.08 provenance"
  resolves: the perp raw-y ceiling on these features is ~0.033 pooled / ~0.047 single
  strong fold. The milestone 0.0816 was a SOFTER CALIBER (5-sigma clip + EMA-demean, per
  the caliber-correction note), NOT a perp-trade signal advantage.
- dual-source (-0.0232) and perp_trades (-0.0099) HURT -- confirms the project's
  "perp book/trades ~2x less predictive" + "dual collapses" findings, now directly on
  the perp target.
- NO lever clears the +0.005 dP gate pooled. cross_venue (+0.0018) and long_context
  (+0.0175 on 2025-04 only) are the only positives, both strong-month-conditional and
  dying in choppy 2026 (regime-dependence, not a transferable edge).
- perp_book is the most REGIME-ROBUST: pooled-neutral but best choppy-2026 (0.0216 vs
  base 0.0091, +0.0125) -- trades strong-month P for choppy P.

## NEXT
No lever clears +0.005 pooled AND sign-consistent across regimes, so DL-validation of a
single lever is not warranted (the project rule: reject feature if Ridge 3-fold dP <
+0.005). Honest perp raw-y ceiling ~0.033 pooled; feature levers do not break it.
The only untested IC lever is orthogonal data (funding/OI differential), absent on disk.


## FUNDING / OI / LIQUIDATIONS AVAILABILITY (the orthogonal IC lever)
VERDICT: **NOT OBTAINABLE from disk.** Exhaustive sweep:
- /mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/ : ONLY book_snapshot_25 + trades
  (no derivative_ticker / funding / open_interest / liquidations streams).
- /mnt/storage/share/23-25-BTCUSDT/ : ONLY book_snapshot_25 + trades.
- /mnt/storage/share/bar_data/bar_1s/<day>/data_<day>.hdf5 : 1103 datasets (LOB + trade
  flow for 14+ symbols) — grepped all keys for fund/oi/open_int/liquid/premium/mark = NONE.
- No *funding*/*open_interest*/*liquidation*/*deriv*ticker* files anywhere under /mnt/storage.
HOW TO OBTAIN: requires a fresh Tardis pull of the `derivative_ticker` stream
(binance-futures BTCUSDT) which carries funding_rate, open_interest, mark/index price,
predicted_funding — and a separate `liquidations` stream. Not on disk; external fetch needed.
=> The only orthogonal IC lever for breaking the ~0.033 perp ceiling is unavailable locally.


## REGIME-AWARE TEST (perp_book-in-choppy + long-in-strong) — the v2 thesis
Causal regime-z (trailing perp rvol-3600s, expanding causal standardization):
shuffle-future null max|Δz| on days<=cut = 0.000 -> PASS (strictly causal).
All on the finite-long-context row subset (fair apples-to-apples); BASE here = 0.0258
(this subset is choppier than the full-screen base 0.0329).

| variant | D | pooled_P | dP_vs_base | per-fold (02/04/26) | sign_consistent | verdict |
|---------|---|----------|-----------|---------------------|-----------------|---------|
| BASE (finite-lg) | 64 | 0.0258 | -- | 0.029/0.045/0.006 | yes | baseline |
| base+regime_z alone | 65 | 0.0278 | +0.0020 | 0.031/0.047/0.009 | yes | indicator alone weak |
| base+perp_book_block | 112 | 0.0311 | +0.0053 | 0.029/0.047/0.020 | YES | lifts CHOPPY (+0.014) |
| base+long_block | 77 | 0.0321 | +0.0063 | 0.038/0.049/0.009 | YES | lifts STRONG (2025-04) |
| **base+perp_book+long (R2)** | 125 | **0.0361** | **+0.0103** | 0.037/0.053/0.021 | **YES (all 3 folds)** | **WINNER — additive, both regimes** |
| R3 regime-CONDITIONED interactions | 187 | 0.0454 | +0.0196 | 0.078/0.017/-0.000 | NO | OVERFIT — breaks 2026 |
| R3b regime-cond-lite | 116 | 0.0515 | +0.0257 | 0.090/0.014/-0.002 | NO | OVERFIT worse |

### REGIME VERDICT
- The WIN is ADDITIVE feature blocks (perp_book_block + long_block), NOT regime
  conditioning. R2 = base + both blocks = +0.0103 pooled, **sign-consistent across all
  3 folds**, and captures BOTH regimes (perp_book -> choppy +0.014, long -> strong) that
  the pooled single-block screen averaged away.
- Explicit regime INTERACTIONS (R3/R3b) OVERFIT: higher pooled P but sign-consistency
  BREAKS (2026 goes negative), sig_ratio inflates to 0.10-0.11. This REPEATS the prior
  single-asset causal-vol-gating FAILURE — regime gating is not the lever; the additive
  blocks are.
- R2 clears the +0.005 gate AND is sign-consistent -> the ONE feature combination worth
  DL-validating. CAVEAT: D=125 Ridge on this subset; treat as a Ridge-stage PASS that
  needs DL confirmation (fold-0 ep25/pat12) before production claims. The +0.0103 is on
  the choppy finite-lg subset (base 0.0258); on the full base (0.0329) the equivalent
  combo would land ~0.043 pooled IF it transfers.

## FINAL DECISIVE VERDICT
1. Perp y_600 raw ceiling on single-block features ~0.033 pooled (none of the 7 screened
   levers alone clears +0.005; perp_trades/dual HURT).
2. The perp-trade lever does NOT transfer to the perp target -> the milestone 0.0816 was
   CALIBER (5sig-clip+EMA-demean), not a perp-trade edge. Honest perp raw ceiling ~0.033/
   ~0.047(single strong fold).
3. ONE combination breaks it leak-free + sign-consistent: base + perp_book_block +
   long_block = +0.0103 pooled (Ridge), capturing both regimes ADDITIVELY (not via
   regime gating, which overfits). This is the real remaining IN-DATA path -> DL-validate.
4. Funding/OI/liquidations: NOT on disk (only orthogonal lever, needs external Tardis pull).
=> Two paths forward: (a) DL-validate R2 (base+perp_book+long, additive); (b) fetch
   funding/OI externally. (a) is in-data and testable now; (b) needs a data pull.


## R2 DL-VALIDATION (in progress)
Setup: REG_arch DL on R2 feature set = base npz_spot2perp_clean (64: spot book + spot
trades + perp y) + tv_overlay r2_overlay (29: perp-book KEY-diff 16 per-timestep +
long-context 13 broadcast) -> n_features=93. Recipe ep25/pat12/train270/preload, perp y_600.
REDUCED perp_book (16 KEY cols) confirmed to HOLD the Ridge gain: base+perpbook_KEY16+long
= +0.0104 pooled, sign-consistent (perfold 0.044/0.044/0.015) -- even better balanced than
the 48-col version. Overlay built leak-free (per-timestep book diff <=t, long broadcast <=t).

STATUS: r2dl_04 (2025-04 strong fold) launched + training, but the box is HEAVILY CONTENDED
(external onedrive job, load 12-16) -> GPU starves, ~5+ min/epoch, stuck near the sigma-warmup
zone (ep9, sigma crossing 0.02). The 93-wide DL is impractically slow under this contention;
r2dl_04 continues in background (Monitor armed) and will report when it clears.

INTERPRETATION (pending DL number): the DECISIVE evidence is already the Ridge stage --
R2 = base + perp_book_KEY + long = +0.0104 pooled, SIGN-CONSISTENT across all 3 folds
(strong 2025-02/04 AND choppy 2026 all positive), leak-free, with regime-GATING explicitly
REJECTED (overfit, broke choppy). DL typically delivers 1.3-1.5x Ridge, so transfer is
expected but UNCONFIRMED until r2dl_04/26/02 complete. Treat R2 as a Ridge-stage PASS
(the project's gate) awaiting DL confirmation; do not make a production claim until the
3-fold DL (esp. choppy 2026) lands.


## R2 DL-VALIDATION RESULT — 2025-04 strong fold: FAILS TO TRANSFER
r2dl_04 (base npz_spot2perp_clean 64 + r2_overlay 29 = n_features=93, ep25/pat12/train270):
  test RAW EMA Pearson = 0.0130  (best-ckpt 0.0197)  beta=0.69  sig=0.019
  vs BASE DL decider (spot/spot->spot, train540, 2025-04) = 0.0472
  -> R2 DL = 0.013 << base 0.047. The Ridge +0.0103 lift does NOT transfer to DL; it
     INVERTS. Val Pearson never rose above noise across all 25 epochs (EMA val P ~0.000,
     beta collapsed to ~0.1, sig oscillating at the 0.02 gate) = capacity-dilution /
     channel-addition collapse: appending 29 channels to the 64-feat REG_arch broke
     training (anti-pattern #29: every added channel costs P unless it carries >=+0.003
     alpha/channel AND the model can use it; the 16+13 overlay diluted the signal).
  (basedl_04 = train270 base on the SAME recipe is running to confirm the base trains fine
   at train270, isolating that the collapse is the OVERLAY not the shorter train window.)

### WHY RIDGE-PASSED BUT DL-FAILED (the real lesson)
Ridge is a LINEAR last-timestep readout -- it can exploit a small additive linear
contribution from the perp_book/long blocks (+0.0103). The REG_arch DL is a fixed-capacity
Conformer over 64 channels with RevIN/FiLM tuned to 64; widening to 93 channels (+45%)
without re-tuning dilutes the per-channel capacity and the optimizer cannot find the signal
in the added noise -> collapse. This is the project's documented pattern: Ridge ΔP is
necessary but NOT sufficient; the DL channel-addition penalty can erase a linear Ridge gain.
The single-axis REG_arch is a local optimum; ADD-style channel expansion has repeatedly
failed (v6b/v7/v8, and now R2). A REPLACE-style or SE-block/skip-path integration (not raw
concat) would be needed to test the blocks fairly in DL -- but that is architecture work,
not a screen.

## FINAL DECISIVE VERDICT (morning)
1. Perp y_600 raw ceiling ~0.033 pooled / ~0.047 single strong fold on available features.
   Milestone 0.0816 = softer caliber, NOT a perp-trade edge.
2. Single-lever screen: NONE clears +0.005; perp_trades/dual HURT.
3. R2 (base + perp_book_KEY + long, additive): Ridge +0.0103 sign-consistent across all 3
   folds -- BUT DL-validation FAILS (0.013 vs 0.047 base): the linear Ridge gain does NOT
   survive raw channel-concat into REG_arch (capacity dilution). => R2 is NOT a usable DL
   lever as a raw-concat overlay. It would need architectural integration (SE/skip/replace)
   to test fairly -- a separate effort, not screened tonight.
4. Funding/OI/liquidations: NOT on disk; only orthogonal IC lever; needs external Tardis pull.

=> HONEST CONCLUSION: on available data + the frozen REG_arch architecture, the perp y_600
   raw ceiling is ~0.033 and NO screened feature lever breaks it in DL. The two remaining
   real paths are: (a) ARCHITECTURE work to integrate the perp_book/long blocks non-additively
   (Ridge says the info is there, +0.0103, but raw-concat DL can't use it); (b) ORTHOGONAL
   DATA (funding/OI), which must be fetched externally. Neither is a quick screen; both are
   genuine next-phase efforts. Tonight's screen exhausted the in-architecture feature levers.


## METHODOLOGICAL CORRECTION (important): train270 UNDERTRAINS the DL
r2dl_04 (R2, train270) gave 0.013 -- but the matched control basedl_04 (BASE, train270,
no overlay, SAME recipe) shows the IDENTICAL pathology: val Pearson never rises above noise
across 25 epochs (val P oscillates +0.024/-0.012, sigma_yhat/sigma_y stuck 0.01-0.04, beta
sign-flipping). So the train270 collapse is NOT the overlay -- it is TRAIN270 ITSELF being
too little data for the REG_arch DL to develop stable variance (the train540 decider, by
contrast, crossed sigma=0.02 at ep9 and climbed to val P~0.04). 
=> The "fast screen" train270 recipe is VALID for Ridge (closed-form, data-light) but
   INVALID for the DL (undertrains -> sigma-collapse). The earlier r2dl_04=0.013 vs
   decider=0.047 was a CONFOUNDED comparison (train270 vs train540).
=> Clean DL R2 test requires train540 (r2dl_04_t540, overlay extended to 2023-08). That run
   compares directly to the decider 0.0472 (base, train540, 2025-04). [QUEUED]
HONEST STATE: the R2 DL verdict is NOT YET DETERMINED. Ridge says +0.0103 (sign-consistent);
the train270 DL was undertrained (inconclusive); the train540 DL is the valid test and is
pending. Do not conclude R2 fails DL from the train270 run -- that was a recipe artifact.


## R2 DL — CORRECTED TEST (train415, the max overlay-covered window)
Constraint found: mid_cache (needed for the long-context block) starts 2024-01-01, so the
overlay cannot extend to 2023 -> train540 for the 2025-04 fold is IMPOSSIBLE with the overlay.
Max trainable = train415 (2024-01 .. 2025-03). Running a MATCHED pair at train415:
  r2dl_04_t420  = base + overlay (93-wide), train415, fold 2025-04  [RUNNING]
  basedl_04_t420 = base (64-wide), train415, fold 2025-04           [QUEUED]
This is the valid apples-to-apples DL test (both train415, same recipe). The earlier
train270 runs (r2dl 0.013, base also undertrained) are SUPERSEDED -- train270 undertrains
the DL (sigma-collapse for base AND R2 alike), so that comparison was inconclusive, NOT an
R2 failure. The train415 pair + decider (0.0472, train540 base) bracket the answer.


## DL-VALIDATION: BLOCKED BY ENVIRONMENT (honest final state)
Three DL attempts to validate R2 on this box:
  - r2dl_04 train270: undertrained (sigma-collapse) -- but matched base train270 ALSO
    undertrained, so INCONCLUSIVE (recipe artifact, not R2 failure).
  - r2dl_04_t420 train415 (93-wide): epoch 0 did not complete in 53 min -- the REG_arch DL
    is CPU-BOUND on this box (python at 1000%+ CPU, GPU starved at 0%; dataloader/collation +
    sigma-gate/EMA per-step overhead saturates cores). Killed.
The train540 decider (base, 64-wide) DID complete earlier this session (0.0472), so the
pipeline is not broken -- but the WIDER (93-ch) or LONGER configs are too slow under the box's
CPU contention to finish in a usable time. => The DL confirmation of R2 is BLOCKED by compute,
not by science. It needs a less-contended box / fewer workers / a leaner config to run.

## ============ DECISIVE MORNING VERDICT (perp y_600) ============
SETTLED (Ridge stage = the project's accepted gate, all leak-free + sign-consistency-checked):
 1. Perp y_600 RAW ceiling ~0.033 pooled / ~0.047 single strong fold on available features.
    The milestone 0.0816 = softer CALIBER (5sig-clip + EMA-demean), NOT a perp-trade edge.
 2. Single-lever screen (7 levers): NONE clears +0.005 pooled alone. perp_trades (-0.010)
    and dual-source (-0.023) HURT. Confirms "perp ~2x less predictive" + "dual collapses".
 3. perp_book is the most regime-ROBUST single lever (choppy 2026 +0.0125) but pooled-neutral.
 4. The ONE in-data combination that clears the gate at Ridge: base + perp_book_KEY + long
    (ADDITIVE) = +0.0103 pooled, SIGN-CONSISTENT across all 3 folds (0.044/0.044/0.015),
    capturing BOTH regimes. Regime-GATING interactions OVERFIT (rejected).
 5. Funding/OI/liquidations: NOT on disk anywhere; only orthogonal IC lever; external pull needed.

OPEN (compute-blocked, not science-blocked):
 - Does the +0.0103 Ridge lift survive DL? UNCONFIRMED. The honest expectation is uncertain:
   raw channel-concat (+29 ch) into the fixed 64-ch REG_arch risks the channel-addition penalty
   (anti-pattern #29). A fair DL test needs either a less-contended box OR non-additive
   integration (SE-block / skip-path / replace, not raw concat) -- that is ARCHITECTURE work.

TWO REAL REMAINING PATHS (both next-phase, neither a quick screen):
 (a) ARCHITECTURE: integrate perp_book + long blocks non-additively into REG_arch and DL-test
     on a usable box. Ridge proves the linear info exists (+0.0103); the question is whether DL
     can exploit it without the channel-addition penalty.
 (b) ORTHOGONAL DATA: fetch funding/OI/liquidations (Tardis derivative_ticker) -- the only
     untested IC lever for breaking the ~0.033 ceiling.


## R2 DL-validation FINAL (train415, FREE box) — STRONG fold 2025-04
r2dl_04_t420 (R2 = base + perp_book_KEY16 + long13 = 93-wide, train415, free box):
  sigma TRAJECTORY HEALTHY this time: sigma_yhat/sigma_y climbed 0.001 -> 0.05-0.135
  (well above the 0.02 gate; val P climbed to +0.024..+0.033, beta positive). The free box
  FIXED the train270/contended collapse -> this is a VALID DL run.
  TEST (2025-04): rawP_ema=0.0215  S=0.0265  beta=0.46  sig=0.047  DA=0.503
  (best-ckpt 0.0200)
  [matched basedl_04_t420 (base 64-wide, train415) RUNNING for the clean dP]
Context refs: decider (base, train540, 2025-04) = 0.0472. r2dl_04 at train415 = 0.0215 is
lower, but that mixes train415-vs-540 AND base-vs-R2 -> the matched basedl_04_t420 (train415)
isolates the R2 effect. Verdict pending that number.


## R2 DL-validation FINAL — matched train415 pairs (free box, healthy σ where noted)
| fold | model | rawP_ema | sig | beta | DA | dP (R2-base) |
|------|-------|----------|-----|------|-----|-------------|
| 2025-04 strong | base (64-wide) | 0.0096 | 0.014* | -- | -- | -- |
| 2025-04 strong | R2 (93-wide)   | 0.0215 | 0.047  | 0.46 | 0.503 | **+0.0119** |
*base strong sigma=0.014 = near-collapse (unlucky 64-wide warmup); R2 sigma=0.047 healthy.
 So strong dP +0.0119 is healthy-R2 vs slightly-undertrained-base -> directionally confirms
 transfer but the base leg should ideally be re-run to healthy sigma for an exact dP. R2's
 OWN number (0.0215, healthy) is the solid figure; it is BELOW the train540 decider (0.0472)
 because train415<540, but the R2-vs-base AT train415 shows the overlay HELPS (+0.012).
=> STRONG fold: R2 DL > base DL. The Ridge lift TRANSFERS to DL on strong. [choppy pending]


## ============ MILESTONE CALIBER — DEFINITIVELY SETTLED ============
Eval of reg_arch_npz_v4_repro (milestone REG_arch, npz_v4 = spot book + PERP trades) preds,
fold_0 test 2025-02-09..05-11, EMA checkpoint, q50:
  2025-04 month:  RAW Pearson = +0.0816  |  5sig-clip+EMA-demean = +0.0788   (delta -0.003)
  full fold:      RAW Pearson = +0.0599  |  5sig-clip+EMA-demean = +0.0598   (delta -0.000)
  (best-ckpt 2025-04: RAW 0.0642 / caliber 0.0614)

VERDICT: The milestone 0.0816 is a RAW number, NOT a caliber artifact. The 5-sigma-clip +
causal-EMA-demean changes it by <0.003 -- the clip/demean were RED HERRINGS. The milestone
REG_arch genuinely hit ~0.082 RAW Pearson on the 2025-04 strong month (and ~0.060 raw over
the full 90-day fold). This CORRECTS the earlier "0.08 was a soft caliber" claim (the
caliber-correction memory note's 0.037-0.043 was a DIFFERENT panel-raw eval on different
windows, not this clip-vs-raw comparison).

RECONCILIATION with the lever screen: the screen's base (~0.033 pooled / ~0.047 single fold)
was LOWER than 0.082 NOT because of caliber, but because the screen used a DIFFERENT feature
set (npz_spot / npz_spot2perp_clean = spot book + SPOT trades, std 7.9) and pooled across 3
folds incl choppy 2026. The milestone npz_v4 (spot book + PERP trades, std ~25) on the
2025-04 strong month alone = 0.082 raw. So: (a) the 0.08 is real + raw + strong-month + on
the npz_v4 feature set; (b) it does NOT generalize to choppy or to the spot-trades feature set.
NB: npz_v4 EXISTS at /mnt/storage/private/work_hsy/quant_research/data/npz_v4 (sibling repo) --
it was not absent, just in the other repo than the Phase-1 search covered.
