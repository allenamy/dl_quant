# Handoff audit working notes — block: r12 (regime / smoothing / intervene / verdict) + r13 (deploy / A / B / verdict) + r13b_nulls

> Created 2026-09-12 by the handoff auditor. READ-ONLY audit. Every sha below was RECOMPUTED this
> session with `shasum -a 256`. Labels: [V] = verified this session (file named), [I] = inferred.

## 0. sha recomputation result
All 9 round-level `SHA256SUMS.txt` / `SHA256SUMS_devices.txt` manifests match disk. All 10 PREREG
files match their `receipts/PREREG_FREEZE_sha.txt`. **Zero sha mismatches in this block.** [V]
`PREREG_r12_regime_partition_2026-09-12.md` = `e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c` (brief's `e239f8df…` confirmed).
Cosmetic only: `r13_B_withinhalf/SHA256SUMS.txt` lists itself (`2867b87f…`); the file on disk is
`818388dbe8eaf81d…`. Self-reference, not a defect. `shasum -c` FAILs on that line by construction.
Coverage gaps: `r12_smoothing` has NO round-level manifest (its devices manifest omits PREREG,
RESULT, and 5 `.log` files). `r12_smoothing`, `r12_intervene`, `r13_B_withinhalf` have no
`PREREG_FREEZE_sha.txt`. `r12_verdict` has NO prereg at all.

## 1. The non-causal regime-table kill — CONFIRMED, and it is stronger than stated
Producing code `devices_uplift_pod_regime.py` sha `cc06146098a3a86a890c9564bfe080b602bba503edad16bacb0a28491e1590ce` [V].
L21 `yv = y4[i, m]`; L28-39 build `xs_mean_bps`(L28/36), `disp_bps`(L28/36), `btc_bps`(L29/36),
`altmbtc_bps`(L37), `comov`(L38), `breadth_pos`(L39) — ALL from the forward 4h window. Kill CONFIRMED.
**Auditor's extension (NOT in the round's docs):** `n` and `turnover` (L31-33, membership churn over
the y4-finite set) are ALSO forward-conditioned and are named in neither the killed nor the surviving
group. And the three declared survivors — `fund_med/fund_absp75/fund_sd/fundema_sd`, `share_new90`,
`med_age_d` — are computed on `mm`, the support set filtered at L21-23 by `isfinite(y4[i,·])` with the
row dropped when `mm.size<30`. Their SUPPORT SET is forward-selected. "Only fund_*/share_new90/
med_age_d survive" is therefore too generous.
The r12 v2 replacement device does NOT have this problem: `pod_causal_regime_r12_v2.py` computes
SIGF/FMED as `RN8[j,m][FINF[j,m]]` — filtered by finite FUNDING only [V].

### Which earlier programme results consumed the killed table
- `trackC/devices_v4/*` via `lib.py::regime()` reading `uplift_regime_v4.csv` [V]. **NOT invalidated**:
  every consumption is `trail_mean/trail_std/trail_pct` with `cs[t]-cs[t-K] = sum(x[t-K..t-1])`
  (lib.py L26-33) — strictly lagged, hence causal at anchor t. [V]
- `trackF`: its PREREG L15 names `disp_bps/comov/breadth_pos` as candidates, but `build_regime.py`
  builds its OWN causal vars from trailing panel features (`f_rev_24h/f_mom_7d/f_vol_7d/f_range_24h`)
  under different names (`disp24/breadth_up`). NOT contaminated; prereg-to-implementation drift. [V]
  (Cross-block note: trackF's causality rests on `f_rev_24h` being trailing; this desk has a logged
  lookahead case on a ret24 panel column — memory `panel_lookahead_betaadj_ret24`. Not my block.)
- `RESULT_axis_staleness_regime_2026-09-11.json` §6/§7 use `breadth_pos`/`comovement` for
  distribution-shift description across periods, not to partition the book's own returns.
  Different estimand; not invalidated. [V]
- No other consumer found. `regime_anchor_table_2022_2026-08.csv` (non-v4) has zero code consumers. [V]

## 2. Direction loading — every number reproduces
`RECEIPT_r12_stage3_beta.json` / `RECEIPT_r12_stage4.json`:
identity_maxabs 1.1262785e-05 [V]; six buckets +2.8076 → −2.4033 monotone, Sharpe +4.3498 / −3.6177 [V];
net_gross_tilt ≈ −1.3e-4 each bucket, file caliber netlong −0.025287 [V];
BROAD RALLY expo −0.018663, sele −0.711256, pnl −0.729919, expo_share 2.557% [V];
2023 β +0.0373955 t +16.064; 2026 β −0.0913113 t −12.043 [V]; live β −0.0625 SE 0.02623 t −2.383,
dbeta_g mean −0.08576 [V].
**FINDING A (loud): "rolling 500-anchor beta sliding monotonically" is FALSE on its own receipt.**
`replay_beta_rolling500` has 35 windows; **14 of 34 steps go UP**; from 2024-08 onward **6 of 15 go up**,
including three SIGN FLIPS to positive (2024-11-21 +0.027, 2025-06-17 +0.012, 2025-07-29 +0.022).
RESULT §5.3 quotes a hand-picked 7-window subsequence that omits every positive window, and its own
last quoted value (2026-05 −0.1052) reverses the trend. [V]
**FINDING B: every t-stat in §5.3/§5.4 is iid-OLS, not day-block bootstrap.** The receipt discloses it
("OLS SEs are iid, so treat |t| as indicative"); the RESULT table and the brief drop the caveat.
The PIN's CI rule is day-block bootstrap; 4h anchors within a day are correlated, so t +16.06 / −12.04
are upper bounds on significance. [V]
**Minor:** the §0 "97% from the selection leg" is the BROAD-RALLY cell figure (0.711/0.730 = 97.4%).
The whole-sample decomposition is 92.9% (beta_from_selection −0.0028939 / beta total −0.0031158). [V]
**Structural fact not stated anywhere:** per-year `expo` in BROAD RALLY / BROAD SELLOFF is ~1e-16
(exactly zero) for 2022/2023/2024 and only nonzero in 2025/2026. The whole "exposure term" is a
2025-26 phenomenon. [V]

## 3. Refutation of the causal claim (r13_A §5) — reproduces exactly
`RECEIPT_r13A_diag.json::exposure_pnl_decomposition`: predicted `−mean(β·A)` vs realised `dg_AM_f100`
2022 −0.0061378/−0.0088248 · 2023 −0.1077098/−0.1064504 · 2024 +0.2499212/+0.2543619 ·
2025 −0.1886/−0.18722 · 2026 −0.0246/−0.01658 · full −0.0156/−0.0130. [V]
`exposure_pnl_bps` positive in 2022/2023/2025/2026, negative only 2024 ⇒ **4 of 5 years the
uncontrolled loading EARNED.** [V]
**The document flags its own weakest point and is right to:** "预测用的是同一套 β̂, 所以这是一致性自检,
不是独立验证". The two-decimal match is a self-consistency check, not independent validation. The
substantive refutation is the SIGN of `mean(β·A)`, which does not depend on the overlay.
**Also: a pre-registered gate FAILED here.** G5 required 2023 and 2026 dg to have OPPOSITE signs; both
came out negative. The round reinterpreted rather than stopped. Disclosed in-document.

## 4. Effective lag + the live-documentation defect
`LAG12B.json`: deployed (α=0.1, b=2.5e-4) `eff_lag_kernel_K60 = 11.636699` anchors = 46.5 h [V];
b=0 control 8.538548, theory_truncK60 8.901184, untruncated 9.0 [V]. Band share 11.6367−8.5385 = **3.098** [V].
**FINDING C: the R²=0.9949 belongs to the b=0 CONTROL, not to the deployed corner.**
kernel_R2: b=0 → **0.994866**; deployed b=2.5e-4 → **0.975857**; b=5e-4 → 0.892; α=.05/b=2.5e-4 → 0.890.
The RESULT table prints the lag column but NOT the R² column (R² is receipt-only). The band is a
threshold (nonlinear) operator, so the linear deconvolution is misspecified exactly where the headline
"+3.10 anchors from the band" comes from. Also 8.539 vs theory 8.901 is a −4.1% gap, and the doc calls
it "精确复现" (exactly reproduces). [V]
`lag50_anchors = -1` in every band cell — the gap-closure curve never reaches 50%; deployed
`phi_terminal` 0.2495. Honest and reported.

### Live tree, READ-ONLY, all VERIFIED this session
`~/wide_shadow/shadow_bundle/config.json` sha `3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e`
→ `params.alpha = 0.1`, `params.band = 0.00025`. [V]
`shadow_loop_v3.py` L492-494 and `fea171/combo_stage.py` L90-92 are the EMA+band — line numbers exact. [V]
`~/dl_quant_live/config/book.json`: `harvest_ema.alpha = 0.05`, `no_trade_band_w = 0.002`. [V]
`anchor_loop.py` L1485-1494 (`_is_ext` ⇒ "no harvest EMA, no neutral band", `skipped:"external_book"`)
and L1695-1699 (band `applied:false, skipped:"external_book"`). [V]
`state/live/no_trade_band.json` last written **2026-08-22 12:00** with `band_w 0.002, applied true`;
`state/live/harvest_ema.json` does not exist (only `state/harvest_ema.json`, 2026-08-22 12:46). [V]
Latest live anchor `state/live/pilot_log/20260912/anchors.jsonl` → `book_source = "external"`,
`external_book.path = ~/wide_shadow/state/target_live/1789171200.json`. [V]
⇒ **The r12_smoothing RESULT labelled this INFERRED. It can be upgraded to VERIFIED at runtime.**
**FINDING D: the count and the list of stale memory entries are both wrong.**
The RESULT names THREE (`turnover_shaping_ema_revalidated` / `deepsmooth_band_deployed` /
`two_rulings_deployed_20260810`); the task brief says FOUR. Actual state of the memory store [V]:
- (α=.05, b=.002) recorded as IN SERVICE: `deepsmooth_band_deployed.md`, **`adaptive_turnover_family_closed.md`**
  ("在役 (α=.05, b=.002, target) = 联合最优").
- b=0.002 as the deployed solution: `deposit_kills_implicit_band.md`.
- **α=0.3** (a third, also-not-live value): `turnover_shaping_ema_revalidated.md`, `two_rulings_deployed_20260810.md`.
Two of the three entries the RESULT names record α=0.3, not 0.05. And the entry that most explicitly
labels (α=.05,b=.002) "在役" — `adaptive_turnover_family_closed` — is OMITTED from the RESULT's list,
even though `PREREG_r12_smoothing` §重开依据 cites that very entry's 作废条件 as the formal basis for
reopening the axis. Five entries carry a stale smoothing parameter, not three or four.

## 5. Intervention audit — classification verified against the eight sources
Verbatim quotations confirmed by opening the sources:
R1 `adaptive_turnover_family_closed.md` (D +0.014 / M +0.026 / V +0.003 vs |corr|≥0.03; V-on-|gross| +0.254) [V]
R2/R3 `docs/DESIGN_lob_risk_layer_2026-08-28.md` L24 (cond. mean +2.2…+6.7, EV/trigger ≈ −15 bps) and
L25 (maxDD −10.3%, cost −34…−940 pp) [V]
R4 `graduated_stop_ooS_refuted.md` (S3−S1 = −71/−105 bps/event; v1 judge 1-day lookahead) [V]
R5 `drawdown_ladder_refuted_combo25.md` (gate 〔peak≤10% ∧ cost≤6pp ∧ start≤3%〕, measured −13…−26 pp) [V]
R6 `docs/RESULT_tail_aware_sizing_2026-09-06.md` L6/L36 ("换手不变(+0.6%/+2.0%)"), verdict "(B) 否决 —
它砍的是 alpha"; devices w10_volcap 8102b8c7 / judge_volcap 8e1a9eb2 [V]
R7 `multi_asset/exports/eda/RESULT_tail_forecast_redo_2026-08-20.md` L22 — verbatim including
"且这是乐观上界(未计缩放带来的额外换手)" [V]
R8 `docs/PREREG_funding_extreme_short_2026-08-30.md` L28 (A3 +0.081/+0.081, CI[−0.04,+0.21], 差一口气) [V]
**Only unverifiable item:** the R1 literal quote «α 自适应臂: 无条件量过门, 按门设计跳过» is attributed
to `probe_artifacts/adaptive_turn.py` on jpline — not reachable from this machine. INFERRED. [I]
**FINDING E: the brief's paraphrase of the taxonomy does not match the document.** The document's
partition is 3 (independent/event-level or no arm at all: R1/R2/R4) + 2 (in-book but window/caliber
cannot show an effect: R3/R5) + 3 (formally correct in-book marginal: R6/R7-partly/R8). The
"invalid arithmetic" pair the document names in conclusion #2 is R2 and R5 — which sit in two
DIFFERENT groups of that partition. "3 right-for-the-right-reason, 2 right-but-on-invalid-arithmetic"
is a cross-cut of two partitions, not the document's classification.
**FINDING F: the caliber caveat is applied inconsistently.** The doc flags R4's and R5's calibers as
pre-E-0908-B. It does NOT flag R6 — which it calls "本台在这条轴上做得最对的一次" — even though R6 is
dated 2026-09-06 and its prod caliber is `meta_newprod` (the pre-fix accounting), i.e. also pre-E-0908-B
(09-08) and pre-v4 (09-09). R7 (08-20) and R8 (08-30) are likewise pre-v4. All three "formally correct"
rejections sit on superseded calibers. [V from the source docs' own device/caliber lines]
**Minor:** R8's own document records its rerun command "在 /tmp/ftrim_*.log 头部" — volatile storage;
an E-0826-D gap in the source, inherited by anyone trying to reopen R8.

## 6. Round-8 boundary correction — VERIFIED
`BATTERY_r12.json`: 29 arms, **zero with `dturn_frac_pct ≤ 0`**; minimum `R12_CEM_99_derisk_s42` =
**+0.24120180746238784 %** (= +0.00014292 per gross). Max `identity_resid` across all 29 = 3.61e-16. [V]
CEM_99_neutral: dg +0.0379739, CI95 [−0.0045094,+0.0850773], Bonf-29 [−0.0210089,+0.1158337],
cost_surv 0.970186, dg@3.2167x +0.0369172, fire 141/9199 = 1.5328%, by-year 2025 +0.1293 / 2026 −0.0102. [V]
`reprice_multiple = 3.2167`, `rate_book = 2.9537` in the receipt. [V]

## 7. r12_intervene runs on a DIFFERENT window and a DIFFERENT baseline from the rest of round 12
`DIAG0.json` / `BATTERY_r12.json`: `alpha_window = 2022-06-30 00Z … 2026-09-10 00Z`, **n = 9199**;
`tail_window` … 2026-09-09 20Z, **1683 days**. The block's stated rule is W_ALPHA n=9138 (≤2026-08-30
20Z, E-0911-D) and W_TAIL n=10038. r12_regime and r12_smoothing use 9138/10038; r12_intervene does not.
It is PRE-REGISTERED (PREREG §1 L17 declares n=9199) and disclosed in RESULT L60, but **it is never
reconciled against E-0911-D**, whose stated reason for the 08-30 ceiling is that the F10 leg is
`nan_to_num`-ed to zero where it has no prediction. No receipt in this block shows the F10 leg has
predictions through 2026-09-10. The baseline is also different: `SLOW_NPY = SLOW_v4_x0910.npy` and
`FPRED = f10_v4RAWx_s42.npy` (A1x, v4-native) vs r12_regime's A0 `SLOW_v3_on_v4axis.npy`. [V]
⇒ **Any level comparison across r12 tracks is invalid** (A0 mean_g 0.6602 here vs 0.6342 there;
maxDD 41.81% vs 45.99% vs 46.42% in r13A). The Δg contrasts inside r12_intervene are paired and remain
internally valid.
**Naming trap to flag for the reviewer:** the baseline arm is `w10_ablation_series_R9_A1x_ext_s42.npz`
under `r9/dev_ext/`. Here `_ext` means EXTENDED WINDOW, not the v3 `_ext` cache the PIN forbids
(`meta_newprod_v4_x0910.npz` + `dlnative_5m_wide829_f16_holefix2_x0910.npz` are the real inputs). Exactly
the E-0825-H/G shape; resolvable only from `DIAG0.json`'s input paths. [V]

## 8. UNRECEIPTED numbers found
- r12_intervene §2 "V1b 口径核实": «y4 = Π(1+ret5) over E+1..E+48, **中位误差 1.2e-10**, 其余**三种**形式
  1.6e-3…2.3e-2». **No machine receipt.** The string 1.2e-10 exists only in prose and in a CODE COMMENT
  (`devices/r12_mon.py` L36). The nearest receipt, `DIAG0.json::V1_y4_convention`, reports MAX abs for
  only **TWO** conventions (E..E+47 = 1.813e-2, E+1..E+48 = 4.141e-3 — a 4.4× separation, not 7 orders)
  and self-notes "5m ret5 is float16; tolerance is f16 accumulation, not exactness". This is the gate
  that licenses I-4's intra-anchor path as "the same caliber as the accounting". [V that it is absent]
- r12_intervene §2 "锚内路径端点核对: 中位绝对差 **5.5e-7 bps**, ρ=**0.99246**". No machine receipt. [V]
- r12_regime §1 "共 −104.2688 bps" (the v1 members-bug anchor). `devices/README_VOID_v1.md` records only
  the parity failure `35.3675 / 0.3480`; −104.2688 appears in no receipt. [V]
  (Also: RESULT §1 says the v1 devices were "已删"; they are on disk with a README. Prose imprecision.)
- r12_regime §8 T2 coverage arithmetic ("SPAY d10 covers 2/6 ≤−4% days = 3.4×; FMED d1 3/6 = 5.0×") rests
  on halt frequencies the programme's own verdict device says are wrong — see FINDING G.

## 9. FINDING G — the verdict device caught r12_regime's halt frequencies and the discrepancy stands
`RECEIPT_r12_verdict.json::DISCREPANCIES.halt_per_yr_prose_vs_receipt` [V]:
DEEPNEG_MKT receipt **5.887** vs prose **6.12**; BREADTH_T1 receipt **2.632** vs prose **3.49** (33% off);
POSTCRASH receipt 3.578 vs prose 3.56. r12_regime §8 ranks "按止损线频率" and builds the T2 recommendation
on the prose values. Same receipt also flags empty `env_whitelist` fields in
`BATTERY_r12.json / NULLJUDGE.json / DECISIVE.json` (+ DIAG0.json, which it missed) — though for the
ANALYSIS scripts an empty set is the CORRECT assertion per PREREG_r12_intervene §ENV; the receipt cannot
distinguish "asserted empty" from "never populated". The replay subprocess whitelist IS enumerated in
`RUN_ENV_r12.json`.

## 10. FINDING H — "the same 34 cells, cell-by-cell comparable" is false
r12_verdict §1.2 claims r12_smoothing recomputed "同一套 34 格" for every smoothing corner. It did not [V]:
- r12_regime's 34 cells contain a **6-bin R72 LADDER** (<−4 … ≥+15%); the ≥+15% bin (n=89, Sharpe 4.209)
  is one of its two point-estimate>3.0 cells.
- `RECEIPT_r12_verdict.json::Q1_percell` 34 cells contain **R72_Q1..Q5**, a 5-QUANTILE partition. There is
  no ≥+15% cell at all.
This single substitution fully explains the internal contradiction between §1.1 ("2 / 34") and §1.2
("1") for the IDENTICAL in-service configuration — a contradiction the document never flags.
The shared cell `DEEPNEG_SHORT` also differs: r12_regime n=**914**, Sharpe **2.0471**; r12_verdict
n=**935**, Sharpe **2.4488**. Same name, same claimed window, different numbers.
⇒ The headline "净变化: 点估计过线的格子 +1 个" compares two different partitions.

## 11. r13_deploy — verified, plus a correction the reviewer must have
`RECEIPT_r13_reshape.json` [V]: S1 max|net_after/gross| **9.3675e-17**; S2 max rel gross err **2.2204e-16**;
S3 independent reimplementation vs deployed `legs.reshape_after_withhold` max|Δw| **0.0** (bitwise);
A1_VERDICT median S_A **0.0** ⇒ FORM A NO; B1_VERDICT max S_B **1.2170e-12 USDT** ⇒ FORM B YES;
`net_before_over_gross_pct` median **−5.6859%**, mean −5.9071%, n_negative **80/80**, max|·| **11.273%**;
`B3_cost.delta_turnover_matched` mean **0.0669331** vs A0 0.054027 (+123.9%), fitted cost **0.19770 bps**,
repriced **0.63594 bps**. `S6_src`: `producer_has_exec_reshape=true`, `producer_writes_combo_raw=true`,
`producer_writes_combo_reshaped=false`.
**Independently confirmed from the live tree, read-only** [V]:
`~/dl_quant_live/signal/legs.py` sha `7c0665f817fca948e2f9226dbd20607c9ea7b7fd6c9abfac63d69e3bc8b47da6`,
L179-184 = redemean + L1 rescale; `anchor_loop.py` L263-264 `RESHAPE_REDEMEAN/RESCALE = True` (module
constants); `apply_withhold_and_reshape` defined L287, called ONCE at L1664.
`~/wide_shadow/fea171/combo_stage.py`: `exec_reshape` defined **L199**, called **L271** (`combo =
exec_reshape(combo_raw)`), and `combo` is written only to the DIAGNOSTIC `state/target_combo/{A}.json`
(L272-282). The file the executor reads — `state/target_live/{A}.json`, schema `wide_target_v1` —
is built at **L347** (`val=combo_raw[_nz]`) and **L351** (`_weights = {syms[j]: float(combo_raw[j])}`).
PRE-reshape. Confirmed at runtime: today's anchor row names that exact path.
**Auditor's independent recomputation** of `sum(w)/sum|w|` directly on the producer's own
`target_live/*.json` over the same window: 99 anchors, median **−3.94%**, mean −4.09%, **98/99** negative,
min −9.29%, max +0.06%. Same sign and order of magnitude, but NOT the doc's numbers — because the doc's
figure is the EXECUTOR's post-pop `net_before/sizing_gross` (mean 12.65 names popped per anchor), not the
producer file as written. The headline sentence does not say which. The producer-file number is the
weaker (and more conservative) of the two.
**FINDING I (new, not in any document): the producer's `exec_reshape` is NOT the executor's reshape.**
combo_stage L199-207 demeans over the NONZERO subset only and rescales to preserve the ORIGINAL gross;
legs.py L179-184 demeans over the FULL vector and renormalises to UNIT gross. The r13_deploy conclusion
("前提是生产者先自己 reshape 一次 —— 它已经有这个函数") treats them as interchangeable. They are two
different maps. [V from source; consequence INFERRED]
**FINDING J (loud — it corrects r13_deploy §9.4 and protects the PIN): the cost parameters ARE reproducible.**
r13_deploy §9.4 flags "K=0.17 / alpha=0.87" as UNRESOLVED, quoting `FITK_v3_shape.json`'s
`UNIF.K_vwap 0.2359 / UNIF.K_excess 0.1165` and `implied_impact_exponent_alpha_1_over_p 0.7826`.
It read the WRONG BRANCH. The pinned file `costb_PWR_G230k.json` (sha
`295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53`) is the **POWER** caliber
("POWER-shape book-walk impact"), and `FITK_v3_shape.json` (sha
`0f682c91c29725c3bd0f294ac4b004051bb9e96661976c759e239b38e90a5d16`) `POWER.K_excess = **0.17**`
CI95 [0.1522, 0.1883]. Conclusive: the pinned file's `impact_bps_by_tier = [0.01954, 0.07144, 0.85794]`
is EXACTLY `FITK_v3_shape.POWER.per_tier.{tier0,tier1,tier2}.excess`. And `alpha = **0.8739**`
(se 0.0015) is in `FITK_v2.json` (sha `60e5ded62b0be84b560a180b96845489e0c3a6fa893400e2ac17e652634cacf7`).
The genuine open item is narrower: the artifact carries TWO impact exponents (0.8739 direct fit vs
0.7826 shape-implied 1/p) and the pinned cost file records neither. [V]
**Disclosed weaknesses worth carrying:** P0 parity passes on only **34/80** anchors (gate was "≥30"),
`max_rel_nb` 0.6945; 17 anchors (2026-09-05 12Z…09-08 04Z) had the ledger `reshape` field overwritten by
a reject-rate report (`_rs` name collision, fixed 09-08) and were excluded by a STRUCTURAL selector and
listed individually. `S5.n_call_sites = 2` counts def+call; the field name is misleading (there is one
call site).

## 12. r13_A / r13_B / r13b — verified
**r13_A** `RECEIPT_r13A_judge.json` [V]: 18 arms; AM_f100 dg **−0.0129583**, AM_cond **+0.0120611**;
tail on n_days 1673 — AM_cond halt4 **3** vs A0 **6**, alert 19 vs 24, worst day −0.1087942 vs −0.1117140,
maxDD 0.447708 vs 0.464179. Null match: 6 nulls within 0.06–0.84% turnover rel-err. Correct window
discipline (tail on no-warm-drop).
**r13_B** `RECEIPT_r13B_full.json` [V]: `GATE_M.K1.00_W250.pct_reduction = **91.90095870**`,
`ci_delta_abs` pooled [−0.081338, −0.074989] excludes zero, and every per-year `ci_delta_abs` excludes
zero. Primary dg **+0.0077303**, CI95 [−0.1638638, +0.1794332], Bonf-12 [−0.2273659, +0.2490639],
`dg_reprice_3p2167` **−0.0139369** (sign flips), `cost_survival` 0.4416, `dturn_pct` +5.81,
sharpe 1.2912 → 1.4378. `executor_reshape_idempotence_maxabs` **5.204170e-18** (the brief's 5.204e-18).
tail (W_TAIL 1673 d): halt 6→2, worst day −11.171%→−6.334%, maxDD 0.46418→0.37429.
**FINDING K (the strongest attack surface in r13_B): AMENDMENT 1 moved the pre-registered PRIMARY arm
more than any other cell, and in the author's favour.**
`RECEIPT_r13B_v1_vs_v2_disclosure.json` [V] — the round discloses that the amendment moved K1.00_W250
from **−0.0118 to +0.0077** (+0.0195). What it does NOT say: across the 12-cell grid the amendment's
delta is **positive for every W250 arm** (+0.0014, +0.0031, +0.0117, +0.0195) and **negative for every
W60/W120 arm**, and **+0.0195 on K1.00_W250 is the single largest delta in the grid**. The gate figure
also moved with it: `gate_m_pct_reduction` v1 **50.33%** (barely past the pre-registered 50% gate) →
v2 **91.90%**. Both the headline "+0.0077" and the headline "91.90%" are post-amendment numbers.
Mitigating: both values sit deep inside the v2 CI, so the REJECT verdict is unchanged either way, and
v1 receipts are retained under `VOID_v1/`.
Also: the prereg's `|L1(u')−1| < 1e-12` gate logged **7.37e-9** against the archived float32
gross_total and was reclassified "diagnostic-only" (`RECEIPT_r13B_conservation_check.json`).
**r13b_nulls** `RECEIPT_r13bn_nulls_on_sd.json` [V]: ΔREAL 0.09097691, 70% threshold 0.06368384;
SHIFT101 0.0696377 = **0.765443×**, SHIFT503 0.0654179 = **0.719061×**, SHIFT1009 0.479,
RELAB1/2/3 = **−0.104860 / −0.089830 / −0.030235** (all negative);
**C1 0.08592665 = 0.944489×**; `closed_by = ["R1","C1"]`.
`beta_vs_sigma_spearman_mean = **0.5457780**`, median **0.6469318**. [V]
`H_headroom`: point ratio−1 = **+0.0521279** (L_crit 1.6072065 → 1.6909868), bootstrap CI95
**[−0.0547754, +0.7524398]**, median +0.2145, P(>0)=0.917, split-half does not flip sign in the same
direction ⇒ **WITHDRAWN**. [V]
**FINDING L (the methodological one, and the round already concedes it): SHIFT is a weak null for a
persistent quantity.** `beta_staleness` [V]: SHIFT101 (16.8 days) retains cross-sectional Spearman
**0.8748**; SHIFT503 (83.8 days) **0.6015**; SHIFT1009 (168 days) **0.5400**. A "null" that keeps 54–87%
of the true cross-sectional ranking is not a null. A shifted-beta arm reproducing 72–77% of the effect
is therefore EXPECTED and is near-uninformative. RESULT §limitation (b) concedes exactly this and notes
RELAB (the clean zero-information family) did NOT close the wire. ⇒ **The CLOSED verdict is load-bearing
on C1 alone**; listing R1 as a co-equal closer overstates the evidence. The substantive mechanism
(β↔σ Spearman 0.55/0.65; the per-name volatility axis was refuted and DNR'd on 2026-09-06) is sound.

## 13. E-0826-D rerun/env status per round
Full literal command + enumerated whitelist in a receipt: r12_smoothing (`R12_RUN_ENV.json`,
`R12C_RUN_ENV.json` — per-cell `cmd` strings), r12_intervene (`RUN_ENV_r12.json`,
`RUN_ENV_r12_nulls.json`), r13b_nulls (`RECEIPT_r13bn_nulls_on_sd.json::env`, and the RESULT prints the
literal `env -i …` line for both pod and local instruments).
Whitelist enumerated but command only in the RESULT prose (not in a receipt field): r12_regime
(RESULT §9), r13_deploy, r13_A, r13_B, r13_verdict.
Empty `env_whitelist` in r12_intervene's BATTERY / NULLJUDGE / DECISIVE / DIAG0 (intentional for the
analysis scripts per its prereg, but indistinguishable from unpopulated).
r12_verdict device asserts an empty whitelist; no literal command recorded anywhere.

## 14. Cross-round supersession / non-comparability summary
- Three different A0 maxDD values in this block, all legitimate on their own windows:
  r12_regime W_TAIL 45.99% (to 2026-08-30) · r12_intervene 41.81% (A1x, to 2026-09-09, 1683 d) ·
  r13_A/r13_B 46.42% (1673 d). Never compare them.
- Turnover: the brief's factor **1.4375** (= 1/0.6956, ratio-of-means) is NOT the factor that converts
  the receipt's RAW 0.0303158 to the matched 0.0540270 — that is **1.78214** (mean-of-ratios).
  r12_regime §7 and r12_smoothing §83 both state this correctly and print both. Anyone applying 1.4375
  to the RAW mean gets the wrong answer by 24%.
- r12_intervene's book-average cost rate is **2.9537** with mean gross 0.68125 and matched turnover
  0.059252; r12_regime's is the same 2.9537 model but mean gross 0.6956 and matched turnover 0.054027.
  Different windows/arms ⇒ different denominators. Both self-checked in-device.
- Every arm/verdict in this block that ADDS turnover has its sign decided by the unresolved 3.2167×
  dispute: r13_B PRIMARY +0.0077 → −0.0139; r12 CEM_99 +0.03797 → +0.03692 (survives);
  r12 ICO +0.01623 → −0.08496 (flips); r13_deploy full-closure FORM B 0.198 → 0.636 bps cost;
  r12_regime pooled g +0.6342 → +0.2657 and 11/34 cells turn negative.
