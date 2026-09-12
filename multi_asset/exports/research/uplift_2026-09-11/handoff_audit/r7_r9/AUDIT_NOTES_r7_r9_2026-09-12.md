> **created:** 2026-09-12 | **Session:** session_01H39k5rgyd43mFMNsaBqzeX (handoff audit, block = rounds 7-9)
> **status:** working notes for the independent reviewer. READ-ONLY audit; nothing under uplift_2026-09-11/ outside this directory was modified. pod2 accessed read-only (sha256sum / sed / numpy reads only). No GPU job, no live touch.
> **invalidation:** any of the recomputations below failing to reproduce on the reviewer's machine.

# Block audit: rounds 7-9 (fuel curve, basis in-book, dispersion seat tilt, coverage ceiling, completeness critic)

## 0. sha256 RECOMPUTED THIS SESSION (all match the value the documents claim, unless noted)

| object | recomputed sha256 | claimed where | verdict |
|---|---|---|---|
| pod2 `/workspace/uplift_2026-09-11/w10_sleeve.py` | `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` | CALIBER_PIN, GATE_P_r7.json, GATE_P.json, RECEIPT_r8_BUILD2 | MATCH |
| local `trackA/`, `r13_A_halfscale/`, `r12_smoothing/devices/`, `r2_sleeve/devices/` copies of w10_sleeve.py | same as above | — | MATCH (pinned device IS archived locally, just not under r7*/r8*) |
| pod2 `r3k/costb_PWR_G230k.json` | `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53` | R7/R8 receipts | MATCH (local `r3k_impact/` copy identical) |
| pod2 `r7f2/r7_fuel.py` | `aecc09c46e1ec9fe486769f05f490f39da8d4cd5b7b295b96f0898fb929303a2` | R7_FUEL_RECEIPT.self_sha256 | MATCH |
| pod2 `r7f2/r7_final.py` | `391a7c1545c9452212eff667ed9252b085062e621e518c23e98c10d92e05b834` | R7_FINAL.self_sha256 | MATCH |
| pod2 `r7f2/r7_withinyear.py` | `993e8d5905af08c6c1cf4b6708e767c8d9b05eaf9c1311ef69af22188a0bf6bd` | R7_WITHINYEAR.self_sha256 | MATCH |
| pod2 `r8b2/w10_sleeve_tilt.py` | `7dd6324acd3610811b9cd191b5ab753ae6a01a80f46d3bcc0f17a5f0e1233c71` | RECEIPT_r8_BUILD2 (16-char) | MATCH |
| pod2 `r8b2/w10_sleeve_tilt2.py` | `0ff501815bdc564f680ed5f89e832a5f02841786977b59546ef26b07fc861328` | RECEIPT_r8_BUILD2 (16-char) | MATCH |
| local `PREREG_r8_basis_inbook_2026-09-12.md` | `83f4bed01cd90f9f415e0d2a89e173fb23ff8c89c2567633a99c923ddea03c8e` | RESULT_r8_basis_inbook header AND GATE_P.json AND battery.py literal | MATCH |
| local `PREREG_r8_BUILD2_...md` | `b4308fd79949d6283d3cfa55268e5d3cec6576c226d93f3ad9586465d550cc82` | RECEIPT_r8_BUILD2 (16-char `b4308fd79949d628`) | MATCH |
| `r9_coverage/SHA256SUMS_devices.txt` (10 devices) | all 10 recomputed | manifest | 0 MISMATCHES |

**No sha mismatch found anywhere in this block.** Devices that are NOT archived locally (pod2 only): every `r7f1/*.py` and `r7f2/*.py`, and `r8b2/w10_sleeve_tilt{,2}.py`. If pod2 is lost these verdicts have no device.

## 1. ★ THE BIG ONE — E-0911-D-left is 36.11%, not 12.15%; the KING leg is silently zeroed too

Round 9 found that `w10_sleeve.py` L267 `np.nan_to_num(xz(F10P[i,m]))` silently zeroes the F10 leg on a
contiguous prefix. It measured 1110/9138 = 12.15%. **The same pattern is on L219 for the king leg and
nobody measured it on A0's baseline.**

```
L219: z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*_fs*np.nan_to_num(FZ)
L267: _zf = (_w3f[0]*np.nan_to_num(xz(F10P[i,m])) + _w3f[1]*... + _w3f[2]*...)
```

RECOMPUTED first-hand on pod2 (`wide_fea_v4_meta.npz` axis 10182, `SLOW_v3_on_v4axis.npy`,
`f10_A0_s42.npy`, arm `r3k/arms/A0_PWR230k_s42.npz`, post-warm 900 + ts<=2026-08-30 20Z, n=9138):

| quantity | value |
|---|---|
| `SLOW_v3_on_v4axis.npy` finite rows | 5838; FIRST finite anchor **2024-01-01 00:00Z**; last 2026-08-30 20Z |
| `f10_A0_s42.npy` finite rows | 8028; first 2023-01-01 00:00Z; last 2026-08-30 20Z |
| KING-dead anchors inside the pinned window | **3300 / 9138 = 36.11%**, contiguous prefix 2022-06-30 00Z .. 2023-12-31 20Z |
| F10-dead anchors | 1110 / 9138 = 12.15% (reproduces r9 exactly), subset of the king-dead set |
| mean g on KING-dead / KING-live | **-0.3770 / +1.2058** |
| Sharpe on KING-dead / KING-live | **-1.1302 / +2.1508** (pinned full-window = 1.2912) |
| mean g on F10-dead / F10-live | +0.1586 / +0.7000, Sharpe live-only 1.3741 (reproduces r9's addendum bitwise) |

Because A0 runs `LEGS=101` the rev24 leg carries weight 0. Therefore on the 1110 both-dead anchors the
replayed A0 is a **single-leg (fund-only) book**, and on the other 2190 king-dead anchors it is
fund + (F10,fund). CLOSEOUT A-1's phrase "A0 在 2022 那段其实是一本两腿书" understates it on one side
(the F10 sleeve loses its F10 leg, the base book keeps king — only when king is ALSO dead is it one leg)
and understates the blast radius by 3x on the other.

**Fairness note:** the fact that SLOW is NaN before 2024-01-01 is already in the programme —
`RESULT_r5_angle1_fixed_seat_2026-09-11.md` L61 states it, `r12_regime` restates it, and
`RESULT_r7_fuel2` §9 hole 6 records it *for the standalone king-leg arm*. What is nowhere in the
programme is that the same fact eats 36% of **A0's own baseline**. This is the desk's own
"declared blind spot is not closed" morphology.

### Blast radius, precisely
- Affected: every full-window (2022-start) A0 statistic — R7 fuel-1 and fuel-2 screens, R8 BUILD-1
  `FULLCYCLE`/`FULL_TO_CEIL`, R8 BUILD-2 full-axis, R9's A0 reproduction, every rho-to-A0 over the full window,
  CLOSEOUT §2, the planning number +0.6342/1.2912.
- NOT affected: the FROZEN window 2025-03-01..2026-08-10 20Z (n=3168), the EXT window, the GIVEBACK window,
  the 61 newly-covered anchors, and the live book (live king predictions exist; this is a replay-only artifact).
- **Direction:** the defect makes A0 look WORSE, so the planning number is conservative w.r.t. it. But it also
  means "cross-regime Sharpe 1.29" is measured on a book that is not the book for 36% of its sample, and the
  clean-subsample reading (2.15) is era-selected (2024-on, which contains the +4.52 year 2026), so it is NOT a
  clean Sharpe estimate either. The honest statement is that era and leg-coverage are **not separable** here.

### It confounds round 7's central contrast
RECOMPUTED, r7f2 gauge, same tercile breaks the receipt used (2.818 / 9.098):

| cell | n | mean g | Sharpe | share KING-dead |
|---|---|---|---|---|
| T0 (low dispersion) | 3047 | +0.0838 | +0.2197 | **0.560** |
| T2 (high dispersion) | 3046 | +1.4899 | +2.5572 | 0.161 |
| T0 restricted to KING-LIVE | 1342 | +0.7692 | **+1.8075** | 0 |
| T2 restricted to KING-LIVE | 2555 | +1.9424 | +3.1509 | 0 |

(T0/T2 n, mean and Sharpe reproduce `R7_FINAL.json` `decisive/A0_s42` exactly.)
So **56% of the "no fuel" tercile is anchors where A0 has no king leg**, and the T2-T0 Sharpe gap collapses
from 2.34 to 1.34 once the king-dead anchors are removed. Round 7 offered two explanations of that gap
(dispersion; calendar year). There is a third, mechanical one it never considered: **leg coverage**.
This does not overturn round 7's conclusion (no identifiable dispersion dependence) — if anything it
reinforces it — but it invalidates the specific tercile numbers as evidence about dispersion.

## 2. ★ The r7 FUEL-2 dispersion gauge is NOT masked, despite the document's claim

`r7f2/r7_fuel.py` (read first-hand on pod2, sha aecc09c4…) lines 26-29:
```
j = pw_row.get(int(t))        # j is a panel ROW INDEX
...
k = umap.get(j)               # umap is keyed by TIMESTAMP
if k is not None: m = m[UMM[k][m]]
elif int(t) > last_mask_ts: m = m[UMM[-1][m]]; carried += 1
```
`umap.get(j)` looks a row index up in a timestamp-keyed dict and therefore ALWAYS returns None. The receipt's
own field `carried_mask_rows = {"incumbent": 0, "x0910": 60}` proves it: the CRYPTO-m1 mask was applied to
**0 of 10039** incumbent anchors and only to the last 60 (the 08-31 + September tail, via the carry branch).

This is the *same* defect `RECEIPT_r7_fuel1_viability` itself diagnosed in `r6j1_regime.py`
("umap.get(j) looks a panel ROW INDEX up in a TIMESTAMP-keyed dict"). `r7_fuel.py`'s docstring says the
definition was "copied VERBATIM" from `r6j1_regime.py` — it copied the defect with it.

Consequence: `RESULT_r7_fuel2` §1's statement *"带 CRYPTO-m1 掩码(= 口径锁定的成员集)得 9.0565 / −0.1419,
不带掩码得 8.7012"* has the labels wrong. RECOMPUTED from `r7f1/out/sigma_variants.npz`:

| gauge (fuel-1 naming) | 2026-08 median | 2026-09 median | post-warm(9138) median |
|---|---|---|---|
| `R6_sig` = meta members, umask never applied | **10.0581** | **9.0565** | 5.0205 |
| `R6M_sig` | 10.8881 | 9.0565 | 4.6047 |
| `LIVE_sig` = 829 qvk base ∩ m1 CRYPTO (the book's actual set) | 9.7830 | **8.1995** | 4.5447 |
| `ALL_sig` | 8.1219 | 7.3299 | 5.4375 |

r7f2's monthly medians are **bit-for-bit `R6_sig`** (10.0581 / 9.0565), i.e. the unmasked gauge.
Round 8 BUILD-2's internal tilt gauge, by contrast, is the LIVE gauge (device source confirms it uses the
book's masked member set `m`, and `R8_JUDGE.json.sigma_gauge_check` records maxabs 0.0 vs the round-7 LIVE gauge).
**So r7 fuel-2 is the only track in this block whose sigma is the defective one.** Impact on its conclusions is
expected to be small (the year-confound result is about time, not level) — but "today's sigma" is 9.0565
unmasked vs 8.1995 on the set the book actually trades, a 10% difference in the headline positional claim.

## 3. ★ "8.20 = 69.5th percentile of post-warm full history" is computed on the NO-WARM-DROP sample

RECOMPUTED from `sigma_variants.npz`:

| sample | n | median | pct of 8.20 | pct of 9.06 |
|---|---|---|---|---|
| LIVE, warm-dropped 900, cut 08-30 20Z (= W_ALPHA) | 9138 | 4.5447 | **66.98** | 69.91 |
| LIVE, NO warm drop, cut 08-30 20Z | **10038** | **4.0858** | **69.51** | 72.35 |
| R6, NO warm drop, cut 08-30 20Z | 10038 | 4.4963 | 66.61 | **69.28** |
| R6, warm-dropped 900 | 9138 | 5.0205 | 63.78 | **66.51** |

`RECEIPT_r7_fuel1_viability.headline_findings.2` says "69.5th percentile of post-warm full history
(median 4.09)". 69.51 and 4.0858 are the **n=10038, no-warm-drop** row. The label "post-warm" is wrong.
The same receipt's `three_numbers.c` contains `anchors_with_sigma_ge_8.20 = 3017`, `share 33.0%`, out of
`total n 9138` — i.e. 66.98th percentile — so the receipt **contradicts itself by 2.5 percentage points**.
`DOCKET_r7_ship` L315 then quotes three percentiles in one sentence that come from three different
(gauge, window) pairs: 8.20@69.5 (LIVE, no-warm), 9.06@69.3 (R6, no-warm), 9.0565@66.5 (R6, post-warm) —
and calls the last one "掩码口径" when R6 is the unmasked gauge (§2 above). DOCKET hole #8 flags a
"caliber" divergence but not the window divergence, which is the larger half of it.
**Conclusion ("today is not a low, it is about the 2/3 point") is unaffected.**

## 4. ★ The completeness critic used the un-normalised turnover caliber

`r9_critic/critic_arith.py` C2: `dg = turn * gap` with `turn = 0.03032` and `gap` in bps per unit *traded
notional*, then subtracts `dg` from `A0.mean_g_bps`, which is **per unit gross**.

RECOMPUTED on `r3k/arms/A0_PWR230k_s42.npz`, post-warm, cut 08-30 20Z, n=9138:
```
mean(turnover)              = 0.030316      <- the raw L1 field the critic used
mean(gross_total)           = 0.695644
mean(turnover)/mean(gross)  = 0.043579      (= 0.030316 x 1.4375)
mean(turnover/gross_total)  = 0.054027      <- the caliber that matches g
mean g                      = 0.6342        (reproduces the pin)
```
The correct per-anchor ratio is 0.054027, i.e. **1.7822x** the number used. Corrected C2:

| quantity | critic | corrected (x 1.7822) |
|---|---|---|
| extra cost bps/anchor/unit gross | 0.0633 | **0.1128** |
| A0 mean g repriced | 0.5709 | **0.5214** |
| A0 Sharpe repriced (same vol) | 1.1623 | **1.0615** |
| haircut to the planning number | 9.98% | **17.79%** |
| NAV %/yr lost at 2.0x | 2.773 | **4.94** |

Note the r9 REV_SHORT receipt got this right (`A0_decomposition... turnover: 0.054`,
`turnover_ratio_candidate_vs_A0: 24.4`) — but CLOSEOUT Amendment 1 §A-8 quotes "**~39×**" for the same
object, which is 1.3178 / 0.0335 (candidate per-unit-gross turnover over A0's *raw* turnover). The
receipt's own 24.4x is the caliber-consistent number. **The CLOSEOUT prose contradicts the receipt it cites.**

## 5. Cost-model dispute: this block contains a THIRD point estimate

The handoff names a dispute between 3.2167x (realised 9.5012 = fee 2.7847 + adverse 6.7164) and the
estimand-mismatch rebuttal. The completeness critic in THIS block measured, first-hand on
`trackB_realized_cost_rows.json` (sha16 `8ae867eb3c1e47cf`), window 2026-08-01..09-11, 229 rows with finite
markout, $1,265,349 traded:

    fee 2.3848 + adverse selection 2.6573 = 5.0421 bps/unit traded one side
    pinned model book average               = 2.9537
    ratio                                   = 1.7071,  gap = 2.0884

So the desk's instruments give **1.71x** (r9 critic) and **3.22x** (the other track) for the same object,
on different windows. `r9_horizon/REOPEN_CHECK_r9.json` adds a fourth line already in the programme:
`costb_honest_X1` (fee + spread + exec-caliber impact K=1) = **5.517** bps, 1.87x the pinned model.
**Where a verdict in this block depends on the cost model, the sign of the 3.2167x repricing is:**
- R8 BUILD-1 (basis in-book): **verdict strengthens toward ACCEPT-on-cost, unchanged on alpha.** Marginal
  turnover is NEGATIVE (-5.13%), so a more expensive cost book makes the in-book form *better*: the
  receipted `COST_LADDER.json` already shows Δg +0.01057 (near-zero fee) → +0.01444 (fitted) → +0.02307 (10x
  book). It does not move Δg's CI off zero (the marginal series Sharpe is 0.170).
- R8 BUILD-2 (dispersion seat tilt): S00/S25/S50/R* all *add* turnover (1.04-1.14x), so repricing makes them
  worse; P10 is turnover-neutral (0.9929x). Verdict REJECTED gets stronger.
- R9 horizon 1h sub-anchor reopen: breakeven 0.8198 vs pinned 2.9537 = 3.60x short; under 9.5012 it is 11.6x
  short. Verdict (NOT REOPENED) gets much stronger.
- The planning number: repricing at the disputed gap (9.5012-2.9537 = 6.5475 bps) x 0.054027 = **0.3537
  bps/anchor**, i.e. A0 mean g 0.6342 → **0.2805** (a 55.8% haircut), Sharpe → ~0.571. That is the number the
  reviewer should hold in mind while the markout term structure is unresolved.

## 6. Smaller but reportable

1. **`battery.py` L59 identity check has a sign error.** It stores
   `identity_resid = (dpnl - dcarry - dcost) - dg`, but `load()` defines `carry := -carry_ex/gt`, so the
   identity is `dg = dpnl + dcarry - dcost`. Stored `identity_resid` values reach **0.5118**; RECOMPUTED
   with the correct sign the max over all arms and windows is **1.0159e-14**, which is exactly the
   "maxabs 1.02e-14" the RESULT document claims. So the prose is right and the archived receipt field is
   wrong — a reviewer opening `BATTERY_*.json` will see an apparently failing accounting identity.
2. **`RECEIPT_r7_fuel1_viability.legs.FUND_only`**: `yearFE_slope = 0.04608` with
   `yearFE_slope_CI95 = [-0.13286, 0.03693]` — the point estimate is **outside its own CI**. Sign or
   pairing error in the receipt; unexplained.
3. **Two different primary windows inside one round.** R8 BUILD-1's headline window is
   `FULLCYCLE = (None, 2026-08-10 20Z)`, **n=9018** (device `battery.py` L12-14). R8 BUILD-2, R7 and R9 use
   **n=9138** (cut 2026-08-30 20Z) = W_ALPHA. `BATTERY_dyn_s42.json` does carry the W_ALPHA reading
   (`FULL_TO_CEIL`: dg **+0.01732**, dturn -5.03%, cost survival 1.8225) but **no bootstrap was run on it**
   (`BOOTW` = FULLCYCLE/EXT/GIVEBACK only), so the W_ALPHA number has no CI anywhere.
4. **`RULINGS_OUTSTANDING_2026-09-11.md` is superseded and unamended.** Its header pins the primary window at
   n=9018 and the honest planning number at Sharpe **1.4150** [0.449, 2.381]; every 09-12 document uses
   n=9138 / **1.2912**. Its own hole #5 warns that older docs quote a stale pair (1.32 / n=9918) — the same
   thing has now happened to it. Its hole #1 (the eligibility gate's falsifiability receipt, UNRESOLVED) is
   still open and is re-listed as DOCKET hole #1.
5. **`DOCKET_r7_ship` §B-4 is internally inconsistent** about the proposed primary window: the composition
   table says FULLCYCLE post-warm **9018** while the prose two paragraphs later says "判决窗 n 从 3168 到 **9138**".
6. **Bootstrap caliber deviates from the pin in several devices.** The pin says B=2000, `default_rng([20260905,k])`.
   Actual: r7 fuel-1 B=4000 base seed **20260912**; r8_inbook `battery.py`/`fastboot.py` B=4000 seed 20260905
   (k=0 and k=9, both reported); r8b2 `r8_judge.py`/`r8_final.py`/`r8_rep.py` B=4000 seed **20260912**;
   r9 `r9_adden.py` reports both `CI95_R8_B4000` and `CI95_TASK_B2000` (good practice); r9 REV_SHORT uses the
   pinned B=2000/20260905. None of these is wrong per se, but **CI widths in this block are not all on the
   pinned caliber** and the documents do not say so.
7. **The z-statistics in `RESULT_r8_basis_inbook` §5 G3 and §6.1 have no stored field.** `null_cmp.py` computes
   no z. They are arithmetic on receipted null values; I reproduced them by hand:
   A BLEND 0.10 FULLCYCLE z(net) = **+1.822**, z(gross) = **+1.952**; GIVEBACK z = **+0.887**. They check out.
8. **G3's "全周期 6/6 全胜" is true only for the one best arm.** From `NULLS.json`, the FULLCYCLE beats-nulls
   counts are: A BLEND 010 **6/6**, C GT 025 **4/6** (SHIFT101 +0.02106 and SHIFT503 +0.01631 both beat the
   arm's +0.01435), A BLEND 050 1/6, B OVL 100 2/6. The doc's second-best arm fails its own null test on the
   full cycle and the document does not say so.
9. **`r9_screen/` contains three directories whose names are entire prose paragraphs** (a subagent prompt used
   as a path), one of which contains a literal "/" and so created a nested directory. The REV_SHORT track —
   the most interesting negative in CLOSEOUT Amendment 1 §A-8 — exists **only** under such a path and is not
   reachable by any stable reference in any document. The OPTIONS_IV track is duplicated under both a
   prose path and a clean one.
10. **`RECEIPT_r9_cohort_independence.json` contains `ic_fund_eq = [-0.4741, 0.0, 1]`** — an IC on **n=1**.
    Not quoted by the survey document, but it is in an archived receipt.
11. **GATE X-P cannot be re-run off the original GPU.** `r9_device.py` asserts `DEV == "cuda"`,
    `FC["torch"] == torch.__version__` and `FC["gpu"] == torch.cuda.get_device_name(0)`
    ("NVIDIA RTX PRO 4500 Blackwell"). Bitwise reproduction is conditional on that hardware.
12. **GATE_X_COV counts disagree with the headline by one anchor**: `A0_archived_s42` is recorded with
    `n_postwarm_anchors_with_zero_finite_F10 = 1111`, `A1_inc_s42` with 1110; the NEW_FINDING block uses
    1110 for A0. My own recomputation inside the pinned window gives 1110 for A0, so the 1111 is over the
    arm's own longer axis. Harmless, but it is a receipt that disagrees with the claim it supports.

## 7. What I checked and found SOUND (so the reviewer does not re-do it)

- GATE P (round 7 and round 8 BUILD-1 and BUILD-2): device sha equals the pin, `d30_n2_c42_rec` and `_W`
  `array_equal` with maxabs 0.0 in all four cells, prereg sha bound into the gate receipt.
- GATE X-P is a real gate, not a tautology: `r9_device.py` rebuilds the fold's per-fold standardisation from
  the trainer's own L317-328 arithmetic, re-infers from the checkpoint, and compares to the fold's stored `P`;
  it also asserts targets/fea82/fea89/trainer sha equal the fold's own config **before** using them.
- The A0 v3-lineage claim is true and I confirmed it from source, not from prose:
  `/workspace/review_scratch/build_dev_v4.py` L42-45 loads `dlw_ext/data/dlw_targets.npz` and
  `/workspace/f8_ext/preds/f10_V2MAIN_s{42,2027}.npy` to build `f10_A0_s{s}.npy`; `/workspace/f8_ext/models/`
  holds **only** `f10_live_s{42,2027}.pt` (full-history refits), which `w10_sleeve.py` L110-111's own comment
  forbids for historical evaluation — so the 2026-fold weights genuinely do not exist. The king leg
  `SLOW_v3_on_v4axis.npy` (sha `647673183e6af44a…`) is likewise v3; `SLOW_v4.npy` is `dde19142d017c37d…`.
  A1x reads the v4-native `f10_v4RAW` monthly-WF chain extended by `r9_extend2.py` to
  `r9/out/f10_v4RAWx_s42.npy` (sha `d41fcc933dfe3033…`) / `_s2027.npy` (`01180436a573fef2…`).
- `LIVE` monthly medians 2026-02..09 = 19.5966 14.3486 13.2942 6.2803 16.5456 12.7906 9.7830 8.1995,
  reproducing the receipt's [19.60 … 8.20] exactly; the up-step is 16.5456-6.2803 = **+10.2653**.
- R8 BUILD-1 headline numbers all reproduce from `BATTERY_dyn_s42.json`: dg +0.014441
  CI95 [-0.05605,+0.08487] Bonf13 [-0.08104,+0.11887], dturn_frac -0.051274, cost_surv 2.01249,
  dpnl +0.013175 (= 0.727% of the standalone 1.81307), by-year dg 2022..2026
  +0.0657/+0.0614/+0.0906/-0.0971/-0.0476 (two years opposite sign), marginal Sharpe 0.170
  (`COST_LADDER.json` PWR230k `marg_SR`).
- The SHIFT503 null beating the arm on the giveback is real: `NULLS.json` R8B_OVL_100 GIVEBACK arm
  **+7.8796** vs SHIFT503 **+10.1698**.
- R8 BUILD-2's 26.5% is real: `R8_FINAL.json` `arms.S00.n_no_book = 2422`, 2422/9138 = **0.26505**.
  The premise numbers are in `RECEIPT_r7_fuel1_viability.legs.seat_response`:
  corr(sigma,w3_fund) = **-0.0361**, w3_fund decile-1 = **0.6834**, and
  `RECEIPT_r8_BUILD2.step1...seat_blindness` gives 0.5555 (sigma<4.75) vs 0.5204 (>=4.75).
- The tilt devices differ from the pinned device by exactly the declared knobs (diff read on pod2).
- REV_SHORT's numbers all reproduce from its receipt (rho +0.0186, gross +1.1585 CI95 [0.5109,1.7911],
  turnover 1.3178, cost 3.8683, net -2.7097 CI95 [-3.3334,-2.1182], SR_net -4.1986, z 3.476,
  breakeven 0.8791, effective rate paid 2.9353, rho in A0's bottom quintile +0.1109 CI95 [0.0207,0.1969]).

## 8. How to re-run (as recorded, verbatim where recorded)

- **R8 BUILD-1 arms**: `r8_inbook/drive.py` builds the command line and stores every one of them in
  `R8_RUN_ENV.json`. Example (from `GATE_P.json.runs`):
  `env LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1
   UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz
   SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy FSEED=42 FPRED=f10_A0_s42.npy
   COSTB_JSON=<costb> OUT_TAG=<tag> /workspace/venv/bin/python /workspace/uplift_2026-09-11/w10_sleeve.py`
   (cwd `r8_inbook/dev`), plus `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=3`. **This is the only
   track in the block that stores the literal command string.**
- **R7 fuel-1 / fuel-2**: env whitelist is recorded (`env_whitelist_asserted`, and `env_whitelist: []` for the
  analysis scripts) but **no command line is recorded**; the devices exist only on pod2 under
  `/workspace/uplift_2026-09-11/r7f{1,2}/`.
- **R8 BUILD-2**: env whitelist recorded (22 names); command lines not recorded in the local receipts;
  replay devices pod2-only.
- **R9 coverage**: devices archived locally with a verified sha manifest; each device hardcodes its CONFIG and
  asserts `READ_ENV == []` plus a list of trainer/replay knobs absent from the process env. GATE X-P requires
  the original GPU (see §6.11).
- **r9 critic / r9 horizon / REV_SHORT**: `env_whitelist: []` asserted in-file (`critic_arith.py` even
  monkey-patches `os.environ.get` to raise). REV_SHORT ran under `env -i`.

## 9. Files created by this audit
Only this file, under `handoff_audit/r7_r9/`. Nothing else in the programme tree was written or modified.
