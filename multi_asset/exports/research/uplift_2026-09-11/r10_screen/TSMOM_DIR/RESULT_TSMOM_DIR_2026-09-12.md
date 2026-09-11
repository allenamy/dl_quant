> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 结论 — **DEAD**(独立性真、净额不显著、下行更坏、且对冲性质在实盘 regime 已反号) | **作废条件:** 判据在看数字之后被改; 出现比 v4 更新的口径链并逐门验过; 触碰实盘
> **口径锁:** `../../CALIBER_PIN_v4_2026-09-11.md`(v4 链 2026-09-09)。**零实盘触碰**:`~/dl_quant_live` 与 `~/wide_shadow` 全程只读, 未调用任何交易 API, 未下单。GPU 未使用(纯 numpy/CPU), 未抢占独立研究员任务。

# R10 SCREEN · TSMOM_DIR — per-name time-series trend as a DIRECTIONAL book, merged at the BOOK layer

## 0. VERDICT — **DEAD**

The candidate is **exactly what the surveyor said it was on the axis the surveyor measured** — I reproduced
its gross number to four decimals independently — and it still dies, on four separate axes, any one of
which is sufficient:

| # | kill | number (all VERIFIED by me this session) |
|---|---|---|
| 1 | **net edge is zero** | net g **+0.4076 bps/anchor/gross**, CI95 **[−1.8376, +2.6668]**, annualised Sharpe **+0.162** against SE **0.4895** |
| 2 | **cost eats half the gross** | price alpha +0.8181 → cost 0.4274 at the fitted `costb_PWR_G230k` ⇒ **49.8% survives**; turnover 0.1433 vs A0's 0.0303 (**4.7×**) |
| 3 | **it deepens the worst day at every allocation** | worst UTC day standalone **−1764.9 bps (2022-11-10)** vs A0's **−232.2 bps on the same day**; combined worst day is **worse** at c=0.02/0.05/0.10/0.20 on the full window |
| 4 | **★ the hedge property INVERTS in the live regime** | 2026: ρ to A0 **+0.1848 CI95 [+0.113, +0.256]** (positive, CI excludes 0) and TSMOM's mean inside A0's bottom quintile is **−16.48 bps CI95 [−25.28, −8.19]** (significantly negative) |

**The honest arithmetic:** with in-sample-optimal weights (an UPPER BOUND), combining A0 with this object
moves the full-window Sharpe from **1.3991 → 1.4308**, i.e. **+0.0318 = 0.065 SE**. The desk needs 3.966.
The gap closes from 2.567 to **2.535**. On the regime-matched frozen window it is +0.0275 = 0.033 SE.
**On 2026 the combination is NEGATIVE at every allocation tested** (−0.025 at c=0.02 … −0.473 at c=0.20).

**Kill #4 is the one that matters and it is the Amihud failure mode arriving one regime later.**
The entire measured hedge — the −0.0978 unconditional / −0.1857 bottom-quintile ρ that made this the most
interesting object in the survey — is a **2022–2024 phenomenon**. It is gone by the frozen window
(TSMOM's mean in A0's bottom quintile = **+0.958 bps, CI95 [−11.39, +13.58]** — zero) and it is
**reversed in 2026**. Screening only on the pooled 2022–2026 sample is what made it look like a hedge.

---

## 1. ENV WHITELIST (E-0826-D) and pins

**ENV WHITELIST = THE EMPTY SET.** Every run executed as
`env -i OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 /workspace/venv/bin/python <script>`;
each of the four scripts opens with an assertion that **none** of
`LEGS CAL WRULE LOOK PHI UMASK_NPZ UMASK_SCOPE FSEED FPRED COSTB_JSON MEMBERS_TOPN FTRIM SLOW_NPY W3FIX
FEMAT_NPZ OUT_TAG SLEEVE SEATNET CDAMP KMOD KMOD_F10 KMOD_L KMOD_AGREE SEATF10 KTAIL FUNDSCALE TRADE_TOPN
RNSM FTPOS LTRIM_TH FTRIM_TH REF_SKIP PANEL EXPORT_PANEL EMA_STATE_JSON`
is present, and raises if it is. These are analysis scripts, not device runs: no knob can silently change
what they measure. (The `OMP/OPENBLAS/MKL` thread caps are the only variables set and they are numerical-
identity-preserving thread counts, declared here for completeness.)

**Pins — sha256 COMPUTED BY ME this session, not copied:**

| role | path | sha256 |
|---|---|---|
| RAW accounting (y4, qvk, members) | `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` | `0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3` |
| A0 series + weight matrix | `/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz` | `88283c5f05b5d6b5213ca45f20577a3060a4831f72c6169c6efea8588cea1419` |
| funding panel (carry) | `/workspace/data/wide_panel_4h_v2ext.npz` | `5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116` |
| fitted cost model | `/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json` | `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53` |
| universe mask | `/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz` | `47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5` |

`meta_newprod_v4.npz` is `y4 (10182, 829)` — **axis 10182, VERIFIED**, and it is byte-identical to the
`wide_fea_hist_meta.npz` the device tree reads (symlink resolved, `max|Δy4| = 0.0` VERIFIED).
**No `expm1` is applied to y4 anywhere** (E-0904-F): this lineage's y4 is Σ of 5-minute SIMPLE returns.
The one `expm1` in my code is `qv4h = expm1(clip(qvk,0,30))·48`, which is the device's own quote-volume
transform (`w10_sleeve.py` L322 / `shadow_loop_v3.py` L473) and has nothing to do with the return caliber.
Nothing from the forbidden v3 lineage was opened: no `_ext` cache, no `pod_fea_ext.py`, no clipped-compound
accounting, no `pod_legs_ext.py`, no `shadow_bundle_v3`, no `wide_fea_v2ext_meta`, and no default panel from
`panel_source.py` (the funding panel is passed explicitly by absolute path).

**Cost model, re-derived by me, not read off:** blended bps per unit turnover
= `maker_share·maker_bps + (1−maker_share)·taker_bps` per tier
= **[2.6705, 2.6824, 3.6417]** — identical to the file's own `blended_bps_per_unit_turnover`. VERIFIED.
Charged **per name, per anchor**, by that name's own qv4h tier (≥5e6 / ≥1e6 / rest), on |Δw|.

**Window (frozen before any number):** drop the first **900** device anchors (E-0911-A), then cap at
`ts ≤ 1788120000` = 2026-08-30 20:00Z (E-0911-D). **n = 9138 reproduces exactly.** VERIFIED.
**Statistic:** `g = net_ex / gross_total`, bps per 4h anchor per unit gross, paired per anchor.
**Bootstrap:** UTC-day blocks, 2000 resamples, `numpy.default_rng([20260905, k])`.

---

## 2. STEP 1 — FEASIBILITY: the data exists, the object builds, and the accounting axis has no lookahead

**The signal.** `score_t = sign( Σ_{j=1..42} y4[t−j] )` per name — the trailing 7-day sum of the name's own
4h returns, strictly over rows `t−1 … t−42`, i.e. everything the score sees closes **at or before E_t**.
Eligible = member ∧ finite y4 ∧ `qv4h ≥ 250000` (the live gate: `~/wide_shadow/shadow_loop_v3.py` L473–474
reads `P["qv4h_min"]`, and `~/wide_shadow/shadow_bundle/config.json` L1449 sets it to **250000.0** — VERIFIED,
read-only). Weights `w = ±1/n`, `Σ|w| = 1`, **no demean** — this is the directional book by construction.
Mean eligible names per anchor **267.2** (matches the surveyor's 267.2).

**Reproduction of the surveyor.** My independent rebuild returns gross price alpha **+0.8181352** bps/anchor
and turnover **0.1433008** against the surveyor's `KLASS_SCREEN.json` **0.8181352498777134** / **0.1433008405278086**,
and ρ to A0 **−0.09783592** against **−0.0978326007032871**. **VERIFIED — independent reproduction to the
printed precision.** The surveyor's data claim is correct.

**★ GATE A — the no-lookahead receipt, and it closes bitwise.** The question that matters is not whether my
score is causal (it is, by construction) but whether `y4[t]` is genuinely the **forward** return earned by a
book decided at `E_t`. I proved it with a second instrument: I took A0's **archived weight matrix**
`d30_n2_c42_W` and re-derived A0's own `pnl` and `carry` columns from `y4` and the funding panel.

| membership rule used | max&#124;Δpnl&#124; (bps) | max&#124;Δcarry&#124; (bps) | mean&#124;Δpnl&#124; |
|---|---|---|---|
| meta `members` array | 3.537e+01 | 3.480e-01 | 2.096e-01 |
| **device's actual rule** (`MEMBERS_TOPN=829` rebuilds membership from qvk, it does **not** read `members`) | **6.528e-06** | **1.552e-07** | **2.499e-07** |

The first row is not a leak, it is **me initially reading the member set from a filename-shaped assumption**
(E-0825-H). A0's `config_json` says `MEMBERS_TOPN: 829`, and `w10_sleeve.py` L70–76 rebuilds membership as
"all names with finite qvk" when that is set. Under the device's real rule the identity closes to **6.5e-06 bps**.
**Therefore `y4[t]` is the forward 4h return for weights set at `E_t`, and my carry and cost arithmetic is the
device's arithmetic.** VERIFIED.
(For the candidate itself I keep the meta-`members` eligibility, because that is the object the surveyor built
and the one I am asked to screen; the difference is the eligibility set, not the return alignment.)

**Other logged leakage families, checked:** the dirty default panel — not used, the funding panel is passed by
absolute path; vol-scaling leakage — there is no vol scaling in this object; stride < horizon — stride = horizon
= one 4h anchor; champion-selection contamination — the arm set (K=6: lookback ∈ {12,42,90} × shaping ∈ {raw, EMA α=0.1})
was written into the script before the first number was printed, and the **primary arm was declared as
`TSMOM_L42_raw`, the surveyor's exact object**, not the best of the six.

**A deployability fact, recorded because it is load-bearing and was NOT in the brief.** The live signal chain
is structurally market-neutral at four independent points, all read READ-ONLY out of `~/dl_quant_live/signal/legs.py`
this session: L14 (composition → demean), **L180 `w = w - w.mean()`** inside `reshape_after_withhold(redemean=True)`,
L238 `shaped = mag - mag.mean()` in `shape_position`, L260 re-demean after the risk budget, and L269 (EMA → 二次
demean → L1). A net-exposure book cannot reach the exchange through that chain without a change to the executor's
risk architecture. This does not by itself decide the screen — the candidate is specified as merged at the BOOK
layer, which could in principle bypass `legs.py` — but it means an admission here would arrive with a
deployment blocker attached, exactly as round-2's F8 family found (`r2_timeseries/RESULT_r2_timeseries_sleeves_2026-09-11.md` §1).

---

## 3. STEP 2 — INDEPENDENCE: **the surveyor was right, and this is the real finding of the screen**

All VERIFIED, day-block bootstrap, 2000 resamples, `rng([20260905,k])`, n = 9138.

| quantity | value | CI95 |
|---|---|---|
| ρ(TSMOM net g, A0 g) unconditional | **−0.0978** | **[−0.1469, −0.0473]** |
| Spearman, unconditional | −0.0354 | — |
| ρ inside A0's **bottom quintile** (n=1828, threshold g ≤ −13.909) | **−0.1853** | **[−0.2981, −0.0687]** |

**|ρ| < 0.30 on both — the independence screen PASSES, and it is the first candidate in this programme to do so
while going MORE negative where A0 loses.** The Amihud sleeve went to +0.343/+0.438 there.

**And conditional ρ understates it. The conditional MEAN is the test that matters for a hedge, and it is
monotone and significant across all five A0 quintiles:**

| A0 quintile | n | A0 mean g | **TSMOM mean g** | CI95 |
|---|---|---|---|---|
| Q0 (A0 worst) | 1828 | −29.399 | **+14.782** | **[+6.12, +23.09]** |
| Q1 | 1827 | −8.269 | +1.941 | [−2.58, +6.04] |
| Q2 | 1828 | +0.272 | −1.727 | [−5.59, +2.40] |
| Q3 | 1827 | +9.530 | −5.485 | [−10.05, −0.68] |
| Q4 (A0 best) | 1828 | +31.302 | −7.475 | [−14.68, −0.62] |
| **A0 worst decile** | 914 | −40.676 | **+19.988** | **[+5.62, +34.56]** |

Pooled over 2022–2026 this is a textbook crisis-alpha profile: it pays most where A0 bleeds most. **This is real
and it is new. §6 is where it stops being true.**

---

## 4. STEP 3 — NET EDGE: the candidate has no standalone edge

Primary arm `TSMOM_L42_raw`, n = 9138, net of carry and of the fitted `costb_PWR_G230k` cost, all VERIFIED:

| component | bps/anchor/unit gross |
|---|---|
| gross price alpha (pnl) | **+0.8181** |
| carry (funding), subtracted | −0.0168 ⇒ **+0.0168 tailwind** |
| cost at fitted PWR_G230k | **−0.4274** |
| **NET g** | **+0.4076** |
| **CI95 (day-block, 2000, rng[20260905,k])** | **[−1.8376, +2.6668]** |
| annualised Sharpe (net) | **+0.1616** |
| SE(annualised Sharpe) = √(2190/9138) | **0.4895** |
| turnover per anchor | **0.1433** (A0: 0.0303) |
| **cost survival** | **49.82% of gross** |

**The CI contains zero with enormous margin and the Sharpe is 0.33 SE from zero.** For reference, the
level a single uncorrelated source needs in order to close the desk's gap on its own is a standalone Sharpe
of **3.711** (√(3.966² − 1.3991²), recomputed by me against the brief's 3.705, which uses A0 = 1.2912);
this object delivers **0.162**, i.e. **4.4% of it**. Put the other way: closing 1.3991 → 3.966 out of sources
of **this** quality would take **≈527** mutually uncorrelated copies of it
((3.966² − 1.3991²)/0.1616² = 527.4, computed at ρ ≈ 0 — the exact ρ = −0.098 version is not evaluable
because a 500-asset correlation matrix with that common loading is not positive semi-definite, which is
itself a reminder that this arithmetic is an upper bound and not a plan).

The carry is a small **tailwind**, not the killer — mean net exposure is −0.0159 (marginally net short) and
funding is usually positive, so the book receives slightly more than it pays. The killer is cost: turnover is
4.7× A0's while the gross alpha is 0.62× A0's.

**All six arms, declared before measurement (K = 6, primary = `TSMOM_L42_raw`):**

| arm | net g | CI95 | SR net | price g | carry | cost | turnover | ρ to A0 |
|---|---|---|---|---|---|---|---|---|
| TSMOM_L12_raw | +0.8366 | [−1.463, +3.167] | +0.333 | +1.6146 | −0.0445 | 0.8225 | 0.2780 | −0.050 |
| TSMOM_L12_ema10 | −0.3951 | [−2.676, +1.851] | −0.159 | −0.1163 | +0.0143 | 0.2645 | 0.0895 | −0.088 |
| **TSMOM_L42_raw** (primary) | **+0.4076** | **[−1.838, +2.667]** | **+0.162** | +0.8181 | −0.0168 | 0.4274 | 0.1433 | −0.098 |
| TSMOM_L42_ema10 | +0.2053 | [−2.032, +2.531] | +0.081 | +0.3764 | −0.0010 | 0.1721 | 0.0581 | −0.085 |
| TSMOM_L90_raw | +0.8810 | [−1.422, +3.104] | +0.356 | +1.1639 | −0.0042 | 0.2870 | 0.0960 | −0.077 |
| TSMOM_L90_ema10 | +0.6736 | [−1.763, +2.980] | +0.264 | +0.8160 | +0.0283 | 0.1141 | 0.0383 | −0.072 |

**Every one of the six has a CI95 that contains zero, before any Bonferroni correction for K=6.**
The best of six (L90_raw, SR 0.356) is still 1.28 SE from zero, and selecting it after the fact would be
exactly the champion-selection contamination the checklist forbids.

**Turnover-matched nulls** (the defective per-anchor permutation placebo was NOT used). Two families,
built to the same construction as `r3_attack_RESID_SHARPE/null.py`: `SHIFT_k` advances the whole score matrix
by k anchors (destroys time alignment, preserves the marginal, the persistence and therefore the turnover);
`RELAB_d` applies one FIXED symbol permutation at every anchor (`rng=default_rng([4242,d])`, destroys the
symbol↔score mapping, preserves everything else).

| null | net g | SR | turnover |
|---|---|---|---|
| SHIFT101 | −1.6335 | −0.679 | 0.1433 |
| SHIFT503 | −1.3456 | −0.572 | 0.1438 |
| SHIFT1009 | −0.4245 | −0.176 | 0.1425 |
| RELAB1 | −0.2179 | −0.087 | 0.1440 |
| RELAB2 | −0.0954 | −0.039 | 0.1449 |
| RELAB3 | −0.4534 | −0.177 | 0.1441 |
| **REAL** | **+0.4076** | +0.162 | 0.1433 |

Turnover is matched to 3 decimal places across all seven. **The real point estimate exceeds all six nulls**
— the gross signal is not a construction artefact. **But this is not a significance claim and I am not going to
dress it as one:** six draws cannot resolve a statistic whose own CI95 is [−1.84, +2.67]. The nulls sit near
−cost (≈ −0.43) as they should, and the real number sits one gross-alpha above them. That is consistent with a
real but tiny gross signal, which is exactly what §6 then dismantles.

---

## 5. STEP 4 — DOWNSIDE: it is 5× the risk of A0 per unit gross, and its worst day is A0's worst day

| quantity | TSMOM_DIR | A0 |
|---|---|---|
| **sd per anchor** (bps/unit gross) | **118.03** | 22.99 — **ratio 5.135×** |
| mean net exposure (netlong) | −0.0159 | −0.0253 |
| **mean &#124;net exposure&#124;** | **0.5705** | **0.0379** |
| net exposure p5 / p95 | −0.8986 / +0.9202 | — |
| **β to the eligible-universe mean return** | **−0.1769** (corr −0.239) | **−0.0026** (corr −0.018) |
| **worst UTC day** | **−1764.9 bps (2022-11-10)** | **−232.2 bps (2022-11-10)** |
| 1st-percentile UTC day | −738.5 | −139.5 |
| **maxDD** (cumulative g, bps of gross) | **5433.9** | 2520.5 |
| top-5 anchors' share of Σ&#124;g&#124; | 1.06% (not a point-mass artefact) | — |

**The worst day, anchor by anchor — this is where the "crisis-alpha convexity" mechanism is refuted directly.**
2022-11-10 is the post-FTX reversal. The trend book was **97% net short** going into it:

| anchor | TSMOM g | of which pnl | netlong | A0 g | market return |
|---|---|---|---|---|---|
| 2022-11-10 00:00Z | **−629.79** | −622.93 | −0.973 | −71.15 | **+623.48 bps** |
| 2022-11-10 04:00Z | −433.58 | −423.13 | −0.947 | −80.39 | +462.55 bps |
| 2022-11-10 08:00Z | +187.45 | +192.47 | −0.947 | −8.33 | −223.09 bps |
| 2022-11-10 12:00Z | **−928.13** | −923.16 | −0.933 | −66.31 | **+1000.94 bps** |
| 2022-11-10 16:00Z | +105.63 | +107.93 | −0.893 | −2.53 | −87.15 bps |
| 2022-11-10 20:00Z | −66.49 | −60.21 | −0.893 | −3.53 | +58.71 bps |

The claimed mechanism is "a trend book earns in sustained directional moves". The **post-crash reversal** —
the second half of the user's own complaint — is precisely the state in which a trend book is maximally
wrong-footed. On the single worst day in the sample it lost **7.6× what A0 lost, on the same day**.

**Its ten worst days are mostly NOT A0's bad days** (A0 was flat or positive on 6 of them: 2024-08-08 A0 +103.2,
2025-04-09 A0 +72.7, 2024-03-20 A0 +143.5, 2025-10-12 A0 +14.2, 2024-03-05 A0 +26.3, 2024-12-09 A0 −33.6).
So most of its tail is **new, added, uncorrelated downside**, not hedged downside.
On A0's ten worst days it helps on 6 (+405.9, +134.2, +64.9, +327.7, +193.6) and hurts on the two deepest
(2022-11-10 **−1764.9**, 2025-11-07 **−591.6**).

**Combined book, full window** (gross adds, so combined `g = (g_A0 + c·g_T)/(1+c)`):

| c | combined SR | ΔSR | maxDD | ΔmaxDD | **worst UTC day** | **Δ worst day** |
|---|---|---|---|---|---|---|
| 0.02 | 1.4225 | +0.0234 | 2420.5 | −100.0 | −262.3 | **−30.1 (worse)** |
| 0.05 | 1.4294 | +0.0303 | 2287.4 | −233.1 | −305.2 | **−73.0 (worse)** |
| 0.10 | 1.3741 | −0.0249 | 2081.7 | −438.7 | −371.6 | **−139.3 (worse)** |
| 0.20 | 1.1494 | −0.2496 | 1878.3 | −642.2 | −487.7 | **−255.4 (worse)** |
| 0.50 | 0.6813 | −0.7178 | 2010.1 | −510.4 | −743.1 | −510.9 (worse) |

**maxDD improves, the worst day gets worse — at every allocation.** The live desk halts on a daily-loss line
(`live_stop_loss_2026_09_06_resume_and_flowday`), so the metric that is improving is not the metric that halts
the desk, and the metric that halts the desk is the one that degrades. This is the failure shape the brief
named in advance, and it is confirmed.

---

## 6. ★ THE DECISIVE FINDING — the hedge is a 2022–2024 artefact and it has ALREADY INVERTED

E-0907-A: the reference window must match the live regime. Split the same object and the same statistic:

| span | n | TSMOM net g | SR | A0 SR | **ρ** | ρ CI95 | **ρ &#124; A0 Q0** | **TSMOM mean in A0 Q0** | that CI95 |
|---|---|---|---|---|---|---|---|---|---|
| FULL post-warm | 9138 | +0.4076 | +0.162 | 1.399 | **−0.0978** | [−0.147, −0.047] | −0.1853 | **+14.782** | [+6.12, +23.09] |
| ex-2022 | 8028 | +0.8790 | +0.348 | 1.489 | −0.1159 | [−0.167, −0.065] | −0.2141 | +17.937 | [+9.56, +26.68] |
| 2024-on | 5838 | +0.7381 | +0.280 | 2.278 | −0.1330 | [−0.190, −0.074] | −0.2315 | +20.959 | [+10.75, +31.62] |
| **FROZEN 2025-03-01…2026-08-10** | 3192 | +0.6725 | +0.316 | 3.013 | **−0.0305** | **[−0.119, +0.060]** | −0.2861 | **+0.958** | **[−11.39, +13.58]** |
| 2025-on | 3642 | +0.4260 | +0.182 | 2.763 | −0.0907 | [−0.173, −0.007] | −0.2833 | +9.646 | [−2.61, +23.01] |
| **2026** | 1452 | +0.4301 | +0.311 | 4.585 | **+0.1848** | **[+0.113, +0.256]** | +0.0126 | **−16.484** | **[−25.28, −8.19]** |

Read the last two rows against the first.

- On the **frozen window**, the window the project uses as its regime-matched reference, the unconditional
  correlation is **statistically zero** (CI straddles 0) and, decisively, **the hedge payoff is zero**:
  TSMOM earns **+0.958 bps CI95 [−11.39, +13.58]** inside A0's bottom quintile, where A0 is losing −37.55.
  The conditional ρ is still −0.286 — **and that is exactly the trap.** A negative conditional correlation
  with a zero conditional mean is not a hedge; it is scatter. **ρ measures co-movement, not payoff.**
  Screening on ρ alone would have passed this. It is the same shape as the project's own
  `attribution_gate_not_causal` and `measuring_a_misunderstood_quantity` entries.
- On **2026** the sign has flipped with confidence: ρ = **+0.1848, CI95 [+0.113, +0.256]**, and inside A0's
  bottom quintile TSMOM **loses −16.484 bps, CI95 [−25.28, −8.19]**. In the live regime it is not a
  diversifier at all — it is a **correlated loser in exactly the cells the candidate was bought for.**

**Per-year, for the mechanism:**

| year | n | net g | price g | SR | A0 g | mean netlong |
|---|---|---|---|---|---|---|
| 2022 | 1110 | **−3.0017** | −2.3728 | −1.205 | +0.1725 | −0.075 |
| 2023 | 2190 | +1.2546 | +1.6394 | +0.570 | −0.6248 | +0.073 |
| 2024 | 2196 | +1.2557 | +1.8353 | +0.409 | +0.5597 | +0.036 |
| 2025 | 2190 | +0.4232 | +0.6170 | +0.151 | +0.7627 | −0.135 |
| 2026 | 1452 | +0.4301 | +0.7838 | +0.311 | **+3.1385** | −0.003 |

The gross price alpha decays monotonically after 2024 (1.84 → 0.62 → 0.78) while A0's own g rises to +3.14.
The pooled "hedge" statistic is dominated by 2023–2024, the years in which A0 was weak (2023 A0 −0.62) and
the trend book happened to be strong. That is a **shared-regime coincidence**, not a structural hedge, and the
2026 row is the out-of-that-regime read.

---

## 7. STEP 5 — THE HONEST ARITHMETIC, not rounded in the candidate's favour

Two-asset optimum with in-sample weights (an **UPPER BOUND**, unattainable out of sample):
`S = √((s₁² + s₂² − 2ρs₁s₂)/(1−ρ²))`.

| window | A0 SR | TSMOM SR | ρ | **optimal combined SR (UB)** | **ΔSR** | **in SE** | gap to 3.966 |
|---|---|---|---|---|---|---|---|
| FULL post-warm (n=9138) | **1.3991** | +0.162 | −0.0978 | **1.4308** | **+0.0318** | **0.065 SE** | 2.567 → **2.535** |
| ex-2022 | 1.489 | +0.348 | −0.116 | 1.5782 | +0.0895 | 0.171 SE | — |
| 2024-on | 2.278 | +0.280 | −0.133 | 2.3528 | +0.0746 | 0.122 SE | — |
| FROZEN | 3.013 | +0.316 | −0.031 | 3.0401 | +0.0275 | 0.033 SE | 0.953 → **0.926** |
| **2026** | 4.585 | +0.311 | **+0.185** | 4.6177 | +0.0324 | 0.026 SE | — (and see below) |

At that optimum TSMOM takes **17.4% of the risk** but only **3.9% of the gross**, because it is 5.14× more
volatile per unit gross than A0. At any realistic allocation the full-window gain is smaller still:
**+0.0234 at c=0.02, +0.0303 at c=0.05, and negative from c=0.10 upward.**

**The 2026 row's optimal (+0.0324) is an artefact of the in-sample optimiser, and the honest 2026 answer is the
grid, which is negative at every allocation:** c=0.02 → **−0.0251**, c=0.05 → **−0.0746**,
c=0.10 → **−0.1844**, c=0.20 → **−0.4734**. With ρ = +0.185 the optimiser's "gain" comes from
shorting the candidate, which is a different object requiring its own screen and its own mechanism.

**Stated plainly, as asked:** *this is a real, genuinely near-orthogonal gross signal that moves the combined
book's Sharpe from 1.399 to 1.431 at in-sample-optimal weights — +0.032, which is 0.065 of one standard error —
while deepening the worst UTC day at every allocation, and its entire diversification value has already
reversed sign in 2026.* It does not move the desk toward 3.966; the remaining gap is 2.535 out of 2.567.

**Fairness footnote (VERIFIED arithmetic):** A0's archived record was priced at `costb_fee_steady`
(turnover-share-weighted blended **2.067** bps/unit) while I charged the candidate the fitted PWR model
(**2.954** bps/unit). Repricing A0 at PWR would cost it `0.0303 × 0.886 = 0.027` bps/anchor — negligible, and
independently corroborated by `r3k_impact/RESULT_R3K.json` `A0_PWR230k_s42` (g 0.689, SR 1.415). The comparison
is not rescued by the cost asymmetry.

---

## 8. WHAT WOULD CHANGE THIS VERDICT

1. **A 2026-and-forward sample in which ρ returns negative AND the conditional MEAN in A0's bottom quintile is
   positive with a CI excluding zero.** Conditional ρ alone is not sufficient — the frozen window proves ρ can
   be −0.286 while the payoff is +0.96 ± 12. The gate must be on the payoff.
2. **A version whose worst day does not coincide with A0's worst day.** A trend book that is stopped out of, or
   flattened into, violent reversals is a different object; nothing in this screen measures one. That would be a
   new candidate with its own mechanism and its own pre-registration, not a re-read of this one.
3. **A ~3× improvement in gross alpha per unit turnover**, which would take net Sharpe from 0.16 to ~0.5 and
   make the allocation question meaningful. There is no evidence in this screen that such a version exists: the
   gross alpha is decaying year on year.
4. Nothing here reopens the deployability question in §2: a net-exposure book still cannot pass the live
   signal chain's four demean points without an executor risk-architecture change.

---

## 9. LIMITS — what this screen did NOT do

- **It is not a `w10` judge verdict and no GATE P bitwise parity was run against `w10_sleeve.py`.** The book is a
  crude per-name ±1/n construction on the pinned RAW accounting matrix, not the deployed replay device. GATE A
  (§2) proves the **accounting** is the device's accounting to 6.5e-06 bps; it does not make the **book** the
  device's book. A promotion would need the device.
- Membership for the candidate uses the meta `members` array (267.2 names/anchor), which is the surveyor's object;
  the device's own `MEMBERS_TOPN=829` rule is a different, larger set. Both are documented in §2; the candidate
  was screened on the surveyor's.
- No smoothing/turnover-shaping search beyond the declared α ∈ {1.0, 0.1}, no vol-targeting, no per-name sizing,
  no stop layer. **Deliberate:** the task was to screen the object, not to make it work, and every such knob is a
  new arm requiring its own K.
- Bootstrap CIs are UTC-day block; overlapping-regime dependence beyond one day is not modelled.
- The 2026 sample is n=1452 anchors (≈8 months). Its ρ CI excludes zero, but it is one regime.
- Live was never touched. `~/dl_quant_live` and `~/wide_shadow` were opened READ-ONLY for exactly three reads
  (the demean points in `signal/legs.py`, the liquidity gate in `shadow_loop_v3.py` L473–474, and
  `shadow_bundle/config.json` L1449). No exchange API was called. GPU util was 0% and no job was preempted.

## 10. ARTIFACTS

- `devices/r10_tsmom.py` … `r10_tsmom4.py` — the four analysis scripts (sha256 in `SHA256SUMS.txt`).
- `receipts/STEP13.json` — pins, gates, all six arms, cost survival.
- `receipts/STEP245.json` — independence + conditional means + nulls + downside + combination grid.
- `receipts/STEP_REGIME.json` — GATE A closure, worst-day decomposition, worst-10 day lists, regime split, per-year.
- `receipts/STEP_REGIME2.json` — regime-conditional ρ / conditional-mean bootstrap CIs and combination grids.
- `receipts/primary_series.npz` — the per-anchor series (`ts`, `gT`, `gA0`, `pnl`, `carry`, `cost`, `turn`, `netlong`, `mkt`).
- `logs/part1..4.log` — verbatim run logs.
- pod2 working copy: `/workspace/uplift_2026-09-11/r10_tsmom/` and `/workspace/uplift_2026-09-11/r10_tsmom*.py`.
- Screened object's origin: `../../klass_independent_objective_2026-09-12/` (`klass_screen2.py`, `KLASS_SCREEN.json`).
