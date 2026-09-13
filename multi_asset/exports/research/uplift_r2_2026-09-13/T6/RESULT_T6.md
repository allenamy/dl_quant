> **创建:** 2026-09-13 09:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (worker T6, dispatched by lead) | **状态:** T6 结果 — 冻结规格(家族与方法于 c0ed46c8 先于数字提交)下全部门过后的读数; §7 为 POST-HOC 分解(不作判决); §11 录取规程为**提案**, 未采纳; 未经 lead 复跑 | **作废条件:** (a) FAMILY_T6.md §2 规则被证明漏入/误入成员(按规则重跑后以 AMENDMENT 追加); (b) 任一被引装置或记录(`w10_sleeve` 谱系 GATE P、`costb_PWR_G230k`、归档 A0 `352ac36f…`)被推翻; (c) v4 口径被取代

# RESULT · T6 · Selection-bias audit (CSCV-PBO, DSR, nested walk-forward selection)

Program: `uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md` AMENDMENT 5. Family + frozen spec: `T6/FAMILY_T6.md` (commit **c0ed46c8**, written before any Sharpe/PBO/DSR). All numbers below are rendered in `T6/receipts/TABLES_T6.md` from `receipts/RECEIPT_T6_compute.json` (frozen device `devices/t6_compute.py` sha256 `103974f3…`) and, for §7 only, `receipts/POSTHOC_T6_decomposition.json` (POST-HOC device `devices/t6_posthoc.py`). Units: annualized net Sharpe (SR) of g = net_ex/gross_total, ×√2190. W_FULL = 2022-01-31 00Z…2026-08-30 20Z (10,038 anchors); FROZEN = 2025-03-01 00Z…2026-08-10 20Z (3,168).

**What this is and is not.** T6 measures a defect in our research method (choosing among candidates by backtest on the same history). It is not an explanation of live results and must not be quoted as one.

## §0 One page

**VERIFIED (frozen devices, receipts, all gates green):**
1. **Family.** 1,280 v4-caliber device records on pod2 → primary family **F1 = 125 distinct full-book configurations (seed 42) / 70 (seed 2027)**, all on the archived-A0 replay lineage, `costb_PWR_G230k`, CRYPTO m1, full W_FULL grid. The members are almost one book: **N_eff (participation ratio) = 1.57 on W_FULL, 1.51 on FROZEN**.
2. **Gates.** GATE-X 147/147 + 74/74 series re-hash; GATE-0 reproduces 8/8 published A0 numbers (FROZEN SR 2.93571303735249 to 1e-10; W_ALPHA mean g 0.6341957 to 3e-8); GATE-I max |Δ| 1.07e-14; controls: planted SR 4.0 edge → **PBO 0.0000**, found in 4/4 nested years, DSR 1.000; all-noise → **PBO 0.8089** (10 noise replicates 0.356–0.809), DSR 0.299.
3. **PBO (frozen rule: ≥ 0.5 ⇒ selection has no OOS value).** F1: **0.157 (W_FULL) / 0.187 (FROZEN)** seed 42; **0.147 / 0.210** seed 2027; W_ALPHA 0.231. P(IS-best loses OOS) 0.5–5.8 %. **Rule not triggered for F1.** Pre-declared sensitivity **F3 = only rounds r8–r21 + T2 (the AMENDMENT 5 named scope): PBO 0.508 on W_FULL ⇒ rule triggered** (FROZEN 0.300).
4. **Selection haircut (frozen rule: nested − hindsight best, a lower bound).** W_FULL span 2023-01-01…2026-08-30: nested **1.610 [0.578, 2.711]** vs hindsight best (XIB_LAG50) **2.261** ⇒ **−0.652 [−1.735, +0.392]**; seed 2027 −0.610 [−1.704, +0.418]. FROZEN: nested **2.202 [0.457, 3.939]** vs hindsight best (XIB_LAG50) **3.758** ⇒ **−1.555 [−3.347, +0.200]**; seed 2027 −1.398 [−3.170, +0.297]. CIs are day-block, conditional on the realised selection path, and include 0.
5. **Negative OOS years of the nested selection (seed 42):** 2023 **−0.088** (picked T2 `Ns_A0`), 2025 **−0.108** (picked T2 `WIRE_A0`); FROZEN 2025-03…12 **−0.607**. A0 in 2023: **−1.936**.
6. **DSR.** Family best on FROZEN (XIB_LAG50, 3.758): P(true SR > 3.0) **0.672 at N_eff**, 0.089 at N_raw 125, **0.055 at N = 300**, 0.025 at N = 1,221. **A0's 2.9357 on FROZEN: P(true SR > 3.0) 0.299 at N_eff, 0.0095 at N_raw, 0.0047 at N = 300**; P(true SR > 0) 0.999 / 0.891 / 0.837. A0 on W_FULL (1.106): P(true SR > 0) 0.967 at N_eff, **0.439 at N_raw, 0.335 at N = 300**.

**INFERRED (reading, not a measurement):**
- F1's low PBO is carried by one line: `XIB_PWR230k` + its argsort rebuild `IB_LAG50` take 82 % of CSCV selections on W_FULL. That line was itself picked post hoc from a 78-arm screen on the same history (`RESULT_trackD_sleeves_v4_2026-09-11.md` L137). CSCV inside a later family cannot see a selection made before the family existed, so "PBO < 0.5" here does not certify our process. Removing the line (POST-HOC, §7) gives PBO 0.480 / 0.364, and the pre-declared r8–T2 family is at 0.508.
- The 2.94 frozen-window level is mostly shared by the whole family (median member 2.673 on FROZEN vs 1.006 on W_FULL), and A0 was never the family's backtest leader (rank 27/125 on FROZEN; ranks 56, 75, 54, 43 on the training data at each nested selection point). The August selection that produced A0 (leg ablation, φ, FTRIM, seat rule) is **not** in the family, so T6 cannot size selection inflation inside A0's 2.94 directly; it can size what backtest selection over the uplift candidates costs (§0.4) and what A0's 2.94 is worth after deflation (§0.6).
- **Concrete change proposed (§11, PROPOSAL):** a candidate registry of saved per-anchor series; admission only on a nested-out-of-sample increment over the incumbent (paired day-block CI95 lower bound > 0) plus a DSR gate on the increment at the registry's trial count; pre-selected lines carry their originating screen size into N; best-candidate backtest Sharpes are never quoted without their nested counterpart.

## §1 What was measured

- **Inventory** (`FAMILY_T6.md` §0–§2; receipts `INVENTORY_pod2.json` sha256 `575f2413…`, `INVENTORY_pass2_pod2.json`): 21,697 npz seen under pod2 `/workspace/uplift_2026-09-11/` and `/workspace/uplift_r2_2026-09-13/T2/`; 2,839 with per-anchor records; 1,280 on the v4 accounting caliber; 1,019 cover W_FULL with finite g; rules R1–R9 → 221 members (147 seed 42 incl. 22 standalone sleeves, 74 seed 2027).
- **Families** (frozen): F1 primary 125 / 70; F2 admission candidates 88 / 41; F3 r8–r21+T2 scope 101 / 57; F4 F1+standalone sleeves 147 / 74; F5 A0 model inputs only 108 / 63. F1 s42 roles: 1 baseline (A0), 86 in-K candidates, 1 in-K construction control (r16 X4), 32 design variants (fixed-seat ladders, r8 fixed-seat cells, single-leg books, `R9_PHI0`, r12 `C_AS`), 5 tradable diagnostics (T2 `WIRE_A0`, `TW_Ns_stale1`, `TW_Ns_cleadm1`; r4p3 `IB_LAG50`, `IB_PAR`). By round: r12_smoothing 30, r8_inbook 26, r12_intervene 15, r8b2 8, r5_oi 8, r5_seeds_grid 7, T2 6, r16 6, r15 5, r5a2 4, r3k 2, r9 2, seatladder 2, r4p3 2, r7f1 1, r7f2 1.
- **Excluded from the matrix, counted only in the N ledger:** overlays (r12 ICO/IAS 14, r13A 12, r13B 14, r14 SET C 14), off-grid device arms (r8b2 S00, basis 20, LOB 16, liq/OI standalone 8, XIB fixed-seat cells), other calibers (uplift r1–r2 fee_steady arms 423, r5 universe 10), independent-source screens (r9 5, r10 47), and the pre-uplift in-service design ledger ≈105 (`FAMILY_T6.md` §4.8: ledger 825 low / 1,221 high).
- **Extraction** (`devices/t6_extract.py` sha256 `b5699d06…`, pod2, `nice -n 10`, CPU, `nvidia-smi` 0 % / 2 MiB before and after): `receipts/T6_SERIES_s42.npz` sha256 `a3120f29…` (10,038 × 147), `T6_SERIES_s2027.npz` sha256 `74d4b88d…` (10,038 × 74). `*.npz` are git-ignored repo-wide; both files are on disk locally and on pod2 with hashes in `T6/SHA256SUMS`.
- **Computation** (`devices/t6_compute.py`, local CPU, env whitelist asserted): `SUMMARY t6_compute GATE0=True GATEI=True(maxabs=1.07e-14) GATEC=True [C1 PBO=0.0000 SEL=m124 picks=4 DSR=1.000 | C2 PBO=0.8089 nestedSR=-0.509 DSR=0.299] ALL=True | F1s42 WFULL PBO=0.1568 Neff=1.57 nested=1.610 Hstar_span=2.261 haircut=-0.652 ; FROZEN PBO=0.1873 nested=2.202 Hstar=3.758 haircut=-1.555 self_sha256=103974f3d7958a4e`, **rc=0**, wall 10 s.

## §2 Gates and controls (all passed before any family number was read)

| gate | result |
|---|---|
| GATE-X extraction | seed 42: 147/147 g sha256 equal to `FAMILY_T6.json`; seed 2027: 74/74 |
| GATE-0 reproduction | A0 s42 W_ALPHA g 0.6341956722 (pub. 0.6341957, tol 5e-7) · SR 1.2912234 (1.2912) · W_FULL g 0.5607541 (0.5608) · SR 1.1061630 (1.1062) · **FROZEN SR 2.9357130374 (2.93571303735249, tol 1e-9)** · s2027 FROZEN 2.9021472 (2.9021) · s2027 W_ALPHA g 0.6579358 (0.6579) · SR 1.3298651 (1.3299) ⇒ 8/8 |
| GATE-I implementation | 12,870 splits, blocks of 627 (6 oldest anchors dropped), block-sum SR = direct SR to 1.07e-14 over 20 random splits × 125 members |
| C1 planted edge (seeds `default_rng([20260905, i])`, i = 0…124, member 124 + 4.0/√2190) | PBO **0.0000**, SEL = planted (SR 3.735), nested picks planted **4/4**, nested SR 3.576, DSR 1.000 ⇒ PASS; replicates r1–r9: PBO 0.0000–0.0019, planted picked 3–4/4 |
| C2 all noise (`default_rng([20260905, 1000+i])`) | PBO **0.8089**, nested SR −0.509 (bound ±1.306), DSR(SEL) 0.299 ⇒ PASS; replicates r1–r9: PBO **0.356–0.628**, DSR 0.265–0.747, nested −0.549…+0.625, haircut −0.40…−2.26 |

**Second implementation** (`devices/t6_verify_independent.py`, explicit row concatenation + `scipy.stats.rankdata`, hand-coded moments): PBO on 1,000 random splits 0.1650 (binomial se 0.0117) vs frozen 0.1568 over all 12,870; nested W_FULL SR 1.609541 = 1.609541; DSR(SEL, N_eff) P(SR>0) 0.999942 = 0.999942, P(SR>3) 0.006690 = 0.006690 ⇒ PASS (`receipts/VERIFY_T6_independent.json`, rc=0).

Two rulers for reading §3: a family with one true edge gives PBO ≈ 0; pure noise gives 0.36–0.81. Also note from C1: the OOS-on-IS slope is ≈ −1 **even with a genuine edge** (complementary halves of the same selected series), so the slope sign is not evidence of overfitting in this design.

## §3 CSCV-PBO (S = 16, 12,870 splits)

| family · seed | window | N | PBO | median logit | slope | P(OOS loss) | mean SR IS(n*) → OOS(n*) | most selected (share) |
|---|---|---|---|---|---|---|---|---|
| **F1 · 42** | **W_FULL** | 125 | **0.1568** | 4.127 | −0.641 | 0.0322 | 2.097 → 1.708 | XIB_PWR230k 0.58 · IB_LAG50 0.24 · Ns_A0 0.11 · TW_Ns_stale1 0.04 · WIRE_A0 0.03 |
| **F1 · 42** | **FROZEN** | 125 | **0.1873** | 3.186 | −0.706 | 0.0099 | 3.877 → 3.153 | XIB_PWR230k 0.35 · IB_LAG50 0.31 · C_AS_fast_a005 0.14 · G_A0_k0 0.10 · C_AS_fast_a010 0.04 |
| F1 · 42 | W_ALPHA | 125 | 0.2307 | 4.127 | −0.723 | 0.0577 | 2.171 → 1.596 | XIB_PWR230k 0.55 · IB_LAG50 0.21 · TW_Ns_stale1 0.10 |
| F1 · 2027 | W_FULL | 70 | 0.1473 | 3.541 | −0.731 | 0.0256 | 2.076 → 1.688 | IB_LAG50 0.42 · XIB_PWR230k 0.38 · Ns_A0 0.13 |
| F1 · 2027 | FROZEN | 70 | 0.2099 | 1.808 | −0.731 | 0.0049 | 3.736 → 2.969 | IB_LAG50 0.31 · XIB_PWR230k 0.29 · G_A0_k0 0.15 |

Average in-sample → out-of-sample decay of the selected member: −0.39 SR (W_FULL) and −0.72 SR (FROZEN), seed 42.

## §4 DSR

| target · window (seed 42) | SR | rank/125 | N_eff (floored to 2) | N_raw 125 | N = 300 | N = 825 | N = 1,221 |
|---|---|---|---|---|---|---|---|
| SEL XIB_LAG50 · W_FULL — P(SR>0) | 2.062 | 1 | 0.9999 | 0.9688 | 0.9440 | 0.9030 | 0.8835 |
| SEL XIB_LAG50 · W_FULL — P(SR>3.0) | | | 0.00669 | 4e-6 | 1e-6 | 0 | 0 |
| **A0 · W_FULL — P(SR>0)** | 1.106 | 34 | **0.9672** | **0.4391** | **0.3345** | 0.2363 | 0.2048 |
| SEL XIB_LAG50 · FROZEN — P(SR>0) | 3.758 | 1 | 1.0000 | 0.9857 | 0.9739 | 0.9535 | 0.9434 |
| **SEL XIB_LAG50 · FROZEN — P(SR>3.0)** | | | **0.6724** | 0.0887 | **0.0553** | 0.0316 | 0.0254 |
| A0 · FROZEN — P(SR>0) | 2.936 | 27 | 0.9989 | 0.8913 | 0.8373 | 0.7638 | 0.7330 |
| **A0 · FROZEN — P(SR>3.0)** | | | **0.2985** | **0.0095** | **0.0047** | 0.0021 | 0.0016 |

SR0 (annualized selection benchmark): W_FULL 0.235 (N_eff) / 1.179 (125) / 1.309 (300) / 1.446 (825) / 1.497 (1,221); FROZEN 0.379 / 1.902 / 2.111 / 2.333 / 2.414. Undeflated references: A0 FROZEN PSR(0) 0.9998, PSR(3.0) 0.4694. Cross-member sd of SR is 0.452 on W_FULL and 0.729 on FROZEN, close to pure estimation noise √(2190/T) = 0.467 / 0.831. Seed 2027 reproduces the table (A0 FROZEN P(SR>3.0) 0.284 / 0.013 / 0.004; XIB 0.595 / 0.082 / 0.035). **How to read the N columns:** N_eff is AMENDMENT 5's primary and says the 125 members are ≈1.6 independent trials; N_raw, 300 and the ledger counts treat trials as independent, which the family is not, but the program's wider history of heterogeneous screens partly is. The truth for "how many independent looks" lies between, which is exactly why the probabilities span 0.30 → 0.005 for A0's 2.94 exceeding 3.0.

## §5 Nested walk-forward selection (expanding training; annual re-selection by training SR)

| family · seed | window | hindsight best H\* | SR(H\*, window) | **SR nested** [CI95] | SR(H\*, span) | SR(A0, span) | **haircut** [CI95] | level haircut |
|---|---|---|---|---|---|---|---|---|
| **F1 · 42** | **W_FULL** | XIB_PWR230k | 2.062 | **1.610** [0.578, 2.711] | 2.261 | 1.374 | **−0.652** [−1.735, +0.392] | −0.453 |
| **F1 · 42** | **FROZEN** | XIB_PWR230k | 3.758 | **2.202** [0.457, 3.939] | 3.758 | 2.936 | **−1.555** [−3.347, +0.200] | −1.555 |
| F1 · 2027 | W_FULL | XIB_PWR230k | 2.032 | 1.613 [0.595, 2.637] | 2.222 | 1.416 | −0.610 [−1.704, +0.418] | −0.419 |
| F1 · 2027 | FROZEN | XIB_PWR230k | 3.586 | 2.187 [0.405, 3.918] | 3.586 | 2.902 | −1.398 [−3.170, +0.297] | −1.398 |

**Per year, F1 seed 42, W_FULL** (NEG = negative Sharpe):

| segment | selected by training SR | SR train | **SR OOS** | A0 | H\* (XIB_LAG50) | best member that year |
|---|---|---|---|---|---|---|
| 2022 (training only) | — | — | — | +0.010 | +1.274 | Ns_A0 1.337 |
| 2023 | Ns_A0 (T2 κ σ-bin arm) | 1.337 | **−0.088 NEG** | **−1.936 NEG** | +0.047 | WIRE_A0 0.504 |
| 2024 | WIRE_A0 (T2 κ≡1 name path) | 0.762 | +2.125 | +1.088 | +1.780 | WIRE_A0 2.125 |
| 2025 | WIRE_A0 | 1.269 | **−0.108 NEG** | +1.187 | +1.936 | IB_LAG50 1.936 |
| 2026-01-01…08-30 | IB_LAG50 | 1.328 | +5.356 | +4.516 | +5.358 | XIB_PWR230k 5.358 |

**Per segment, F1 seed 42, FROZEN:** 2025-03-01…12-31 selected WIRE_A0 (train 1.386) → **−0.607 NEG** (A0 +0.831, H\* +1.715, best C_AS_fast_a005 1.927); 2026-01-01…08-10 selected IB_LAG50 (1.328) → +6.281 (A0 +5.433, H\* +6.283). Seed 2027: same picks; 2023 −0.114 NEG, 2025 +0.106, FROZEN 2025 segment −0.457 NEG.

## §6 Pre-declared sensitivities (seed 42)

| family | window | N | N_eff | PBO | P(OOS loss) | SEL (SR) | nested SR | H\* span SR | haircut [CI95] |
|---|---|---|---|---|---|---|---|---|---|
| F2 admission candidates | W_FULL | 88 | 1.27 | 0.1509 | 0.0233 | XIB_PWR230k (2.062) | 1.603 | 2.261 | −0.658 [−1.742, +0.384] |
| F2 | FROZEN | 88 | 1.24 | 0.1618 | 0.0103 | XIB_PWR230k (3.758) | 2.204 | 3.758 | −1.554 [−3.344, +0.199] |
| **F3 r8–r21 + T2** | **W_FULL** | 101 | 1.51 | **0.5078** | 0.1227 | Ns_A0 (1.440) | 1.358 | 1.464 | −0.106 [−0.326, +0.117] |
| F3 | FROZEN | 101 | 1.45 | 0.2998 | 0.0145 | C_AS_fast_a005 (3.332) | 1.104 | 3.332 | −2.228 [−4.511, +0.079] |
| F4 with standalone sleeves | W_FULL | 147 | 2.13 | 0.3603 | 0.0256 | XIB_PWR230k (2.062) | 1.399 | 2.261 | −0.862 [−2.073, +0.275] |
| F4 | FROZEN | 147 | 2.06 | 0.2162 | 0.0473 | XIB_PWR230k (3.758) | **0.990** | 3.758 | **−2.768 [−5.181, −0.467]** |
| F5 A0 model inputs | W_FULL | 108 | 1.62 | 0.1517 | 0.0322 | XIB_PWR230k (2.062) | 1.610 | 2.261 | −0.652 [−1.735, +0.392] |
| F5 | FROZEN | 108 | 1.57 | 0.1779 | 0.0099 | XIB_PWR230k (3.758) | 2.202 | 3.758 | −1.555 [−3.347, +0.200] |

F5 ≈ F1: the 17 A1-base members (A1, PHI0, r12 intervention arms) change nothing. F4: once standalone sleeves are eligible, nested selection picks them (SL_ORTHLAG 2023/2024/2026, TBF7D 2025) and the FROZEN haircut is the only one whose CI95 excludes 0.

## §7 POST-HOC decomposition (written after reading §3–§6; descriptive; no verdict rests on it)

- **PH1 · F1 without the XIB_LAG50 line** {XIB_PWR230k, IB_LAG50}: PBO **0.480** (W_FULL) / **0.364** (FROZEN) seed 42; 0.383 / 0.345 seed 2027. Hindsight best becomes Ns_A0 (1.464 on span) on W_FULL and C_AS_fast_a005 (3.332) on FROZEN; haircut −0.106 [−0.326, +0.117] and −2.228 [−4.511, +0.079].
- **PH2 · training ranks at each selection point (seed 42):** H\* (XIB_LAG50) ranked **3, 3, 5, 2** of 125 (W_FULL) and 5, 2 (FROZEN) — near the top, never first. **A0 ranked 56, 75, 54, 43** (training SR +0.010, −0.799, −0.125, +0.283) and 50, 43 on FROZEN.
- **PH3 · nested selection minus A0 on the same span:** W_FULL **+0.235 [−0.849, +1.283]**, FROZEN **−0.733 [−2.571, +1.047]** (seed 2027: +0.196 / −0.715).

## §8 Reading under the frozen rules (AMENDMENT 5)

1. **PBO.** F1, both seeds, both windows: 0.147–0.210 < 0.5 ⇒ the trigger 「按回测挑选在该家族上没有样本外价值」 is **not** met for the primary family. For the pre-declared F3 (the r8–r21 + T2 scope AMENDMENT 5 names) it **is** met on W_FULL (0.508), not on FROZEN (0.300).
2. **Selection haircut (lower bound).** −0.65 SR on the full-cycle span and −1.56 SR on the frozen window (seed 42; seed 2027 −0.61 / −1.40). Lower bound because unsaved/off-caliber trials (ledger) and the August design family are absent. Statistically the haircuts are not distinguishable from 0 at 95 % (conditional CIs include 0).
3. **Planning numbers.** A0's planning number (W_ALPHA SR 1.29, CLOSEOUT §7) is **not lowered by within-family evidence**: A0 is not the family's selected member and the nested procedure did not beat it significantly (+0.235 [−0.849, +1.283]). What must be lowered is any planning or target number built on a best-candidate backtest: subtract at least 0.65 SR (full cycle) / 1.56 SR (frozen window). The frozen-window 2.94 should keep its "do not plan on it" status (`DOCKET_r7_ship_2026-09-12.md` L332); after deflation its P(true SR > 3.0) is 0.30 at N_eff and 0.005 at N = 300.

## §9 Reconciliation with earlier records (quoted)

- **Qualifies the T6 premise.** AMENDMENT 5: 「在役形态与「冻结窗回测 2.94」是在同一段历史上从大量候选里挑出来的。挑选本身把回测抬高了多少?」. In the testable family A0 is mid-pack (27/125 on FROZEN; training ranks 43–75), and the frozen level is common to the family (median 2.673). The within-family data therefore attribute most of 2.94 to the window, as `CLOSEOUT_uplift_program_2026-09-12.md` L11 already did (「冻结窗的高夏普里有 **2.075×** 是 regime 租金」). The selection of A0 itself happened in August on families that are not on this device (`docs/PREREG_leg_ablation_2026-08-26.md` L15 「多重比较台账 +7(消融), 累计 ≈88」; `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` L61 「多重比较台账 ≈95 臂 … DSR 折价适用 ⇒ 前向影子为终审」) and remains unmeasured. This is a gap, not a finding of no inflation.
- **No DSR gate at admission of the in-service form.** `docs/REVIEW_f10_blend_deployment_2026-08-23.md` L30 disqualified a blend candidate on 「DSR = 0.287(s42)/ 0.527(s2027) ⇒ 双双 < 0.75 取消线」; three days later the in-service form's admission document states only 「DSR 折价适用 ⇒ 前向影子为终审」 (CANDIDATE L61) without a DSR number. T6's A0 FROZEN P(true SR > 0) at N_raw is 0.891, above that 0.75 line; P(true SR > 3.0) is not.
- **XIB_LAG50 is a pre-selected line.** `RESULT_trackD_sleeves_v4_2026-09-11.md` L137-138: 「信号选择是事后的(… = 78 臂里挑 2)… 混合比例 0.5 是从 {0.25, 0.5} 两点里挑的」; `RULINGS_OUTSTANDING_2026-09-11.md` L42: 「提议者书面声明: 动手前就被任务书告知 XIB 在全周期强 … 故「无盲性可主张」」. T6 confirms it is the family's hindsight best on every window and seed, and adds that nested selection never ranks it first before 2026 (PH2). Its W_ALPHA SR 2.1078 reproduces `RESULT_r7_fuel2_dispersion_screen_2026-09-12.md` L64 (2.108).
- **Consistent with T2's leak flag, and a lesson for admission.** `PROGRAM_uplift_r2_2026-09-13.md` L88 (T2 pointer): σ-bin arm 「**UNDECIDED, LEAK-SUSPECT** —— 超 0.165 触发线; §7 调查未通过 … 执行器有 24 分钟延迟 ⇒ 视为不可执行」; `T2/RESULT_T2_carry_net_sizing_2026-09-13.md` L138 「⇒ §7 FAIL ⇒ UNDECIDED (LEAK-SUSPECT); the +0.17 is not an effect.」 Backtest selection picks exactly that arm (nested 2023; F3 hindsight best; 11 % of F1 CSCV picks, 4 % more via `TW_Ns_stale1`).
- **Consistent with "reweighting cannot close the gap".** `PROGRAM_uplift_r2_2026-09-13.md` L10 「~300 候选都进同一个席位, 与在役书 ρ≈0.9」 and memory note `reweighting_cannot_close_the_sharpe_gap_2026_09_12`: 125 saved members are ≈1.57 effective independent trials.
- **Earlier PBO/DSR numbers are not comparable** (v3 caliber, other families): `docs/DESIGN_wide_replay_P3_2026-08-16.md` L83 「整形网格 CSCV PBO=34%」, L101 「DSR(20试验税后)=0.969」 (later cut by the carry fix, L127 「全史夏普 3.59→2.42」); REVIEW 08-23 L29 「PBO(CSCV S=12, 家族 38)= 0.448」. T6's A0 W_FULL DSR is 0.967 at N_eff but 0.335 at N = 300. The DSR verdict is driven by the N choice, which those documents fixed at 20–50.
- **Contradiction found in method, not in data.** The OOS-on-IS slope of the CSCV-selected member is negative even for a planted true edge (C1 −0.94 … −1.00). Negative slopes should not be cited as overfitting evidence without that control.

## §10 What T6 cannot see (lower-bound caveats)

1. Trials without saved device series on this grid (overlays, off-grid arms, other calibers, independent screens, the August design ledger) are absent from PBO and nested selection and enter only DSR's N sensitivity (825 / 1,221 documented, unreceipted counts).
2. **Pre-family selection is invisible to CSCV** (XIB_LAG50; any candidate first chosen on the full history). This biases PBO **down**.
3. The August design choices that produced A0 are not regenerated on the v4 device (lead instruction: no new devices): LEGS 111 vs 101, φ ≠ 0.45, LOOK ≠ 900 and FTRIM off do not exist on `costb_PWR_G230k`.
4. Bootstrap CIs condition on the realised selection path. The first nested selection trains on 11 months that include the 900-anchor warm-up and the F10-dead prefix (E-0911-D left side).
5. A0-state members share the archived device's causal-eligibility defect (3 cells, r18 N2) and warm-up rev24; NW-state twins were excluded by rule.
6. Seed 2027 family is smaller (70) because many arms were run on seed 42 only.
7. Published per-arm numbers were visible in source documents while roles were read; the membership rules are structural and were committed before any T6 statistic (disclosure in `FAMILY_T6.md` §0).

## §11 PROPOSAL — candidate admission protocol (not adopted; for lead / user ruling)

T6's measurements say our admission failure mode is **ranking on the same history** (the best backtest is a pre-selected line, timing-sensitive arms, or a window-shared level), not a lack of candidates. Proposed rules:

1. **Registry.** Every configuration evaluated on the v4 device writes its judged per-anchor record on the canonical grid with a role tag (candidate / design / diagnostic / null / control), seed and device sha. `devices/t6_inventory.py` → `t6_inventory_pass2.py` → `t6_family.py` builds it from pod2 as-is. A trial with no saved series, or with dropped anchors, is logged with its count and enters N.
2. **Out-of-sample increment gate (replaces in-sample ΔSharpe as the admission statistic).** Run the frozen nested walk-forward over {incumbent} ∪ registry. Admission needs the nested-selection series minus the incumbent-only series on the nested span to have a paired UTC-day block CI95 lower bound > 0. On today's registry this reads +0.235 [−0.849, +1.283] (W_FULL) ⇒ no admission, consistent with the program's zero admissions. Forward shadow remains the final judge.
3. **DSR on the increment.** For the candidate's paired increment series (candidate − incumbent), require P(true increment SR > 0) ≥ 0.95 at both N_eff of the registry's increment matrix and N = the registry's cumulative trial count including the ledger. Report both; admission needs both.
4. **PBO with rulers.** Report the round's PBO only alongside the planted-edge and all-noise controls on the same N and T. PBO ≥ 0.5 blocks admission for that round.
5. **Pre-selection carries its N.** A candidate that entered through a post-hoc pick (e.g. XIB_LAG50: 78 arms, 2 mix ratios) carries that screen size into its DSR N, and cannot be admitted on CSCV evidence from a later family.
6. **Eligibility.** Arms flagged timing-sensitive or leak-suspect by their own round (T2 Nσ, T2 tripwire offsets) are excluded from the nested selection pool.
7. **Quoting rule.** Any best-candidate backtest Sharpe in a planning or target document is quoted with its nested counterpart and haircut: at least −0.65 SR full cycle and −1.56 SR frozen window from T6, both lower bounds.

## §12 Reproduction (commands as run) and files

pod2 (`/workspace/uplift_r2_2026-09-13/T6`, CPU only, `nvidia-smi` 0 % / 2 MiB before and after each run, PIDs 333197 / 339489 untouched):
```
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /usr/bin/python3 devices/t6_inventory.py PATH,HOME,LC_CTYPE receipts/INVENTORY_pod2.json /workspace/uplift_2026-09-11 /workspace/uplift_r2_2026-09-13/T2
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /usr/bin/python3 devices/t6_inventory_pass2.py PATH,HOME,LC_CTYPE receipts/INVENTORY_pod2.json receipts/INVENTORY_pass2_pod2.json
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /usr/bin/python3 devices/t6_extract.py PATH,HOME,LC_CTYPE FAMILY_T6.json receipts
```
local (`multi_asset/exports/research/uplift_r2_2026-09-13/T6`):
```
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME LC_CTYPE=C.UTF-8 /usr/local/bin/python3 devices/t6_family.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING receipts/INVENTORY_pod2.json receipts/INVENTORY_pass2_pod2.json FAMILY_T6.json
python3 devices/t6_family_tables.py FAMILY_T6.json receipts/FAMILY_T6_tables.md
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME LC_CTYPE=C.UTF-8 /usr/local/bin/python3 devices/t6_compute.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING receipts
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME LC_CTYPE=C.UTF-8 /usr/local/bin/python3 devices/t6_posthoc.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING receipts
python3 devices/t6_tables.py receipts receipts/TABLES_T6.md
python3 devices/t6_verify_independent.py receipts
```
Receipts printed: `SUMMARY t6_inventory … with_record=2839 errors=1` rc=0 · `SUMMARY t6_inventory_pass2 rows=1280 complete_wfull=1019 complete_finite=1019 errors=0 checks_equal=[True×9]` rc=0 · `SUMMARY t6_family files=1280 members=221 … flags=0` rc=0 · `SUMMARY t6_extract s42 n=147 gateX=True s2027 n=74 gateX=True` rc=0 · `SUMMARY t6_compute … ALL=True …` rc=0 · `SUMMARY t6_posthoc (POST-HOC) F1-minus-XIBfam s42 WFULL PBO=0.4798 … FROZEN PBO=0.3638 …` rc=0 · `SUMMARY t6_tables lines=296` rc=0 · `SUMMARY t6_verify_independent PBO_sub=0.1650(se 0.0117) vs 0.1568 | nested 1.609541 vs 1.609541 | DSR P>0 0.999942 vs 0.999942 P>3 0.006690 vs 0.006690 | PASS=True` rc=0.

pod2 quota window (lead warning, 08:02:2xZ–08:03:1xZ): the only T6 write near it was the exploratory `devices/_scratch_tscheck.py` (deleted 08:57Z). It was re-created (sha `bece3bae…` on both machines) and re-run at 09:33:54Z: rc=0, empty stderr, stdout byte-identical to the 08:04Z run (sha `35d1d20f…`), and its coverage counts agree with the later pass-2 receipt. All other pod2 outputs lie outside 08:00–08:05Z and match their local sha. Receipt: `receipts/RECHECK_pod2_quota_window_2026-09-13.md`, which also records a Mac-side hazard found during the recheck: with the data volume 98 % full, evicted (`dataless`) files were read as 0 bytes by `shasum` without error. All T6 hashes were re-made with `devices/t6_sha_guard.py` (refuses dataless files and short reads) and equal the git blobs and pod2 copies.

Files: `FAMILY_T6.md`, `FAMILY_T6.json`, `RESULT_T6.md`, `devices/{t6_inventory, t6_inventory_pass2, t6_family, t6_family_tables, t6_extract, t6_compute, t6_posthoc, t6_tables, t6_verify_independent}.py`, `receipts/{INVENTORY_pod2.json(.gz), INVENTORY_pass2_pod2.json, FAMILY_T6_tables.md, RECEIPT_T6_extract.json, T6_SERIES_s42.npz, T6_SERIES_s2027.npz, RECEIPT_T6_compute.json, POSTHOC_T6_decomposition.json, TABLES_T6.md, VERIFY_T6_independent.json}`; hashes in `T6/SHA256SUMS`.
