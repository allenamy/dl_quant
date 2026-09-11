# RESULT · TRACK A: carry is the price of the alpha, not a leak — except on the short side of negative funding

> **created:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **status:** exploratory, NO arm admitted; one candidate at (C) UNDECIDED | **void if:** GATE P parity is broken, or the v4 basis paths change
> **prereg (gates frozen before numbers):** `PREREG_trackA_carry_sleeves_2026-09-11.md` + AMENDMENT 1 (round 2) + AMENDMENT 2 (round 3), each written before the numbers it governs.
> **caliber:** v4 chain 2026-09-09 ONLY. dev_v4 tree, `meta_newprod_v4.npz` RAW accounting, king `shadow_bundle_v4`, F10 `f10_A0_s{42,2027}` (in-service yearly OOS), CAL=log (no expm1), CRYPTO m1 mask, FTRIM=zero in the baseline. Env verbatim from `run_v4_arms.sh` COMMON. NOTHING here is v3.
> **device:** `trackA/w10_sleeve.py` sha256 b88e35a4… = `w10_health.py` (sha256 8684d9a9…) + {LTRIM_TH, CDAMP, FTRIM_TH, FTPOS, RNSM, SLEEVE}, defaults off.
> **GATE P (bitwise parity, run three times — after each patch):** with all knobs off, `d30_n2_c42_rec` AND `d30_n2_c42_W` are **bitwise identical** to the archived `w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}.npz`. PASS 4/4 arms × 3 rounds. Sleeve identity Σ_sleeve pnl/carry/cost == pnl_ex/carry_ex/cost_ex to 8e-13 / 2e-15 / 1e-16.
> **eligibility:** `ELIGIBILITY_CONTRACT.json` has an EMPTY `BUNDLE_export.approved_source_sha256`, so **no arm in this document can be a candidate**. Every verdict is informational.

## §1 GATE A — the deciding question, answered

Sleeve decomposition of the **in-service form (A0)**, frozen window 2025-03-01→2026-08-10 20Z, bps/anchor per unit TOTAL gross, ex caliber (= the judge's numerator). carry > 0 means PAID.

| sleeve | gross% | pnl | carry | cost | net | net CI95 (s42) |
|---|---|---|---|---|---|---|
| L ≤−30bp | 0.21% | −0.072 | −0.135 | +0.000 | +0.063 | [−0.089, +0.251] |
| L −30..−10 | 0.26% | +0.039 | −0.022 | +0.000 | +0.061 | [−0.009, +0.139] |
| L −10..0 | 5.07% | −0.023 | −0.037 | +0.010 | +0.005 | [−0.454, +0.434] |
| **L 0..10bp** | **42.98%** | **+0.711** | **+0.308** | +0.049 | **+0.355** | [−2.083, +2.695] |
| L 10..30 | 1.32% | +0.383 | +0.099 | +0.001 | +0.283 | [+0.022, +0.562] |
| L ≥30bp | 0.12% | −0.076 | +0.032 | +0.000 | **−0.108** | [−0.213, −0.000] ← CI<0 both seeds |
| S ≤−30bp | 0.72% | +0.434 | +0.339 | +0.001 | +0.094 | [−0.026, +0.207] |
| S −30..−10 | 1.69% | −0.020 | +0.137 | +0.003 | **−0.161** | [−0.306, −0.024] ← CI<0 both seeds |
| S −10..0 | 18.99% | +0.142 | +0.254 | +0.019 | −0.132 | [−1.212, +1.009] |
| **S 0..10bp** | **28.42%** | **+1.390** | **−0.136** | +0.036 | **+1.490** | [−0.354, +3.190] |
| S 10..30 | 0.15% | −0.070 | −0.012 | +0.000 | −0.059 | [−0.151, +0.029] |
| S ≥30bp | 0.02% | −0.005 | −0.008 | +0.000 | +0.003 | [−0.029, +0.033] |
| **TOTAL** | **99.96%** | **+2.833** | **+0.819** | **+0.120** | **+1.894** | = the pinned A0 level |

Readings:
1. **The big long-positive-funding sleeve is NOT a leak.** L 0..10bp is 43.0% of gross, pays +0.308 of the book's +0.819 carry bill, and returns +0.711 of price — net +0.355. Removing it would destroy alpha, not save money (proved directly in §3, arm LT10).
2. **The book's whole net is one sleeve**: S 0..10bp, 28.4% of gross, **+1.490 of the total +1.894** (79%). The book is paid carry there (−0.136) *and* it is where the price alpha is. Every other sleeve nets under +0.36.
3. **Only two economically real sleeves are carry-negative on both seeds**: L ≥30bp (0.12% of gross, −0.108) and S −30..−10 (1.69%, −0.161). Together 1.81% of gross and −0.27 bps/anchor. A third, S −10..0, is −0.132 on 19.0% of gross with a CI that is wide open ([−1.21,+1.01]).
4. **FTRIM's z-layer implementation is leaky.** The band FTRIM is supposed to empty (shorts ≤ −10bp) still holds **2.41% of gross** (0.72% + 1.69%) — the EMA(α 0.1) + 2.5e-4 band residue that `PREREG_deploy_ftrim_2026-09-02` §8 predicted and accepted. One of those two residue sleeves is the book's clearest carry-negative cell.

## §2 GATE C — FTRIM at v4 caliber: carry is 86% priced in

| contrast | seed | Δ bps/anchor/gross | CI95 | Δpnl | Δcarry | Δcost | turnover |
|---|---|---|---|---|---|---|---|
| NOFTRIM − A0 | 42 | −0.125 | [−0.460, +0.225] | +0.806 | +0.943 | −0.011 | −12.2% |
| NOFTRIM − A0 | 2027 | −0.092 | [−0.408, +0.240] | +0.822 | +0.929 | −0.011 | −11.7% |

**(C) UNDECIDED, point estimate in FTRIM's favour, far inside the ±0.23 resolution.** Mechanism: removing FTRIM pays **+0.94 more carry** and recovers **+0.81 more price P&L** — i.e. **86% of the carry FTRIM saves is given straight back as price return.** This independently replicates the v3-lineage `health_check/decomp_ftrim.json` (2024→26, log/s42: Δcarry −0.389, Δpnl −0.409 = 95% priced in). Two lineages, two devices, same mechanism.
**So the premise of Track A is falsified on the sleeve FTRIM addresses: there is no free money in "stop paying carry" there.** FTRIM as deployed is right-signed but its measured value is ~0.1 bps/anchor, which this window cannot resolve.
**Live (task item 5):** `~/regime_dash/regime_dash.jsonl` `ftrim_counterfactual_prev`, 50 anchors 09-02T16Z→09-11T04Z: mean **−0.525 bps of gross/anchor** (negative = the exclusion COST price P&L), helping in 19/50 anchors, 7.9 names/anchor. **That field counts PRICE only and not the carry saved, so it measures one side of a trade-off the replay says is 86/100 balanced — it is not evidence against FTRIM.** n=50 with per-anchor price sd ≈ 37 bps of gross ⇒ SE ≈ 5 bps: the live tape cannot see an effect of this size (this is finding #6 of the forensic pass, restated).

## §3 GATE B — 13 arms, none admitted; one survives everything but the CI

Δ = arm − A0, dynamic seat, frozen window, paired per anchor, UTC-day block bootstrap 2000, rng `[20260905,k]` (boot() copied verbatim from `judge_v4.py`).

| arm | mechanism | Δ s42 / s2027 | CI95 s42 | Δpnl | Δcarry | turnover | verdict |
|---|---|---|---|---|---|---|---|
| **FT00S** | trim shorts whose **24h-mean** funding < 0 | **+0.235 / +0.295** | [−0.151, +0.625] | +0.052 | **−0.272** | +20.4% | **(C) UNDECIDED** (fixed seat: +0.015/+0.053, §4b) |
| FT00S3 | same, 12h mean | +0.228 / +0.242 | [−0.089, +0.539] | | | +24.4% | (C) |
| FT00 | trim shorts whose **current** funding < 0 | +0.171 / +0.151 | [−0.088, +0.423] | +0.131 | −0.166 | +29.3% | (C), turnover gate FAIL |
| FT00S12 | same, 48h mean | +0.163 / +0.198 | [−0.285, +0.608] | | | +16.4% | (C) |
| FT05 | FTRIM threshold −5bp | +0.031 / +0.064 | [−0.066, +0.135] | −0.052 | −0.103 | +7.7% | (C) |
| FT30 | FTRIM threshold −30bp (less trim) | −0.078 / −0.022 | [−0.229, +0.057] | +0.144 | +0.235 | −6.8% | (C) |
| NOFTRIM | FTRIM off | −0.125 / −0.092 | [−0.460, +0.225] | +0.806 | +0.943 | −12.2% | (C) |
| FTPOS | FTRIM band enforced at the POSITION layer | −0.038 / −0.026 | [−0.245, +0.155] | −0.434 | −0.461 | +55.5% | (C), turnover gate FAIL |
| **LT10** | **trim LONGS with funding ≥ +10bp** | **−0.153 / −0.147** | [−0.320, +0.005] | **−0.210** | **−0.055** | +3.6% | (C), P(Δ>0)=0.03 |
| LT30 | trim longs ≥ +30bp | −0.013 / +0.000 | [−0.075, +0.045] | −0.022 | −0.010 | +0.3% | (C) |
| LT50 | trim longs ≥ +50bp | −0.017 / −0.009 | [−0.060, +0.020] | −0.021 | −0.005 | +0.1% | (C) |
| CD05 | z ÷ (1+0.5·carry/10bp) | −0.061 / −0.017 | [−0.169, +0.048] | −0.152 | −0.087 | +0.7% | (C) |
| CD1 | λ=1 | −0.086 / −0.074 | [−0.239, +0.059] | −0.233 | −0.145 | +2.0% | (C) |
| CD2 | λ=2 | −0.084 / −0.093 | [−0.295, +0.118] | −0.313 | −0.228 | +4.8% | (C) |

**Price given up per unit of carry saved** — the single number that settles Track A:
| sleeve acted on | Δpnl / Δcarry | reading |
|---|---|---|
| shorts of deep-negative funding (NOFTRIM reversed) | 0.86 | slightly favourable to trim |
| **longs of high funding (LT10)** | **3.81** | **strongly unfavourable — this is where the alpha is** |
| all carry-paying names (CDAMP, λ 0.5→2) | 1.75 → 1.37 | unfavourable at every dose |
| **shorts of negative funding (FT00S)** | **−0.19** (price IMPROVES too) | **favourable — not a trade-off at all** |

## §4 The one candidate: FT00S (NOT ADMITTED)

**Rule (one line, at the same z layer FTRIM already occupies):** in both the king chain and the F10 chain, for a name whose causal trailing-24h mean 8h-equivalent funding rate is negative, zero any negative z. I.e. **generalise the live FTRIM from "shorts below −10bp instantaneous" to "shorts below 0 on a 24h mean".**

**What it does, mechanically** (sleeve gross share, A0 → FT00S, s42, frozen window): S −10..0 **18.99% → 13.99%**, S −30..−10 1.69% → 1.07%, S ≤−30 0.72% → 0.55%; the freed **5.8pp of gross lands in S 0..10bp (28.42% → 34.21%)**, the book's single profitable sleeve. Total carry bill **+0.819 → +0.527 (−36%)**. Total net **+1.894 → +2.128**.

**Levels, frozen window:** g +1.894 → +2.128 (s42) / +1.897 → +2.193 (s2027); **Sharpe 3.04 → 3.21 / 3.01 → 3.28** (SE(Sharpe) = √(2190/3168) = 0.83, so the Sharpe move is *not* separately significant); in-window maxDD 820 → 811 bps gross. Annualised: +0.235 bps/anchor × 2190 = **+5.1%/gross/yr = +10.3% of NAV/yr at 2× gross**.

**GATE B clause by clause:** ① CI lower > 0 both seeds — **FAIL** (−0.151 / −0.082). ② point > +0.23 — **PASS both seeds** (the only arm of 13 that clears the resolution floor). ③ per-year Δ ≥ −0.30 — PASS (2022 +0.093, 2023 −0.063/−0.078, 2024 −0.037/−0.025, 2025 +0.259/+0.284, 2026→08-10 +0.145/+0.193). ④ turnover ≤ +25% — PASS (+20.4% / +19.7%).
⇒ **(C) UNDECIDED. NOT ADMITTED. This is not "non-inferior" and not an improvement.**

**Every other named window (secondary), both seeds, all positive, all CIs containing 0:**
| window | n | Δ s42 / s2027 | CI95 s42 | level A0 → FT00S | Sharpe A0 → FT00S |
|---|---|---|---|---|---|
| frozen 2025-03→2026-08-10 | 3168 | +0.235 / +0.295 | [−0.144, +0.606] | 1.894 → 2.128 | 3.04 → 3.21 |
| 2024-01→2026-08-10 | 5718 | +0.119 / +0.144 | [−0.104, +0.356] | 1.376 → 1.495 | 2.47 → 2.58 |
| EXTENDED →2026-08-31 | 3289 | +0.241 / +0.286 | [−0.111, +0.619] | 1.703 → 1.945 | 2.72 → 2.91 |
| FULL 2022-01-31→2026-08-31 | 10039 | +0.078 / +0.084 | [−0.095, +0.236] | 0.615 → 0.693 | 1.21 → 1.35 |

**RNSM shape check (not four independent arms — one smooth family):** Δ (seed mean) 0h +0.161 → 12h +0.235 → **24h +0.265** → 48h +0.181; turnover +28.8% → +24.0% → +20.1% → +16.1%. A smooth inverted-U with monotone turnover. **8/8 cells positive.** The family, not the point, is the claim.

**Multiple testing, stated plainly:** 13 arms × 2 seeds, plus a 4-point RNSM grid; FT00S is the best of them. A nominal 95% interval selected this way is not a 95% interval. Bonferroni at K=13 would need a 99.6% interval, which is roughly 1.5× wider than the one printed. **The honest statement is: one arm out of thirteen has a point estimate above the window's resolution and the right mechanism in every sub-window, and the frozen window cannot resolve it.**

## §4b FALSIFIER 1 RUN — and it bites: FT00S is SEAT-DEPENDENT

Falsifying experiment #1 from the plan below was run immediately. At the **fixed live seat (W3FIX 0.21/0/0.79)**, frozen window:

| seed | Δ bps | CI95 | Δpnl | Δcarry | turnover | level A0→FT00S | **Sharpe A0→FT00S** | 2023 / 2024 / 2025 / 2026 |
|---|---|---|---|---|---|---|---|---|
| 42 | +0.015 | [−0.284, +0.311] | +0.161 | −0.079 | **+40.5%** | 1.826 → 1.841 | **2.88 → 2.73** | −0.086 / −0.109 / −0.123 / +0.264 |
| 2027 | +0.053 | [−0.243, +0.354] | +0.198 | −0.079 | +40.7% | 1.833 → 1.886 | **2.87 → 2.79** | −0.070 / −0.080 / −0.104 / +0.324 |

**The dynamic-seat gain (+0.235/+0.295, Sharpe 3.04→3.21) shrinks 5× at the fixed seat (+0.015/+0.053) and the Sharpe falls.** Three of four years turn negative; only 2026 stays positive. Mechanically: at the fixed seat the fund leg carries 0.79 weight, so the same trim removes a far larger share of the fund leg's short tail — turnover doubles (+40.7% vs +20.1%) and the price alpha given up rises.
**Consequence for the reading.** The live book *does* use the dynamic seat, so the dynamic row is the correct comparison under the pinned caliber — but an uplift that only exists at one seat parameterisation is not a robust sleeve effect. It is at least partly the dynamic seat re-weighting in response to the changed leg returns. **This moves FT00S from "under-powered candidate" to "under-powered candidate with a failed robustness read"**: its confidence is LOW, and falsifiers #2 (matched placebo) and #3 (LEGS=100 / fund-leg re-parameterisation) must run before anyone proposes it as a book change.

## §5 What this closes and what it reopens

**Closed by measurement (do not re-run these):**
- The long-positive-funding half — 43% of replay gross, 46.6% of live gross — is **not** a carry leak. Trimming it at +10bp destroys 3.8 bps of price per bp of carry saved (LT10, P(Δ>0)=0.03 on both seeds). Task item 2's hypothesis is **refuted**.
- Alpha-per-unit-carry sizing (task item 3b) loses at every dose: CDAMP λ = 0.5/1/2 all negative, price/carry ratio 1.4–1.8.
- Position-layer cleanup of FTRIM's EMA/band residue (task item 3c-adjacent) is worth ~0 before turnover and negative after: FTPOS Δ −0.038/−0.026 with turnover +55%.
- Explicit carry hedging was not built: the sleeve table says the carry bill is 40% concentrated in the sleeve with the best price alpha, so a hedge would short the alpha. Not pursued, with a reason.

**Reopened:** `docs/PREREG_funding_extreme_short_2026-08-30` DNR. Its own reopen condition was "≈1 year of forward sample". That condition is the wrong one. Opening the receipt: the family was probed at −30bp, −10bp and half-weight **only**, and its best arm (A3, −10bp, post-mix overlay) read +0.081 [−0.04,+0.21]. At v4 the same family's **shallow end has 2–4× the effect** (FT00 +0.16, FT00S +0.26) and a different injection layer changes it again (the same −10bp rule read +0.081 post-mix in that DNR vs +0.21 pre-chain in `PREREG_deploy_ftrim_2026-09-02` §7). **The DNR was decided on an unprobed corner of its own parameter space, on the v3 lineage.** It is not thereby overturned — FT00S is still (C) — but "this axis is closed" is no longer supportable as written.

## §6 Cheapest falsifying experiments (in order)
1. ~~FT00S at the fixed live seat~~ **RUN — see §4b. The sign held but the magnitude collapsed 5× and the Sharpe fell. Partially falsified.**
2. **Sleeve-conditional placebo:** re-run FT00S with the trim applied to a random 14% of shorts matched on |z| and liquidity but NOT on funding sign, both seeds. If the placebo also returns ≈+0.25, the effect is "shrink the short book", not "avoid negative-funding shorts".
3. **Is it just the fund leg?** Run FT00S with LEGS=100 (king only, PHI=0) and with the fund leg's z replaced by its own rank within positive-funding names. If the effect vanishes, FT00S is a re-parameterisation of the fund leg, not a carry sleeve.
4. **Power:** the frozen window cannot resolve +0.25. The only honest route to (A) is a pre-registered forward read on the live book with the anchor count named in advance (515 anchors ≈ 86 days for t=2 on a 3.3 bps gap; for a 0.25 bps effect against per-anchor sd 37 bps it is ~87,000 anchors — i.e. **this will never be settled on the live tape**, only by a wider replay window or a lower-variance estimator).

## §7 Artifacts
Device + judges + receipts: `multi_asset/exports/research/uplift_2026-09-11/trackA/` (`w10_sleeve.py`, `judge_uplift.py`, `judge_round3.py`, `run_uplift.sh`, `mk_sleeve.py`, `patch2.py`, `patch3.py`, `launch_arms.sh`, `commands.txt` = every command verbatim, `SHA256SUMS.txt`, `RESULT_trackA*.json`).
Pod side (read-only basis untouched): `/workspace/uplift_2026-09-11/` — 31 arm artifacts in `probe_artifacts/` (book weight arrays stripped after the parity gates to stay inside the shared /workspace quota, which was hit once mid-session; `rec` and the sleeve arrays are intact).
