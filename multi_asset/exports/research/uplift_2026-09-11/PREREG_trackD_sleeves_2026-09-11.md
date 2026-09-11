> **创建:** 2026-09-11 (Track D agent) | **Session:** session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 预注册, 判据冻结先于任何数字 | **作废条件:** 装置(w10_health.py sha 8684d9a9…)或 v4 树被证明不成立

# PREREG · Track D — standalone uncorrelated sleeves at v4 caliber

## 0 装置(冻结)
- device: `/workspace/review_scratch/health_check/w10_health.py` sha256 8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d
- tree: mirror of `dev_v4` built under `/workspace/uplift_2026-09-11/dev_v4s/` — same symlink targets
  (meta = `meta_newprod_v4.npz`, king = `SLOW_v4.npy`, panel = `wide_panel_4h_hist_v2.npz`). dev_v4 itself untouched.
- env COMMON: `CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 UMASK_SCOPE=m1 UMASK_NPZ=masks/umask_UPIT_CRYPTO.npz COSTB_JSON=calib/costb_fee_steady.json`
- sleeve arms: `LEGS=001 PHI=0 FTRIM=off FEMAT_NPZ=<signal matrix>` — the injected matrix REPLACES the fund-leg
  score `f_fund_ema_v1`; with LEGS=001 the book is a pure single-signal book carrying the device's full
  accounting chain (xz -> liquidity sel -> demean -> L1 -> cap 2.5/n -> L1 -> EMA 0.1 -> band 2.5e-4 -> forced exit),
  the same carry model, the same fee tiers, the same CRYPTO m1 universe.
- readout: `g = net_ex / gross_total` [bps/anchor per unit gross], judge_v4's frozen definition.
- baseline A0 = `dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz` (and s2027 as a second read).

## 1 候选集(冻结, 在看任何数字之前)
Panel columns, each tested at BOTH signs (sign not mechanically pinned for most):
f_rev_4h, f_rev_24h, f_rev_3d, f_mom_7d, f_mom_30d, f_mom_7d_x24, f_vol_7d, f_volq_ratio,
f_amihud_24h, f_range_24h, f_cpos_24h, f_tbf_24h, f_asz_24h, f_fund_now(8h-normalised), f_fund_iv,
f_fund_ema, f_fund_ema_v2.
Derived (mechanism stated):
- D_SURP = rn8(f_fund_now) - f_fund_ema_v1      (funding surprise / term-structure dislocation; the part of
  carry the 8h-settled, capped funding rate cannot express — the mechanism breadth-round2 named for basis)
- D_MOMSPREAD = f_mom_30d - f_mom_7d            (intermediate-term momentum net of the fast leg)
- D_VOLADJMOM = f_mom_7d / (f_vol_7d + eps)     (risk-adjusted momentum)
- D_ILLIQ_FUND = xz(f_amihud_24h) * xz(f_fund_ema_v1)  (state-conditioned carry: carry harvested where it is
  illiquidity-compensated rather than everywhere)
References (not candidates, for calibration): FUND (f_fund_ema_v1, FTRIM off and zero), KING (LEGS=100), REV24 (LEGS=010).
K = 2 x 21 = 42 candidate arms.

## 2 判据(Gate S; 全部必须成立才算录取)
- **S1 standalone economics**: full-cycle 2022-01-01 -> 2026-08-10 20Z mean g > 0 AND annualised Sharpe >= 1.0.
- **S2 cross-regime**: >= 4 of the 5 year buckets (2022 / 2023 / 2024 / 2025 / 2026->08-10) have mean g > 0.
- **S3 diversification**: |corr(g_sleeve, g_A0)| <= 0.30 on BOTH the frozen window (2025-03-01->2026-08-10 20Z)
  and 2024-01->2026-08-10 20Z.
- **S4 portfolio value**: an equal-gross 50/50 blend with A0 (g_blend = 0.5 g_A0 + 0.5 g_sleeve, a LOWER bound
  because it forgoes trade netting) must raise full-cycle Sharpe by >= +0.20 vs A0 alone AND raise the worst
  year's mean g.
- **S5 resolution**: full-cycle mean g must have a UTC-day block bootstrap (2000 resamples, base seed 20260905,
  substream [20260905, k]) 95% CI excluding 0, and |mean g| > 0.23 bps/anchor (the frozen-window bootstrap
  resolution).
- **S6 multiple testing**: with K = 42 arms, the leading candidate must also clear a Bonferroni-adjusted
  interval (alpha = 0.05/42 => 99.881% two-sided) on S5. A candidate clearing S1-S5 but not S6 is reported
  EXPLORATORY, never admitted.
- **S7 leakage** (only run on arms that clear S1-S5): offset spectrum corr(signal rank at anchor i, y4 at
  anchor i+k) for k in [-4, +4] must peak at k = 0 with no larger |value| at k < 0.

## 3 预先声明的读法
- Nothing here promotes anything. Admission under Gate S means "worth a deployment prereg", not "deploy".
- A sleeve failing S3 is not a sleeve, it is a re-weighting of the existing book.
- Cost is charged by the device's own tier model; turnover is reported per arm.
- All arms are evaluated on the SAME anchor set; any arm with a different frozen-window anchor count is void.

---
## AMENDMENT 1 (written before batch-1 numbers were read; disclosure below)
**Disclosure:** while debugging an artifact-path bug I read ONE arm's device receipt in full
(`SL_f_rev_3d__m`: net_ex_all -0.2004, by_year_ex 2022 +0.048 / 2023 -0.059 / 2024 -0.044 /
2025 -0.442 / 2026 -0.630, turnover_ex 0.111). It is a rejection on S1/S2 and plays no part in the
design below, which was written from mechanism.

**Batch 2 — DIFFERENT UNIVERSE SLICE (Track D item c).** Mechanism: `young_listings_carry_fund_alpha`
records fund-leg IC on names listed < 90 days at 3-4x the old-name IC (2026 +0.086 vs +0.024) and deep
negative funding 3x more frequent. A sleeve restricted to that slice trades a different set of names,
so its book-level correlation to A0 is bounded by the overlap of the two name sets.
Arms (both signs): YOUNGFUND (fund score, age < 540 anchors = 90 d), OLDFUND (age >= 540),
YOUNG180 (age < 1080), YOUNGREV (-f_rev_24h on young), YOUNGILLIQ (f_amihud_24h on young).
Listing age = anchors since the name's first appearance as a member with finite y4 in the v4 meta
(era-synchronous, causal by construction). K += 10.

**Batch 3 — ORTHOGONALISED RESIDUAL SLEEVES (targets S3 by construction).** Mechanism: the
`breadth_round2_basis_orthogonalised` result showed a candidate's book-level correlation can sit
almost entirely in ONE leg, and that per-anchor cross-sectional residualisation moves it (0.40 -> 0.13).
Arm form: signal' = rank(signal) - beta_i * rank(fund score), beta_i = per-anchor OLS slope, so the
sleeve carries only what the deployed carry leg cannot express. Run for the three batch-1 arms with
the highest full-cycle Sharpe, whatever they turn out to be (selection declared here, before the
numbers, as "top-3 by full-cycle Sharpe"; this selection is itself part of the K accounting).
K += 6.

**Total K = 42 + 10 + 6 = 58.** S6's Bonferroni level becomes alpha = 0.05/58.

**Prediction registered before the numbers (falsifies the low-dimensionality story if wrong):**
`slow_book_alpha_low_dim` + the vol-structure mirror pair say the deployed book's net is ~65% carried
by a low-vol-long / high-vol-short style tilt. Therefore `SL_f_vol_7d__m` (short high vol) MUST show
|corr to A0| well above 0.30 and fail S3. If it does not, that receipt's premise is wrong at v4 caliber.

## AMENDMENT 2 (written before ANY LOB number is computed)
**Batch 4 — MICROSTRUCTURE (Track D item e), the one source the ammunition campaign never priced.**
`ammunition_campaign_night1` closed the bar/funding/book-state feature space at a measured ceiling of
+0.0029 +- 0.0003 IC, and its LOB row is "L0 BTC LOB stage 0 +0.0007/44 (<+0.005 => do not buy Tardis)"
— a SINGLE-NAME, phase-0 DL-channel probe. It never tested an 811-name cross-sectional resting-liquidity
sleeve, and 28 GB of that data already sits on pod2 (`/workspace/lob_npz`, producer
`/workspace/f10/lob_consolidate.py`: 30 s grid, `lnot[:,i] = log1p(cumulative notional within band i)`,
bands [-5,-4,-3,-2,-1,-0.2,+0.2,+1,+2,+3,+4,+5] % from mid). Coverage (sampled 150 of 811 names):
~114 names 2023-01, ~232 2024-01, ~319 2025-01, ~562 2026-01, ~654 2026-07 — multi-year, so cross-regime
evaluation is possible, with the caveat that the early universe is thin.
**Mechanism:** resting-liquidity asymmetry is an inventory / positioning state that no bar-derived or
funding-derived column can express; the closed feature ceiling was measured without it.
**Construction (strictly causal):** for each name and each 4h anchor E, average the 30 s rows in
[E - 3600 s, E) (the hour BEFORE the anchor; no row at or after E is read), then
- LOBIMB1  = (N(-1) - N(+1)) / (N(-1) + N(+1)),  N = expm1(lnot)
- LOBIMB5  = (N(-5) - N(+5)) / (N(-5) + N(+5))
- LOBSLOPE = log((N(-5)+N(+5)) / (N(-1)+N(+1)))     [how far from mid the liquidity sits]
- LOBDEPTH = log(N(-1)+N(+1))
- LOBIMB1D = LOBIMB1 minus its own trailing 42-anchor (7 d) mean, causal   [innovation, not level]
Both signs => K += 10. **Total K = 68**; S6's Bonferroni level becomes alpha = 0.05/68.
Same Gate S, same device, same windows. A name-anchor with fewer than 20 of the 120 expected 30 s rows
in the window is NaN (not zero).

**AMENDMENT 2a (written after the LOB PANEL coverage receipt, before any LOB book number).**
Receipt `/workspace/uplift_2026-09-11/lob/COVERAGE.json`: mean names carrying LOBIMB1 per anchor =
2022 0.0 | 2023 182.0 | 2024 270.5 | 2025 430.2 | 2026 553.5. 2022 has NO LOB data, so S2 ("4 of 5
years positive") is unsatisfiable for batch-4 arms by construction. For batch 4 ONLY, S2 reads
">= 3 of the 4 year buckets with data (2023/2024/2025/2026) positive", and S1's full-cycle window
becomes 2023-01-01 -> 2026-08-10 20Z. All other gates unchanged. The LOB signal matrices are masked
to the same rank base as every other arm (finite f_fund_ema_v1) so the universes are comparable.
