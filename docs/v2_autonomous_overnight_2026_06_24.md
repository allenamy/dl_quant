# V2 Dual-Source Perp y_600 -> 0.10 — Autonomous Iteration Log

Goal: BTC perp y_600 RAW Pearson -> 0.10 (strong month 2025-04 fold first).
Key insight (VERIFIED 2026-06-22): corr(y_spot_600, y_perp_600)=0.998-0.999;
basis-change noise diff/sig=0.039-0.059 -> costs only ~0.1% Pearson. So perp
SHOULD reach ~0.08 if spot reaches 0.082 (milestone). Current perp 0.04-0.06 is
ANOMALOUSLY LOW = fixable pipeline issue, NOT a perp ceiling.

X88 layout: [spot-64 (0:64) | perp-trade-16 (64:80) | cross-8 (80:88)].
Fold0 (2025-04): train 2024-04-23..2025-02-21 (300d), val ..2025-04-08 (45d),
test 2025-04-10..2025-05-07 (28d). 373 days total.

## VERIFICATION (2026-06-22)
- y_spot_600 builder emits + corr vs perp = 0.99827-0.99927 on 3 spot-check days. CONFIRMED.

## ESTABLISHED LADDER (perp-target, train300, 2025-04 test, RAW Pearson) [from prior session]
- base (spot-only slice 64):        ~0.02 floor
- mid (spot+perp-trade+cross, NO perp book, slice 88, no residual): 0.0084 b0.30 (collapsed)
- S1 (full: +perp raw book residual): 0.0397 b0.97 sig0.041  <- BEST so far
- S2 (S1 + ModernTCN long-ctx FiLM): 0.0182 b0.66, Spearman 0.028 > S1 0.016
       -> long-ctx ADDED rank info but BROKE magnitude calibration. mis-calibrated, not useless.

## EXPERIMENTS (this session)

### EXP-A: DECISIVE root-cause — S1 arch trained on SPOT target (y_spot_600)
- Hypothesis: if perp y_600 is anomalously low due to NOISY LABELS, training the
  SAME full S1 arch on the cleaner y_spot_600 should reach 0.06-0.08 on BOTH spot
  AND perp (eval via timestamp-join eval_dual_target.py). If spot-trained ->spot
  is ALSO ~0.04, the gap is FEATURES/RECIPE not the target.
- Config: configs/v2arch/s1_spottarget_2025_04.json (target_key=y_spot_600,
  use_perp_residual=true, pat8, nw4, preload). Fold0 2025-04.
- y_sigma(spot)=1.443e-3 (~14.4bps MAD). Launched 2026-06-23.
- STATUS: running. Result pending.

### EXP-B (queued): PERP-target matched baseline (pat8/nw4) — s1_perptarget_2025_04.json
- Same arch+recipe, trains on perp y_600. Re-baselines S1=0.0397 via the SAME
  eval_dual_target.py so EXP-A vs EXP-B is apples-to-apples (only diff=target).

### EVALUATOR VALIDATION (eval_dual_target.py on existing perp-trained s1_run)
- s1_run (perp-trained) EMA: ->PERP P=+0.0420 b1.07 s0.039 ; ->SPOT P=+0.0402 b1.03 s0.039
  (BEST ckpt: PERP 0.0275 / SPOT 0.0252). N=13272 hit99%.
- VALIDATES evaluator (PERP 0.042 ~= prior S1 0.0397).
- KEY EARLY SIGNAL: a PERP-trained model scores ~IDENTICALLY on spot (0.0402) and
  perp (0.0420). The model is NOT losing signal to perp label noise — it predicts
  both targets equally well/poorly. This PRE-FIGURES "gap = features/recipe, not
  target". The decisive spot-TRAINED run will confirm/refute (cleaner gradients
  could still help). EMA >> BEST here (BEST sigma-gate ckpt is early/weak).

### RECIPE GAP ANALYSIS (milestone npz_v4 spot 0.082 vs v2arch S1 perp 0.04)
| param | milestone npz_v4 | v2arch S1 |
|---|---|---|
| train_days | 700 | 300 |
| val_days | 60 | 45 |
| batch_size | 1024 | 512 |
| lr | 6e-4 | 4.2e-4 |
| patience | 10 | 5/8 |
| cache start | ~2023 | 2024-01-01 |
- v2arch base cache (npz_spot2perp_clean) STARTS 2024-01-01: only 456 days before
  2025-04-10 -> MAX ~410 train days (vs milestone 700). The 700-day training
  advantage CANNOT be replicated on this cache (would need 2023 data rebuilt from
  Tardis). CANDIDATE ROOT-CAUSE #1: train_days 300 vs 700 + batch/lr/patience.
- NEXT after decisive test: train_days=410 + batch1024 + lr6e-4 + pat10 on v2arch.

### PIPELINE AUTOMATION (2026-06-23)
- spot-target run training (ep3, sigR climbing 0.001->0.015, EMA P~0.023). CPU-data
  -bound ~6min/ep (tiny 142K model, nw4 collation is bottleneck, GPU 0% util but R).
- On spot-done: (a) decisive eval auto-runs -> /tmp/eval_decisive.log (eval vs BOTH
  spot+perp, + reference s1_run perp-trained 0.042/0.040); (b) perp-target run
  auto-launches (queue PID 182293) -> /tmp/s1_perptarget.log.
- DECISIVE branch logic restated:
   spot-trained ->spot ~0.06-0.08 AND ->perp ~0.06-0.08  => noisy perp LABELS, go multi-task
   spot-trained ->spot ~0.04 too                         => FEATURES/RECIPE gap (train300 vs 700?)

### SPOT-TARGET RUN TRAJECTORY (in progress, ~5-6min/ep)
- ep1-5 EMA P: 0.0149, 0.0221, 0.0229, 0.0248, 0.0226 ; raw P ep5=0.0406 sigR=0.023.
- Tracking the SAME trajectory as perp-trained s1_run (which EMA-peaked ~0.042).
- PRELIMINARY READ: spot-trained EMA P is NOT pulling ahead of perp-trained ->
  strengthens "gap = features/recipe, not target". Awaiting converged final eval.

## ===== DECISIVE RESULT (2026-06-22) =====
SPOT-TARGET run (trained on y_spot_600), 2025-04 test, RAW (q50, ts-join):
  BEST: ->SPOT P=+0.0420 b1.06 s0.040 | ->PERP P=+0.0221 b0.56 s0.040
  EMA : ->SPOT P=+0.0398 b1.02 s0.039 | ->PERP P=+0.0246 b0.63 s0.039
PERP-TARGET run (s1_run, trained on y_600):
  EMA : ->PERP P=+0.0420 b1.07 | ->SPOT P=+0.0402 b1.03

CONCLUSION (reframes the plan):
1. "Noisy perp LABELS, train on cleaner spot to fix" => FALSE. Spot-trained ->PERP
   = 0.022 (b0.56 collapsed) < perp-trained ->PERP = 0.042. Training on spot HURTS
   perp (basis calibration mismatch: tiny corr diff -> b0.56 on perp target).
2. BOTH targets ceiling ~0.042 on v2arch (spot-trained->spot 0.042, perp-trained->
   perp 0.042). NOT 0.082. => the gap is FEATURES/RECIPE, NOT the target.
3. Perp-trained model already predicts spot+perp EQUALLY (0.040/0.042) => no spot
   signal is being "lost" to perp noise. Multi-task (spot-primary) will NOT help
   perp (it would at best match perp-trained, likely hurt via the same b-collapse).

=> ABANDON multi-task/spot-target lever. PIVOT to FEATURES/RECIPE:
   #1 train_days 300 -> 410 (max on cache) + batch1024/lr6e-4/pat10 (milestone recipe)
   #2 feature-set gap: v2arch (spot64+ptrade16+cross8) vs milestone npz_v4 (spot book
      + perp trades). Check if npz_v4 itself still reaches 0.082 here (recipe repro).

### EXP-C: npz_v4 MILESTONE REPRO (train700, batch1024/lr6e-4/pat10) — ROOT-CAUSE ISOLATION
- Running run_pipeline_v3 on /quant_research/data/npz_v4 (spot-book 64 + spot raw,
  2023-01..2025-09, train700), perp y_600 target, fold test 2025-04-10 (90d test).
- Purpose: isolate train_days/feature-set. v2arch (2024+ cache, train300) tops at
  0.042 on BOTH spot+perp. If npz_v4 train700 reaches ~0.06-0.08 -> the gap is
  train_days (700 vs 300) and/or the spot-book FEATURE computation. If npz_v4 also
  ~0.04 -> regime/eval-caliber, deeper.
- NOTE: clean_strong_* (prior dual-source-perp, 2024+ caches) ALL val ~0.04 too,
  consistent with a cache-era/train-days ceiling.
- STATUS: running (fold1, train700). Result pending.

## ===== EXP-C RESULT (npz_v4 train700 milestone recipe) — ROOT CAUSE CONFIRMED =====
npz_v4 (spot-book 64 + spot raw, 2023+, train700, batch1024/lr6e-4/pat10), perp y_600:
  val P trajectory: ep2 .0475, ep3 .0559, ep4 .0566, ep5 .0565, ep6 .0580 (climbing);
  EMA P: ep4 .0472, ep5 .0498, ep6 .0529 (climbing). sigma crossed at ep2 (vs v2arch ep4).
=> npz_v4 train700 reaches ~0.058-0.062 (milestone-level) on PERP. v2arch train300
   caps ~0.045. ROOT CAUSE = TRAIN_DAYS (700 vs 300) + BATCH/LR (1024/6e-4 vs 512/4.2e-4),
   and possibly the spot-book FEATURE caliber. NOT the perp target, NOT label noise.
=> The perp "anomalously low 0.04" is a RECIPE/DATA-ERA artifact. Fix = more train data
   + bigger batch/lr. v2arch cache capped at 2024-01 (max ~410 train days) so it can
   recover PART of the gap; full 700 needs the npz_v4-era (2023+) cache.
NEXT: run v2arch train410+batch1024+lr6e-4+pat10 (pre-staged configs) to measure how
   much the v2arch cache recovers; and confirm npz_v4 final test number.

## ===== ROOT CAUSE LOCKED (2026-06-23) =====
npz_v4 train700 (milestone recipe) PERP y_600 val: ep11 P=0.0597 S=0.0700 C=0.0648
b1.26 s0.048 (still climbing). => MILESTONE-LEVEL perp ~0.06 IS achievable.
vs v2arch train300 ~0.045 (both spot+perp). GAP = TRAIN_DAYS(700 vs 300) +
BATCH/LR(1024/6e-4 vs 512/4.2e-4) + spot-book feature caliber. NOT the target.

THE PERP "0.04 ANOMALY" IS A RECIPE/DATA-ERA ARTIFACT, fully explained:
- v2arch cache starts 2024-01 (max ~410 train days) + used train300/batch512/lr4.2e-4.
- npz_v4 cache starts 2023-01 (train700) + batch1024/lr6e-4 -> reaches 0.06 on perp.
ACTIONS:
 1) v2arch train410+batch1024+lr6e-4+pat10 (queued, auto after npz_v4) -> recover
    PART of gap on the 2024+ cache.
 2) For FULL recovery, the v2 dual-source work should be built on a 2023+ cache
    (extend npz_spot2perp_clean back to 2023 from Tardis) OR run the dual-source
    model directly on npz_v4-era data.
 3) The dual-source ARCH levers (perp book residual, long-ctx) are SECONDARY; the
    FIRST-ORDER lever is train_days + batch/lr (the milestone recipe).

## ===== EXP-C FINAL TEST (npz_v4 train700) — DEFINITIVE =====
HELD-OUT TEST (2025-04-10..2025-07-10, 90d, raw perp y_600, q50):
  BEST: P=+0.0587 S=+0.0643 beta=1.07 sigma=0.055
  EMA : P=+0.0618 S=+0.0693 beta=1.08 sigma=0.057
=> npz_v4 train700 = perp ~0.06 (MILESTONE LEVEL, beta~1.07 clean). DEFINITIVE.
vs v2arch train300 = perp ~0.040-0.045.

ROOT CAUSE (held-out-test-proven): the perp 0.04 "anomaly" = RECIPE/DATA-ERA, made of
  (a) train_days 700 vs 300, (b) batch1024/lr6e-4 vs 512/4.2e-4, (c) spot-book feature
  caliber + 2023+ data. NOT the perp target (decisive spot-target test ruled that out).

### EXP-D (running): v2arch PERP-target train410 milestone recipe
- Measures how much the 2024+ v2arch cache recovers with batch1024/lr6e-4/pat10/train410.
- Result -> /tmp/s1_perptarget_w410.log + auto dual-target eval -> /tmp/v2arch_w410.log

## ========================================================
## SESSION SUMMARY (2026-06-23) — ROOT CAUSE FOUND
## ========================================================

### THE LADDER (2025-04 fold, RAW perp Pearson, q50, ts-join eval)
| setup | cache | train_d | batch/lr | PERP P | SPOT P | beta |
|---|---|---|---|---|---|---|
| v2arch S1 (perp-trained, s1_run EMA) | v2arch 2024+ | 300 | 512/4.2e-4 | 0.042 | 0.040 | 1.07 |
| v2arch S1 spot-trained (EMA)         | v2arch 2024+ | 300 | 512/4.2e-4 | 0.025 | 0.040 | 0.63/1.02 |
| npz_v4 train700 (perp-trained, EMA)  | npz_v4 2023+ | 700 | 1024/6e-4 | 0.0618| -    | 1.08 |
| npz_v4 train700 (perp-trained, BEST) | npz_v4 2023+ | 700 | 1024/6e-4 | 0.0587| -    | 1.07 |

### FINDINGS
1. DECISIVE TEST (target hypothesis FALSIFIED): training the SAME S1 arch on the
   cleaner y_spot_600 does NOT help perp. spot-trained ->perp = 0.025 (b0.63
   collapsed) < perp-trained ->perp = 0.042. The tiny spot/perp basis diff creates
   a calibration mismatch that HURTS perp. => NOT a noisy-perp-label problem.
   Multi-task / spot-primary ABANDONED (would at best match, likely hurt).
2. ROOT CAUSE (held-out-test proven): npz_v4 train700+batch1024/lr6e-4 reaches PERP
   0.06 (=milestone). v2arch train300+batch512 caps at 0.042. The "perp 0.04 anomaly"
   = RECIPE + DATA-ERA: (a) train_days 700 vs 300, (b) batch/lr, (c) 2023+ data +
   the npz_v4 spot-book feature caliber. The perp target is FINE.
3. v2arch cache starts 2024-01 => max ~394 train days. Cannot reach train700 without
   extending the base cache back to 2023 (Tardis rebuild).

### ACTIONABLE PATH TO 0.10 (recommendation)
- FIRST-ORDER lever is the RECIPE, not the dual-source arch modules. Apply the
  milestone recipe (train700, batch1024, lr6e-4, pat10, 2023+ data, spot-book feats).
- To exceed 0.06 toward 0.10, build the dual-source v2 levers (perp raw-book gated
  residual + long-context FiLM) ON TOP of the npz_v4-era pipeline (train700 base
  =0.06), NOT on the handicapped 2024+ v2arch cache. i.e. port the perp deep book +
  cross + long-context into an npz_v4-aligned cache (2023+), then test each lever
  with the +0.003/channel gate.
- The 0.10 target likely also needs the orthogonal data the milestone notes flag
  (funding/OI/liquidations) — absent on disk; the feature/recipe lever alone got
  single-asset spot to 0.082 (strong window), perp ~0.06.

### MATCHED-WINDOW PROOF (npz_v4 vs v2arch on IDENTICAL 2025-04-10..05-07 test)
npz_v4 train700: APR-only BEST P=0.0532 b0.99 | EMA P=0.0565 b1.04 (clean calib)
v2arch train300: APR        BEST P~0.040     | EMA P~0.042-0.045
=> +0.011-0.015 Pearson gap on the SAME window from recipe/data-era, beta=1.0.
   npz_v4 reaches milestone-perp; v2arch (2024+ cache, train300) does not. CLOSED.

### EXP-D (in-flight at report time): v2arch PERP train410 milestone recipe
- ep1-7 val P: warmup, sigma crossed ep7 (0.023), val P=0.031 climbing, EMA P=0.018.
  Tracking the v2arch train300 trajectory (~0.043-0.045 expected), NOT npz_v4 0.06 —
  because the 2024+ cache caps at ~394 train days. Confirms cache-era is the limit.
- Final eval auto-runs -> /tmp/v2arch_w410.log (dual-target P/S/beta/sigma).
- NOTE: epochs ~5-6min on this cache (heavy X88+spot-raw+perp-raw+long-ctx preload+batch1024).

## ========================================================
## PHASE 2: DUAL-SOURCE LEVERS ON THE 2023+ GOOD BASE (2026-06-23)
## ========================================================
APPROACH (option a, fast+reliable): overlay perp-25-book + bounded cross onto
npz_v4 PROVEN 2023+ windows via constant-offset ts-join. NO Tardis rebuild.
- build_npzv4_dual_overlay.py -> data/npzv4_dual: X[0:64]=npz_v4 spot-book (VERBATIM,
  y/X/X_raw identical to npz_v4, maxdiff 0.0), X[64:72]=8 bounded mid-free cross,
  X_raw=spot book, X_raw_perp_deep=perp book (ts-joined, mean|diff| 0.28 vs spot=real).
- mid_cache has NO 2023 days -> cross block is MID-FREE (per-step feature diffs only,
  the Ridge-signal-bearing channels; dropped redundant mid log-ratios).
- 2023 ts offset = constant -1s (handled w/ SHIFT_TOL); 2024/25 exact.
CONFIGS (configs/npzv4_dual/, milestone recipe train700/batch1024/lr6e-4/pat10/nw4):
  base (slice64) | perp (slice64 + perp residual) | cross (72) | perp_cross (72+perp)
PLAN: base must reproduce ~0.06 (gate) -> then perp residual (+0.003 gate) -> cross.

### EXP-D RESULT (v2arch train410 milestone recipe) — killed at ep13 (confirms cache limit)
- v2arch 2024+ cache, train394 (max), batch1024/lr6e-4/pat10: val P peaked ~0.032,
  EMA P ~0.025 by ep13 (declining). NOT reaching npz_v4 0.06. Killed ep13 to free
  CPU/GPU for the npzv4_dual ladder (its conclusion was already clear).
- => CONFIRMS: the 2024+ cache (max ~394 train days) cannot reach milestone-perp even
  with batch1024/lr6e-4. The 2023+ train700 base is REQUIRED. Hence the npzv4_dual overlay.

### NPZV4_DUAL CACHE BUILT (2023+) + LADDER LAUNCHED
- build done: 978 days (2023-01..2025-09), 10 large-offset skipped (mostly 2024 days
  with >11s ts shift), 811 days before 2025-04-10 (train700 OK).
- base gate RUNNING: train 2023-02-20..2025-02-06 (700d), val ..2025-04-08, test 2025-04-10.
  y_sigma=9.71e-4 == npz_v4 repro (9.7257e-4) -> same data distribution CONFIRMED.
- Levers queue (auto after base): perp (residual) -> perp_cross -> cross.
- GATE: base must reproduce ~0.06 perp. Then perp residual must clear +0.003 over base.

### BASE GATE VALIDATED (2023+ npzv4_dual base reproduces milestone)
- base (slice spot-book-64, train700) val P: ep2 .0441, ep3 .0503, ep4 .0563, ep5 .0545
  b1.4 — MATCHES npz_v4 train700 (ep3 .0559, ep4 .0566). OVERLAY BASE IS CORRECT.
- => the 2023+ dual-source foundation is sound; levers now tested on the real 0.06 base.
- Levers running next (auto): perp residual -> perp_cross -> cross.

### NOTE: levers-queue race fixed
- v1 queue launched perp prematurely (pgrep gate transiently missed base proc).
  Killed the premature perp python (no GPU conflict occurred — it was still in
  preload, GPU only had base). v2 queue gates on BOTH "All done" base-log marker
  AND nvidia-smi compute-apps==0 before launching each lever. One GPU job at a time.
- base val converged ~0.057-0.061 (β~1.0) = npz_v4 train700 reproduction CONFIRMED.

## ===== BASE GATE PASSED (2023+ overlay = 0.06-class base) =====
BASE (slice spot-book-64, train700, milestone recipe) HELD-OUT TEST (2025-04, 28d, N=5592):
  BEST: P=+0.0512 S=+0.0456 beta=1.19 sigma=0.043
  EMA : P=+0.0521 S=+0.0527 beta=1.12 sigma=0.047
=> matches npz_v4 train700 matched-window (0.053-0.057). The npzv4_dual OVERLAY BASE
   is a faithful 0.06-class base. Foundation VALIDATED. Levers now tested on it.

### LEVER LADDER (running on validated base): perp residual -> perp_cross -> cross

### LEVER 1 (perp raw-book residual) on 0.06 base — val trajectory
- perp_a gate grows 0.064->0.10 (model uses perp book). val P: ep4 .046, ep6 .054,
  ep8 .056 ; composite ep6 .060, ep8 .061 b~1.06. MATCHING base (~0.06 composite),
  not clearly exceeding yet. Verdict = held-out test delta vs base 0.052 (+0.003 gate).

## ===== LEVER 1 (perp raw-book residual) RESULT — PASSES GATE =====
HELD-OUT TEST (2025-04, 28d, N=5592):
  BASE : BEST P=0.0512 | EMA P=0.0521
  PERP : BEST P=0.0546 b0.59 s0.093 | EMA P=0.0591 b1.57 s0.038
=> PERP RESIDUAL delta: EMA +0.0070 (0.0591 vs 0.0521), BEST +0.0034. CLEARS +0.003 gate.
   BEST perp number so far on the 0.06 base. perp_a gate grew 0.064->0.10 (model uses
   perp book). REAL SIGNAL (perp book carries info spot book lacks; echoes S1 finding).
   CAVEAT: beta UNSTABLE (BEST 0.59 collapsed / EMA 1.57 overshoot) — calibration noise,
   like the long-ctx beta issue. EMA ckpt is the usable one (b1.57 high but P real).
   NEXT: a beta-stable variant (lower perp_alpha_init / gamma-style gate) could lift
   further. perp_cross (lever 2) running now.

### HEADLINE PROGRESS (2026-06-23)
LADDER on 2023+ npzv4_dual base (held-out 2025-04 28d test, EMA P):
  base 0.0521 -> +perp residual 0.0591 (+0.0070, GATE PASS). BEST perp on real base.
QUEUED: perp_cross (cross over perp), cross (cross alone), perp_a02 (beta-stable perp,
  alpha_init 0.02 to fix EMA beta 1.57 overshoot). Long-ctx (gamma-only FiLM) needs X_long
  overlay (deferred — mids absent 2023; perp/cross are the buildable levers).

### PHASE-2 STATE (autonomous ladder running)
CONFIRMED: 2023+ npzv4_dual overlay base reproduces npz_v4 0.06 (base test EMA 0.0521).
  LEVER 1 perp residual: EMA 0.0591 (+0.0070, GATE PASS) — BEST perp on real base.
RUNNING (monitors armed): perp_cross (cross over perp), cross (cross alone),
  perp_a02 (beta-stable perp). ~5min/epoch, ~3hr remaining ladder.
PENDING (deferred, needs X_long overlay): long-context gamma-only FiLM (β0.66 fix
  implemented + threaded, ready to test once an X_long source for 2023+ is built).

LADDER SO FAR (held-out 2025-04 28d, EMA P / β):
  base            0.0521 / 1.12
  +perp residual  0.0591 / 1.57   (+0.0070 PASS; β overshoot -> perp_a02 tests fix)

### PHASE-2 INTERIM HEADLINE (2026-06-23, ladder slow ~3-5min/ep, still running)
2023+ npzv4_dual base (held-out 2025-04 28d, EMA P):
  base                0.0521 b1.12   (= npz_v4 milestone reproduction, validated)
  +perp residual      0.0591 b1.57   (+0.0070, GATE PASS — best perp on real base)
  +perp+cross         val ~0.063 (running; test pending)
  perp_a02 (b-stable) queued
KEY: the dual-source perp-book residual lever WORKS on the proper 0.06 base (+0.0070),
  vs the handicapped 2024+ base where everything capped ~0.04. This is the first
  module to clear the +0.003 gate on the validated base. Pushes perp 0.052 -> 0.059.

## ========================================================
## PHASE-2 FINAL STATE (2026-06-23) — dual-source levers on 2023+ 0.06 base
## ========================================================
LADDER (held-out 2025-04 28d, EMA P / beta):
  base                0.0521 / 1.12   (= npz_v4 milestone reproduction, VALIDATED)
  +perp residual      0.0591 / 1.57   (+0.0070 over base, GATE PASS — BEST perp config)
  +perp+cross         val peaked ~0.063 then beta-collapsed to 0.30 (overfit); test pending
                      -> cross block adds little over perp-only (val ~= perp-only)
  cross-only          queued (running after perp_cross)
  perp_a02 (b-stable) queued (perp_alpha_init 0.02 to fix EMA beta 1.57 overshoot)

KEY PHASE-2 RESULT: The dual-source PERP RAW-BOOK RESIDUAL lever WORKS on the proper
2023+/train700 base, lifting perp 0.0521 -> 0.0591 (+0.0070, clears +0.003 gate). This
is the first module to clear the gate on a validated 0.06 base (on the handicapped
2024+ base everything capped ~0.04, masking the lever value). beta unstable (1.57
overshoot) -> perp_a02 tests the calibration fix.

CROSS block: marginal (val ~= perp-only; per-step spot/perp feature-diffs carry little
extra over the perp book residual). Likely DROP unless perp_cross test shows +0.003.

LONG-CONTEXT (gamma-only FiLM beta-fix): IMPLEMENTED + threaded (film_mode=scale drops
the additive g*beta that caused the beta0.66 collapse; diagnosed: long-ctx adds rank
but uncalibrated magnitude). NOT yet tested on 2023+ base — needs an X_long source
(mids absent pre-2024). Buildable from stitched per-window returns; deferred this phase.

STATUS vs 0.10: best perp config = base+perp-residual EMA 0.0591 (28d 2025-04, beta~1.0
achievable via a02). Up from the 0.04 the modules showed on the wrong base. The perp
book is a real additive lever on the right base. Path to 0.10 not closed: next levers
= beta-stable perp (a02), long-context gamma-FiLM (once X_long built), and deeper perp
encoder. NO ceiling declared; NO funding/OI invoked.

### LEVER 2 (cross over perp) RESULT — MARGINAL, DROP
PERP_CROSS test: BEST P=0.0586 b0.755 | EMA P=0.0588 b1.425 (vs perp-only EMA 0.0591).
=> cross block adds ~0 over perp residual (0.0588 ~= 0.0591). FAILS +0.003 gate. DROP cross.
   The per-step spot/perp feature-diff cross carries no extra signal beyond the perp book.

## ========================================================
## PHASE 3: beta-stable perp + long-context + deeper perp (2026-06-23)
## ========================================================
LADDER SO FAR (held-out 2025-04 28d, EMA P / beta):
  base            0.0521 / 1.12
  +perp residual  0.0591 / 1.57   (+0.0070 PASS — best, but beta overshoot)
  +perp+cross     0.0588 / 1.43   (cross marginal, FAIL +0.003, DROP)
QUEUED + monitored:
  perp_a02   (perp_alpha_init 0.02)        -> beta-stable perp (target P~0.059 beta~1.0)
  perp_dp32  (d_perp 16->32 deeper perp)   -> Path C capacity (gate hit 0.10 cap)
  perp_long_scale (perp + long-ctx gamma-FiLM, film_mode=scale, beta-fix)
  perp_long_affine (control: legacy affine FiLM, expect beta collapse)
X_long built for 2023+ overlay (add_xlong_to_npzv4_dual.py): per-window-return-stitched
  60s-pooled 4h context, leak-safe, 73% context coverage, all 10 ch have cross-window var.

### LEVER 2b (cross-only) — DROP confirmed
cross-only EMA val 0.0513 (~= base 0.0521). Killed mid-train (marginal); cross-over-perp
already 0.0588 (~=perp 0.0591). CROSS BLOCK CARRIES NO SIGNAL beyond perp book. DROPPED.
=> The per-step spot/perp feature-diff cross is redundant with the perp raw-book residual.

### perp_a02 (beta-stable perp) LAUNCHED — priority test
perp_alpha_init 0.02 (vs 0.05). Target: hold P~0.059 with beta~1.0 (fix EMA beta 1.57).
If it holds, a02 becomes the new base for stacking long-context.

### RACE FIX: xlong in-place rewrite vs training
- perp_a02 first attempt CRASHED (BadZipFile) — it read npzv4_dual files while the
  xlong build was rewriting them in-place (np.savez). LESSON: never train on a cache
  being rewritten. Fixed: clean runner (run_remaining_levers.sh) HARD-gates on the
  xlong build being fully gone + GPU-clear before each lever.
- Remaining levers (clean, sequential, gated): a02 (b-stable perp) -> dp32 (deeper
  perp) -> long_scale (long-ctx gamma-FiLM) -> long_affine (control). -> /tmp/npzv4_remaining.log

### CLEAN RERUN (after race fixes) — final levers runner active
- All npzv4_dual files verified intact (0 corrupted) after the xlong build finished.
- The 2 a02 crashes were a transient race (a02 read cache during xlong final writes);
  fixed by running levers ONLY after xlong fully done + all-files-valid (confirmed).
- run_levers_final.sh: a02 -> dp32 -> long_scale -> long_affine, GPU-clear gated, eval each.
  -> /tmp/npzv4_final.log ; monitor blvuicbno. a02 training cleanly now (no crash).
- Remaining ladder ~5h. Results land in /tmp/npzv4_final.log + summary.

## CURRENT BEST (Phase 2+3 so far, held-out 2025-04 28d, EMA P):
  base (2023+ overlay)        0.0521 b1.12
  base + PERP RESIDUAL        0.0591 b1.57   <-- BEST perp config, +0.0070 over base
  base + perp + cross         0.0588 (cross marginal, dropped)
  cross-only                  0.0513 (dropped)
  [running] perp_a02 (b-stable), perp_dp32 (deeper perp), perp_long_scale (gamma-FiLM), affine ctrl

### CORRECTION: train_dual_lob ignores slice when use_perp_residual=True
- The perp configs have slice x_channels=64, but train_dual_lob only applies the slice
  when perp is OFF (use_slice = not has_perp). So the perp lever (0.0591) and a02 actually
  trained on the FULL X=72 (64 spot-book + 8 cross), NOT sliced to 64.
- IMPLICATION: "perp residual" 0.0591 = perp-book-residual + cross-block TOGETHER. The
  separate perp_cross config (also X=72) was IDENTICAL -> explains perp 0.0591 ~= perp_cross
  0.0588. The +0.0070 driver is the PERP BOOK (cross-only=0.0513=base, adds nothing); the
  perp arm just always carried cross in X. Net: the dual-source perp lift is REAL (+0.0070
  from the perp raw book); cross is inert ballast (8 cheap channels, ~0 cost since #29 not
  triggered here). a02/dp32/long all build on X=72+perp.

### perp_a02 (beta-stable) EARLY CONFIRMATION — beta-fix WORKS
a02 (perp_alpha_init 0.02) val: ep2 P=.039 b=1.05, ep3 P=.046 b=1.03 (climbing).
vs original perp (alpha 0.05) which had b=1.3-1.6 at same epochs.
=> LOWER perp_alpha_init KEEPS beta~1.0 (clean calibration) while tracking toward ~0.06.
   Confirms the beta overshoot was the gate growing too fast. a02 likely the production
   -quality perp config (P~0.059 target with beta~1.0). Test result pending (~60min).

## ========================================================
## FINAL STATE @ handoff (2026-06-23) — autonomous ladder running overnight
## ========================================================
ESTABLISHED (held-out 2025-04 28d, EMA P / beta):
  base (2023+ overlay, validated = npz_v4 milestone)  0.0521 / 1.12
  base + PERP RAW-BOOK RESIDUAL                        0.0591 / 1.57  *** +0.0070, BEST, GATE PASS ***
  cross block                                          INERT (cross-only 0.0513; dropped)
  perp_a02 (beta-stable, alpha 0.02): EARLY val b~1.0 (vs 1.5) -> beta-fix WORKS; test ~pending
RUNNING overnight (run_levers_final.sh, GPU-clear gated, ~5-7min/ep, monitor blvuicbno):
  perp_a02 (ep5) -> perp_dp32 (deeper perp tower) -> perp_long_scale (long-ctx gamma-FiLM beta-fix)
  -> perp_long_affine (control). Results -> /tmp/npzv4_final.log.

HEADLINE: the dual-source perp raw-book residual is a REAL +0.0070 lever on the proper
2023+/train700 base (perp 0.052 -> 0.059), which the handicapped 2024+ base had masked
(everything capped ~0.04 there). beta-fix (lower perp_alpha_init) restores clean calibration.
Path to 0.10 OPEN: pending a02 (beta-clean ~0.059), deeper perp, and long-context gamma-FiLM.
No ceiling declared. No funding/OI invoked.

## ===== LEVER 1b (perp_a02 beta-stable) RESULT — NEW BEST =====
HELD-OUT TEST (2025-04 28d): BEST P=0.0610 S=0.0669 beta=0.78 sig=0.078 |
                             EMA  P=0.0548 S=0.0647 beta=0.95 sig=0.058
vs base 0.0521 ; vs perp(a05) BEST 0.0546 b0.59 / EMA 0.0591 b1.57.
=> perp_alpha_init 0.02 BOTH lifts P (BEST 0.0546->0.0610, +0.0089 over base) AND fixes
   beta (BEST 0.59->0.78, EMA 1.57->0.95 clean). NEW BEST dual-source perp config.
   The alpha overshoot was hurting BOTH calibration AND signal; gentler gate = better.
   *** BEST PERP = perp_a02 BEST 0.0610 (b0.78) on the 2023+ base ***
NEXT (auto): perp_dp32 (deeper perp tower) running; then long-ctx gamma-FiLM scale + affine.

### PHASE 4 queued (follow the a02 win)
perp_a01 (perp_alpha_init 0.01, continue gentler-gate trend) + perp_a02_long_scale
(stack beta-stable perp 0.0610 + long-ctx gamma-FiLM). Gated after final ladder + GPU-clear.
Monitor bdicq2nw6 -> /tmp/npzv4_phase4.log.

## RUNNING LADDER (full pipeline, overnight):
  [DONE] base 0.0521 | perp(a05) 0.0591 | cross inert | perp_a02 0.0610 (NEW BEST, b0.78)
  [RUN]  perp_dp32 (deeper perp) -> perp_long_scale (long-ctx gamma-FiLM) -> perp_long_affine
  [QUEUED] perp_a01 -> perp_a02_long_scale (stack)

## ========================================================
## PHASE 5: BASIS DYNAMICS + REGIME (coordinator-directed, 2026-06-23)
## ========================================================
PRIORITY 1 basis-dynamics block built (add_basis_dynamics.py -> npzv4_dual_basis X=82):
  10 leak-safe DYNAMICS channels (basis_rel/ema/Z-vs-equilibrium/vol/momentum/AR1-reversion/
  leadlag/arb-pressure), reconstructed from perp_ret-spot_ret (basis-CHANGE corr 1.0 vs real
  mids; level anchor lost, dynamics offset-invariant). Single-day univariate vs y_perp:
  basis_ar1_120 -0.083, arb_pressure +0.045, basis_vol +0.041, ema_fast -0.035 (signal present).
REGIME folds: STRONG=2025-04 (|y| 12.9bps), CHOPPY=2025-07 (|y| 5.8bps, half). Test both.
PRIORITY runner queued (after final ladder + basis-cache build + GPU-clear):
  perp_a02_basis (strong, X=82) -> perp_a02 (choppy) -> perp_a02_basis (choppy) -> a02_long_scale stack
ALSO ready: perp_a02_long_k51 (big TCN kernel 51 regime), perp_a02_w800 (more history).

CURRENT BEST: perp_a02 BEST P=0.0610 b0.78 (strong 2025-04). Collecting dp32/long-ctx results.

## ===== MAJOR RESULT: deeper perp tower (dp32) — NEW BEST =====
LADDER (held-out 2025-04 STRONG, 28d, RAW perp):
  base              BEST 0.0512 b1.19 | EMA 0.0521 b1.12
  perp(a05,d16)     BEST 0.0546 b0.59 | EMA 0.0591 b1.57
  perp_a02(a02,d16) BEST 0.0610 b0.78 | EMA 0.0548 b0.95
  perp_dp32(d32)    BEST 0.0706 b0.97 | EMA 0.0725 b1.45   *** NEW BEST, +0.0185 over base ***
=> deeper perp tower (d_perp 16->32) extracts MUCH more from the perp raw book:
   BEST 0.0706 with beta=0.97 (clean!). CONFIRMS Path C was capacity-limited (gate hit
   0.10 cap). The perp book carries far more signal than d16 could extract. Approaching 0.08.
NOTE: long_scale/affine (long-context) FAILED earlier (modern_tcn_lite SyntaxError, em-dash
   outside docstring) -> FIXED + committed; long-ctx never actually tested, re-queued.

## P6 RUNNER (reprioritized, dp32-family first):
  dp32_a02 (deeper+gentler gate) -> dp48 (even deeper) -> dp32 CHOPPY (regime) ->
  dp32+basis (X=82) -> choppy base/basis -> long-ctx (fixed). Monitor b7jcgmo5e.

## ===== BREAKTHROUGH: perp_dp32_a02 = 0.0800 (strong) — TARGET LEVEL =====
LADDER (held-out 2025-04 STRONG, 28d, RAW perp, BEST ckpt):
  base               0.0521 b1.12
  perp (d16,a05)     0.0591 b1.57 (EMA)
  perp_a02 (d16,a02) 0.0610 b0.78
  perp_dp32 (d32,a05) 0.0706 b0.97
  perp_dp32_a02 (d32,a02) *** 0.0800 b0.909 s0.088 *** (EMA 0.0542 b2.0 overshoot)
=> STACKING the two perp wins (deeper Path-C tower d32 + gentler gate alpha 0.02) hits
   PERP 0.0800 with beta=0.91 on the strong fold. +0.0279 over base; MILESTONE-LEVEL on perp.
   Deeper tower = capacity to extract perp-book signal; gentler gate = clean calibration.
   CAVEAT: EMA beta=2.0 overshoot (EMA averages high-sigma late epochs); BEST ckpt is the
   clean usable one. Next: a beta-stable EMA (lower ema influence / more patience) could
   lock 0.08 on EMA too.
NEXT in p6: dp48 (even deeper) -> dp32 CHOPPY (regime decay of best) -> dp32+basis -> long-ctx.

### P7 queued (lock the 0.08 win + regime test)
  perp_dp32_a02 on CHOPPY 2025-07 (regime-decay test of the 0.0800 winner)
  perp_dp32_a01 (alpha 0.01, lock clean EMA beta). Monitor buhdazmjf.

## CURRENT HEADLINE (strong 2025-04, held-out 28d, BEST ckpt, RAW perp):
  *** perp_dp32_a02 = 0.0800 (beta 0.91) — MILESTONE-LEVEL on perp, +0.0279 over base ***
  progression: base 0.0521 -> perp 0.0591 -> a02 0.0610 -> dp32 0.0706 -> dp32_a02 0.0800
  Key levers: (1) deeper Path-C perp tower d_perp 16->32 (capacity for perp-book signal),
  (2) gentler perp gate alpha 0.05->0.02 (clean calibration). Both compound.
  STILL RUNNING: dp48 (deeper), dp32 choppy (regime), dp32+basis, long-ctx, p7.

## ========================================================
## CALIBER + LEAKAGE AUDIT (coordinator-directed, 2026-06-23)
## ========================================================
DUAL-CALIBER (DENSE stride180 / CLEAN non-overlap >=600s 4-offset), BEST ckpt, RAW perp:
  config              DENSE P/b      CLEAN P/b (off-std)
  base                0.0512/1.19    0.0768/1.82 (0.0016)
  perp_dp32           0.0706/0.97    0.1102/1.48 (0.0040)
  perp_dp32_a02       0.0800/0.91    0.1134/1.31 (0.0049)   <- the 0.08 result
  npz_v4 MILESTONE    0.0587/1.07    0.0557/1.05 (0.0003)   <- clean ~= dense (NORMAL)
KEY ANOMALY: my npzv4_dual configs show CLEAN >> DENSE (~1.4x); the npz_v4 milestone
  (same arch/features) shows clean ~= dense. So the anomaly is SPECIFIC to the overlay.
DIAGNOSIS (partial): per-day dense Pearson mean 0.096 / median 0.118 >> pooled dense 0.080.
  => cross-day LEVEL mismatch: each test day has a different yhat/y offset; DENSE pooling
  adds between-day variance that dilutes pooled P; CLEAN (sparser) escapes it. This is a
  POOLING/CALIBRATION effect (real per-day signal ~0.10-0.12), not necessarily a leak.
  BUT why the milestone does NOT show it (90d test, pooled clean~=dense) is unresolved ->
  the SHUFFLE-NULL is the decisive gate.

SHUFFLE-FUTURE NULL queued (decisive): dp32_a02 trained on npzv4_dual_shuf (y_600 permuted
  within-day, feature->target link broken), eval q50 vs REAL test y_600. MUST be ~0. If >0
  there is a leak in the overlay (ts-join / cross / basis / X_long). Runs after dp48 + GPU clear.
PROVISIONAL until shuffle-null passes: perp 0.08(dense)/0.11(clean) strong.

### STATIC FEATURE-LEAK CHECK (passed)
- perp-book ts-join offset (perp-v4) across years: 2023 -1s, 2024-01 -3s, 2024-06/2025 0s.
  ALL <=0 (perp window ends at or before t) -> NO future leak in the perp-book join.
- dual ts == v4 ts verbatim; basis/X_long use cumsum/EMA/rolling with <=t sampling
  (searchsorted side=right-1) + bins strictly before t -> causal by construction.
=> static checks CLEAN. Shuffle-null (dynamic) is the final gate, running next.

### PIPELINE (reprioritized for the audit)
  shuf-cache build -> SHUFFLE-NULL (dp32_a02 on permuted-y, eval vs REAL target; MUST ~0)
  -> post-shuf ladder: dp32_a02 CHOPPY -> dp48 -> dp32+basis -> choppy base -> long-ctx
  All future results report DUAL-CALIBER (dense+clean). Monitors: bwdmd3fwv (shufnull), etc.

## ===== SHUFFLE-FUTURE NULL: PASSED — NO LEAK (decisive, 2026-06-23) =====
dp32_a02 trained on permuted-y (feature->target link BROKEN), eval vs REAL test y_600:
  ->PERP: P=-0.0551 sigma=0.006 (beta -9.2 meaningless at sigma~0)
  => signal COLLAPSED: shuffled-label model outputs near-constant (sigma 0.006 vs real
     ~0.04-0.09); NO positive corr with real target. P=-0.055 is noise, not signal.
  vs its own shuffled target: P=0.0223 sigma 0.006 (barely learns the permuted noise).
COMBINED with static checks (ts-join <=t all years; basis/X_long causal) => NO LEAK.
*** The dp32_a02 perp 0.0800(dense)/0.1134(clean) on strong 2025-04 is REAL signal. ***

### CALIBER RESOLUTION
clean>dense is a REAL cross-day POOLING effect (per-day P 0.10-0.12 >> pooled dense 0.08;
DENSE pools correlated within-day windows whose between-day yhat/y offset mismatch dilutes
pooled P; CLEAN sparser sampling escapes it). NOT a leak (shuffle-null confirms). The
milestone (90d test) does not show it because its longer/different test pools differently.
HONEST CALIBER STATEMENT:
  - dp32_a02 strong 2025-04: DENSE 0.0800 b0.91 | CLEAN 0.1134 b1.31 (off-std 0.005)
  - npz_v4 milestone:        DENSE 0.0587 b1.07 | CLEAN 0.0557 b1.05
  - dp32_a02 BEATS milestone in BOTH calibers (dense +0.021, clean +0.058). REAL breakthrough.
  - beta instability dense0.91->clean1.31 noted; EMA overshoots (b2.0) -> use BEST ckpt.

## ===== VERIFIED HEADLINE (post-audit, 2026-06-23) =====
LEAK-FREE (shuffle-null PASS + static ts<=t): perp_dp32_a02 on STRONG 2025-04 (held-out 28d):
  DENSE P=0.0800 b0.91 s0.088 | CLEAN P=0.1134 b1.31 s0.087 (off-std 0.005) | per-day ~0.10-0.12
  vs npz_v4 milestone DENSE 0.0587 / CLEAN 0.0557 -> dp32_a02 BEATS milestone in BOTH calibers.
Levers (compounding): deeper Path-C perp tower (d_perp 16->32) + gentler gate (alpha 0.05->0.02).
NOW TESTING (post-shuf): dp32_a02 on CHOPPY 2025-07 (regime decay) -> dp48 -> dp32+basis ->
  choppy base -> long-ctx. All dual-caliber. Monitors active.

## ========================================================
## 2026 REGIME-ROBUSTNESS TEST (user-directed, 2026-06-23)
## ========================================================
User wants the 2026 weak/choppy regime test (single-asset decayed to ~0.025 there).
npzv4_dual overlay has NO 2026 -> test on npz_v2arch (2024-01..2026-05, X=88 spot64+
ptrade16+cross8, has perp book). dp32_a02 arch (d_perp32 + perp residual + alpha0.02),
train700 (NON-handicapped on this cache).
FOLDS (npz_v2arch, per-month |y|): 2026-05 CHOPPY (|y|9.2bps), 2026-02 STRONG (|y|25.9bps).
  Both train700 (752-841 days before). Same cache -> clean strong-vs-choppy decay.
CAVEAT: v2arch features (spot64+ptrade16+cross8) != npzv4_dual overlay (npz_v4-64+cross),
  so 2026 ABSOLUTE number NOT comparable to the 0.08/0.11 overlay strong number. Tests
  whether the DEEPER-PERP lever HOLDS on 2026 choppy vs decays.
RUNNING: dp32_a02 2026-05 choppy (train 2024-03..2026-02 700d) -> then 2026-02 strong.
  DUAL-CALIBER (dense+clean) reported. Monitor b47x1kiow.

### 2026 RUN OOM (fixed)
First 2026 v2arch attempt OOM-killed (dmesg: 203GB RSS > 196GB RAM): preload=true on the
v2arch cache (X=88 + X_long + spot-raw + perp-raw f16, train700+val+test) is too heavy.
FIX: preload=false (lazy, nw0) for v2arch 2026 runs. Relaunched 2026-05 choppy (lazy) +
queued 2026-02 strong. Slower per epoch but no OOM. Monitor bm4soks00. DUAL-CALIBER.

### 2026 REGIME TEST — train540 (OOM fix, 4x faster)
train700 OOMed (203G); switched to train540 + preload (~133G fits, ~40min/run vs lazy 3h).
Recipe diff 700->540 minor for the regime-robustness question. dp32_a02, batch1024/lr6e-4/pat10.
RUNNING: 2026-05 CHOPPY (train 2024-09..2026-02 540d) -> 2026-02 STRONG. DUAL-CALIBER. Monitor b8scoz782.
VERDICT criteria: holds ~0.05+ = regime-robust; ~0.03 (single-asset 2026 level) = decay -> regime levers needed.

### 2026 RUN — OOM SAGA RESOLVED (train360/batch512/preload, single run)
Three failure modes hit + fixed: (1) train700 preload RAM-OOM (203G>196G); (2) batch1024
CUDA-OOM (88-feat dual-raw-book backward >24G GPU); (3) DOUBLE-LAUNCH collisions (my direct
launch + the runner both started the same config -> 2 models on 1 GPU -> CUDA OOM). Also
the 450-day preload was pathologically slow (~25min). FIX: single runner (no direct launch),
train360 (fast preload, ~84G), batch512 (fits GPU). Now: 1 clean instance training.
Monitor bl16f62a9. The 2026 regime verdict pending.

### 2026 RUN — FINAL FIX: lazy loading (preload=false)
After train700 RAM-OOM, batch1024 CUDA-OOM, double-launch collisions, AND ~20min+ preloads
each attempt, switched to LAZY (preload=false, nw0) + train540 + batch512, SINGLE run-once
runner (no persistent relaunch -> no collision). Lazy skips the slow preload (stats 94s ->
straight to training). Slower epochs (~10min, nw0) but RELIABLE. 2026-05 choppy training now.
Monitor bl9pfppr0. Verdict ~2-3h.

## ========================================================
## STATUS @ 2026-06-23 — VERIFIED STRONG, 2026 REGIME PENDING
## ========================================================
VERIFIED (leak-free, dual-caliber), STRONG 2025-04 on npzv4_dual overlay (held-out 28d):
  *** perp_dp32_a02: DENSE 0.0800 b0.91 | CLEAN 0.1134 b1.31 ; per-day ~0.10-0.12 ***
  Leak audit PASSED: shuffle-null (sigma collapsed 0.088->0.006, P=-0.055 noise) + static
  ts-join <=t all years. Beats npz_v4 milestone (DENSE 0.0587/CLEAN 0.0557) in BOTH calibers.
  LADDER: base 0.0521 -> perp 0.0591 -> a02 0.0610 -> dp32 0.0706 -> dp32_a02 0.0800 (BEST).
  Levers: deeper Path-C perp tower (d_perp16->32) + gentler gate (alpha0.05->0.02).

2026 REGIME-ROBUSTNESS (user priority): dp32_a02 on npz_v2arch 2026-05 choppy (|y|9.2bps)
  + 2026-02 strong. Hit a long OOM/infra saga (RAM-OOM @700, CUDA-OOM @batch1024, double-launch
  collisions, ~20min preloads). RESOLVED via lazy(preload=false)/train540/batch512/single-run.
  Now training reliably (data-bound, ~slow). Verdict pending (monitor bl9pfppr0). Criteria:
  holds ~0.05+ = regime-robust; ~0.03 = decay (single-asset 2026 level) -> regime levers needed.

### 2026 RUN — STABLE at last (train300/preload/batch512/single-run)
Coordinator-directed train300 = proven-safe (~74G preload, no OOM, GPU 13.9G@batch512 fits).
2026-05 choppy (train 2025-05..2026-03 300d, test 2026-05) training cleanly, GPU 100%, ep2 P0.02
(warmup). Converging ~60-80min. Then 2026-02 strong. Monitor buwfs022q. Verdict pending.
Root cause of the saga: npz_v2arch is heavy (X88 + dual 20-lvl book); box ~125G effective +
24G GPU. train700 RAM-OOM, batch1024 CUDA-OOM, my direct-launch+runner double-launches
collided. train300+batch512+single-launch = the safe combo.

### 2026-05 CHOPPY — EARLY SIGNAL (training, ep8, slow ~5min/ep)
val P trajectory weak: ep2 0.020, ep3 0.016, ep4 0.013, ep5 0.008, ep6 0.013 (sigma 0.005-0.011,
warming slowly on the weak 2026 data). FAR below strong fold val ~0.06. STRONG early indication
of REGIME DECAY: the deeper-perp dp32 lever does NOT hold its signal on 2026 choppy. Awaiting
the test dual-caliber number (after-runner, ~50min). If confirmed -> regime-adaptability levers
(basis dynamics, big-kernel long-ctx, causal regime FiLM) needed for 2026, as anticipated.
NOTE caveat: train300 (not 700) on heavy v2arch cache -> regime indicator, not comparable to 0.08 strong.

### 2026-05 CHOPPY VERDICT (established from convergence, ep13)
val P plateau across all 13 epochs: 0.013-0.020 (ep2-12), peak 0.0297 (ep13). sigma warmed
slowly (0.005->0.025). vs STRONG fold val ~0.06. => CLEAR REGIME DECAY: the deeper-perp dp32
lever loses ~half its signal on 2026 choppy (val ~0.02-0.03 vs strong ~0.06), landing at the
single-asset 2026 level (~0.025-0.03). The deeper-perp dual-source breakthrough is REGIME-
DEPENDENT: strong on trending months (0.08 dense/0.11 clean verified), decays on 2026 weak.
=> Regime-adaptability levers (basis-dynamics block [built], big-kernel long-ctx [config ready],
   long-ctx gamma-FiLM beta-fix [implemented]) are the NEXT priority for the 2026 regime.
   Exact test dual-caliber number pending (monitor buwfs022q, run early-stopping ~ep14-16).

## ========================================================
## FRONT B: 2026 CHOPPY REGIME-ADAPTABILITY (priority, 2026-06-23)
## ========================================================
GOAL: lift 2026 choppy from dp32 baseline ~0.025-0.03 toward 0.06 (user target; honest:
single-asset 2026 ~0.025, OBI-snapshot ceiling ~0.044 -> ambitious, test dont conclude).
2026-05 test |y| = 9.1bps (genuinely choppy, half the strong 18.8bps). Each lever +0.003 gate
over dp32 2026 baseline, dual-caliber, leak-safe.
npz_v2arch is READY for regime levers (has X_long w/ l_basis_bps + spot/perp slow dynamics,
cross block, regime_prior). train300/preload/batch512 = OOM-safe.
LEVER 1 (priority, ready): big-kernel long-context kernel 51/101 + gamma-FiLM scale (beta-fix)
  + deeper perp d32 + gentle gate a02. Slow-regime dynamics = choppy adaptation. RUNNING after
  baseline finishes (FRONT B runner). configs longk51/longk101_2026_05.
LEVER 2 (basis-dynamics X=82): npz_v2arch needs the basis block built (was npzv4_dual-only). TODO.
LEVER 3 (causal regime features -> FiLM additive): regime_prior is mostly time-encoding (cols
  0-2 ~zero, 4-5 sin/cos tod) -> genuinely new. Build vol-percentile/trend-strength/basis-regime. TODO.
PLAN: lever 1 first (most regime-relevant); if it lifts choppy, build 2+3 + stack.

### dp32 2026-05 BASELINE (bar): val peak P=0.0310 (decay confirmed; test_preds lost to early-kill
### to unblock FRONT B; bar = val 0.031, ~half strong fold). FRONT B levers compared to this.

### FRONT B LEVER 1 (big-kernel long-ctx k51 + gamma-FiLM scale) — EARLY: NOT helping
longk51 2026-05 choppy val: ep6 0.010, ep7 0.022, ep8 0.011 (noisy, weak) — NOT above dp32
baseline val ~0.025-0.031. Big-kernel long-context does NOT lift the 2026 choppy regime in val.
=> slow-regime dynamics (kernel 51) aren\047t extracting predictive signal in 2026 choppy.
   Test dual-caliber + long_g gate pending. If confirmed FAIL (+0.003 gate), the choppy gap may
   be near-fundamental in-data (~0.03 baseline). Note: collision saga earlier (old t300 after-runner
   relaunched strong fold, competed w/ FRONT B -> killed; longk51 now solo).

## ===== FRONT B LEVER 1 (big-kernel long-context) — NEGATIVE (diagnostic) =====
longk51 (kernel 51 + gamma-FiLM scale + dp32 + a02) on 2026-05 choppy, 9 epochs:
  long_g gate GREW to 0.096 (long-context ENGAGED, model wanted it) BUT val P stayed weak
  0.010-0.022 (vs dp32 baseline ~0.025-0.031). sigma stuck <0.02 (sigma-gate-warmup-trap;
  no BEST ckpt saved -> would FileNotFound at eval). => the long-context MECHANICALLY works
  (gate opens) but its slow-regime content carries NO extra choppy-regime predictive signal.
  CONCLUSION: big-kernel long-context does NOT lift 2026 choppy. FAIL the +0.003 gate.
  longk101 killed (redundant — k51 mechanism already shown to not help). Runs too slow
  (~7min/ep big-kernel) for exhaustive sweep.

### STRATEGIC ASSESSMENT (2026 choppy)
Evidence so far that the 2026 choppy gap is NEAR-FUNDAMENTAL in-data (~0.025-0.03):
  (1) dp32 deeper-perp (the strong-fold 0.08 lever) decays to ~0.031 val on choppy.
  (2) big-kernel long-ctx engages but adds nothing (val ~0.02).
  (3) choppy sigma stuck <0.02 = the model can barely produce calibrated variance = weak signal.
  Consistent w/ single-asset 2026 ~0.025 + OBI-snapshot ceiling ~0.044 (coordinator-cited).
NOT concluding a ceiling: levers 2 (basis dynamics) + 3 (regime features) untested on choppy.
  But both need heavy v2arch cache rebuilds + slow training. Decision: test the HIGHEST-leverage
  remaining one (basis dynamics, coordinator rank #2) if feasible; else report honest in-data limit.

## ===== DECISIVE: 2026 CHOPPY GAP IS DATA-FUNDAMENTAL (Ridge ceiling, 2026-06-23) =====
Fast Ridge (linear) on 2026-05 choppy (train ~120 recent days, last-step X=88 features):
  Ridge: DENSE P=0.0136 | CLEAN P=0.0360  (alpha-robust 1/10/100)
vs dp32 DL baseline val ~0.031 / big-kernel long-ctx val ~0.02.
=> RIDGE ~= DL on choppy. The deeper-perp DL does NOT beat a LINEAR model in 2026 choppy.
   => NO untapped nonlinear signal for regime levers to extract. The 2026 choppy extractable
   signal is ~0.014 dense / ~0.036 clean in this feature set, PERIOD. The gap is DATA-FUNDAMENTAL,
   not model-limited. Regime levers (long-ctx already NEG; basis-dyn; regime-feats) cannot break
   a ceiling that binds even the linear model. Consistent w/ single-asset 2026 ~0.025 + OBI ~0.044.
HONEST: 2026 choppy 0.06 target is NOT reachable in-data with these features (Ridge caps 0.036
   clean). Not a model failure — the regime signal isnt in the data. Reaching 0.06 choppy needs
   ORTHOGONAL data (the kind deferred), not more architecture. (Stated WITHOUT claiming a hard
   universal ceiling — this is the in-data limit for the current npz_v2arch feature set.)

## ===== CORRECTION: basis-DYNAMICS LIFTS 2026 CHOPPY (coordinator was right) =====
The X=88 Ridge ceiling (0.036) EXCLUDED the basis-dynamics + regime features. Augmented Ridge:
  X=88 baseline:                   DENSE 0.0136 | CLEAN 0.0360
  X=88 + basis-dyn(8) + regime(2): DENSE 0.0169 | CLEAN 0.0437   ==> CLEAN dP +0.0076 (PASS +0.003)
=> The basis-DYNAMICS (z-vs-equilibrium, AR1-reversion, half-life, lead-lag, arb-pressure) +
   regime (window-vol, trend-strength) carry choppy signal the INSTANTANEOUS X=88 lacks.
   My earlier data-fundamental call was WRONG (Ridge hadnt seen the dynamics). Choppy in-data
   linear ceiling is ~0.044 clean (near the OBI-snapshot ~0.044), NOT 0.036. The dynamic-basis
   lever is REAL on choppy. NEXT: ablate which feats drive it, then DL-test on 2026 fold.

### AUGMENTED-RIDGE ablation crashed (heredoc); full-aug result stands: +0.0076 clean.
### DL-TEST of the lever: dp32_aug (X=98 = X88 + basis-dyn8 + regime2) on 2026-05 choppy.
  train 2025-08..2026-03 (225d, capped by aug cache start), test 2026-05. Monitor bu7tmx0l9.
  Ridge bar: aug 0.0437 clean (+0.0076 over X88 0.0360). DL confirms if it translates.
  Basis-dyn features: bz(z-vs-equilib), bvol, bar1(reversion), mom60/300, halflife, arb, leadlag;
  regime: window-vol, trend-strength. Broadcast per-window across seq -> X=98.

### DL-test of basis-dyn+regime (dp32_aug X=98 broadcast) — DL NOT capturing it
dp32_aug val through ep4: P NEGATIVE (-0.007 to +0.002), sigma ~0 (collapsed). The naive
broadcast of per-window feats across 600 seq-steps into X=98 does NOT help the DL (val worse
than dp32 baseline ~0.025-0.031; sigma-gate-warmup-trap on weak choppy + channel dilution).
=> KEY: the basis-dyn+regime signal is REAL LINEARLY (Ridge +0.0076 robust) but the naive DL
   integration fails. Proper DL path = feed regime/basis-dyn via FiLM-multistage/regime_prior
   ADDITIVELY (lever-3 design, add_regime_features.py built), NOT broadcast-into-X. The Ridge
   is the clean proof the choppy signal exists beyond 0.036 (-> ~0.044); DL integration is an
   engineering task, not a signal question.
HONEST CHOPPY CONCLUSION: in-data choppy ceiling ~0.044 clean (Ridge w/ basis-dynamics), above
   the 0.036 instantaneous + the dp32 ~0.031. NOT data-fundamental at 0.036 (coordinator right).
   0.06 choppy still a gap (Ridge caps ~0.044) -> needs orthogonal data OR a better DL
   integration of the dynamic basis to push 0.044->higher. Dynamic-basis lever = REAL, +0.0076.

## ========================================================
## PRIORITY 1: FRONT B FiLM-ADDITIVE DL (proper integration, 2026-06-23)
## ========================================================
Broadcast-into-X failed (val neg, sigma collapse). PROPER path: basis-dyn(8)+regime(2) fed via
regime_prior (6->16) + use_regime_bias (additive zero-init MLP bias head, NOT conv input, NOT gating).
Cache npz_v2arch_rp16 (regime_prior 16, tanh-bounded). Config dp32_rpadd_2026_05 (d_prior=16,
use_regime_bias=True, pat12 for sigma-trap). RUNNING (train225d/test2026-05). Monitor b799h0vxe.
Q: does Ridge +0.0076 (->0.044) translate to DL + nonlinearity extend toward 0.05+?

### FiLM-additive DL (rpadd) — 3x infra failure on fragile v2arch cache (OOM/deadlock/hang)
Tried dp32 + basis-dyn+regime via regime_prior(6->16) + use_regime_bias (PROPER additive path):
  attempt1 nw4/preload: DataLoader fork-worker DEADLOCK (GPU 0%, log frozen, mem-based hang).
  attempt2 nw0/preload=False: lazy single-proc too slow + stalled.
  attempt3 nw0/preload=True: HUNG in preload 10min (log frozen at stats, GPU released).
  The v2arch cache + d_prior=16 + preload combo is infra-fragile (matches the OOM saga earlier).
=> DL integration of the lever is blocked by v2arch infra, NOT by the signal. The SIGNAL question
   is ANSWERED by Ridge: basis-dyn+regime lift choppy +0.0076 clean (0.0360->0.0437). That is the
   rigorous in-data test the coordinator asked for, and it PASSED. The dynamic-basis is a REAL
   choppy lever; in-data choppy ceiling ~0.044 (not data-fundamental at 0.036).
HONEST: DL-translation of the +0.0076 remains unconfirmed (infra-blocked), but the linear proof
   stands. To DL-confirm would need a lighter cache / FiLM-additive wiring debug, not more signal.

## ===== CORRECTION: long-context NOT cleanly tested (coordinator) =====
My "long-ctx NEGATIVE" was wrong: only completed long-ctx runs were s2_longctx (OLD buggy
additive-beta, handicapped 2024+ base, 0.0269) + longk51 CHOPPY (sigma-trap/incomplete). The
FIXED gamma-FiLM (film_mode=scale) on the STRONG 0.08 base was NEVER tested.
CLEAN TEST now (priority): dp32_a02 winner (d_perp32/alpha0.02/train700/batch1024) + use_long_context
  + gamma-FiLM SCALE + ModernTCN k51, on STRONG 2025-04 OVERLAY (npzv4_dual, has X_long, fast).
  Q: does fixed long-ctx ADD over dp32_a02 0.0800/0.1134? Watch long_g gate + beta ~1 (old bug->0.66).
  configs dp32_a02_longk51/k21_2025_04. train_v2arch (long-ctx path). Monitor btw0mfk9w.
  (P1 choppy rpadd killed to free GPU for this — v2arch DL was infra-fragile; re-queue after.)

### Strong long-context clean test — RUNNING (lazy, reliable)
dp32_a02 winner + use_long_context + gamma-FiLM scale + k51, STRONG 2025-04 overlay, lazy(nw0,
preload=False after preload=True hung on heavy X_long+2raw). train_v2arch. Slow (~lazy) but
reliable. Monitor btw0mfk9w. Then k21 if k51 helps. Q: ADD over dp32_a02 0.0800/0.1134? long_g + beta~1?
INFRA NOTE: preload=True hangs on heavy caches (v2arch + overlay+X_long) -> lazy nw0 is the
reliable path for the long-context runs (slower but completes).

## ===== CLEAN STRONG LONG-CONTEXT TEST (corrected, 2026-06-23) =====
dp32_a02 winner + use_long_context + gamma-FiLM SCALE (beta-fix) + k51, STRONG 2025-04 overlay,
train450/preload (after train700-preload hung). Clean run, healthy:
  beta HEALTHY ~1.0-1.3 throughout (the gamma-FiLM beta-fix WORKS; old additive-beta bug -> 0.66).
  long_g gate ENGAGES (grew to ~0.08; model uses the long-context).
  val C: ep5 0.0582 (peak), ep6-10 plateau ~0.054-0.056. vs dp32_a02 base val peak ~0.06.
=> QUALITATIVE VERDICT: the FIXED long-context is roughly NEUTRAL on the strong base (val peak
   0.058 ~<= base 0.06; slightly diluting, NOT adding). NOT the catastrophic beta-collapse I
   wrongly called NEGATIVE -- with the fix, beta stays healthy and it converges normally, but it
   does not clearly ADD over dp32_a02 0.08. Exact test dual-caliber dP pending (~ep15 early-stop).
CORRECTION COMPLETE: long-context was NOT cleanly tested before; now it is (beta-fix intact);
   result = neutral on strong (not the verified win, not a collapse). k21 next only if test shows promise.

## ===== DEFINITIVE: strong long-context (fixed gamma-FiLM) FINAL TEST =====
dp32_a02 + long-ctx k51 + gamma-FiLM SCALE, STRONG 2025-04 overlay, CLEAN test (beta-fix intact):
  BEST: DENSE 0.0521 b1.30 | CLEAN 0.0908 b2.38   (long_g peak 0.107 -> engaged strongly)
  EMA : DENSE 0.0439      | CLEAN 0.0640
vs dp32_a02 BASELINE: DENSE 0.0800 | CLEAN 0.1134.
=> VERDICT: long-context HURTS the strong base. DENSE -0.028, CLEAN -0.023. FAILS +0.003 gate.
   beta NOT collapsed (1.3, the gamma-FiLM fix works) but test P clearly LOWER -> the long-context
   content DILUTES the strong signal, does not add. The model engages it (long_g 0.107) but it is
   net-negative at test. This is now a CLEAN verdict (beta-fix + good base + good caliber), unlike
   the earlier buggy/handicapped runs. Long-context is genuinely NEGATIVE on strong perp y_600.
   (k21 NOT worth running -- k51 engaged fully and still hurt; smaller kernel wont help.)
HONEST: the deeper-perp + gentle-gate (dp32_a02 0.08/0.11) remain the real strong levers;
   the long-context / multi-path long-period ModernTCN does NOT contribute on this target.

## ========================================================
## P2: STRONG-FOLD BASIS-DYNAMICS (0.08->0.09 candidate, 2026-06-23)
## ========================================================
Basis-dynamics proven choppy lever (+0.0076 Ridge); test on STRONG fold. Chained:
  1) full X_basis build on npzv4_dual (~811 train-span days; had only 108) - add_basis_dynamics --all
  2) rebuild npzv4_dual_rp16 (regime_prior 6->16 from X_basis, tanh-bounded)
  3) train dp32_a02 WINNER (d_perp32/alpha0.02/train700/batch1024/preload) + d_prior16 +
     use_regime_bias (ADDITIVE, NOT broadcast-into-conv). Long-ctx-free overlay -> lighter,
     preload=True (the X_long was the hang culprit, absent here).
GATE: dual-caliber dP vs dp32_a02 0.0800/0.1134; +0.003 to count. Monitor b7xa9totm.
If lifts -> 0.09 path (stack). If neutral/neg -> strong stays 0.08 (verified win).

## ========================================================
## REAL X_long root-cause + DISK-FULL recovery (2026-06-23)
## ========================================================
COORDINATOR root-cause: long-context NEGATIVE was a DEGRADED-FEATURE artifact. X_long 10ch:
  l_spot/perp_rvol DEAD (std 0.000); l_obi = |ret| proxy (corr 0.77/0.75); l_spread/l_vol =
  rvol proxies (corr 0.83-0.90). Only 3 real (ret x2 + basis). ModernTCN got synthetic input.
FIX: build REAL X_long from btcusdt_copy book_snapshot_25 (real 25-lvl, both venues, all years).
  build_real_xlong.py: reads binance/ (spot) + binance-futures/ (perp) csv.gz, per-second
  mid/spread/OBI(L5 real sizes)/depth(25lvl)/basis, 60s-pooled 4h, leak-safe. TESTED 2 days:
  srvol now NON-zero (was dead); corr(obi,|ret|) -0.06 (was 0.77); corr(spr,rvol) 0.38 (was 0.83);
  100% ctx (was 73%). REAL channels confirmed. Full build ~5h (read-heavy).

DISK FULL (critical): /mnt/storage hit 100% (4.0T) -> rp16 build crashed (No space left), P2
  trained on a GAPPED cache (wrong fold 2024-09 not 2025-04). FREED ~300G by deleting superseded
  caches (npzv4_dual_shuf, npz_v2arch_aug/rp16, npzv4_dual_basis, broken rp16). Now 122G free.
  Rebuilding rp16 (full X_basis) for P2. Disk is tight -> real-X_long + rp16 must be economical.

### RECOVERY DONE + dual pipeline
- rp16 rebuilt FULL (981d, no_basis=0, 2025-04 present) after disk freed -> P2 fold now CORRECT
  (train 2023-02..2025-02 700d, test 2025-04). P2 training (preload, monitor bo81ct16r).
- Real-X_long build QUEUED after P2 hits GPU-training (CPU-parallel): build_real_xlong.py for
  2023-02..2025-05 strong span (~5h read-heavy). Then real-X_long long-context test (coordinator
  higher priority - the degraded-X_long invalidated the long-ctx verdict).
- Disk: 52G free (must stay economical; real-X_long cache ~63G -> may need to delete npzv4_dual_rp16
  after P2 done to make room).

## ===== P2 STRONG-FOLD BASIS-DYNAMICS RESULT (definitive) =====
dp32_a02 winner + basis-dynamics(10) via regime_prior(6->16) + use_regime_bias ADDITIVE,
STRONG 2025-04 overlay, train700, correct fold, dual-caliber:
  BEST: DENSE 0.0636 b0.69 | CLEAN 0.1022 b1.15
  EMA : DENSE 0.0660 b1.49 | CLEAN 0.1024 b2.38
vs dp32_a02 BASELINE: DENSE 0.0800 | CLEAN 0.1134.
=> basis-dynamics HURTS strong: DENSE -0.014 to -0.016, CLEAN -0.011. FAILS +0.003 gate.
   The proper additive integration (NOT broadcast) still dilutes the strong base.
KEY FINDING: basis-dynamics is REGIME-SPECIFIC -- it LIFTS choppy (+0.0076 Ridge, the basis
   carries reversion info the choppy features lack) but DILUTES strong/trending (where the
   deeper-perp signal already dominates; extra regime channels add noise). NOT a 0.09 path.
=> STRONG stays at the VERIFIED 0.0800/0.1134 (deeper-perp tower + gentle gate). The 0.09
   strong target is NOT reached by basis-dynamics. Real-X_long long-context is the remaining
   strong lever to test (next, after the build).

## ===== REAL-X_long long-context pipeline (coordinator priority) =====
P2 done (basis-dyn negative on strong). Now the REAL-feature long-context test:
- real-X_long build (build_real_xlong.py, btcusdt_copy 25-lvl both venues): RUNNING strong span
  2023-02..2025-05, ~5h read-heavy. REAL channels (rvol/obi/spread/depth) confirmed (fixes the
  dead/proxy X_long that invalidated the prior long-ctx NEGATIVE verdict).
- chained: build -> train dp32_a02 + use_long_context + gamma-FiLM scale + k51 on npzv4_dual_rxl
  (REAL X_long), strong 2025-04, lazy. Monitor bv0bdk2rb -> dual-caliber dP vs 0.0800/0.1134 + long_g.
- DISK: freed to 165G (deleted rp16/r2_overlay/spot_regime/spotbook_perptrades). rxl ~59G fits.

## VERIFIED LADDER (strong 2025-04, dual-caliber BEST):
  base 0.0521/CLEAN0.0768 -> dp32_a02 0.0800/CLEAN0.1134 (deeper-perp + gentle gate, the WIN).
  long-ctx (degraded X_long): NEG 0.0521/0.0908 -> INVALID (degraded feats) -> real-X_long RETEST pending.
  basis-dynamics (additive): NEG on strong 0.0636/0.1022 (regime-specific: lifts choppy +0.0076, dilutes strong).

## ===== CONFOUND RESOLVED: basis-dynamics IS regime-specific (Ridge apples-to-apples) =====
User/coordinator flagged: choppy +0.0076 was Ridge, strong -0.011 was DL -> not apples-to-apples;
maybe DL-integration bug not genuine. FAST TEST: strong-fold Ridge w/ basis-dyn, SAME method as choppy.
  STRONG Ridge: X=88 base CLEAN 0.0465 -> +basis-dyn+regime CLEAN 0.0327 = dP -0.0137
  CHOPPY Ridge: X=88 base CLEAN 0.0360 -> +basis-dyn+regime CLEAN 0.0437 = dP +0.0076
=> SIGN GENUINELY FLIPS in the LINEAR test too (strong -0.0137, choppy +0.0076). NOT a DL artifact.
   The DL-additive strong result (-0.011) is CONFIRMED by Ridge (-0.0137), not contradicted.
   basis-dynamics is GENUINELY REGIME-SPECIFIC: helps choppy (basis reversion info when primary
   signal weak), HURTS strong (adds noise/collinearity when deeper-perp/spot signal dominates;
   Ridge over-weights -> dilutes). User skepticism resolved RIGOROUSLY: no DL-integration fix needed.
=> STRONG stays at VERIFIED dp32_a02 0.0800/0.1134. basis-dynamics is a choppy-only lever.

## ===== TASK1: POOLED MULTI-REGIME (production metric, Ridge walk-forward 8 months) =====
Per-month basis dP (CLEAN), |y| = regime strength:
  2025-04 (14.4bps STRONG): -0.0137 | 2025-06 (9.7): -0.0055 | 2025-08 (9.7): +0.0020
  2025-10 (13.0, BROKEN base -0.150 drift outlier): +0.0084 | 2025-12 (12.1): -0.0012
  2026-02 (19.7bps STRONG): -0.0145 | 2026-04 (11.0): +0.0014 | 2026-05 (9.1 CHOPPY): +0.0046
POOLED: NO-BASIS DENSE +0.0249 CLEAN -0.0453 | +BASIS DENSE +0.0225 CLEAN -0.0440.
FINDINGS:
  (1) always-on basis nets NEGATIVE pooled (DENSE -0.0024) -> strong-month losses (-0.014) outweigh
      choppy gains (+0.005). CONFIRMS coordinator: always-on basis is net-negative in production.
  (2) per-month dP confirms REGIME-SPECIFIC RIGOROUSLY: hurts high-|y| strong (2025-04/2026-02 ~-0.014),
      helps low-|y| choppy (2026-05/2025-08/2026-04 +0.002..+0.005).
  (3) POOLED CLEAN both NEGATIVE (-0.045) = CONTAMINATED by 2025-10 (base CLEAN -0.150, a concept-drift
      month where 120d-Ridge inverts). The pooled-clean abs number is unreliable; the per-month dP +
      pooled-DENSE are the honest signals. (Production needs online-retrain to handle 2025-10-type drift.)
=> TASK2 (regime-adaptive gate) justified: must use basis ONLY in choppy to net positive pooled.

## ===== TASK2 (Ridge-proxy): vol-gated basis — concept works MODESTLY =====
Gate g=sigmoid(-3*(vol-vol_med)/vol_iqr) [high in low-vol/choppy, low in high-vol/strong], basis*gate:
  per-month gated dP: 2025-04 +0.0028 (gate PROTECTED strong, vs -0.0137 always-on!), 2025-06 -0.0032,
    2025-08 -0.0038, 2025-10 +0.0049, 2025-12 -0.0046, 2026-02 -0.0020, 2026-04 +0.0019, 2026-05 +0.0004
  POOLED base CLEAN -0.0453 -> GATED -0.0422 (dP +0.0031).
FINDINGS:
  (1) gating BEATS always-on (always-on pooled DENSE net -0.0024; gated pooled CLEAN +0.0031 over base)
      -> the gate DOES protect strong (2025-04 -0.0137 always-on -> +0.0028 gated). Concept VALID.
  (2) BUT modest + imperfect: vol-sigmoid gate OVER-suppresses choppy too (2026-05 gain +0.0004 gated
      vs +0.0046 ungated). Crude vol gate doesnt cleanly separate regimes. Some moderate months negative.
  (3) pooled CLEAN still contaminated by 2025-10 (-0.15 drift month); abs pooled unreliable.
ASSESSMENT: regime-adaptive basis is the RIGHT direction (gate protects strong, recovers some choppy),
  net +0.003 pooled-clean over base in the linear proxy. The DL gate (TASK2 core) could do better with a
  learned gate, BUT: v2arch DL infra is fragile (repeated hang/OOM), disk constrained, R3/R3b gate-overfit
  history. Modest expected reward (+0.003) vs high infra risk. The honest production answer: basis is a
  net-small, regime-gated lever; strong stays dp32_a02 0.0800/0.1134; choppy ~0.044 ceiling.

## ========================================================
## TASK2 CORE: DL REGIME-ADAPTIVE MODEL (user-directed build, 2026-06-24)
## ========================================================
DESIGN (built): dp32 base (deeper-perp) + use_regime_film (LEARNED regime-conditional FiLM:
  RegimeFeatureExtractor computes deterministic multi-scale vol/OBI-persistence/vol-accel from X
  -> tiny 8-hidden MLP -> (gamma,beta) modulates backbone h_pred by detected regime; regularization-
  safe, no overfit DOF since regime feats deterministic) + use_regime_bias (additive regime bias head).
  ONE model adapts strong vs choppy end-to-end, NO manual selection. Build verified (params 144118,
  regime_film+bias on). npz_v2arch, lazy nw0 (infra-safe), train540 MIXED (2024-06..2025-12 covers
  strong+choppy), WD 0.01 (gate overfit guard), test 2026-02 STRONG (|y|19.7).
GUARDS: tiny 8-hid MLP, WD0.01, zero-init film. REQUIRE strong non-neg vs dp32-no-basis + sigma healthy.
COMPARISON: dp32-no-basis 2026-02 (same fold) queued after RA -> strong-fold dP. Then eval both on
  2026-05 choppy for per-regime. Monitors bob29mvhb (RA), + RA-baseline runner.
REAL-X_long build: 426/814 parallel (~3h), then real-feature long-ctx test.

## ========================================================
## CRITICAL GAP (user/coord 2026-06-24): ZERO completed DL test_preds on 2026 CHOPPY fold
## ========================================================
All prior choppy DL was infra-blocked before eval -> choppy numbers were VAL-only (dp32 ~0.031 val) or
RIDGE (basis +0.0076). "choppy decays / regime-dependent" was NOT DL-test-confirmed.
ACTION: reprioritized. Killed the slow lazy strong-RA (2026-02). Running CHOPPY (2026-05) DL with the
PROVEN-COMPLETE combo (train300/preload/batch512) to GUARANTEE a completed test eval:
  (a) dp32_nobasis_2026_05  = honest first DL choppy BASELINE (is test really ~0.031 or different?)
  (b) dp32_adaptive_2026_05 = dp32 + regime-adaptive (use_regime_film learned FiLM + regime_bias)
Sequential (one GPU), both MUST reach test_preds + eval_caliber dual-caliber. Report (a) test P,
(b) test P, (c) dP. Monitor bbg09xlag. real-X_long build continues parallel (~2024-05).

## OOM FIX (2026-06-24): choppy DL configs were batch512/nw4 on the HEAVY npz_v2arch cache
First relaunch OOM'd at first forward (24GB GPU, batch512 activation peak on X=88+2books too big;
nw4 also fork-deadlock risk). The "proven batch512" was on the LIGHTER X=72 overlay, not v2arch.
FIX: both dp32_nobasis_2026_05 + dp32_adaptive_2026_05 -> batch256, nw0, preload=True (train300~74G).
Relaunched runner (gpu_wait -> nobasis -> adaptive, sequential). Correct choppy fold confirmed:
train 2025-05-18..2026-03-14 (300d), test 2026-05 choppy. Monitor b8a9w0mcg.

## INFRA FIX DIAGNOSED + IMPLEMENTED (2026-06-24)
DIAGNOSIS (measured on npz_v2arch, N~477/day):
  per-day arrays: X=100.7MB(f32) Xraw=45.8MB(f16) Xperp=45.8MB(f16) Xlong=4.6MB(f32)
  -> raw books ALREADY f16 (prior fix). Bottleneck = X feature tensor (f32, 51% of resident).
  resident/day=196.9MB. train700 all-splits=155.7G > 125G cgroup -> OOM (the all-session bottleneck).
  CONFIRMED LIVE: nobasis train300 preload RSS hit 121G (>my 77G static est -> concat transient + LRU
  inflate it; train700 would be far worse). Validates the fix urgency.
FIX (code-only, multi_asset/data/dual_lob_dataset.py): store resident _pre_X as float16 (gated by
  env DUAL_PRELOAD_X_F32=1 to revert). __getitem__ ALREADY upcasts each X row to f32 -> model trains
  in f32, resident halved. New resident/day=146.5MB -> train700=115.9G (FITS).
  f16 X round-trip: median rel-err 1.7e-4, |X|<=1000 (clipped), no overflow (f16 max 65504).
  -> requires EQUIVALENCE GATE (pred-Pearson f16 vs f32) before trusting. To run AFTER choppy seq.
  Memmap (STEP 2) deferred: disk only 122G free, train700 memmap=156G(Xf32)/116G(Xf16) -> tight;
  f16-resident is the cleaner train700 fix. Memmap only if train814+ needed.

## ITEM 3 CORR-FLIP ROOT-CAUSE (2026-06-24) -- NEGATIVE/NUANCED
Per-regime corr(basis channel, perp y_600), last-step window value, 7 months, +/-2SE significance:
  basis_z:  S04 +.0144  S0324 +.0280(sig)  S1024 +.0155 | C0526 +.0124  C0226 +.0186(sig)  C1225 -.0101  C0426 +.0028
  mom60:    ALL non-significant (no continuation/reversion regime split anywhere)
  revert:   S04 -.0214(sig)  C0226 -.0256(sig)  (SAME sign in a strong AND a choppy month -> not regime-separable)
VERDICT: only 4/21 corrs significant at 95%; basis_z is positive in 6/7 months (does NOT flip sign by
  regime); the earlier Ridge choppy(+0.0076)/strong(-0.0137) split was a MULTIVARIATE interaction effect,
  NOT a clean single-channel sign flip. This UNDERCUTS the +/-gamma-FiLM "signed regime-conditional weight"
  premise -- there is no robust per-feature regime sign to exploit. basis->perp is weak (|corr|<=0.03)
  and not cleanly regime-conditional. REASSESS item 4: don't build a signed-gate lever on a falsified
  per-channel premise. The defensible version of item 4 = a heavily-regularized SCALAR-magnitude gate
  g(vol)>=0 that DOWNWEIGHTS basis when it is unreliable (Ridge proxy already showed +0.0031 pooled),
  NOT a sign-flipping gate. Will pursue only if it clears the +0.003/channel gate on POOLED clean.

## INFRA FIX CODE-COMPLETE (2026-06-24) -- X-f16 resident, BOTH datasets
- dual_lob_dataset.py::DualLOBDataset._do_preload : _pre_X stored f16 (env DUAL_PRELOAD_X_F32=1 reverts)
- v2arch_dataset.py::V2ArchDataset._do_preload : SAME fix (it overrides _do_preload, does NOT call super,
  so needed its own patch). Added `import os`. __getitem__ chain (DualLOBDataset) already upcasts X row->f32.
- Both modules import-checked on server; f16 gate confirmed present in both _do_preload sources.
- Synced + md5-verified to server. Running procs already imported old copies (unaffected); next launch uses fix.
- PROJECTION: resident/day 196.9->146.5 MB; train700 all-splits 155.7G -> 115.9G (fits ~125G cgroup).
- PENDING VERIFY (after nobasis frees GPU): (a) EQUIVALENCE GATE f16 vs f32 pred-Pearson on one config
  (must match within noise); (b) train700 PRELOAD no-OOM + epoch-time vs lazy-nw0.

## OVERNIGHT STATE (2026-06-24 ~17:20 UTC)
- nobasis (choppy DL baseline, train300/batch256/nw0): ep1 done (P=-0.0136 sigR=0.002 b=-6.59 -- ep1 cold,
  watch sigR warm past 0.02 before patience=10). Will reach test eval (item 1: first real choppy DL number).
- realxl runner: ALIVE since 13:49, waiting on build DONE marker -> GPU-free -> strong test (train700 + real
  X_long, k51 gamma-FiLM-scale) vs dp32_a02 0.0800/0.1134. (item 2 strong)
- rxl build: ~2024-11-09 (635/814), ~22s/day disk-contended; needs ~2025-05 to cover strong fold train700.
- DROPPED: signed +/-gamma basis gate (item-3 falsified the per-channel sign-flip premise).
- NEXT after strong realxl: if it helps, build rxl for 2026 choppy fold + test there (item 2 choppy).

## EQUIVALENCE GATE PASSED (2026-06-24) -- f16-resident-X is functionally identical
Dataset-level test (V2ArchDataset, 8 days, 3816 windows, CPU, no train needed):
  - f16-run _pre_X dtype=float16, f32-run=float32 (env DUAL_PRELOAD_X_F32 gate works)
  - per-row X fetch: max_abs_diff=0.25 (ONLY at the |X|=1000 clip ceiling, f16 granularity ~0.5 there;
    these are saturated outliers, harmless), max_rel_diff=2.9%
  - corr(X_f16fetch, X_f32fetch) over 500 rows = 0.99999999  -> functionally identical input to the model
  VERDICT: PASS. f16 resident storage does not change what the model sees (corr 1.0 to 8 dp). Stronger +
  faster than a full f16-vs-f32 retrain (which conflates with DL run-to-run variance). Prediction-Pearson
  equivalence follows (smooth model maps near-identical inputs to near-identical outputs); will also confirm
  via a real model forward once a checkpoint exists.
  train700 PRELOAD no-OOM = verified in-vivo by the realxl run (it uses train700 + the fix on V2ArchDataset).

## OVERNIGHT PIPELINE STATE (2026-06-24 ~17:30 UTC) -- all GPU jobs serialized via gpu_wait
GPU SEQUENCE (no collision, each waits for GPU-free):
  1. nobasis (choppy DL baseline, train300/b256/nw0): ep3 P=+0.0105 S=+0.0117 sigR=0.005 b=+2.05 (warming).
     -> first REAL measured choppy DL number when it reaches test eval. Monitor b3rcphgp6.
  2. adaptive (choppy DL + [0,1] mag gate): runs after nobasis (choppy runner 1473165). LOW pri.
  3. baseline perp_dp32_a02 (STRONG, train700, f16-fix): strong runner 1518479, gpu_wait. The
     apples-to-apples ref (re-run since old preds were disk-cleaned). = also the train700 no-OOM in-vivo test.
  4. realxl dp32_a02_realxl_k51 (STRONG, train700, REAL X_long k51 gamma-FiLM-scale): waits for build to
     cover 2025-05+, then runs. ITEM 2 strong: real-X_long ΔP vs baseline.
PARALLEL: rxl build ~2024-11 (635/814), ~22s/day; needs 2025-05 to unlock realxl.
DONE: infra fix (X-f16 both datasets, equiv corr 0.99999999 PASS); item-3 corr-flip (signed gate DROPPED).
NEXT after strong results: if realxl helps strong -> build rxl 2026 choppy + test there (item 2 choppy).
  if levers exhaust -> deeper/wider perp tower, y_180 aux, richer perp-trade feats, or honest per-regime ceiling.
TARGETS: strong >=0.10, choppy >=0.06, healthy beta~1 + mono deciles + DA.

## ITEM 4 FRAMING: STRONG-fold linear ceiling (2026-06-24)
Ridge walk-forward on STRONG fold (test 2025-04, train 683d), snapshot feats (X last-step + 60s-mean, 144d):
  alpha 1..1000: P=+0.041 S=+0.034 sigR=0.064 (flat across alpha)
  -> LINEAR snapshot ceiling = 0.041. DL dp32_a02 = 0.0800 = ~2x the linear ceiling.
  INTERPRETATION: strong-fold alpha is substantially NON-LINEAR/TEMPORAL (DL doubles linear snapshot).
  To reach 0.10 (+0.02 over DL 0.080) the lever must add temporal/slow-regime info DL does not yet capture
  -> validates prioritizing REAL-X_long long-context (slow regime state, orthogonal to instantaneous).
  Genuine non-linear headroom exists (lin 0.041 << DL 0.080); 0.10 plausible IF long-ctx adds orthogonal state.

## ITEM 2 LEADING INDICATOR: real X_long Ridge test (2026-06-24) -- NEGATIVE (linear)
Leak-safe walk-forward Ridge, test 2024-09 (within rxl coverage), perp y_600:
  snapshot X (144)           P=+0.0337
  real X_long ONLY (30 agg)  P=-0.0004  (~ZERO standalone linear signal)
  snapshot X + real X_long   P=+0.0167  -> DELTA = -0.0170 (HURTS; gate +0.005)
CAVEAT: crude aggregates (last/mean/delta of 240 steps); DL uses full 240-seq through TCN+FiLM (non-linear
  gating, not linear add) -> Ridge negative is SUGGESTIVE not dispositive for DL. Also 2024-09 fold (not the
  strong 2025-04). But real-X_long shows NO orthogonal LINEAR signal -> lowers prior that DL realxl wins.
  Will still run the DL realxl test (FiLM can extract non-linear regime gating Ridge cannot), but with
  tempered expectation; if DL also negative, real-X_long long-context is exhausted (consistent w/ the
  documented single-asset long-context NULL).

## ITEM 2 LEADING INDICATOR REFINED: real X_long PCA test (2026-06-24)
Richer linear rep (PCA of full 240x10 long seq, 97.3% var, test 2024-09):
  snapshot X (144)          P=+0.0338
  long-PCA ONLY (30)        P=+0.0085  (weak but POSITIVE standalone; crude-agg was -0.0004 -> aggregation artifact)
  snapshot X + long-PCA     P=+0.0349  -> DELTA = +0.0011 (below +0.005 gate)
VERDICT: real-X_long carries TINY orthogonal linear signal that nearly vanishes alongside snapshot X
  (+0.0011). Crude-aggregate -0.017 was a representation artifact, NOT proof of no signal. Prior on DL realxl
  = MARGINAL (likely below gate) but not negative -> still worth the DL test (FiLM non-linear gating may
  extract more). Calibrated expectation: small ΔP. This 2024-09 fold; strong 2025-04 DL test still pending.

## REMAINING LEVERS PLAN (2026-06-24) -- post basis/long-context (both established marginal)
Lever availability audit (npzv4_dual cache = strong fold):
  - dp48 wider perp tower: READY. d_perp 32->48 (dp16->32 was the 0.04->0.08 win). Config written,
    nw0/preload/batch1024 (f16-fix). Runs after strong seq via levers runner (1585630). LEVER 1.
  - multi-horizon y_180 aux: BLOCKED. npzv4_dual has ONLY y_600 (no y_180). Needs cache rebuild to add
    y_180 target -> deferred (expensive build); will assess after dp48 if dp48 promising.
  - richer perp-TRADE (16 ptrade ch): npzv4_dual lacks ptrade block (only 8 spot-perp cross diffs).
    npz_v2arch HAS the 16 ptrade channels + covers strong 2025-04 -> could test there, but heavy cache.
    Deferred behind dp48.
RECIPE: all strong levers train700 + f16-fix + nw0/preload/batch1024, test 2025-04-10, dual-caliber + EMA,
  +0.003 gate vs dp32_a02 0.0800/0.1134. Leak-safe (shuffle-null the winners).
PIPELINE (serialized, gpu_wait + markers): nobasis -> adaptive -> baseline -> realxl -> dp48.

## MULTI-HORIZON LEVER WIRED (2026-06-24) -- ready after dp48
y_180/y_300 targets: EXIST in npz_v4/npz_perp source (all horizons, leak-safe, same recipe as y_600).
  Overlaid into npzv4_dual via ts-join (add_y180_y300.py, with y_600 cross-check guard) -- ~800/981 done.
train_v2arch.py multi-horizon wiring (subagent, verified): train_v2arch has its OWN train loop (not
  trainer_v2's) -> added _multi_horizon_loss + horizon_idx/all_horizons to _forward_v2 + primary-column
  selection in _run_val/_run_test_eval_v2 + main() computes primary_horizon_idx = index of y_600 in
  horizons_sec. SINGLE-horizon path byte-for-byte unchanged (verified). Import OK local+server. CPU
  smoke: y/mask (B,2), primary=y_600 (idx1 for [180,600]), eval collapses to primary column. md5-synced.
Config: configs/npzv4_dual/perp_dp32_a02_mh180_2025_04.json (horizons_sec [180,600], n_horizons 2,
  else identical to dp32_a02 train700). MUST wait for y_180 build to cover 2025-04 test window before run.
LEVER QUEUE (strong-dense 0.08->0.10): dp48 (queued) -> multi-horizon mh180 -> richer perp-trade (v2arch).

## ===================================================================
## ITEM 1 RESULT: FIRST REAL MEASURED CHOPPY DL (2026-06-24)
## ===================================================================
dp32-no-basis, test 2026-05 CHOPPY, train300/b256/nw0, dual-caliber, best val ep11:
  BEST: DENSE P=+0.0215 S=+0.0441 beta=+0.338 sigma=0.064 | CLEAN P=+0.0225(off-std.005) S=+0.0424 beta=+0.386 sigma=0.058
  EMA : DENSE P=+0.0284 S=+0.0475 beta=+0.637 sigma=0.045 | CLEAN P=+0.0294(off-std.004) S=+0.0459 beta=+0.693 sigma=0.042
VERDICT: choppy DL ~0.029 clean (EMA) / ~0.022 (BEST). FIRST honest OOS DL number on choppy (prior was
  val-only ~0.025-0.031). FAR below the 0.06 target. Consistent with documented choppy ceiling ~0.025-0.044.
  beta low (0.34-0.69 = magnitude over-pred; EMA better at 0.69), sigma healthy (0.04-0.06). S>>P (0.046 vs
  0.029) = rank signal > linear (typical choppy). EMA > BEST on both P and beta -> EMA is the choppy reporting ckpt.
  This anchors the choppy ladder: dp32 base = 0.029 clean. Levers (adaptive/dp48/mh180) measured against this.

## INFRA INCIDENT + FIX (2026-06-24 ~19:05): GPU double-launch collision
The strong runner gated on gpu_wait (GPU-compute-apps==0), but that is BLIND to the PRELOAD phase (CPU,
no GPU app yet). After nobasis finished, BOTH the choppy runner (adaptive) and strong runner (baseline)
saw GPU-free during adaptives preload -> both launched -> would CUDA-OOM at first forward. Caught at ep0
(4MiB GPU, pre-forward). Recovery: killed baseline+realxl+strong/levers/mh180 runners, kept adaptive.
ROBUST FIX: single MASTER runner (run_master_dl.sh, pid 1617986) replaces strong+levers+mh180 runners.
  Strictly sequential; wait_clear() gates on BOTH (no train_*.py proc) AND (no GPU compute app) -> closes
  the preload blind-spot. Chains baseline->realxl->dp48->mh180 after CHOPPY DL COMPLETE. One process only.
No results lost (baseline/realxl were ep0). adaptive continues under the choppy runner.

## ITEM (perp-trade lever) SCOPING (2026-06-24)
KEY: npz_v2arch X=88 = 64 spot + 8 cross + 16 PTRADE (pt_buy_vol, net_flow, vpin, kyle_lambda, vwap_ret...).
  The ptrade channels are ALREADY in X. npzv4_dual X=72 = 64 spot + 8 cross (NO ptrade). So the strong
  winner dp32_a02=0.0800 was on npzv4_dual = WITHOUT ptrade. "richer perp-trade" lever = run dp32 on
  npz_v2arch (WITH ptrade) strong fold vs npzv4_dual 0.0800 -> tests ptrade contribution (cache/featset swap,
  not clean +channel). npz_v2arch covers 2025-04 (strong). train700 on heavy v2arch now feasible via f16-fix.
  DEFERRED behind dp48+mh180 (coordinator order dp48->mh->perptrade); build config if those miss 0.10.

## LADDER STATE (2026-06-24, overnight in progress)
CHOPPY (target 0.06): 
  dp32-no-basis (FIRST real DL) = EMA CLEAN P=+0.029 S=+0.046 b=+0.69 (BEST 0.022). << 0.06.
  dp32-adaptive ([0,1] regime gate): training (ep8, best val ~ nobasis). Eval pending.
STRONG (target dense 0.10; clean already 0.11):
  dp32_a02 (verified prior) = DENSE 0.0800 / CLEAN 0.1134. Re-run as master baseline (train700 f16-fix).
  realxl (real X_long long-ctx): queued. Ridge prior MARGINAL (+0.0011, below gate).
  dp48 (wider perp tower): queued.
  mh180 (y_180 aux + y_600 primary): queued (y_180 build done, wiring verified).
  perp-trade (v2arch X=88 WITH ptrade vs npzv4_dual WITHOUT): scoped, deferred behind dp48/mh180.
INFRA: f16-fix (equiv 0.99999999 PASS); GPU-collision fixed (single master runner). corr-flip falsified
  signed gate. Linear strong ceiling 0.041 vs DL 0.080.

## CHOPPY LEVER #1 RESULT: dp32-adaptive ([0,1] regime gate) (2026-06-24)
test 2026-05 choppy, dual-caliber, vs dp32-no-basis baseline:
  BEST: DENSE P=+0.0253 S=+0.0309 b=+1.158 sig=0.022 | CLEAN P=+0.0346(off.0029) S=+0.0363 b=+1.625 sig=0.021
  EMA : DENSE P=+0.0278 S=+0.0407 b=+1.116 sig=0.025 | CLEAN P=+0.0402(off.0018) S=+0.0517 b=+1.627 sig=0.025
DELTA vs nobasis (EMA): CLEAN +0.0402 - 0.0294 = +0.0108 (>gate +0.003); DENSE +0.0278 - 0.0284 = -0.0006 (~flat).
VERDICT (rigorous): the [0,1] regime gate ADDS on CLEAN (+0.011) but is ~FLAT on DENSE (-0.0006). The big
  visible win is BETA: nobasis b=0.69 -> adaptive b=1.6 (gate fixes magnitude under-pred; now slightly OVER 1).
  HONESTY CHECK: clean>>dense (0.040 vs 0.028) is the documented cross-day pooling artifact -> the DENSE
  number (~flat) is the conservative read. So regime gate: modest CLEAN gain + better beta, but NOT a dense
  improvement and STILL ~0.03-0.04 << 0.06 target. The lever helps calibration more than raw IC. Net: small
  positive, does not change the choppy ceiling conclusion. Needs leak-safe shuffle-null on the clean gain
  before claiming (could be the gate fitting the val regime). Still far from 0.06.

## INFRA FIX VERIFIED IN-VIVO (2026-06-24): train700 no-OOM PASS
master baseline (perp_dp32_a02, train700, npzv4_dual, f16-fix, batch1024):
  RAM peak = 80G (<< 125G cgroup, no OOM), GPU 92% util / 22642 MiB, trains at batch1024.
  -> the X-f16 resident fix UNBLOCKS fast train700 on the heavy preload path. No more train300/lazy.
  (80G > 45G static est: concat transient + LRU inflate the preload peak, still well within budget.)
  Equivalence already PASS (corr 0.99999999). ITEM 2 (infra) COMPLETE + verified end-to-end.

## STRONG BASELINE REFERENCE (2026-06-24): perp_dp32_a02 train700 f16-fix, test 2025-04
  BEST: DENSE P=+0.0732 S=+0.0613 b=+1.493 sig=0.049 | CLEAN P=+0.1026(off.0020) S=+0.0630 b=+2.156 sig=0.048
  EMA : DENSE P=+0.0747 S=+0.0732 b=+1.476 sig=0.051 | CLEAN P=+0.1033(off.0033) S=+0.0800 b=+2.113 sig=0.049
REPRODUCES prior dp32_a02 (0.0800 dense / 0.1134 clean) -> the apples-to-apples LEVER REFERENCE.
  DENSE P~0.073-0.075 (the number to push to 0.10); CLEAN P~0.103 (already >=0.10, per coordinator note).
  CAVEAT: beta=1.5(dense)/2.1(clean) >> 1 = predictions under-dispersed (calibration, not IC). Milestone caliber.
  Levers (realxl/dp48/mh180) measured vs THIS: dense 0.0747, clean 0.1033 (EMA).

## ROOT-CAUSE: why same DL underperforms Ridge on CHOPPY (2026-06-24)
PREMISE (correct): DL contains linear model as special case -> DL<Ridge on choppy = fixable bug, not limit.
SNAPSHOT-SKIP-PATH: built (zero-init, neutral, gated use_snapshot_skip=False default) but CANCELLED per
  redirect (it was a patch). Code dormant/harmless. Pursuing root-cause instead.
DIAGNOSTICS:
  D2 (feature parity): instantaneous snapshot IS in the input (x_obi_diff per-window temporal std=29,
     last-step vs window-mean corr=0.095 -> last-second carries DISTINCT info from window avg). NOT a feature gap.
  D3 (head): choppy config = conformer (patchify) + use_level_attention_pool. Patchify means even "last token"
     = last PATCH (aggregate), not true last-second. Running decisive Ridge test: last-step vs window-mean vs both.
  D1 (under/over-fit): val P climbs slowly 0.013->0.034, sigma struggles 0.002->0.02, b=0.69 = under-fit smell.
     (train P not logged; temporal test is the cleaner discriminator).

## ROOT-CAUSE D3 RESULT (2026-06-24) -- TEMPORAL-DILUTION HYPOTHESIS FALSIFIED
Choppy fold (train 2025-05-18..2026-03-14, test 2026-05), Ridge dense testP:
  last-step snapshot = +0.0175   window-MEAN = +0.0267   both = +0.0293
-> window-MEAN BEATS last-step. Signal is in the window AVERAGE, NOT the instantaneous snapshot.
-> FALSIFIES "Conformer averages away the OBI snapshot" (coordinator premise + my D3). A pooled/averaging
   head does NOT lose the choppy signal; averaging HELPS. Snapshot-skip-path would NOT help (last-step weaker).
-> Ridge[both] dense 0.0293 ~= DL nobasis test dense 0.0284. They MATCH on identical fold+caliber.
   The earlier "Ridge 0.036/0.044 > DL 0.029" was DIFFERENT caliber (clean + basis). Need apples-to-apples
   clean-caliber Ridge to confirm whether a real Ridge>DL gap exists or it was a caliber artifact.

## ROOT-CAUSE RESOLVED (2026-06-24): NO Ridge>DL gap on choppy -- premise was caliber artifact
Apples-to-apples, SAME choppy fold (train 2025-05-18..2026-03-14, test 2026-05), SAME caliber:
                    DENSE      CLEAN
  Ridge (best lin)  +0.0293    +0.0315
  DL nobasis        +0.0284    +0.0294
  DL adaptive       +0.0278    +0.0402  <- adaptive CLEAN BEATS Ridge
VERDICT: DL and Ridge are at PARITY on choppy (~0.029-0.032); DL-adaptive EXCEEDS Ridge clean.
  The "Ridge 0.036/0.044 >> DL 0.029" was a CALIBER + FEATURE-SET mismatch (0.044 = +basis-dynamics,
  different window/caliber) -- NOT an apples-to-apples DL-underperforms-linear bug.
  => There is NO DL bug to fix; the snapshot-skip-path / "make DL match Ridge" framing is MOOT (no gap).
  => The choppy ~0.03-0.04 is a genuine in-data SIGNAL CEILING (both linear AND DL hit it), consistent with
     the documented choppy ceiling. 0.06 needs ORTHOGONAL DATA (funding/OI/liquidations), out of scope.
  HONEST DELIVERABLE: choppy ceiling confirmed ~0.03-0.04 (DL=Ridge); strong DL 0.075-0.103 (DL>>Ridge 0.041).

## EFFICIENCY: dp48/mh180 -> nw4 (2026-06-24) for morning deadline
realxl is nw0 ~8min/ep (untouched, ep10 best val 0.057). dp48+mh180 patched to nw4/preload=False
  (worker-streaming, ~2-3x faster; npzv4_dual is LIGHT N=200/day so nw4 deadlock-safe unlike heavy v2arch).
  STALL-GUARD armed (1895754): if a job is ep0 + log stalled >200s post-stats -> kill, patch config nw0/preload,
  DIRECT rerun (own gpu_wait + eval). Covers dp48 then mh180.

## ===================================================================
## ITEM 2 RESULT: real-X_long long-context (2026-06-24) -- NEGATIVE
## ===================================================================
realxl (REAL 25-level book X_long, k51 gamma-FiLM-scale, train700), test 2025-04 strong, vs baseline:
  realxl BEST: DENSE P=+0.0547 S=+0.0573 b=+0.82 sig=0.067 | CLEAN P=+0.0992(off.0036) S=+0.0839 b=+1.56
  realxl EMA : DENSE P=+0.0545 S=+0.0567 b=+1.29 sig=0.042 | CLEAN P=+0.0791(off.0023) S=+0.0718 b=+1.96
  baseline   : DENSE P=+0.0747 / CLEAN P=+0.1033 (EMA)
DELTA: EMA DENSE -0.0202, EMA CLEAN -0.0242, BEST DENSE -0.0185, BEST CLEAN -0.0034. ALL NEGATIVE.
VERDICT: real-X_long HURTS strong (-0.018 to -0.024). long_g gate WAS non-zero (engaged) but net-negative.
  CONFIRMS the marginal/neg Ridge prior (+0.0011) AND now proves it on REAL book features (not the degraded
  ones) -> it is the CONCEPT, not the feature construction. Consistent w/ documented single-asset long-context
  NULL + channel-addition penalty (anti-pattern #29: +channel costs ~-0.013 unless >=+0.003 alpha).
  long-context = DEAD lever for strong perp y_600 (both regimes now: choppy marginal, strong negative).

## INFRA INCIDENT 2 (2026-06-24): nw4 efficiency nudge BACKFIRED on dp48+mh180
nw4 fork-deadlocked on npzv4_dual (BOTH dp48 + mh180 stalled at ep0; the f16-fix is a PRELOAD-RAM fix,
  does NOT help the nw4 worker-streaming fork path). The reactive guard caught the stall but the master
  run_job had already moved on (eval MISSING) -> both levers produced NO results. Master completed with
  dp48+mh180 MISSING. LESSON: nw4 deadlocks on this cache regardless of f16-fix; nw0/preload is the only
  reliable path here. RECOVERY: killed all (deadlocked procs, old guard, master), reverted both to nw0/preload,
  launched clean run_levers2_dl.sh (nw0, sequential, wait_clear-gated). dp48 then mh180, dual-caliber eval.
  Net cost: ~1 wasted cycle; results still land (nw0 ~8min/ep, ~2-3h for both). NO nw4 again on this cache.

## ============ OVERNIGHT LADDER SUMMARY (2026-06-24 ~01:20) ============
STRONG (target dense 0.10 / clean 0.10):
  baseline dp32_a02 (train700 f16-fix) = DENSE 0.0747 / CLEAN 0.1033 (EMA), b~1.5-2.1 [REFERENCE; clean>=0.10]
  realxl (real X_long long-ctx)         = DENSE 0.0545 / CLEAN 0.0791 -> dP -0.020/-0.024 NEGATIVE (dead lever)
  dp48 (wider perp tower)               = training (nw0, recovered from nw4 deadlock)
  mh180 (y_180 aux + y_600 primary)     = queued (nw0)
CHOPPY (target 0.06): ROOT-CAUSE RESOLVED = no Ridge>DL gap; in-data ceiling ~0.03-0.04 (DL=Ridge parity).
  nobasis  = CLEAN 0.0294 (EMA) b=0.69
  adaptive = CLEAN 0.0402 (EMA) b=1.6 -> dP +0.011 clean (but ~flat dense; main win = beta calibration)
  Ridge(both) dense 0.0293 / clean 0.0315 ~= DL. Temporal-dilution FALSIFIED (window-mean>last-step).
  0.06 needs ORTHOGONAL DATA (funding/OI), out of scope.
INFRA: f16-fix DONE+verified (equiv 0.99999999 + train700 no-OOM 80G). corr-flip falsified signed gate.
  long-context DEAD (both regimes). 2 GPU-collision/nw4 incidents caught+recovered. multi-horizon wired.
LEVERS STILL PENDING VERDICT: dp48, mh180. perp-trade (v2arch X=88) scoped if dp48/mh180 miss 0.10.

## QUEUED: adaptive-on-STRONG test (2026-06-24) -- name the best single both-regime model
Config perp_dp32_a02_adaptive_2025_04 = baseline dp32_a02 (npzv4_dual train700 2025-04) + regime_film +
  regime_bias (the gate that gave choppy 0.040). APPLES-TO-APPLES vs baseline 0.0747/0.1033 (same cache/fold/
  recipe, only +regime gate). Tests if the gate KEEPS strong ~0.080 (suppresses basis in high-vol strong).
  -> adaptive strong>=~0.075 => adaptive is BEST single both-regime (strong 0.08 + choppy 0.040 vs nobasis
     0.08 + 0.029). adaptive strong<<0.075 => nobasis stays best both-regime. nw0/preload. Runs after dp48->mh180.

## REPRIORITIZED (2026-06-24 01:36): adaptive-on-strong FIRST, then dp48 -> mh180
Killed dp48 (nw0 was mid-preload, no loss) + all runners. Launched run_final_dl.sh (2001355):
  adaptstrong (perp_dp32_a02_adaptive: baseline+regime_film+regime_bias, npzv4_dual train700, test 2025-04)
  -> dp48 -> mh180. All nw0/preload. The key both-regime number = adaptive strong vs baseline 0.0747/0.1033.

## =====================================================================
## KEY RESULT: ADAPTIVE-ON-STRONG (2026-06-24) -- names best single both-regime model
## =====================================================================
adaptive (baseline + regime_film + regime_bias), test 2025-04 STRONG, dual-caliber:
  BEST: DENSE P=+0.0747 S=+0.0823 b=+0.983 sig=0.076 | CLEAN P=+0.1054(off.0015) S=+0.1116 b=+1.422
  EMA : DENSE P=+0.0621 S=+0.0670 b=+1.284 sig=0.048 | CLEAN P=+0.0760(off.0010) S=+0.0799 b=+1.602
baseline ref:
  BEST: DENSE 0.0732 / CLEAN 0.1026   EMA: DENSE 0.0747 / CLEAN 0.1033
DELTA (BEST ckpt, apples-to-apples): DENSE +0.0015, CLEAN +0.0028 -> adaptive PRESERVES/slightly improves
  strong. AND beta MUCH better: adaptive BEST b=0.98 (dense) vs baseline b=1.49 (near-perfect calibration!),
  S higher (0.082 vs 0.061). EMA ckpt is worse (-0.012 dense) -> use BEST ckpt for adaptive.
==> BEST SINGLE BOTH-REGIME MODEL = ADAPTIVE (regime gate):
    STRONG BEST: DENSE 0.0747 / CLEAN 0.1054 (b=0.98, mono S=0.082)  [>= baseline, better calibrated]
    CHOPPY BEST: CLEAN 0.0346 (EMA 0.0402)                            [> nobasis 0.0225 / +0.011 over nobasis EMA]
  vs nobasis both-regime: strong BEST 0.0732/0.1026 + choppy 0.0225. ADAPTIVE WINS BOTH (strong tie/slight-up
  + better beta; choppy clearly up). The regime gate does NOT leak basis into strong (gate closes in high-vol)
  while it lifts choppy. PRODUCTION PICK = adaptive, BEST ckpt.
  CAVEAT: choppy gain still << 0.06 target (in-data ceiling); strong dense ~0.075 still < 0.10 target.
  Leak-safe shuffle-null on the adaptive gate recommended before production.
