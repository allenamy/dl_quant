# AUDIT NOTES — Rounds 1-3 block (caliber pin, ground truth, six tracks, instruments+gates, cost model)
> created 2026-09-12 | auditor: handoff-audit subagent | scope: trackA..trackF, attacks, infra1/2, r2_*, r3_*, r3k, p6, event_state, stoploss_frequency
> Every sha below RECOMPUTED this session with `shasum -a 256` on the local file. NOTHING copied from a document.

## 0. SHA LEDGER (all RECOMPUTED, all MATCH the claiming document)
b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650  trackA/w10_sleeve.py            (pinned device)
295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53  r3k_impact/costb_PWR_G230k.json (the cost book)
3fd2f76496a593ba5342bbf8dd21d9f52473a52fe55657b7592f30d06143ab11  r3_gates/devices/rs_conc.py     (tail ruler)
2ce8b88b49ae54626d13219e2317836b7a5485c36da26fd5c768d4e2e2a1fd06  r3_placebo/null_families.py     (repaired nulls)
91d4c91cb92a64404f8e635a76969b435b86ab7840fc110564d9509a1b0c7fa9  r3_attack_RESID_SHARPE/null.py  (shift/relabel battery)
64d4c3469b42b52b8fd4c39cd25f00d5d6d1291278c2e62684f5abdafb49b4ed  r3_gates/devices/offspec.py
e222289a027c933de552e441cca60dd30f62188dba51f2482bd117abb6ff9059  r3_gates/devices/echo.py
62f6186ed52c5ec43a28ff780655ffdb0e4554917756b05ac154e0f65f8e6c1f  r3_gates/devices/echo2.py
f38d7024975a05e5e6f0c594c4f435fb39b3a24ccb030ecdfd414a1137e3bf23  r3_gates/devices/rs_recon.py
e3e877783e61a2dea3cc994c82bbddc35d71cf633e7f05ba33135874e03e976e  r3_gates/devices/rejudge.py
a6bae3a1975c7b325321f798f0e3d46c8bb1e022dc604e2e39d0b0db8a28ea87  trackB_devices/w10_tb.py
58c586f3ccb98b18b740df079edbe4896fd27d53c3d61a7497d399d7370a894d  infra1_cost/extract_fill_costs.py
943ada020d675e360fed9163c38556b9ab68553d79a050ef9cd7f345bf1088a8  infra1_cost/reprice.py
299c041fda4fe7362a2be9c03bd2b80cd34d72557dc9d1b4cbb584795543d35b  infra1_cost/killcurve.py
3d49859270ac54b30e7b0c7de7b9a738c92ed5f53de1ca0b749cc054b3ad6768  infra1_cost/mk_costb.py
18729ce3f8619ee079f59f7faf55e8159312c92711880feaf2c55ea2423cf520  PREREG_r3_instrument3_xib_seeds_2026-09-11.md
e2e7273d58a861854da6ad03c4f6809c0dfead9737e0223e91bcfff4bb771ca9  PREREG_gateA_offset_spectrum_2026-09-11.md
f5152851830310ef3e3a4ee200ccfedc7aa6176be392e996374feeda820938ec  p6_receipts/p6_book.py
=> ZERO SHA MISMATCHES in this block. sha hygiene is the strongest part of the programme.
   CAVEAT: every /workspace/... artifact (meta_newprod_v4.npz, dev_v4 probe npz, lobcube.npz, preds/*.npy,
   w10_health.py 8684d9a9…) is REMOTE and was NOT verifiable from this machine. All parity/GATE-P claims
   resting on them are INFERRED, not VERIFIED, by me.

## 1. THE COST MODEL — costb_PWR_G230k.json (the denominator of the programme)
PRODUCER: r3k_impact/r3k_fitK3.py (read in full). Inputs: r3k/lobcube.npz (LOB cumulative notional at
band edges 0.2%/1%/2%/3%/4%/5%), meta_newprod_v4.npz (qvk -> QV), the ARCHIVED A0 weight matrix
w10_ablation_series_V4_A0_dyn_s42.npz d30_n2_c42_W. tier_stats.json supplies fees/spread/maker share.

WHAT K=0.17 ACTUALLY IS — read the code, not the label:
  agg() returns K_excess = book_excess_bps / infra1_K1, where infra1_K1 = turnover-weighted
  IMP_K1 = [0.638144642177287, 1.557767793871295, 4.5250173304217896] from infra1/replay_participation.json.
  IMP_K1 is the K=1 square-root-law reference (calib6.py: imp = sqrt(participation)*sigma_4h).
  => K=0.17 is a RATIO ("the measured book-walk is 0.17x what a K=1 sqrt law would charge"),
     NOT a fitted coefficient that appears anywhere in costb_PWR_G230k.json. That file contains NO K field.
  VERIFIED: FITK_v3_shape.json POWER.K_excess = 0.17, K_excess_CI95 = [0.1522, 0.1883], bootsd 0.0091.
  The CI is a 2000x UTC-day block bootstrap, rng default_rng([20260905, 31]).

THE alpha=0.87 CLAIM IS WRONG FOR THIS FILE:
  CLOSEOUT L2, PREREG_r6 L204, RESULT_r10 L2 all say "K=0.17, alpha/冲击指数 0.87".
  costb_PWR_G230k is built from walk_power(), whose inner-band VWAP ~ Q^(1/p) with
  p_exponent_turnwtd = 1.2777 => implied_impact_exponent_alpha_1_over_p = 0.7826 (FITK_v3_shape.json).
  0.8739 is a DIFFERENT estimand: FITK_v2.json FINE2026.powerlaw_vwap_vs_participation.pooled.alpha,
  an OLS slope of log(vwap_bps) on log(participation) POOLED ACROSS TIERS (r3k_fitK2.py L100-108).
  Within-tier slopes on the same sample are 1.2661 / 1.2076 / 0.9884 -- ALL above 1. The pooled 0.87 is a
  between-tier (Simpson) artifact, and on the coarse-band all-history sample the same pooled statistic
  reads 0.7517. So "alpha = 0.87" describes neither the model nor a within-name impact curve.

FIT SUPPORT AND EXTRAPOLATION (the reviewer's best attack):
  - LOBCUBE_COV.json: mean_names_by_year 2022=0, 2023=0, 2024=0, 2025=0, 2026=525.1. The +-0.2% band
    exists ONLY in 2026. Tier impacts are measured on 1331 2026 anchors and applied to 2022-2026.
    mk_costb.py CAL_BASE declares this and asserts the 1%-band control makes it conservative (0.40x);
    I did NOT find a standalone machine receipt for that 0.40x number -> UNRECEIPTED AS STATED.
  - LIVECHECK2.json: replay turnwtd participation z at G=230k is 0.15929. Live taker z support:
    median 0.00111, p90 0.00861, p99 0.04841, MAX 0.14936. The replay's turnover-weighted operating
    point is ABOVE the live maximum. The model is evaluated entirely outside its live support.
  - LIVECHECK.json: book-walk predicted slope 9.5 bps per unit z; live anchor-FE regression slope
    307.612 (se 92.709), CI95 [-19.65, +614.44] z-only. Point estimate = 32x the model; CI contains 0.
    Trimmed spec fit_trim99 gives 876.869 [134.4, 1536.6]; fit_trim95 gives 136.5 [-279, +1168].
    The live check neither confirms nor refutes the model; it is 1064 taker rows over 86 anchors.
  - MAKER LEGS ARE CHARGED THE FULL AGGRESSIVE WALK. mk_costb emit(): maker_bps = fee_mk + I_t.
    81-85% of live fills are maker. Declared as deliberately conservative. There is NO adverse-selection
    term at all -- which is exactly the 6.7164 bps the infra dispute is about.
  - BLENDING WEIGHT MISMATCH (quantified by me, arithmetic from the two receipts):
    book_avg 2.9537 = 2.6705*0.3092 + 2.6824*0.4041 + 3.6417*0.2867 (turn shares from
    infra1/replay_participation.json = FULL-HISTORY replay). But the impacts were measured on 2026,
    where FITK_v2 FINE2026 turn shares are 0.1073/0.2474/0.6453. Reweighting with the measurement
    sample's own shares gives 3.3002 -- 11.7% higher. 2.954 is a full-history-weighted average of
    2026-only impacts; it understates what the 2026 book pays.
  - HALF-SPREAD constants are hardcoded in r3k_fitK3.py L21 as [1.0999658777781905, 1.638999737554008,
    2.4344380023739175]; I checked these equal tier_stats.json "all" spread_bps/2 exactly. OK.
  - FILLS DEDUPE: extract_fill_costs.py L45-51 keys (symbol, trade_id) and upgrades only when the
    incumbent LACKS mid_at_fill_plus_60s => the +60s backfill IS captured. Receipt: n_raw 81161,
    n_dedup 33886, dup_same 47275, dup_diff 0. The last-wins trap did NOT bite here. VERIFIED.

## 2. THE DEFECTIVE PLACEBO — contamination map
Canonical receipts: r3_placebo/REPORT_FULL.txt, MATCH_DIAGNOSTIC.json, LEGACY_AUDIT.json, JUDGE_r3_placebo.json.
16 arms were re-judged against R (relabel-bijection), RO (relabel-orbit), T (per-name rotation), with the
legacy per-anchor permutation kept as positive control P_legacy.

LEGACY-vs-MATCHED overstatement (VERBATIM from REPORT_FULL.txt, these ARE receipted):
  LOBDEPTH_RAW      +1.9339 -> +1.2629  (+53%,  legacy cost ratio 46.2x)
  ORTH_LISTEVT      +0.7908 -> +0.4559  (+73%,  44.8x)
  ORTH_AMIRESID     +1.7346 -> +1.0402  (+67%,   7.5x)
  AMI_lag           +1.8199 -> +0.9310  (+95%,   7.9x)
  ORTH_amihud       +1.7644 -> +0.9046  (+95%,   7.9x)
  RESID_SHARPE      +2.4916 -> +1.2374  (+101%, 10.6x)
  RESID_SHARPE_s2027+2.5436 -> +1.2832  (+98%,  13.5x)
  ORTH_AMI3D        +1.3525 -> +0.6252  (+116%, 40.8x)
  LOBDEPTH_ORTH     +1.6921 -> +1.0518  (+61%,  42.2x)
  ORTH_RESSKEW      +1.0850 -> +0.1979  (+448%, 29.0x)
  TBF_ema08         +0.7683 -> +0.5963  (+29%,   1.9x)
  XIB_LAG50_s42     +0.5658 -> +0.5529  (+2%,    1.8x)   <- for the XIB family the defect barely moves it
  XIB_LAG50_s2027   +0.5779 -> +0.5510  (+5%,    1.8x)
  XIB50_s42/s2027, IB_TRI_B_s42: +5%/+6%/+5%
  => "53-448%" VERIFIED (LOBDEPTH_RAW 53%, ORTH_RESSKEW 448%).

** THE "2.6-7.7x TURNOVER" RANGE IS NOT RECEIPTED AS STATED **
  Repeated in CLOSEOUT L68, PREREG_r3_resid_deployable L66, PREREG_r5_basis_newdata L89,
  RESULT_r5_basis_newdata L104, RESULT_r5_newdata2 L157.
  MATCH_DIAGNOSTIC.json P-family TURNOVER ratios (I recomputed the range from the receipt):
    XIB50 1.696 | TBF 1.686 | IB_TRI_B 1.846 | ORTH_AMIRESID 2.266 | AMI_lag 2.344 | ORTH_amihud 2.346
    RESID_SHARPE 3.259 | ORTH_RESSKEW 9.297 | ORTH_AMI3D 13.481 | LOBDEPTH_ORTH 13.727
    ORTH_LISTEVT 14.497 | LOBDEPTH_RAW 16.360    => RANGE 1.686 - 16.360
  COST ratios range 1.861 - 46.211.
  The only "2.6" I could source is r2_sleeve/RESULT L109 (TBF turnover .035->.091 = 2.6x, a single arm).
  "7.7" matches no turnover ratio; the nearest receipted values are the AMI-family COST ratios 7.5-7.9.
  => the range mixes a turnover ratio with a cost ratio AND understates the max by 2.1x (turnover) / 6x (cost).

STILL-CONTAMINATED / STILL-UNRESOLVED after the repair:
  7 of the 16 re-judged arms came back UNRESOLVED_null_not_matched (pooled cost ratio outside [0.75,1.25]):
  RESID_SHARPE_s2027, LOBDEPTH_RAW, RESID_SHARPE, LOBDEPTH_ORTH, TBF_ema08, ORTH_LISTEVT, ORTH_RESSKEW.
  For these the repaired instrument did NOT succeed; their round-1/2 verdicts are neither confirmed nor
  replaced. 9 arms read SURVIVES (ORTH_AMIRESID, AMI_lag, ORTH_amihud, ORTH_AMI3D, XIB_LAG50 x2,
  XIB50 x2, IB_TRI_B_s42).
  Any round-1/2 arm NOT in the 16 has never been re-judged at all; the re-judge list was not
  cross-checked against a complete round-1/2 arm census in any receipt I found.

PRESENTATION DEFECT IN REPORT_FULL.txt (VERIFIED by reading r3_judge.py L86-118 + the JSON):
  For arms with a PAIR baseline, row["real"] and the per-family NL rows are arm-MINUS-BASELINE
  (lvl() paired branch), while the pooled ALL row's NL_net/NL_gross are RAW levels (G.mean()), and
  every margin is RAW-minus-RAW. Example XIB_LAG50_s42|FULL: RE_net +0.4167 (a difference),
  pooled null_g +0.6060 (a level), margin_net +0.5529 (= raw real 1.15887 - 0.6060).
  The table cannot be recomputed from its own printed columns. Verdicts are internally consistent;
  the level columns are not comparable to the margin columns.

COVERAGE MISMATCH INSIDE ONE TABLE: RESID_SHARPE rows carry n=7908, LOBDEPTH n=7849, the rest n=9018.
  r3_attack RECEIPTS.json "no_full_cycle_number_exists": the RESID_SHARPE arm's only pre-2023 rows ARE
  the 900 warm-up anchors, so its "FULL" is F23. Margins are compared across arms on different samples.

## 3. XIB_LAG50 CHAIN
  Definition (PREREG_r3_xib L14-18): producer shadow_loop_v3.py L471 fund leg becomes
  0.5*xz_in_base(f_fund_ema_v1) + 0.5*xz_in_base(f_amihud_24h with the 24h window ending one anchor early).
  rho to A0 = +0.8891 -> it is a REWEIGHTING OF THE WHOLE BOOK, not a sleeve. Blast radius = the book.
  PREREG STATUS: BLOCKED. S3 (repaired GATE A) and S4 (blocking tests B1/B2) are declared 未跑 (NOT RUN).
  It is a ruling document, not an execution permit, and it says so.

  Frozen-window readings (r3_gates/rejudge_windows.json, n=3168):
    as-judged  dyn_s42 +0.4698 [+0.0958,+0.8375]; dyn_s2027 +0.3932 [-0.0038,+0.7669] -> (C) UNDECIDED
    post-warm  dyn_s42 +0.4698 [+0.0851,+0.8962]; dyn_s2027 +0.3932 [+0.0048,+0.7914] -> (A) PASS
  ** THESE TWO ROWS ARE THE SAME SAMPLE. ** rejudge.py L32-33 labels the second
  "(identical, warm<start)"; L47-53 pass a RUNNING COUNTER ci as the bootstrap sub-stream, so the two
  rows draw default_rng([20260905,2]) vs default_rng([20260905,6]). Same n, same mean, different CI,
  DIFFERENT VERDICT LETTER. The dyn_s2027 lower bound is -0.0038 vs +0.0048: the frozen-window verdict
  for the programme's headline candidate is inside the bootstrap's own Monte-Carlo error at B=2000.

  Seed verdict (RESULT_r3_instrument3, prereg sha 18729ce3f8619ee0 VERIFIED): REJECT.
  dyn 4/6, fix 0/6. Six seeds' paired deltas span [+0.3932,+0.4540], cross-seed sd 0.0294 (6.8% of effect);
  per-anchor paired-difference series correlate 0.969 (dyn) / 0.984 (fix) across seeds. The t ceiling on
  the prereg window is 2.12 (dyn) / 0.66 (fix): more seeds cannot reach 1.96 on fix. Single-seed PASS
  probability on fix = 0.000. The fix REJECT was determined before the first seed ran.
  The later attribution of the 0/6 to a stale W3FIX constant lives in ROUND 5 (DOCKET_r7 L249,
  RESULT_r5_angle1) and is OUTSIDE this block; I verified only the round-3 side.

## 4. W3FIX = (0.21, 0, 0.79)
  VERIFIED in source, trackA/w10_sleeve.py:
    L27-28  W3FIX = os.environ.get("W3FIX"); assert W3FIX == "0.21,0,0.79"   (single-value whitelist)
    L170-172 w3_at(i): if W3FIX is not None: return np.array([...])  -- returns before any leg-return
             logic, for all 10039 anchors, all three legs pinned.
  It is a REPLAY DEVICE ENV KNOB ONLY. The deployed producer runs WRULE=msharpe dynamic seats
  (PREREG_r3_xib L18 quotes shadow_loop_v3 L456 P["msharpe_look"]=900). There is no code path by which
  the live book runs a constant seat triple => "never runnable by the deployed code" is VERIFIED.
  WHERE W3FIX NUMBERS APPEAR IN MY BLOCK: RESULT_trackA_carry_sleeves §(falsifier #1, "fixed live seat");
  RESULT_r3_instrument3 §"fix 席位" (the 0/6 REJECT); r3_gates rejudge fix_* rows; p6_receipts/gateP_p6.py
  (GATE P fix cells); RESULTS_window_percentile.json config_json; PREREG_gateA §8 run line.
  NONE of these present a W3FIX number as deployable; every one labels it a fixed-seat robustness read.
  The danger is the reverse: PREREG_universe_dyn_2026-09-04 §2 (quoted in RESULT_r5_angle1 L27) had said
  "the deployment-equivalent reading is PRIMARILY W3FIX", i.e. a non-runnable configuration was once the
  PRIMARY reference. That inheritance, not this block's usage, is the live hazard.
  SIDE EFFECT WORTH KNOWING: with W3FIX set, w3_at never takes the p<LOOK branch, so the E-0911-A
  warm-up mechanism (w3=[1/3,1/3,1/3] + LEGS-mask bypass) does NOT fire on fix-seat arms. Dropping their
  first 900 anchors is therefore sample loss, not bias removal (INFERRED: I did not rule out other warm state).

## 5. AMIHUD SLEEVE a=0.20 -- BOTH HALVES
  HALF 1 (the gain) VERIFIED from p6_receipts/P6_COMBO_PAIRED.json:
    s42  a=.20 dSR point +0.24579898, k0 CI95 [+0.03364,+0.45866], k9 [+0.03147,+0.47190]
    s2027 a=.20 dSR point +0.24074513, k0 [+0.03190,+0.45531], k9 [+0.03051,+0.46384]
    => 4/4 lower bounds > 0. VERIFIED.
    BUT frozen s2027 CI95 = [-0.004553, +0.620407] -> G2 is 3/4, which the prereg itself states.
  HALF 2 (the give-away) -- WEAKER THAN STATED IN BOTH DOCUMENTS:
    dg_point s42 -0.0025163, s2027 -0.0058134. Chain -0.0025163*2190*2.0 = -11.02 bps/yr NAV: arithmetic
    VERIFIED. BUT the same receipt gives dg_ci95 s42 k0 = [-0.11941, +0.12038] and P(dg>0) = 0.4825.
    The dg CI is ~47x wider than the point estimate and straddles zero symmetrically. So "Delta-g is
    negative at every allocation" is a POINT-ESTIMATE-ONLY statement; Delta-g is statistically
    indistinguishable from zero. Neither PREREG_p6 nor PREREG_ship1 foregrounds the dg CI. This cuts
    FOR the sleeve, not against it, and the handoff should say so.
  WHERE THE +0.2458 ACTUALLY COMES FROM (P6_COMBO.json by_year, s42):
    A0     2022 +0.48  2023 -1.936  2024 +1.088  2025 +1.187  2026 +5.433
    sleeve 2022 +0.168 2023 +1.861  2024 +1.197  2025 +1.379  2026 +2.407
    combo  2023 -1.237 2024 +1.239 2025 +1.408 2026 +5.944
    SR_A0_frozen 2.9357 vs SR_sleeve_frozen 1.9267; rho_frozen -0.0124 (s42) / +0.0292 (s2027).
    The sleeve is WORSE than A0 in the frozen window and far worse in 2026. The whole full-sample
    Sharpe gain is the 2023 repair. 2023 is ONE YEAR and it is A0's only negative year.
  ** CROSS-ROUND KILL SHOT (my finding, from two receipts in this block) **
    trackF/RESULT_trackF §1 establishes, from a coverage scan, that A0's 2022 and 2023 rows are
    FUND-LEG-ONLY: king OOS predictions are non-finite for all of 2022 and 2023 in
    SLOW_v3_on_v4axis.npy / SLOW_v4.npy / slow_pred_hist_oos.npy (anchors with >=10 finite names:
    2022 = 0, 2023 = 0; 2024/2025/2026 = 2196/2190/1452), the DL leg sits in the king slot and is
    silenced with it, and AR_KF_p0 2023 = AR_FUND 2023 = -0.606 exactly.
    => the Amihud sleeve's headline ΔSharpe is diversification against a DEGENERATE ONE-LEG
       baseline, not against the deployed three-source book. This is the single most load-bearing
       unstated qualification in the block. (trackF's coverage scan is reported in prose with the
       AR_KF_p0 / AR_FUND equality as its receipt; I did not find a standalone JSON for the scan.)
  CAPACITY (P6_CAPACITY.json): sleeve_g 0.6764 < A0_g 0.6890 already at 230k; at 2300k SR 1.1334 vs
    A0 1.1411 and at 4600k 0.7736 vs 0.8481 -- the standalone sleeve's SR edge inverts with size.
  DEPLOYABILITY GAP (P6_PARITY.json): "R2_meanlogqv_vs_PANEL" = the producer's current construction
    vs the research panel: bitwise_equal_frac 1.75e-05, max_abs_rel_diff 803719, spearman_mean 0.9890,
    spearman_min 0.8736. The live producer would NOT compute the researched feature.
    Also RESEARCH_extcube_vs_PANEL_holefix2: nan_pattern_equal FALSE (3,125,890 vs 3,140,350 finite
    cells), spearman_min 0.5566 -- a v3/v4 lineage delta sitting inside p6.
  rho RISING IN THE LOSS CELLS (+0.342 LL / +0.438 HL) is RESULT_r7_fuel2 L161 -- ROUND 7, outside this
    block. Not verified by me. p6's own rho readings are the full-sample 0.1490/0.1553 and
    frozen -0.0124/+0.0292.

## 6. RESID_SHARPE -- WHICH INSTRUMENTS, AND ARE THEY INDEPENDENT?
  (a) GATE A / S7-R R2 era stability (PREREG_gateA L79-80): xic pre-2025 +0.0225 -> 2025-on
      -0.0079 [-0.0115,-0.0043] (s42) and +0.0250 -> -0.0193 [-0.0231,-0.0154] (s2027). Sign flip, CI
      excludes 0 => FAIL.
  (b) rs_recon.py rank IC (r3_gates/rs_reconcile.json): 2025-on rank IC -0.00973 (s42) / -0.02151 (s2027)
      while leg_ret +2.4179 / +2.0864 bps and leg Sharpe 4.02 / 3.27.
  (c) rs_conc.py tail ruler (r3_gates/rs_concentration.json): 2025-on top20_share_of_mean 1.2977 (s42) /
      1.8892 (s2027); ex_top20 -0.7198 / -1.8553 bps; ex_top20_sharpe -2.399 / -5.596.
      Control LIVE_FUND 2025-on: 0.1109 / +2.5535 / +6.709 -- THIS is the source of the brief's
      "11.09% / +6.71". It is the LIVE FUND LEG control, not RESID_SHARPE.
  (d) turnover-matched shift nulls (r3_attack RECEIPTS.json matched_F24_span_n5718): ARM 1.0674,
      SHIFT101 1.1816, SHIFT503 1.0862, SHIFT1009 -0.1762 => the arm is 3rd of 4.
  (e) marginal contribution over XIB_LAG50: F23 +0.569 [-0.165,+1.300]; F24 -0.000 [-0.832,+0.894];
      FROZEN +0.091 [-0.979,+1.201]; y2026 -0.884 [-2.149,+0.331]; only y2023 +2.814 [+0.974,+4.670].
  (f) the resid term is inert vs plain SHARPE: F23 +0.037 [-0.771,+0.821], rho 0.707.
  (g) SHUFFLE-FUTURE (r3_receipts/CONTRAST_SHUFY.json) -- the strongest and least advertised:
      FULL n=9018 arm 1.119 vs shufy 0.395; dmean CI95 [-0.0132,+1.5481] CONTAINS 0;
      dSharpe CI95 [-0.148,+2.754] CONTAINS 0. FROZEN both contain 0. Only F23 dSharpe [0.157,3.285]
      excludes 0, and even there dmean [-0.002,1.773] does not.
      => RESID_SHARPE does not beat its own shuffled-future control in net mean at 95% in ANY window.
  INDEPENDENCE: (a)(b)(c) are three views of ONE fact -- the 2025-on cross-sectional ordering is
  negative -- computed on the same leg construction, the same prediction files, the same era split.
  (b) and (c) are near-mechanically linked (negative rank IC + positive leg return IMPLIES tail
  concentration). (d)(e)(f)(g) are book-layer tests and are genuinely independent of (a)-(c) and
  largely of each other. So "killed by four instruments" is true in count but overstates independence:
  there are about TWO independent axes plus the shuffle-future control.
  LEAKAGE, honest: r3_receipts/LEAK_r3b.json RESID_SHARPE_s2027_f23span
  clause1_canonical_future_no_peak_PASS = FALSE (|ic| at k=+2 is 0.00865 vs |ic(0)| 0.00464).
  One seed fails the canonical future-no-peak clause outright.

## 7. GATE A / offset spectrum -- read the sign convention before quoting it
  offspec.py docstring: k=0 = forward alpha; k=-1 = the bar that just CLOSED before the anchor; k<=-2 older.
  Negative k is PAST information and is legal. offspec_mean.json k=-5..+5 means:
    LIVE_FUND_f_fund_ema_v1 peaks at k=0 (0.007880)
    XIB_LAG50_avgrank peaks at k=-2 (0.019481) vs k=0 (0.014204)     ratio 1.37
    AMI_SLEEVE_ORTHLAG peaks at k=-2 (0.024615) vs k=0 (0.012880)    ratio 1.91
    CTRL_MOM7_legal_trailing peaks at k=-1 (0.09533) with k=0 = -0.03378
    CTRL_REV4 k=-1 = -0.96307 (mechanical)
  A literal reading of the desk checklist ("offset-spectrum peak @ 0") FAILS both XIB_LAG50 and the
  Amihud sleeve. The programme addressed this deliberately: PREREG_gateA RETIRES the backward-IC gate
  with measured operating characteristics (of 13 causal arms it rejected 10, including 2 of the 3
  in-service legs; of 2 synthetic leaks it rejected 0 -- "ANTI-correlated with the thing it claims to
  detect") and replaces it with S7-R (echo-adjusted forward IC + era stability + declared causal edge +
  spectrum-position falsification, argmax <= -1 for edge-0 arms). Calibration receipts: null xic -0.0004
  (CI contains 0), pure lag-1 reversal xic -0.00336 [-0.00386,-0.00288], oracle +0.9605.
  Under S7-R the three in-service legs PASS (king +0.0511, DL +0.0270, fund +0.0092) and the gate BITES
  the two live candidates (AMI_SLEEVE_ORTHLAG FAILs R2 at 0.21 < 0.25; RESID_SHARPE both seeds FAIL R2).
  ** DECLARED PERMANENT BLIND SPOT, and the reviewer's best single attack **: the synthetic leak
  CTRL_LEAK_XIB_FWD50 (Amihud window pushed one anchor into the FUTURE) reads ic(0) +0.0213 / xic +0.0235
  and passes every spectrum test -- HIGHER than the honest XIB_LAG50 (+0.0142 / +0.0151). GATE A cannot
  detect a one-anchor lookahead in EXACTLY the feature family that survived this block.
  ** SELF-DECLARED FRAGILITY **: the R2 threshold 0.25 was chosen by the author; the in-service DL leg
  clears it at 0.32. At 0.35 the in-service leg would FAIL. Logged as a declared sensitive cell.

## 8. WINDOW / n CHAOS INSIDE THIS BLOCK (every number must carry its n)
  n = 3168   frozen 2025-03-01..2026-08-10 20Z (trackB/C/D/E/F, r3_gates, XIB seeds)
  n = 5718   2024-on post-warm
  n = 7849/7908  F23 post-warm (rs_conc windows are 2023-01-01..2026-08-10, split 4386 + 3522)
  n = 9018   FULLCYCLE post-warm to 2026-08-10 20Z (r3_placebo, r3_gates, p6)
  n = 9139   FULLCYCLE post-warm incl. 08-31 (regime_composition, NETTING_BOUND)
  n = 9918   FULLCYCLE NO warm drop to 2026-08-10 (infra1_cost, r3k parity)
  n = 10039  full device axis
  ROUND-12's W_ALPHA (9138) and W_TAIL (10038) DID NOT EXIST YET. Nothing in rounds 1-3 is on them.
  Consequence for the handoff: every alpha/Sharpe/turnover number in this block sits on n=3168, 7908,
  9018, 9139 or 9918, NOT on W_ALPHA. Every tail/maxDD number in this block that is post-warm (9018)
  DROPS 2022-06-07 and is therefore biased optimistic relative to W_TAIL.

## 9. WINDOW-COMPOSITION FINDING (receipted, and it deflates the pinned baseline)
  r3_gates/regime_composition.json: frozen window is 94.26% HH cells, eff_cells 1.124, g 1.8937,
  Sharpe 3.043, se 0.831. FULLCYCLE post-warm (9018): HH 51.46%, g 0.7421, Sharpe 1.524, se 0.493.
  Full history (10039): g 0.6152, Sharpe 1.213. => "Sharpe 3.04" is a one-regime-cell reading.
  The caliber pin's §4 baseline quotes the 3.04 frozen number as the thing to be beaten.

## 10. E-0826-D (ENV WHITELIST / RERUN COMMAND) COMPLIANCE IN THIS BLOCK
  HAVE a local command/env receipt: trackA (commands.txt, run_uplift.sh, launch_arms.sh),
    trackB_devices (run_tb.sh, ARMLIST.txt), trackD_v4 (device_commands.txt), trackE (SHA256SUMS_pod.txt +
    devices/commands_trackE.txt), trackF (runF.sh, arsenal.sh, setup_tree.sh), r3_gates (run line in
    PREREG_gateA §8), p6_receipts (gateP_p6.py builds the env explicitly), infra1_cost (*.log),
    round2_factor_sleeves (gateP.sh + logs), trackB_attack (run_attack.sh), attack_trackD (drive*.log).
  NO local command/env receipt at all: r3k_impact (the COST MODEL -- no run.sh, no RUN_ENV json),
    infra2, r3_placebo (gateP.sh only, no arm-run env), r3_receipts, r3_integrate, r2_sleeve/devices,
    r2_horizon/devices, r2_learned/devices, r2_lob/artifacts, r2_timeseries (no devices dir at all),
    event_state/devices, stoploss_frequency/devices, attack_trackA_carry, trackC/devices_v4.
  ** The single most-cited artifact in the programme (costb_PWR_G230k.json) has NO recorded env
     whitelist and NO recorded run command in this repo. ** Rounds 5-8 later adopted RUN_ENV json files
     (RECEIPT_r7_fuel1, R8_RUN_ENV.json, R12_RUN_ENV.json); rounds 1-3 mostly did not.

## 11. ROUND-2 DEFECTS FOUND BY ROUND 3 (all three are in-block, all VERIFIED)
  r3_attack RECEIPTS.json "errors_found_in_round2_inputs":
  (i) carry sign mislabel: the -0.21x carry values belong to the SIGN-MIRROR SLm book, not the arm;
      measured F23 carry/net = +0.1865 (carry PAID, not received).
  (ii) r2_learned/corr_matrix_f23.json is mislabelled: its span is 2024-01-01 onward n=5718, not F23.
       Proof reproduces to 5 dp.
  (iii) r2_learned/devices/judge_r2.py L66 `t0,g0,R0=A0["42"]` is hoisted OUT of the arm loop, so every
       SL_*_s2027 arm's blend50 / dSharpe columns are paired against A0 SEED 42. I READ THE SOURCE AND
       CONFIRMED IT. Scope claimed to be judge blend50 columns only; portfolio_final.json pairs correctly.
       I did not independently verify the scope limitation.

## 12. WHAT I COULD NOT CHECK
  - Every /workspace artifact (remote). All GATE P "bitwise, maxabs 0.0" receipts are self-reports of a
    remote comparison; I verified only that the receipt files exist, are internally consistent, and name
    the correct device sha.
  - rs_conc.py / offspec.py read META and PANEL from dev_v4/pod_backup_2026-08-21/wide_fea_hist_meta.npz
    and wide_panel_4h_hist_v2.npz -- NOT from the pinned meta_newprod_v4.npz. Whether that backup meta is
    v4-lineage is UNVERIFIED from here and must not be inferred from the path (E-0825-H/G). The tail ruler
    and the whole GATE A spectrum rest on it.
  - The "1%-band control => full-history walk is 0.40x the 2026 level" conservatism claim (mk_costb.py
    CAL_BASE known_limits) has no standalone receipt I could find.
  - The 3.2167x markout dispute (realized fee 2.7847 + adverse selection 6.7164 = 9.5012 vs model 2.9537)
    is NOT in this block: the only file containing "3.2167" is RESULT_r11_cost_tail_income_2026-09-12.md.
    infra1_cost (in this block) is the ORIGIN of the honest-cost programme but does not contain those
    figures. Wherever a verdict in this block turns on cost, a 3.2167x repricing moves every net g DOWN
    by (3.2167-1) * cost_ex: for A0 frozen that is 2.2167 * 0.1201 = -0.266 bps/anchor, which alone is
    larger than the +0.23 bootstrap resolution of the frozen window; for XIB (turnover +12.8%) the paired
    delta moves down roughly 2.2167 * (0.1515-0.1201) ~ -0.070 bps/anchor. Sign: every margin shrinks,
    every high-turnover arm shrinks more than A0.
