> **created:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **status:** FROZEN before the first number | **invalidated by:** STEP-1 gates failing (round stops), or any pinned input sha changing
> **branch:** research/book-uplift-2026-09-11 | **out:** multi_asset/exports/research/uplift_2026-09-11/r14_cleanbase/
> **LIVE ZERO-TOUCH:** ~/dl_quant_live and ~/wide_shadow are neither read nor written by any device in this round.

# PREREG r14 — rebuild the baseline without the dead-leg prefix, and measure what it changes

## §0 The object under test

`w10_sleeve.py` (sha `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`) silently
`np.nan_to_num`s the KING score (L219) and the F10 score (L267). When the underlying prediction file has
no finite value on an anchor, the leg contributes identically zero and NOTHING flags it. The archived
baseline A0 (`LEGS=101`, `SLOW_NPY=SLOW_v3_on_v4axis.npy`, `FPRED=f10_A0_s42.npy`) is claimed to be a
king-less book on 3300/9138 = 36.11% of W_ALPHA and an F10-less book on 1110/9138 = 12.15%, with 1110
anchors where both are dead and the replay is a single-leg fund-only book.

Every rho-to-baseline value in the programme — the evidence for its most-repeated claim, "~300 candidates
all failed because they are re-weightings of the same bet" — was computed against that baseline.

## §1 Caliber (pin v4, non-negotiable)

- `g = net_ex / gross_total`, bps per 4h anchor PER UNIT GROSS. Identity `net_ex = pnl_ex - carry_ex - cost_ex` (carry PAID).
- **W_ALPHA** = `rec[900:]` (E-0911-A) then `ts <= 2026-08-30 20:00Z` (E-0911-D) => n = 9138. Every mean/CI/Sharpe/turnover/rho/leg number.
- **W_TAIL** = same ceiling, NO warm drop => n = 10038. Every maxDD / worst-day / halt number.
- `Sharpe_ann = mean/sd(ddof=1)*sqrt(2190)`; `SE(Sharpe) = sqrt(2190/n)` using the n OF THE SAMPLE THE SHARPE IS ON.
- CI95 = UTC-day block bootstrap, B=2000, `numpy.default_rng([20260905,k])`, k declared per statistic (k=1 unless stated).
- Turnover caliber must be named on every turnover number: RAW `sum|dw|` vs MATCHED `E[t_i/g_i]`. Raw A0 = 0.03032, matched = 0.0540270, ratio 1.78189 (NOT 1/mean_gross_total).
- Bootstrap resolution on the frozen window is +/-0.23 bps/anchor. A point estimate below it is not a result.
- FORBIDDEN v3 lineage is NOT used by any device I write. **Disclosed and unavoidable:** the archived A0 arm
  itself is built on `SLOW_v3_on_v4axis.npy` and `f10_A0_s42.npy` (from `f8_ext`) — that is the defect under
  study, not a choice of mine. Every number in this round is therefore ABOUT a v3-lineage artifact, and is
  labelled so.

## §2 Sample definitions (frozen here)

- **FULL** = W_ALPHA, n = 9138. The sample every archived rho was computed on.
- **KING-DEAD** = anchors in FULL on which the king leg is identically zero.
- **CLEAN** = FULL \ KING-DEAD = the king-live anchors. This is the "clean sample" of the task.
- **F10-DEAD**, **BOTH-DEAD** defined the same way for the F10 leg / intersection.
- CLEAN is **ERA-SELECTED**. It is a contiguous suffix (2024 onward if the prefix claim reproduces). It is
  therefore a clean estimate of the book's behaviour IN THAT ERA and NOT a clean estimate of the
  cross-regime Sharpe. This sentence must appear in the RESULT next to every CLEAN number.

## §3 Leg-death definition (the measurement, stated before it is taken)

The device's own gate is `xz(v)`: `ok = isfinite(v); if ok.sum() >= 10: ... else all-NaN` -> `nan_to_num` -> 0.
So:
- **PRIMARY (source) instrument**: on anchor i with member set m (rebuilt exactly as the arm did:
  `MEMBERS_TOPN=829` from qvk, then `UMASK_SCOPE=m1` mask), the king leg is DEAD iff
  `isfinite(SLOW[i, m]).sum() < 10`. Same for F10 with `f10_A0_s42.npy`.
- **SECONDARY (archived-arm) instrument**: in the arm's own `rec`, `leg_king == 0.0` EXACTLY while
  `w3_king > 0` implies the leg's gross was < 1e-9 on that anchor, i.e. the leg was dead.
- **GATE D**: the two instruments must agree on every anchor of W_ALPHA where `w3_king > 0`. Report maxabs disagreement.

## §4 STEP-1 gates — if any FAILS, the round STOPS and reports the failure

| gate | statement | pass condition |
|---|---|---|
| G1 | `w10_sleeve.py` at the pinned sha contains `np.nan_to_num(xz(sc["king"]))` at L219 and `np.nan_to_num(xz(F10P[i, m]))` at L267 | literal text match, both lines |
| G2 | `SLOW_v3_on_v4axis.npy` has ZERO anchors with >=10 finite member values before 2024-01-01 00:00Z | count == 0 |
| G3 | counts on W_ALPHA | king-dead == 3300, F10-dead == 1110, both-dead == 1110 (exact) |
| G4 | conditional means on W_ALPHA | king-dead mean g == -0.3770 +/- 0.0010 and Sharpe == -1.1302 +/- 0.005; king-live mean g == +1.2058 +/- 0.0010 and Sharpe == +2.1508 +/- 0.005 |
| G5 | axis integrity | FULL is strictly 4h-monotone, n == 9138, span 2022-06-30T00Z .. 2026-08-30T20Z |
| G6 | A0 level parity | A0 mean g on FULL == +0.6341957 +/- 5e-6 and Sharpe == 1.2912234 +/- 5e-5 |

A FAIL on G2/G3/G4 means the whole round's premise does not reproduce -> STOP, report, no STEP 3/4/5.

## §5 Arms. K IS DECLARED HERE.

**K = 41 pre-registered measurement arms.** No arm is added after the first number is seen.

- **SET A — 14 candidate books with an archived per-anchor return series** (rho measured against A0 on FULL and on CLEAN):
  A1 TSMOM (TSMOM_L42_raw, r10 pre-declared primary) · A2 VRP (VRP_L42) · A3 CMUM (A_last) ·
  A4 SLOW (COMBO_G, book-layer equal-gross mean of 13 arms) · A5 COINT (MAIN) · A6 REVS (RAW_jump) ·
  A7 TSMOM_best (L90) · A8 CMUM_static · A9 CMUM_best · A10 SLOW_best (C_TBF3D) · A11 REVS_best (EMA a0.50) ·
  A12 XIB_LAG50 (r13A archived arm, `XIB_LAG50_s42__REAL.npz`) · A13 AMIHUD_SLEEVE (`P6_AMQ64_PWR_s42`) ·
  A14 T1_FORMB (r13B `g_primary`, the within-half beta overlay).
- **SET B — the 13 SLOW_CLOCK component arms** (B1..B13), included ONLY to widen the rho distribution in STEP 5.
- **SET C — 14 Amihud combination arms**: allocation a in {0.10,0.20,0.25,0.30,0.35,0.40,0.50} x seed in {42,2027},
  each as `g_comb = (1-a) g_A0 + a g_sleeve`, the exact two-portfolio object of `p6_combo.py`.

## §6 Thresholds. ALL FROZEN HERE, BEFORE ANY NUMBER.

**Classification bands (the programme's own 0.60 line, from `PREREG_r6_coverage_extension` §3.2 "rho>=0.60"):**
- `REWEIGHTING` : |rho| >= 0.60
- `PARTIAL`     : 0.30 <= |rho| < 0.60
- `INDEPENDENT` : |rho| < 0.30

**A classification CHANGES** iff the band of `rho_CLEAN` differs from the band of `rho_FULL`.

**A movement is MATERIAL** iff |rho_CLEAN - rho_FULL| >= 0.10 AND the paired block-bootstrap CI95 of
(rho_CLEAN - rho_FULL) excludes 0. (Paired: resample UTC days once, recompute rho on the resampled FULL and
on its CLEAN subset, difference. k=2.)

**STEP 4 — the Amihud headline.** The archived headline is `SR_gain_vs_A0` = +0.2458 at a=0.20, seed 42, on
p6's own window (n=9018). Recomputed here on FULL (n=9138) and on CLEAN.
- `SURVIVES` iff on CLEAN: ΔSharpe >= +0.1229 (half the archived value) AND block-bootstrap CI95 lower bound > 0 (k=3).
- `COLLAPSES` iff on CLEAN: ΔSharpe < +0.1229 OR CI95 contains 0.
- `REVERSES` iff on CLEAN: ΔSharpe <= 0.
- Reported for all 7 allocations x 2 seeds; the a=0.20 s42 cell is the PRIMARY, declared now.

**STEP 5 — the central claim "they were all re-weightings of the same bet".**
Let R_FULL / R_CLEAN = the number of SET A candidates in the REWEIGHTING band on each sample (out of 14).
- `CLAIM SURVIVES` iff R_CLEAN >= R_FULL AND median |rho|_CLEAN >= median |rho|_FULL - 0.10.
- `CLAIM WEAKENS` iff R_CLEAN < R_FULL OR median |rho|_CLEAN < median |rho|_FULL - 0.10.
- `CLAIM NEVER HELD` iff R_FULL <= 3 of 14 (i.e. the contaminated-baseline evidence itself does not
  concentrate the candidates at high rho). This branch is declared now precisely because it is a live
  possibility and must not be discovered and then rationalised.

## §7 Controls and their limits (declared now)

1. **Era confound is NOT removable on this artifact.** CLEAN is a contiguous suffix; the king leg does not
   exist earlier. Any rho move is `defect + era`, jointly. I will therefore ALSO report rho on KING-DEAD
   (the complementary subsample) and, if a king prediction file with pre-2024 coverage exists on pod2
   (`SLOW_v4.npy` is checked in STEP 1), report its coverage so a future round can separate the two.
   **I will not claim the defect caused a move that the era alone could explain.**
2. **Nulls.** This round adds no turnover and re-weights nothing; no SHIFT/RELAB null is informative for a
   correlation between two archived return series. The brief's null device path
   `r3_attack_b9646/null.py` is a pod2 path (`/workspace/uplift_2026-09-11/r3_attack_b9646`); its repo
   mirror is `r3_attack_RESID_SHARPE/null.py`. Recorded, not used.
3. **Cost planes differ between arms and this is NOT normalised away.** A0/AMIHUD are on the fitted plane
   (`costb_PWR_G230k.json`); XIB_LAG50 is on the deployed fee-only plane (`costb_fee_steady.json`). A cost
   plane shifts a series' mean and, weakly, its correlation. Every arm's plane is printed in the RESULT.

## §8 Devices, env, and receipts

- `devices/r14_pod_deadmask.py` — runs on pod2, READ-ONLY, produces the leg-death masks from source.
- `devices/r14_main.py` — runs on this Mac, produces every number.
- **ENV WHITELIST (E-0826-D) = EMPTY SET**, asserted in-file by both devices: the forbidden replay-env
  variable list is enumerated in the device and asserted absent from `os.environ`; `env_seen_at_runtime` is
  written into every receipt as an enumerated list.
- Every device asserts the sha256 of THIS prereg file before it runs, self-reports its own sha256, and
  writes both into its receipt.
- Every number is labelled VERIFIED (recomputed here) or INFERRED (reasoning).

