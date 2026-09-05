# REPORT — Axis A: king retrain cadence × cutoff (K0 pinned / K1 rollm60 / K2 rollm1 / K3 rollw1) under strict causal OOS, fixed live seat

> **创建:** 2026-09-04 23:33Z – 2026-09-05 01:5xZ UTC | **Session:** b9646a9e, teammate `axisA` (cadence_seats) | **状态:** complete; decisions under the frozen criteria of `docs/PREREG_retrain_cadence_and_seat_rule_2026-09-05.md` §1 (D1 gate + book verdict) | **作废条件:** PREREG §0/§1 — any per-fold causal assertion False (checked: all True, §2); device default path not bitwise equal to the port baseline (checked: PASS, §1.3); any arm added or parameter changed after numbers were seen (none: arms K0/K1/K2/K3 and the D1 gate are the prereg's; the "K1 replicate" is a device-noise receipt, not a selection arm); also voided by any change of the production king recipe (78 keep cols / rank label / LGBM 400/0.05/63).
> Labels: **VERIFIED** = printed by a script and quoted with its command (all commands in `logs/commands.txt`); **INFERRED** = derived from verified facts with the reasoning stated; **UNRESOLVED** = not established here. **[单仪器 pod]**: every number below is from the pod instrument alone (jpline down); the port baseline equality (§1.3) is the only cross-instrument anchor.
> READ-ONLY on `/workspace/data`, `/workspace/shadow_bundle_v3`, `/workspace/port_w10`, `/workspace/review_scratch/{refute_*,combo_recheck,rolling_king}`. Writes only under `/workspace/review_scratch/cadence_seats/axisA/` (pod) and `…/scratchpad/review_caliber/cadence_seats/axisA/` (Mac). No GPU.

## 1. Device (what was run)

### 1.1 Training script `pod_king_cadence.py` (one script, three modes; sha256 in §7)
- **Data preparation and model recipe = `rolling_king/pod_king_rolling_monthly.py` verbatim** (itself `/workspace/pod_export_bundle_v3.py` L22, L26–47): FEA `/workspace/data/wide_fea_v2ext.npy`, meta `wide_fea_v2ext_meta.npz`, `keep` = 78 columns (asserted `== live_pins.json keep_names`), rows over `members` with finite y4 (anchors with <50 skipped), label `rr = rankdata(y4[ok])/max(n−1,1) − 0.5`; `LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, verbose=-1)`, `n_jobs=48`, `random_state = 20260905 + fold_index`. Printed (VERIFIED, every mode): `PREP X (2741477, 78) float32 Y (2741477,) rows_anchors 10176/10176 keep 78 E_ts[0] 2022-01-08 00:00 E_ts[-1] 2026-08-30 20:00`.
- **MODE=d1 (diagnostic D1)**: the 32 K1 monthly folds (test = calendar month 2024-01…2026-08, K1 rule `E_ts + 48·300 < first_test − 60·14400`, strict causal ASSERT) retrained with the same seeds — K1's script saved no boosters, so retraining was the only route. Each fold model then predicts **every row from its own test-month start through 2026-08-30**. Products: `d1_pred_age{1..12}.npy` (age k for an anchor in calendar month M = the model whose own test month is M−(k−1); age 1 = K1 itself), `d1_matrices.npz` (per (model, anchor) rank-IC and king-leg return vs raw y4 and dlw y4s), `slow_pred_d1_testfold.npy` (age-1 stitch), `models_d1/` (32 boosters), `folds_d1.json`.
- **MODE=monthly1 (K2)**: monthly folds, **embargo 1 anchor**: train rows = anchors with `E_ts + 48·300 <= first_test_E_ts − 14400`, i.e. the last training label window (E, E+4h] has closed by the previous anchor; ASSERT per fold `max(train E_ts)+48·300 <= min(test E_ts) − 14400` (plus a second assert that the last label is realized by the previous anchor). Product `slow_pred_rollm1.npy` + `folds_rollm1.json` + `models_rollm1/`.
- **MODE=weekly1 (K3)**: calendar-week folds (Monday 00:00Z; 2024-01-01 is a Monday, asserted), same 1-anchor rule, seeds 20260905 + fold index. Run only if the D1 gate says so (§2.1). Product `slow_pred_rollw1.npy` + `folds_rollw1.json`.
- All modes: predictions are float32 (10176, 829) aligned to meta E_ts, NaN outside test folds (2022–23 NaN like `slow_pred_pinned.npy`; finite mask asserted equal to pinned), stitched exactly as K1.

### 1.2 Book device and layouts
- `w10_universe_recheck.py` sha256 `5424aceb34b4595b8b9be0d720e90a60e1944fd9bb915fad4c934bc4cf59e9f9` copied from `rolling_king/` (= `combo_recheck/` copy = port `/workspace/port_w10/w10_universe.py` `64c70a44…` + the REF_SKIP guard only; diff printed in `logs/setup_dev.log`).
- `dev/` and `dev_alt/` = `rolling_king/setup_dev.sh` reproduced (ROOT changed only): `pod_backup_2026-08-21/*` → `/workspace/port_w10/pod_backup_2026-08-21/*` (resolving to `/workspace/shadow_bundle_v3/slow_pred_pinned.npy`, `/workspace/data/wide_fea_v2ext_meta.npz`, `/workspace/data/wide_panel_4h_v2ext.npz`), `f8_2026-08-22`, `dlw_2026-08-22` → `/workspace/port_w10/*`; `dev_alt/` swaps the meta for `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz` (sha256 `831857dd…`, y4 = Π(1+r5)−1 over [E+1,E+48] == dlw y4s bitwise per the refuters' PARITY receipt, re-printed in `logs/setup_dev.log`).
- **Arm = L-fix only** (PREREG §1): `MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 LEGS=101 LOOK=900 WRULE=msharpe CAL=log FSEED=42`, PHI default 0.45, F10 = `f10_V2MAIN_s42.npy` (finite to 2026-08-10 20:00Z); king source via `SLOW_NPY`; calibers: `log` (cwd `dev/`, raw Σ-simple y4, no transform) and `prod` (cwd `dev_alt/`, compounded target). `run_arms.sh <king>` launches both calibers and appends every command verbatim to `logs/commands.txt`.

### 1.3 Receipts — device equivalence (VERIFIED, `logs/check_equiv_pinned.log`, `logs/check_equiv_rollm.log`)
- **Port baseline (the prereg's voiding condition)**: my `dev/` pinned L-fix log run vs `/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz`: `d30_n2_c42_rec True, S0_rec True, d30_n2_c42_W True, S0_W True, config_equal(minus REF_SKIP)=True` → **PASS**. Same run vs `rolling_king/dev` pinned: PASS (identical file sha `d02a9724b948e36b`).
- **Compounded caliber**: my `dev_alt/` pinned L-fix prod run vs `rolling_king/dev_alt` pinned (sha `198e0f1ef69478fd`, identical) and vs `refute_C6_2/altrun/newprod/…alt_newprod_w3fix.npz`: PASS, PASS.
- **K1 (rollm) book artifacts reused legitimately**: my `dev/` and `dev_alt/` reruns of K1 L-fix (SLOW_NPY = `rolling_king/slow_pred_rollm.npy`, sha256 `999f7d4d…`) are bitwise equal to `rolling_king`'s (`8f9cd48f7d6d506a`, `d73f21390691efdb`): PASS, PASS → the K1 rows of every book table below are the rolling_king artifacts re-produced in my layout.

### 1.4 Judge `judge.py` (copied from `rolling_king/judge.py`, adapted: L-fix only, kings K0–K3, K2−K1 and K3−K2 pairs, verdict per PREREG §1)
- Arm `d30_n2_c42`, column `net_ex` (bps/anchor per unit NAV, executor caliber); anchors paired by ts (identical sets asserted). Windows: 2024 | 2025 | 2026≤08-10 (ts ≤ 2026-08-10 20:00Z, last finite F10 row) | 2026→08-30 | 2024→26 (auxiliary) | **2025→26 (PRIMARY)**; ≤cut variants printed.
- Bootstrap: UTC-calendar-day blocks, 2000 resamples, seed 20260905, CI95 = 2.5/97.5 pct of resampled means, P = share > 0. Sharpe = mean/std(ddof=1)·√2190; maxDD = max(cummax(cumsum) − cumsum) in bps; Δturnover% = (turn_x/turn_ref − 1)·100 over the **primary window 2025→26** (2024→26 printed too); units chain printed by the script: %/gross/yr = bps/anchor × 2190 / 100.
- **Frozen decision (PREREG §1)**, per candidate K1/K2/K3 vs K0: **ADMIT-candidate** iff for BOTH calibers 2025→26 CI95 lower > 0 AND Δturnover ≤ +15%; **REJECT** iff for EITHER caliber 2025→26 CI95 upper < 0 OR Δturnover > +25%; else **UNDECIDED**. K2−K1 = embargo cost, reported separately (not for selection). K3−K2 = cadence at equal embargo (auxiliary).
- **D1 gate (PREREG §1 D1)**: paired IC(age 1) − IC(age 12) on the common anchor set (anchors where all 12 ages exist = months 2024-12…2026-08), raw y4 primary with dlw y4s alongside; K3 runs iff either ≥ 0.003 (fixed in `d1_curve.py` before any number; `chain_k3.sh` reads the decision from `d1_curve.json`, so the launch itself was mechanical).

## 0. Answer (one paragraph) and the frozen decisions

**Question (PREREG §1, axis A):** does retraining the production king tree more often (monthly, weekly) and/or with the latest possible cutoff (1-anchor embargo instead of 60 anchors) help the live book, evaluated by a literal simulation of the production process under strict causal OOS and the live fixed seat (W3FIX king 0.21 / fund 0.79)?

**Answer.** Model age has a real, measurable cost **at the score level**: with the K1 recipe, a model's rank-IC falls monotonically with age, about −0.0014 IC per month, from +0.0647 at age 1 month to +0.0490 at age 12 (paired, same anchors, n 3828: **Δ +0.0156 ± 0.0012**, CI95 [+0.0133, +0.0180] vs raw y4; +0.0171 ± 0.0012 vs the compounded target) — five times the prereg's 0.003 gate, so the gate fired and K3 (weekly) was run. Inside a month the loss is small: weeks 1–3 are flat (Δ ≤ 0.0009), a step of ≈0.0024 appears at week 4 and the curve is flat again to week 8 (Δ(1w−8w) +0.0028 ± 0.0006); weekly vs monthly freshness is worth ≈ +0.0017 ± 0.0003 IC (weeks 1–4 vs 5–8, paired). Consistently, the fresh kings rank K3 > K2 > K1 > K0 in IC (2025→26 raw: +0.0666 / +0.0648 / +0.0645 / +0.0612), and K2/K3 also beat K0 on the **king-leg return** in every window (+0.18 to +0.43 bps per unit gross per anchor), whereas K1's leg was *lower* than K0's in 2026 (−0.5) — so the previous report's "IC up, leg down" for K1 was in good part the 60-anchor embargo, not freshness. **At the book level, none of it is detectable at the live seat**: with the frozen judge (L-fix, arm d30_n2_c42, net_ex, paired anchors, day-block bootstrap), **K1, K2 and K3 are all UNDECIDED in both calibers** — no CI95 lower bound above zero, no upper bound below zero, turnover unchanged (−0.1%). The best point estimate is **K2 (monthly, 1-anchor embargo): 2025→26 Δ +0.031 [−0.027, +0.093] bps/anchor (raw) and +0.050 [−0.026, +0.128] (compounded) = +0.7 / +1.1 %/gross/yr, P(Δ>0) 0.84 / 0.89**, positive in 2025 and 2026 in both calibers, maxDD 2025→26 902 → 856 bps (raw). **K3 (weekly) is not better than K2 at the book**: K3−K2 at equal embargo is −0.045 [−0.098, +0.003] raw / −0.036 [−0.081, +0.007] compounded on 2025→26 (P(Δ>0) 0.03 / 0.05) despite the higher IC — cadence beyond monthly has no book value under this seat. The embargo itself (K2−K1) is worth +0.040 [−0.015, +0.095] raw / +0.035 [−0.035, +0.107] compounded on 2025→26 (reported separately, not for selection). Everything here is measured with a device whose replicate noise is exactly zero (retrained K1 reproduces K1's predictions bitwise on 2.7M rows) — the widths are the market's, not the device's: with 3642 anchors the CI half-width is ≈0.06 bps/anchor, so a true +0.03 effect cannot be resolved without ≈4× the sample.

**Frozen decisions (PREREG §1, primary 2025→26, both calibers):** D1 gate = **decay detectable (K3 RUN)**; K1 rollm60 **UNDECIDED**; K2 rollm1 **UNDECIDED**; K3 rollw1 **UNDECIDED**. No ADMIT candidate, no REJECT. **[单仪器 pod]** throughout.

## 2. Results — reading guide (all tables in §2.x below are rendered from the JSON products by `render_tables.py`; VERIFIED unless marked)

### 2.0 Fold assertions
- **D1 (32 folds, K1 rule, embargo 60):** every fold printed `-> True`, gap exactly 1 anchor between the last training label end and the embargo boundary (identical to K1's log). **The retrained models reproduce K1 exactly at the prediction level**: stitched test-fold predictions `array_equal(equal_nan) True`, max|Δ| 0, file sha256 identical to `slow_pred_rollm.npy` (`999f7d4d…`); train rows equal 32/32. The booster *text dumps* are bitwise equal to K1's in only 1/32 folds (UNRESOLVED why the text differs — the parameter blocks of the saved models differ across folds only in the per-fold seeds; `force_col_wise/force_row_wise` are both recorded as 0 in every file — but the difference is provably not in anything that affects prediction). Consequence: the "LightGBM-bits noise floor" is **exactly zero** (§2.4): per-anchor Spearman between the replicate and K1 = 1.0000 on all 5838 anchors, ΔIC = 0, Δleg = 0, book Δ = +0.000 in every window.
- **K2 (32 monthly folds, embargo 1 anchor):** every fold `-> True` with gap **0 anchors**, i.e. the last training label window closes exactly at the previous anchor (e.g. fold 0: `max(train E_ts)+48·300 = 2023-12-31 20:00 <= min(test E_ts)−14400 = 2023-12-31 20:00`); train rows 709,220 → 2,669,077; fit 23.6 / 30.2 / 55.4 s (min/median/max, n_jobs 48), total 1054 s, wall 1068 s.
- **K3 (139 weekly folds, Monday 00:00Z 2024-01-01 → 2026-08-24, embargo 1 anchor):** 139/139 `-> True`, gap 0 anchors; train rows 709,220 → 2,724,277; fit **17.8 / 29.1 / 73.8 s** per fit, **total 4677 s (78 min), wall 4702 s** at n_jobs 48 on the pod's 64 cores. (The prereg's "≈190 folds" was an over-estimate: 2024-01-01 → 2026-08-30 contains exactly 139 Monday-weeks, VERIFIED by calendar count.)
- All three prediction files are float32 (10176, 829), finite mask equal to pinned (2024-01-01 → 2026-08-30 20:00Z, 5838 anchors; 2022–23 NaN).

### 2.1 D1 — IC vs model age (monthly resolution; Tables A–F)
- **Monotone decay, ≈ −0.0014 IC/month.** Common set (months 2024-12 → 2026-08, n 3828 anchors, raw y4): age 1 +0.0647 → age 3 +0.0622 → age 6 +0.0593 → age 9 +0.0552 → age 12 +0.0490. Paired Δ(1−k) is already significant at k = 2 (+0.0015 ± 0.0006, CI [+0.0004, +0.0025]) and grows to **+0.0156 ± 0.0012 at k = 12** (t 13.4); the compounded target gives the same shape (+0.0695 → +0.0523, Δ +0.0171 ± 0.0012). The "own set" pairing (Table C) and the days-since-cutoff bins (Table D: 0–30 d +0.0637 → 330–360 d +0.0513) agree. By year (Table E): 2025 Δ(1−12) +0.0173 ± 0.0018, 2026 +0.0126 ± 0.0013 (2024 has only the December anchors, n 186, +0.0196 ± 0.0059).
- **The king-leg return does not follow the IC curve.** Ages 1–11 sit within ±0.4 bps of each other (leg +2.2 to +2.7 bps/gross/anchor, s.e. ≈0.3); only age 12 is lower (+1.62 vs +2.60, Δ +0.99 ± 0.35 raw; +0.99 ± 0.36 compounded). The days bins show no trend until 270+ d. INFERRED: a 0.016 IC loss is ≈25% of the king's IC, but the rank-book leg return is dominated by anchor-level noise (S/anchor ≈ 0.08), so a 25% IC change is barely visible at the leg and, at seat 0.21, invisible at the book.
- **K0's own age curve (Table F, auxiliary):** by month-of-year the pinned king shows no within-year decay (H1 +0.0589 vs H2 +0.0585, ±0.0030 unpaired) — this is the seasonal confound the paired D1 design removes; on the same anchors K1 (age 1) beats pinned mainly in Oct–Dec (+0.0136, +0.0167, +0.0156), exactly where the pinned model is oldest.

### 2.2 Weekly-resolution age curve (addendum; Tables W-A/W-B/W-D)
- From the 139 saved K3 boosters, each predicting its next 8 weeks (16.0 M rows; receipt: the age-1 stitch from the saved boosters equals `slow_pred_rollw1.npy` bitwise). Common set n 5544 (raw): age 1 w +0.0658, 2 w +0.0649, 3 w +0.0654, **4 w +0.0634**, 5 w +0.0636, 6–8 w +0.0630. Paired Δ(1−w): weeks 2–3 not distinguishable from 0 (+0.0009 ± 0.0005, +0.0004 ± 0.0005); **week 4 +0.0024 ± 0.0005**; weeks 5–8 +0.0022 to +0.0028 (± 0.0005–0.0006); compounded target identical in shape. Weeks 1–4 vs 5–8: **+0.0017 ± 0.0003** (raw), +0.0018 ± 0.0003 (compounded). Days bins (7-day): 0–21 d ≈ +0.066, 21–56 d ≈ +0.063. The king leg by weekly age is flat within noise (+2.2 to +2.6, s.e. ≈0.18).
- INFERRED: the intra-month decay is a step around 3–4 weeks of age rather than a slope, and its size (≈0.002–0.003 IC) is what a weekly cadence buys over a monthly one — about 1/6 of the 12-month decay.

### 2.3 IC and king leg by king (Tables "Yearly mean rank-IC", "King leg", "msharpe seat")
- **IC (raw y4, identical anchor sets):** 2025→26 K0 +0.0612, K1 +0.0645 (+0.0034 ± 0.0007), K2 +0.0648 (+0.0036 ± 0.0007), **K3 +0.0666 (+0.0054 ± 0.0008)**; 2026→08-30 K0 +0.0584, K1 +0.0005 ± 0.0009, K2 +0.0017 ± 0.0009, K3 +0.0033 ± 0.0010; 2024 K1/K2/K3 +0.0087/+0.0107/+0.0111 (± 0.0015–0.0017). Compounded target: same ordering (2025→26 +0.0036/+0.0036/+0.0057).
- **King leg (production definition, bps per unit gross per anchor, raw):** 2025→26 K0 +2.680, K1 +2.647 (−0.033), **K2 +2.864 (+0.184), K3 +2.999 (+0.320)**; 2026→08-30 K0 +3.130, K1 +2.625 (**−0.505**), K2 +3.341 (+0.211), K3 +3.337 (+0.208); 2024 Δ +0.311 (K2), +0.140 (K3), −0.020 (K1). Compounded: 2025→26 Δ −0.093 / +0.182 / +0.431. Seat-window S/anchor (900 anchors to 2026-08-10): K0 0.1014, K1 0.0796, K2 0.1083, K3 0.1077 → production msharpe w101 king at 2026-08-10: **0.288 / 0.241 / 0.301 / 0.300**. INFERRED: under the live dynamic rule K2/K3 would take a marginally larger seat than K0 and K1 a smaller one; axis A was judged at the fixed seat per the prereg, so this is a property, not a result.

### 2.4 Book (L-fix, arm d30_n2_c42, net_ex; Tables "Book levels", "Book deltas", "Frozen decision")
- **Levels (raw caliber, bps/anchor; %/gross/yr = ×2190/100):** K0 2024 −0.642 (S −1.68, maxDD 1815) / 2025 +0.284 (S +0.67) / 2026 +2.378 (S +4.21) / 2025→26 +1.119 (S 2.31) / 2024→26 +0.457 (S 1.02) = **−14.1 / +6.2 / +52.1 %/gross/yr**, worst month 2024-11 −717 bps; K2 −0.647 / +0.303 / +2.428 / +1.150 (S 2.37) / +0.474 (S 1.06) = −14.2 / +6.6 / +53.2, worst month −700; K3 −0.639 / +0.275 / +2.356 / +1.105 / +0.449 = −14.0 / +6.0 / +51.6; K1 −0.625 / +0.284 / +2.357 / +1.110 / +0.457. Compounded caliber: K0 −15.5 / +5.6 / +50.9, K2 −15.2 / +6.2 / +52.6, K3 −15.3 / +5.1 / +52.3 (worst month 2024-11 −757 / −735 / −732). **2024 is a losing year for every king (−14 to −16 %/gross)** — the king source does not change that; the level differences across kings are 0.5–1.5 %/gross/yr, one to two orders below the year-to-year swings.
- **Paired Δ vs K0, 2025→26 (primary):** K1 −0.009 [−0.076, +0.058] raw / +0.015 [−0.054, +0.089] compounded; **K2 +0.031 [−0.027, +0.093] (P 0.84) / +0.050 [−0.026, +0.128] (P 0.89)**; K3 −0.014 [−0.077, +0.049] / +0.013 [−0.064, +0.091]. 2024→26 (auxiliary): K2 +0.018 [−0.025, +0.060] / +0.036 [−0.016, +0.090]. Yearly K2−K0 raw −0.005 / +0.018 / +0.050, compounded +0.013 / +0.030 / +0.079. Δturnover −0.1% for every king; maxDD 2025→26 raw K0 902 → K1 881 / K2 856 / K3 856.
- **Embargo cost K2−K1 (separate):** +0.040 [−0.015, +0.095] raw / +0.035 [−0.035, +0.107] compounded (2025→26); yearly raw −0.022 (2024, CI [−0.049, +0.004], P 0.05) / +0.019 / +0.072. **Cadence at equal embargo K3−K2 (auxiliary):** −0.045 [−0.098, +0.003] raw (P 0.03) / −0.036 [−0.081, +0.007] compounded (P 0.05); 2024→26 −0.025 [−0.059, +0.008] / −0.024 [−0.057, +0.006].
- **σ_fund terciles (auxiliary):** every K−K0 cell has a CI containing 0; K2−K1 is nominally negative in the low-σ_fund tercile (−0.024 [−0.050, +0.004]) and positive in the high tercile (+0.059 [−0.020, +0.140]).
- **Verdicts:** K1 UNDECIDED, K2 UNDECIDED, K3 UNDECIDED (both calibers; table "Frozen decision").

## 2.x Tables (rendered by `render_tables.py` from the JSON products; `REPORT_tables.md` sha256 a4e8d6441d2ffefe59ccf866f6e551fc6144c8f16465a41eb2e8a5f364401e0d)

### Folds — D1 retrain of the K1 monthly folds (embargo 60, same seeds): `slow_pred_d1_testfold.npy` sha256 `999f7d4d8fa4de8e9eb46305d31af8a06b14419b07389f269a8d2fbad138be4a`; script sha256 `1756b1ad4e58b62d059c1834700068a16d89f9ec596e5681284d833bef7ddeda`; train_rule = `E_ts + 48*300 < first_test_E_ts - 60*14400 (rolling_king K1 rule verbatim; strict '<')`; assert = `max(train E_ts)+48*300 < min(test E_ts)-60*14400`; finite-mask equal to pinned = **True**; all asserts True = **True**; folds 32; total fit 1104s, wall 1227s
D1 receipts: stitched test-fold predictions == K1 `slow_pred_rollm.npy` (array_equal, equal_nan) = **True**, max|Δ| 0.000e+00; boosters bitwise equal to K1 = **1/32**; train_rows equal to K1 = 32/32

| fold | test key | seed | train rows | train span | test anchors (rows) | test span | ASSERT | gap (anchors) | fit s | rank-IC raw | booster == K1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 202401 | 20260905 | 694,846 | 2022-01-08..2023-12-21 16:00 | 186/186 (45,328) | 2024-01-01 00:00..2024-01-31 20:00 | 1703188800 (2023-12-21 20:00) < 1703203200 (2023-12-22 00:00) → **True** | 1 | 18.6 | +0.0799 | False |
| 1 | 202402 | 20260906 | 739,796 | 2022-01-08..2024-01-21 16:00 | 174/174 (43,891) | 2024-02-01 00:00..2024-02-29 20:00 | 1705867200 (2024-01-21 20:00) < 1705881600 (2024-01-22 00:00) → **True** | 1 | 18.6 | +0.0636 | False |
| 2 | 202403 | 20260907 | 783,135 | 2022-01-08..2024-02-19 16:00 | 186/186 (48,790) | 2024-03-01 00:00..2024-03-31 20:00 | 1708372800 (2024-02-19 20:00) < 1708387200 (2024-02-20 00:00) → **True** | 1 | 18.4 | +0.0698 | False |
| 3 | 202404 | 20260908 | 831,269 | 2022-01-08..2024-03-21 16:00 | 180/180 (47,685) | 2024-04-01 00:00..2024-04-30 20:00 | 1711051200 (2024-03-21 20:00) < 1711065600 (2024-03-22 00:00) → **True** | 1 | 38.2 | +0.0620 | False |
| 4 | 202405 | 20260909 | 878,888 | 2022-01-08..2024-04-20 16:00 | 186/186 (49,326) | 2024-05-01 00:00..2024-05-31 20:00 | 1713643200 (2024-04-20 20:00) < 1713657600 (2024-04-21 00:00) → **True** | 1 | 23.2 | +0.0373 | False |
| 5 | 202406 | 20260910 | 928,597 | 2022-01-08..2024-05-21 16:00 | 180/180 (47,074) | 2024-06-01 00:00..2024-06-30 20:00 | 1716321600 (2024-05-21 20:00) < 1716336000 (2024-05-22 00:00) → **True** | 1 | 24.1 | +0.0498 | False |
| 6 | 202407 | 20260911 | 975,508 | 2022-01-08..2024-06-20 16:00 | 186/186 (48,804) | 2024-07-01 00:00..2024-07-31 20:00 | 1718913600 (2024-06-20 20:00) < 1718928000 (2024-06-21 00:00) → **True** | 1 | 27.1 | +0.0463 | True |
| 7 | 202408 | 20260912 | 1,024,427 | 2022-01-08..2024-07-21 16:00 | 186/186 (49,097) | 2024-08-01 00:00..2024-08-31 20:00 | 1721592000 (2024-07-21 20:00) < 1721606400 (2024-07-22 00:00) → **True** | 1 | 28.5 | +0.0647 | False |
| 8 | 202409 | 20260913 | 1,073,101 | 2022-01-08..2024-08-21 16:00 | 180/180 (50,450) | 2024-09-01 00:00..2024-09-30 20:00 | 1724270400 (2024-08-21 20:00) < 1724284800 (2024-08-22 00:00) → **True** | 1 | 29.0 | +0.0566 | False |
| 9 | 202410 | 20260914 | 1,122,445 | 2022-01-08..2024-09-20 16:00 | 186/186 (54,920) | 2024-10-01 00:00..2024-10-31 20:00 | 1726862400 (2024-09-20 20:00) < 1726876800 (2024-09-21 00:00) → **True** | 1 | 29.3 | +0.0801 | False |
| 10 | 202411 | 20260915 | 1,176,741 | 2022-01-08..2024-10-21 16:00 | 180/180 (55,301) | 2024-11-01 00:00..2024-11-30 20:00 | 1729540800 (2024-10-21 20:00) < 1729555200 (2024-10-22 00:00) → **True** | 1 | 28.4 | +0.0850 | False |
| 11 | 202412 | 20260916 | 1,230,937 | 2022-01-08..2024-11-20 16:00 | 186/186 (60,740) | 2024-12-01 00:00..2024-12-31 20:00 | 1732132800 (2024-11-20 20:00) < 1732147200 (2024-11-21 00:00) → **True** | 1 | 25.0 | +0.0670 | False |
| 12 | 202501 | 20260917 | 1,290,492 | 2022-01-08..2024-12-21 16:00 | 186/186 (64,291) | 2025-01-01 00:00..2025-01-31 20:00 | 1734811200 (2024-12-21 20:00) < 1734825600 (2024-12-22 00:00) → **True** | 1 | 26.0 | +0.0800 | False |
| 13 | 202502 | 20260918 | 1,353,644 | 2022-01-08..2025-01-21 16:00 | 168/168 (60,310) | 2025-02-01 00:00..2025-02-28 20:00 | 1737489600 (2025-01-21 20:00) < 1737504000 (2025-01-22 00:00) → **True** | 1 | 25.7 | +0.0607 | False |
| 14 | 202503 | 20260919 | 1,413,353 | 2022-01-08..2025-02-18 16:00 | 186/186 (68,046) | 2025-03-01 00:00..2025-03-31 20:00 | 1739908800 (2025-02-18 20:00) < 1739923200 (2025-02-19 00:00) → **True** | 1 | 26.7 | +0.0738 | False |
| 15 | 202504 | 20260920 | 1,480,918 | 2022-01-08..2025-03-21 16:00 | 180/180 (69,340) | 2025-04-01 00:00..2025-04-30 20:00 | 1742587200 (2025-03-21 20:00) < 1742601600 (2025-03-22 00:00) → **True** | 1 | 49.8 | +0.0445 | False |
| 16 | 202505 | 20260921 | 1,549,071 | 2022-01-08..2025-04-20 16:00 | 186/186 (74,224) | 2025-05-01 00:00..2025-05-31 20:00 | 1745179200 (2025-04-20 20:00) < 1745193600 (2025-04-21 00:00) → **True** | 1 | 28.7 | +0.0593 | False |
| 17 | 202506 | 20260922 | 1,622,677 | 2022-01-08..2025-05-21 16:00 | 180/180 (72,000) | 2025-06-01 00:00..2025-06-30 20:00 | 1747857600 (2025-05-21 20:00) < 1747872000 (2025-05-22 00:00) → **True** | 1 | 28.7 | +0.0749 | False |
| 18 | 202507 | 20260923 | 1,694,677 | 2022-01-08..2025-06-20 16:00 | 186/186 (74,400) | 2025-07-01 00:00..2025-07-31 20:00 | 1750449600 (2025-06-20 20:00) < 1750464000 (2025-06-21 00:00) → **True** | 1 | 52.9 | +0.0797 | False |
| 19 | 202508 | 20260924 | 1,769,077 | 2022-01-08..2025-07-21 16:00 | 186/186 (74,400) | 2025-08-01 00:00..2025-08-31 20:00 | 1753128000 (2025-07-21 20:00) < 1753142400 (2025-07-22 00:00) → **True** | 1 | 32.0 | +0.0802 | False |
| 20 | 202509 | 20260925 | 1,843,477 | 2022-01-08..2025-08-21 16:00 | 180/180 (72,000) | 2025-09-01 00:00..2025-09-30 20:00 | 1755806400 (2025-08-21 20:00) < 1755820800 (2025-08-22 00:00) → **True** | 1 | 32.9 | +0.0557 | False |
| 21 | 202510 | 20260926 | 1,915,477 | 2022-01-08..2025-09-20 16:00 | 186/186 (74,400) | 2025-10-01 00:00..2025-10-31 20:00 | 1758398400 (2025-09-20 20:00) < 1758412800 (2025-09-21 00:00) → **True** | 1 | 34.7 | +0.0656 | False |
| 22 | 202511 | 20260927 | 1,989,877 | 2022-01-08..2025-10-21 16:00 | 180/180 (72,000) | 2025-11-01 00:00..2025-11-30 20:00 | 1761076800 (2025-10-21 20:00) < 1761091200 (2025-10-22 00:00) → **True** | 1 | 35.5 | +0.0786 | False |
| 23 | 202512 | 20260928 | 2,061,877 | 2022-01-08..2025-11-20 16:00 | 186/186 (74,400) | 2025-12-01 00:00..2025-12-31 20:00 | 1763668800 (2025-11-20 20:00) < 1763683200 (2025-11-21 00:00) → **True** | 1 | 38.1 | +0.0656 | False |
| 24 | 202601 | 20260929 | 2,136,277 | 2022-01-08..2025-12-21 16:00 | 186/186 (74,400) | 2026-01-01 00:00..2026-01-31 20:00 | 1766347200 (2025-12-21 20:00) < 1766361600 (2025-12-22 00:00) → **True** | 1 | 46.4 | +0.0733 | False |
| 25 | 202602 | 20260930 | 2,210,677 | 2022-01-08..2026-01-21 16:00 | 168/168 (67,200) | 2026-02-01 00:00..2026-02-28 20:00 | 1769025600 (2026-01-21 20:00) < 1769040000 (2026-01-22 00:00) → **True** | 1 | 45.1 | +0.0508 | False |
| 26 | 202603 | 20260931 | 2,277,877 | 2022-01-08..2026-02-18 16:00 | 186/186 (74,400) | 2026-03-01 00:00..2026-03-31 20:00 | 1771444800 (2026-02-18 20:00) < 1771459200 (2026-02-19 00:00) → **True** | 1 | 45.0 | +0.0637 | False |
| 27 | 202604 | 20260932 | 2,352,277 | 2022-01-08..2026-03-21 16:00 | 180/180 (72,000) | 2026-04-01 00:00..2026-04-30 20:00 | 1774123200 (2026-03-21 20:00) < 1774137600 (2026-03-22 00:00) → **True** | 1 | 47.2 | +0.0675 | False |
| 28 | 202605 | 20260933 | 2,424,277 | 2022-01-08..2026-04-20 16:00 | 186/186 (74,400) | 2026-05-01 00:00..2026-05-31 20:00 | 1776715200 (2026-04-20 20:00) < 1776729600 (2026-04-21 00:00) → **True** | 1 | 48.3 | +0.0616 | False |
| 29 | 202606 | 20260934 | 2,498,677 | 2022-01-08..2026-05-21 16:00 | 180/180 (72,000) | 2026-06-01 00:00..2026-06-30 20:00 | 1779393600 (2026-05-21 20:00) < 1779408000 (2026-05-22 00:00) → **True** | 1 | 50.6 | +0.0417 | False |
| 30 | 202607 | 20260935 | 2,570,677 | 2022-01-08..2026-06-20 16:00 | 186/186 (74,400) | 2026-07-01 00:00..2026-07-31 20:00 | 1781985600 (2026-06-20 20:00) < 1782000000 (2026-06-21 00:00) → **True** | 1 | 48.4 | +0.0644 | False |
| 31 | 202608 | 20260936 | 2,645,077 | 2022-01-08..2026-07-21 16:00 | 180/180 (72,000) | 2026-08-01 00:00..2026-08-30 20:00 | 1784664000 (2026-07-21 20:00) < 1784678400 (2026-07-22 00:00) → **True** | 1 | 52.5 | +0.0461 | False |

### Folds — K2 monthly, embargo 1 anchor: `slow_pred_rollm1.npy` sha256 `656ae170ce65d78dbcfd40093ddc156c9d62eba0b9d645f7b930124b5301479f`; script sha256 `1756b1ad4e58b62d059c1834700068a16d89f9ec596e5681284d833bef7ddeda`; train_rule = `E_ts + 48*300 <= first_test_E_ts - 14400 (label window (E,E+4h] realized by the previous anchor; '<=')`; assert = `max(train E_ts)+48*300 <= min(test E_ts)-14400`; finite-mask equal to pinned = **True**; all asserts True = **True**; folds 32; total fit 1054s, wall 1068s

| fold | test key | seed | train rows | train span | test anchors (rows) | test span | ASSERT | gap (anchors) | fit s | rank-IC raw | 
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 202401 | 20260905 | 709,220 | 2022-01-08..2023-12-31 16:00 | 186/186 (45,328) | 2024-01-01 00:00..2024-01-31 20:00 | 1704052800 (2023-12-31 20:00) <= 1704052800 (2023-12-31 20:00) → **True** | 0 | 25.7 | +0.0865 |
| 1 | 202402 | 20260906 | 754,541 | 2022-01-08..2024-01-31 16:00 | 174/174 (43,891) | 2024-02-01 00:00..2024-02-29 20:00 | 1706731200 (2024-01-31 20:00) <= 1706731200 (2024-01-31 20:00) → **True** | 0 | 24.5 | +0.0661 |
| 2 | 202403 | 20260907 | 798,421 | 2022-01-08..2024-02-29 16:00 | 186/186 (48,790) | 2024-03-01 00:00..2024-03-31 20:00 | 1709236800 (2024-02-29 20:00) <= 1709236800 (2024-02-29 20:00) → **True** | 0 | 25.1 | +0.0746 |
| 3 | 202404 | 20260908 | 847,203 | 2022-01-08..2024-03-31 16:00 | 180/180 (47,685) | 2024-04-01 00:00..2024-04-30 20:00 | 1711915200 (2024-03-31 20:00) <= 1711915200 (2024-03-31 20:00) → **True** | 0 | 26.6 | +0.0609 |
| 4 | 202405 | 20260909 | 894,887 | 2022-01-08..2024-04-30 16:00 | 186/186 (49,326) | 2024-05-01 00:00..2024-05-31 20:00 | 1714507200 (2024-04-30 20:00) <= 1714507200 (2024-04-30 20:00) → **True** | 0 | 26.2 | +0.0403 |
| 5 | 202406 | 20260910 | 944,220 | 2022-01-08..2024-05-31 16:00 | 180/180 (47,074) | 2024-06-01 00:00..2024-06-30 20:00 | 1717185600 (2024-05-31 20:00) <= 1717185600 (2024-05-31 20:00) → **True** | 0 | 23.6 | +0.0494 |
| 6 | 202407 | 20260911 | 991,289 | 2022-01-08..2024-06-30 16:00 | 186/186 (48,804) | 2024-07-01 00:00..2024-07-31 20:00 | 1719777600 (2024-06-30 20:00) <= 1719777600 (2024-06-30 20:00) → **True** | 0 | 25.6 | +0.0514 |
| 7 | 202408 | 20260912 | 1,040,097 | 2022-01-08..2024-07-31 16:00 | 186/186 (49,097) | 2024-08-01 00:00..2024-08-31 20:00 | 1722456000 (2024-07-31 20:00) <= 1722456000 (2024-07-31 20:00) → **True** | 0 | 26.4 | +0.0666 |
| 8 | 202409 | 20260913 | 1,089,183 | 2022-01-08..2024-08-31 16:00 | 180/180 (50,450) | 2024-09-01 00:00..2024-09-30 20:00 | 1725134400 (2024-08-31 20:00) <= 1725134400 (2024-08-31 20:00) → **True** | 0 | 28.7 | +0.0583 |
| 9 | 202410 | 20260914 | 1,139,615 | 2022-01-08..2024-09-30 16:00 | 186/186 (54,920) | 2024-10-01 00:00..2024-10-31 20:00 | 1727726400 (2024-09-30 20:00) <= 1727726400 (2024-09-30 20:00) → **True** | 0 | 27.4 | +0.0788 |
| 10 | 202411 | 20260915 | 1,194,527 | 2022-01-08..2024-10-31 16:00 | 180/180 (55,301) | 2024-11-01 00:00..2024-11-30 20:00 | 1730404800 (2024-10-31 20:00) <= 1730404800 (2024-10-31 20:00) → **True** | 0 | 28.8 | +0.0831 |
| 11 | 202412 | 20260916 | 1,249,809 | 2022-01-08..2024-11-30 16:00 | 186/186 (60,740) | 2024-12-01 00:00..2024-12-31 20:00 | 1732996800 (2024-11-30 20:00) <= 1732996800 (2024-11-30 20:00) → **True** | 0 | 27.5 | +0.0700 |
| 12 | 202501 | 20260917 | 1,310,528 | 2022-01-08..2024-12-31 16:00 | 186/186 (64,291) | 2025-01-01 00:00..2025-01-31 20:00 | 1735675200 (2024-12-31 20:00) <= 1735675200 (2024-12-31 20:00) → **True** | 0 | 28.3 | +0.0796 |
| 13 | 202502 | 20260918 | 1,374,800 | 2022-01-08..2025-01-31 16:00 | 168/168 (60,310) | 2025-02-01 00:00..2025-02-28 20:00 | 1738353600 (2025-01-31 20:00) <= 1738353600 (2025-01-31 20:00) → **True** | 0 | 27.9 | +0.0602 |
| 14 | 202503 | 20260919 | 1,435,104 | 2022-01-08..2025-02-28 16:00 | 186/186 (68,046) | 2025-03-01 00:00..2025-03-31 20:00 | 1740772800 (2025-02-28 20:00) <= 1740772800 (2025-02-28 20:00) → **True** | 0 | 52.3 | +0.0737 |
| 15 | 202504 | 20260920 | 1,503,136 | 2022-01-08..2025-03-31 16:00 | 180/180 (69,340) | 2025-04-01 00:00..2025-04-30 20:00 | 1743451200 (2025-03-31 20:00) <= 1743451200 (2025-03-31 20:00) → **True** | 0 | 29.7 | +0.0468 |
| 16 | 202505 | 20260921 | 1,572,460 | 2022-01-08..2025-04-30 16:00 | 186/186 (74,224) | 2025-05-01 00:00..2025-05-31 20:00 | 1746043200 (2025-04-30 20:00) <= 1746043200 (2025-04-30 20:00) → **True** | 0 | 29.3 | +0.0584 |
| 17 | 202506 | 20260922 | 1,646,677 | 2022-01-08..2025-05-31 16:00 | 180/180 (72,000) | 2025-06-01 00:00..2025-06-30 20:00 | 1748721600 (2025-05-31 20:00) <= 1748721600 (2025-05-31 20:00) → **True** | 0 | 31.7 | +0.0718 |
| 18 | 202507 | 20260923 | 1,718,677 | 2022-01-08..2025-06-30 16:00 | 186/186 (74,400) | 2025-07-01 00:00..2025-07-31 20:00 | 1751313600 (2025-06-30 20:00) <= 1751313600 (2025-06-30 20:00) → **True** | 0 | 51.6 | +0.0790 |
| 19 | 202508 | 20260924 | 1,793,077 | 2022-01-08..2025-07-31 16:00 | 186/186 (74,400) | 2025-08-01 00:00..2025-08-31 20:00 | 1753992000 (2025-07-31 20:00) <= 1753992000 (2025-07-31 20:00) → **True** | 0 | 30.2 | +0.0794 |
| 20 | 202509 | 20260925 | 1,867,477 | 2022-01-08..2025-08-31 16:00 | 180/180 (72,000) | 2025-09-01 00:00..2025-09-30 20:00 | 1756670400 (2025-08-31 20:00) <= 1756670400 (2025-08-31 20:00) → **True** | 0 | 31.8 | +0.0565 |
| 21 | 202510 | 20260926 | 1,939,477 | 2022-01-08..2025-09-30 16:00 | 186/186 (74,400) | 2025-10-01 00:00..2025-10-31 20:00 | 1759262400 (2025-09-30 20:00) <= 1759262400 (2025-09-30 20:00) → **True** | 0 | 55.4 | +0.0667 |
| 22 | 202511 | 20260927 | 2,013,877 | 2022-01-08..2025-10-31 16:00 | 180/180 (72,000) | 2025-11-01 00:00..2025-11-30 20:00 | 1761940800 (2025-10-31 20:00) <= 1761940800 (2025-10-31 20:00) → **True** | 0 | 33.3 | +0.0754 |
| 23 | 202512 | 20260928 | 2,085,877 | 2022-01-08..2025-11-30 16:00 | 186/186 (74,400) | 2025-12-01 00:00..2025-12-31 20:00 | 1764532800 (2025-11-30 20:00) <= 1764532800 (2025-11-30 20:00) → **True** | 0 | 33.7 | +0.0659 |
| 24 | 202601 | 20260929 | 2,160,277 | 2022-01-08..2025-12-31 16:00 | 186/186 (74,400) | 2026-01-01 00:00..2026-01-31 20:00 | 1767211200 (2025-12-31 20:00) <= 1767211200 (2025-12-31 20:00) → **True** | 0 | 34.0 | +0.0739 |
| 25 | 202602 | 20260930 | 2,234,677 | 2022-01-08..2026-01-31 16:00 | 168/168 (67,200) | 2026-02-01 00:00..2026-02-28 20:00 | 1769889600 (2026-01-31 20:00) <= 1769889600 (2026-01-31 20:00) → **True** | 0 | 35.1 | +0.0496 |
| 26 | 202603 | 20260931 | 2,301,877 | 2022-01-08..2026-02-28 16:00 | 186/186 (74,400) | 2026-03-01 00:00..2026-03-31 20:00 | 1772308800 (2026-02-28 20:00) <= 1772308800 (2026-02-28 20:00) → **True** | 0 | 35.6 | +0.0634 |
| 27 | 202604 | 20260932 | 2,376,277 | 2022-01-08..2026-03-31 16:00 | 180/180 (72,000) | 2026-04-01 00:00..2026-04-30 20:00 | 1774987200 (2026-03-31 20:00) <= 1774987200 (2026-03-31 20:00) → **True** | 0 | 37.2 | +0.0706 |
| 28 | 202605 | 20260933 | 2,448,277 | 2022-01-08..2026-04-30 16:00 | 186/186 (74,400) | 2026-05-01 00:00..2026-05-31 20:00 | 1777579200 (2026-04-30 20:00) <= 1777579200 (2026-04-30 20:00) → **True** | 0 | 37.7 | +0.0597 |
| 29 | 202606 | 20260934 | 2,522,677 | 2022-01-08..2026-05-31 16:00 | 180/180 (72,000) | 2026-06-01 00:00..2026-06-30 20:00 | 1780257600 (2026-05-31 20:00) <= 1780257600 (2026-05-31 20:00) → **True** | 0 | 39.9 | +0.0464 |
| 30 | 202607 | 20260935 | 2,594,677 | 2022-01-08..2026-06-30 16:00 | 186/186 (74,400) | 2026-07-01 00:00..2026-07-31 20:00 | 1782849600 (2026-06-30 20:00) <= 1782849600 (2026-06-30 20:00) → **True** | 0 | 41.8 | +0.0659 |
| 31 | 202608 | 20260936 | 2,669,077 | 2022-01-08..2026-07-31 16:00 | 180/180 (72,000) | 2026-08-01 00:00..2026-08-30 20:00 | 1785528000 (2026-07-31 20:00) <= 1785528000 (2026-07-31 20:00) → **True** | 0 | 41.3 | +0.0496 |

### Folds — K3 weekly (Monday 00:00Z), embargo 1 anchor: `slow_pred_rollw1.npy` sha256 `b726b4d838fe4ab95c5a8e536a50a37fde64f129ebb1080e4760807139e1e434`; script sha256 `1756b1ad4e58b62d059c1834700068a16d89f9ec596e5681284d833bef7ddeda`; train_rule = `E_ts + 48*300 <= first_test_E_ts - 14400 (label window (E,E+4h] realized by the previous anchor; '<=')`; assert = `max(train E_ts)+48*300 <= min(test E_ts)-14400`; finite-mask equal to pinned = **True**; all asserts True = **True**; folds 139; total fit 4677s, wall 4702s

139 weekly folds; every fold printed `ASSERT ... -> True` (all True = **True**); gap between last training label end and (first test anchor − 1 anchor) ∈ [0.0] anchors; train rows 709,220..2,724,277; fit s min/median/max 17.8/29.1/73.8; per-fold rank-IC (raw) mean +0.0663, min +0.0107, max +0.1121

| fold | week (Mon) | seed | train rows | train last | test anchors | test span | ASSERT ok | gap | fit s | rank-IC raw |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2024-01-01 | 20260905 | 709,220 | 2023-12-31 16:00 | 42/42 | 2024-01-01 00:00..2024-01-07 20:00 | True | 0 | 36.3 | +0.0806 |
| 10 | 2024-03-11 | 20260915 | 813,952 | 2024-03-10 16:00 | 42/42 | 2024-03-11 00:00..2024-03-17 20:00 | True | 0 | 19.2 | +0.0772 |
| 20 | 2024-05-20 | 20260925 | 925,400 | 2024-05-19 16:00 | 42/42 | 2024-05-20 00:00..2024-05-26 20:00 | True | 0 | 20.6 | +0.0107 |
| 30 | 2024-07-29 | 20260935 | 1,035,399 | 2024-07-28 16:00 | 42/42 | 2024-07-29 00:00..2024-08-04 20:00 | True | 0 | 21.4 | +0.0480 |
| 40 | 2024-10-07 | 20260945 | 1,150,126 | 2024-10-06 16:00 | 42/42 | 2024-10-07 00:00..2024-10-13 20:00 | True | 0 | 22.6 | +0.0545 |
| 50 | 2024-12-16 | 20260955 | 1,278,730 | 2024-12-15 16:00 | 42/42 | 2024-12-16 00:00..2024-12-22 20:00 | True | 0 | 24.1 | +0.0368 |
| 60 | 2025-02-24 | 20260965 | 1,424,187 | 2025-02-23 16:00 | 42/42 | 2025-02-24 00:00..2025-03-02 20:00 | True | 0 | 25.3 | +0.0587 |
| 70 | 2025-05-05 | 20260975 | 1,581,926 | 2025-05-04 16:00 | 42/42 | 2025-05-05 00:00..2025-05-11 20:00 | True | 0 | 27.1 | +0.0257 |
| 80 | 2025-07-14 | 20260985 | 1,749,877 | 2025-07-13 16:00 | 42/42 | 2025-07-14 00:00..2025-07-20 20:00 | True | 0 | 28.5 | +0.0979 |
| 90 | 2025-09-22 | 20260995 | 1,917,877 | 2025-09-21 16:00 | 42/42 | 2025-09-22 00:00..2025-09-28 20:00 | True | 0 | 34.5 | +0.0597 |
| 100 | 2025-12-01 | 20261005 | 2,085,877 | 2025-11-30 16:00 | 42/42 | 2025-12-01 00:00..2025-12-07 20:00 | True | 0 | 37.9 | +0.0815 |
| 110 | 2026-02-09 | 20261015 | 2,253,877 | 2026-02-08 16:00 | 42/42 | 2026-02-09 00:00..2026-02-15 20:00 | True | 0 | 41.0 | +0.0301 |
| 120 | 2026-04-20 | 20261025 | 2,421,877 | 2026-04-19 16:00 | 42/42 | 2026-04-20 00:00..2026-04-26 20:00 | True | 0 | 44.4 | +0.0716 |
| 130 | 2026-06-29 | 20261035 | 2,589,877 | 2026-06-28 16:00 | 42/42 | 2026-06-29 00:00..2026-07-05 20:00 | True | 0 | 46.7 | +0.0763 |
| 138 | 2026-08-24 | 20261043 | 2,724,277 | 2026-08-23 16:00 | 42/42 | 2026-08-24 00:00..2026-08-30 20:00 | True | 0 | 47.0 | +0.0683 |
(every 10th fold shown; the full per-fold table is `folds_rollw1.json` / `logs/weekly1.log`)

### D1 — Table A: IC and king-leg by model age, full anchor set available at each age

| age (months) | n (raw) | rank-IC raw y4 | n (y4s) | rank-IC y4s | days since cutoff mean (min..max) | n leg | king leg raw (bps/gross/anchor) | S raw | king leg y4s | S y4s | months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5838 | +0.0642 | 5718 | +0.0682 | 25 (10..41) | 5838 | +2.220 | +0.075 | +2.070 | +0.071 | 202401..202608 |
| 2 | 5652 | +0.0621 | 5532 | +0.0662 | 56 (38..72) | 5652 | +2.138 | +0.072 | +2.050 | +0.070 | 202402..202608 |
| 3 | 5478 | +0.0609 | 5358 | +0.0648 | 86 (69..102) | 5478 | +2.260 | +0.077 | +2.153 | +0.074 | 202403..202608 |
| 4 | 5292 | +0.0604 | 5172 | +0.0643 | 117 (99..133) | 5292 | +2.419 | +0.083 | +2.241 | +0.078 | 202404..202608 |
| 5 | 5112 | +0.0598 | 4992 | +0.0634 | 147 (130..163) | 5112 | +2.520 | +0.087 | +2.404 | +0.084 | 202405..202608 |
| 6 | 4926 | +0.0590 | 4806 | +0.0626 | 177 (160..194) | 4926 | +2.256 | +0.080 | +2.128 | +0.076 | 202406..202608 |
| 7 | 4746 | +0.0589 | 4626 | +0.0628 | 208 (191..225) | 4746 | +2.586 | +0.091 | +2.528 | +0.090 | 202407..202608 |
| 8 | 4560 | +0.0584 | 4440 | +0.0623 | 238 (222..255) | 4560 | +2.702 | +0.093 | +2.681 | +0.094 | 202408..202608 |
| 9 | 4374 | +0.0561 | 4254 | +0.0600 | 269 (252..286) | 4374 | +2.377 | +0.082 | +2.327 | +0.082 | 202409..202608 |
| 10 | 4194 | +0.0544 | 4074 | +0.0580 | 299 (283..316) | 4194 | +2.341 | +0.082 | +2.225 | +0.079 | 202410..202608 |
| 11 | 4008 | +0.0523 | 3888 | +0.0558 | 330 (313..347) | 4008 | +2.463 | +0.085 | +2.300 | +0.081 | 202411..202608 |
| 12 | 3828 | +0.0490 | 3708 | +0.0523 | 360 (344..376) | 3828 | +1.616 | +0.055 | +1.417 | +0.049 | 202412..202608 |

### D1 — Table B[raw]: common anchor set (all 12 ages finite), n = 3828 anchors, months 202412..202608; paired Δ = IC(age 1) − IC(age k), s.e. over anchors, UTC-day-block bootstrap CI95 (2000, seed 20260905)

| age | rank-IC | Δ(1−k) | s.e. | CI95 | t | king leg (bps) | S | Δleg(1−k) | s.e. |
|---|---|---|---|---|---|---|---|---|---|
| 1 | +0.0647 | +0.0000 | 0.0000 | [+0.0000, +0.0000] | 0.00 | +2.602 | +0.083 | +0.000 | 0.000 |
| 2 | +0.0632 | +0.0015 | 0.0006 | [+0.0004, +0.0025] | 2.67 | +2.444 | +0.078 | +0.159 | 0.241 |
| 3 | +0.0622 | +0.0024 | 0.0006 | [+0.0013, +0.0037] | 4.07 | +2.585 | +0.084 | +0.018 | 0.241 |
| 4 | +0.0616 | +0.0030 | 0.0007 | [+0.0017, +0.0043] | 4.64 | +2.563 | +0.083 | +0.040 | 0.270 |
| 5 | +0.0610 | +0.0036 | 0.0007 | [+0.0022, +0.0051] | 5.24 | +2.733 | +0.089 | -0.131 | 0.280 |
| 6 | +0.0593 | +0.0054 | 0.0007 | [+0.0039, +0.0069] | 7.29 | +2.259 | +0.076 | +0.344 | 0.292 |
| 7 | +0.0580 | +0.0067 | 0.0008 | [+0.0050, +0.0083] | 8.12 | +2.448 | +0.083 | +0.154 | 0.311 |
| 8 | +0.0572 | +0.0075 | 0.0009 | [+0.0057, +0.0092] | 8.41 | +2.581 | +0.086 | +0.022 | 0.313 |
| 9 | +0.0552 | +0.0095 | 0.0009 | [+0.0077, +0.0113] | 10.02 | +2.303 | +0.078 | +0.299 | 0.326 |
| 10 | +0.0532 | +0.0115 | 0.0010 | [+0.0095, +0.0135] | 11.42 | +2.204 | +0.076 | +0.399 | 0.324 |
| 11 | +0.0517 | +0.0130 | 0.0011 | [+0.0107, +0.0150] | 12.08 | +2.365 | +0.082 | +0.238 | 0.333 |
| 12 | +0.0490 | +0.0156 | 0.0012 | [+0.0133, +0.0180] | 13.35 | +1.616 | +0.055 | +0.987 | 0.345 |

### D1 — Table B[y4s]: common anchor set (all 12 ages finite), n = 3708 anchors, months 202412..202608; paired Δ = IC(age 1) − IC(age k), s.e. over anchors, UTC-day-block bootstrap CI95 (2000, seed 20260905)

| age | rank-IC | Δ(1−k) | s.e. | CI95 | t | king leg (bps) | S | Δleg(1−k) | s.e. |
|---|---|---|---|---|---|---|---|---|---|
| 1 | +0.0695 | +0.0000 | 0.0000 | [+0.0000, +0.0000] | 0.00 | +2.455 | +0.079 | +0.000 | 0.000 |
| 2 | +0.0679 | +0.0016 | 0.0006 | [+0.0005, +0.0027] | 2.80 | +2.382 | +0.076 | +0.073 | 0.256 |
| 3 | +0.0667 | +0.0028 | 0.0006 | [+0.0016, +0.0040] | 4.53 | +2.503 | +0.081 | -0.048 | 0.251 |
| 4 | +0.0661 | +0.0033 | 0.0007 | [+0.0020, +0.0045] | 4.98 | +2.416 | +0.078 | +0.039 | 0.271 |
| 5 | +0.0652 | +0.0043 | 0.0007 | [+0.0028, +0.0057] | 5.98 | +2.654 | +0.086 | -0.199 | 0.289 |
| 6 | +0.0633 | +0.0061 | 0.0008 | [+0.0047, +0.0077] | 8.15 | +2.147 | +0.072 | +0.308 | 0.295 |
| 7 | +0.0621 | +0.0074 | 0.0008 | [+0.0057, +0.0091] | 8.74 | +2.433 | +0.082 | +0.023 | 0.314 |
| 8 | +0.0612 | +0.0083 | 0.0009 | [+0.0066, +0.0101] | 9.15 | +2.605 | +0.087 | -0.150 | 0.328 |
| 9 | +0.0590 | +0.0104 | 0.0010 | [+0.0085, +0.0122] | 10.78 | +2.302 | +0.078 | +0.153 | 0.330 |
| 10 | +0.0567 | +0.0127 | 0.0010 | [+0.0107, +0.0148] | 12.44 | +2.110 | +0.073 | +0.345 | 0.335 |
| 11 | +0.0551 | +0.0143 | 0.0011 | [+0.0121, +0.0166] | 13.06 | +2.236 | +0.078 | +0.220 | 0.346 |
| 12 | +0.0523 | +0.0171 | 0.0012 | [+0.0148, +0.0195] | 14.38 | +1.463 | +0.050 | +0.992 | 0.355 |

### D1 — Table C: paired Δ = IC(age 1) − IC(age k) on each age's own anchor set

| age | n raw | IC age1 | IC age k | Δ raw | s.e. | CI95 | n y4s | IC age1 | IC age k | Δ y4s | s.e. | CI95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 5652 | +0.0636 | +0.0621 | +0.0015 | 0.0005 | [+0.0006, +0.0025] | 5532 | +0.0677 | +0.0662 | +0.0015 | 0.0005 | [+0.0005, +0.0024] |
| 3 | 5478 | +0.0636 | +0.0609 | +0.0027 | 0.0005 | [+0.0016, +0.0038] | 5358 | +0.0678 | +0.0648 | +0.0030 | 0.0006 | [+0.0019, +0.0040] |
| 4 | 5292 | +0.0634 | +0.0604 | +0.0030 | 0.0006 | [+0.0018, +0.0042] | 5172 | +0.0675 | +0.0643 | +0.0032 | 0.0006 | [+0.0020, +0.0044] |
| 5 | 5112 | +0.0635 | +0.0598 | +0.0037 | 0.0007 | [+0.0024, +0.0051] | 4992 | +0.0677 | +0.0634 | +0.0042 | 0.0007 | [+0.0028, +0.0056] |
| 6 | 4926 | +0.0645 | +0.0590 | +0.0055 | 0.0007 | [+0.0041, +0.0069] | 4806 | +0.0687 | +0.0626 | +0.0061 | 0.0007 | [+0.0047, +0.0076] |
| 7 | 4746 | +0.0650 | +0.0589 | +0.0061 | 0.0008 | [+0.0046, +0.0076] | 4626 | +0.0695 | +0.0628 | +0.0067 | 0.0008 | [+0.0053, +0.0082] |
| 8 | 4560 | +0.0658 | +0.0584 | +0.0074 | 0.0009 | [+0.0057, +0.0091] | 4440 | +0.0704 | +0.0623 | +0.0081 | 0.0009 | [+0.0064, +0.0099] |
| 9 | 4374 | +0.0658 | +0.0561 | +0.0097 | 0.0009 | [+0.0081, +0.0117] | 4254 | +0.0706 | +0.0600 | +0.0106 | 0.0009 | [+0.0088, +0.0125] |
| 10 | 4194 | +0.0662 | +0.0544 | +0.0118 | 0.0010 | [+0.0099, +0.0138] | 4074 | +0.0710 | +0.0580 | +0.0130 | 0.0010 | [+0.0111, +0.0149] |
| 11 | 4008 | +0.0656 | +0.0523 | +0.0133 | 0.0011 | [+0.0114, +0.0156] | 3888 | +0.0704 | +0.0558 | +0.0147 | 0.0011 | [+0.0125, +0.0167] |
| 12 | 3828 | +0.0647 | +0.0490 | +0.0156 | 0.0012 | [+0.0134, +0.0179] | 3708 | +0.0695 | +0.0523 | +0.0171 | 0.0012 | [+0.0147, +0.0196] |

### D1 — Table D: all (model, anchor) pairs binned by days since the model's cutoff

| days since cutoff | pairs | rank-IC raw | rank-IC y4s | king leg raw | S raw |
|---|---|---|---|---|---|
| 0-30 | 3808 | +0.0637 | +0.0675 | +2.164 | +0.071 |
| 30-60 | 5641 | +0.0626 | +0.0666 | +2.167 | +0.073 |
| 60-90 | 5467 | +0.0617 | +0.0657 | +2.279 | +0.077 |
| 90-120 | 5287 | +0.0601 | +0.0640 | +2.275 | +0.078 |
| 120-150 | 5113 | +0.0606 | +0.0642 | +2.528 | +0.088 |
| 150-180 | 4933 | +0.0593 | +0.0631 | +2.294 | +0.081 |
| 180-210 | 4759 | +0.0587 | +0.0625 | +2.460 | +0.086 |
| 210-240 | 4567 | +0.0595 | +0.0633 | +2.721 | +0.095 |
| 240-270 | 4393 | +0.0571 | +0.0611 | +2.558 | +0.089 |
| 270-300 | 4219 | +0.0548 | +0.0583 | +2.196 | +0.076 |
| 300-330 | 4039 | +0.0529 | +0.0565 | +2.443 | +0.086 |
| 330-360 | 3865 | +0.0513 | +0.0548 | +2.109 | +0.071 |

### D1 — Table E: common set split by calendar year (raw y4)

| year | n | age 1 | age 2 | age 3 | age 6 | age 9 | age 12 | Δ(1−12) | s.e. |
|---|---|---|---|---|---|---|---|---|---|
| 2024 | 186 | +0.0670 | +0.0685 | +0.0715 | +0.0643 | +0.0641 | +0.0475 | +0.0196 | 0.0059 |
| 2025 | 2190 | +0.0683 | +0.0662 | +0.0651 | +0.0611 | +0.0563 | +0.0511 | +0.0173 | 0.0018 |
| 2026 | 1452 | +0.0588 | +0.0580 | +0.0568 | +0.0559 | +0.0523 | +0.0462 | +0.0126 | 0.0013 |

### D1 — Table F (auxiliary): K0 pinned by month-of-year (= age within its year fold), 2024-01..2026-08

| month | n | pinned IC raw | pinned IC y4s | pinned king leg raw | S | K1 age-1 IC raw on the same anchors |
|---|---|---|---|---|---|---|
| 1 | 558 | +0.0787 | +0.0821 | +4.252 | +0.162 | +0.0778 |
| 2 | 510 | +0.0574 | +0.0596 | +1.404 | +0.040 | +0.0584 |
| 3 | 558 | +0.0633 | +0.0663 | +1.978 | +0.070 | +0.0691 |
| 4 | 540 | +0.0532 | +0.0570 | +0.932 | +0.029 | +0.0580 |
| 5 | 558 | +0.0512 | +0.0555 | +2.002 | +0.071 | +0.0527 |
| 6 | 540 | +0.0492 | +0.0513 | +1.565 | +0.065 | +0.0555 |
| 7 | 558 | +0.0630 | +0.0673 | +3.262 | +0.122 | +0.0635 |
| 8 | 552 | +0.0566 | +0.0609 | +2.422 | +0.101 | +0.0639 |
| 9 | 360 | +0.0555 | +0.0598 | -1.507 | -0.062 | +0.0562 |
| 10 | 372 | +0.0592 | +0.0637 | +2.453 | +0.074 | +0.0728 |
| 11 | 360 | +0.0651 | +0.0693 | +4.948 | +0.155 | +0.0818 |
| 12 | 372 | +0.0507 | +0.0526 | +3.119 | +0.112 | +0.0663 |

pinned H1 (months 1–6) vs H2 (7–12) IC raw: +0.0589 (n 3264) vs +0.0585 (n 2574); diff +0.0004 ± 0.0030 (unpaired)

**D1 decision (frozen statistic):** paired IC(age 1) − IC(age 12), common set: raw **+0.0156 ± 0.0012** CI95 [+0.0133, +0.0180]; y4s **+0.0171 ± 0.0012** CI95 [+0.0148, +0.0195]; threshold 0.003 ⇒ decay detectable = **True** ⇒ K3 **RUN**

### Weekly-resolution age curve (addendum; diagnostic only) — from the 139 saved K3 weekly boosters; receipt: age-1 stitch from the saved boosters vs `slow_pred_rollw1.npy` array_equal = **True** (max|Δ| 0.000e+00); rows predicted 15,968,652. Fit time (n_jobs 48): per fit min/median/max 17.8/29.1/73.8 s, total fit 4677 s, wall 4702 s

#### Table W-A: full anchor set at each weekly age

| age (weeks) | n raw | rank-IC raw | n y4s | rank-IC y4s | days since cutoff mean (min..max) | n leg | king leg raw | S raw | king leg y4s | S y4s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5838 | +0.0663 | 5718 | +0.0705 | 3.6 (0.2..7.0) | 5838 | +2.500 | +0.085 | +2.450 | +0.084 |
| 2 | 5796 | +0.0653 | 5676 | +0.0694 | 10.6 (7.2..14.0) | 5796 | +2.537 | +0.084 | +2.375 | +0.079 |
| 3 | 5754 | +0.0656 | 5634 | +0.0696 | 17.6 (14.2..21.0) | 5754 | +2.472 | +0.084 | +2.348 | +0.080 |
| 4 | 5712 | +0.0632 | 5592 | +0.0672 | 24.6 (21.2..28.0) | 5712 | +2.100 | +0.071 | +2.017 | +0.069 |
| 5 | 5670 | +0.0633 | 5550 | +0.0674 | 31.6 (28.2..35.0) | 5670 | +2.430 | +0.081 | +2.353 | +0.079 |
| 6 | 5628 | +0.0629 | 5508 | +0.0669 | 38.6 (35.2..42.0) | 5628 | +2.299 | +0.077 | +2.232 | +0.076 |
| 7 | 5586 | +0.0629 | 5466 | +0.0670 | 45.6 (42.2..49.0) | 5586 | +2.258 | +0.076 | +2.130 | +0.072 |
| 8 | 5544 | +0.0630 | 5424 | +0.0672 | 52.6 (49.2..56.0) | 5544 | +2.228 | +0.076 | +2.133 | +0.073 |

#### Table W-B[raw]: common anchor set (all 8 weekly ages finite), n = 5544; paired Δ = IC(age 1 w) − IC(age w); weeks 1–4 vs 5–8: +0.0649 vs +0.0632, paired Δ +0.0017 ± 0.0003

| age (weeks) | rank-IC | Δ(1−w) | s.e. | CI95 | king leg | S | Δleg(1−w) | s.e. |
|---|---|---|---|---|---|---|---|---|
| 1 | +0.0658 | +0.0000 | 0.0000 | [+0.0000, +0.0000] | +2.549 | +0.086 | +0.000 | 0.000 |
| 2 | +0.0649 | +0.0009 | 0.0005 | [-0.0001, +0.0018] | +2.612 | +0.086 | -0.063 | 0.171 |
| 3 | +0.0654 | +0.0004 | 0.0005 | [-0.0006, +0.0014] | +2.550 | +0.085 | -0.001 | 0.174 |
| 4 | +0.0634 | +0.0024 | 0.0005 | [+0.0013, +0.0035] | +2.201 | +0.074 | +0.348 | 0.183 |
| 5 | +0.0636 | +0.0022 | 0.0005 | [+0.0011, +0.0033] | +2.540 | +0.084 | +0.009 | 0.185 |
| 6 | +0.0630 | +0.0028 | 0.0005 | [+0.0016, +0.0038] | +2.395 | +0.080 | +0.154 | 0.185 |
| 7 | +0.0630 | +0.0028 | 0.0006 | [+0.0017, +0.0040] | +2.312 | +0.078 | +0.237 | 0.191 |
| 8 | +0.0630 | +0.0028 | 0.0006 | [+0.0016, +0.0040] | +2.228 | +0.076 | +0.321 | 0.198 |

#### Table W-B[y4s]: common anchor set (all 8 weekly ages finite), n = 5424; paired Δ = IC(age 1 w) − IC(age w); weeks 1–4 vs 5–8: +0.0691 vs +0.0673, paired Δ +0.0018 ± 0.0003

| age (weeks) | rank-IC | Δ(1−w) | s.e. | CI95 | king leg | S | Δleg(1−w) | s.e. |
|---|---|---|---|---|---|---|---|---|
| 1 | +0.0701 | +0.0000 | 0.0000 | [+0.0000, +0.0000] | +2.549 | +0.085 | +0.000 | 0.000 |
| 2 | +0.0692 | +0.0009 | 0.0005 | [-0.0000, +0.0018] | +2.500 | +0.082 | +0.050 | 0.183 |
| 3 | +0.0696 | +0.0005 | 0.0005 | [-0.0005, +0.0015] | +2.479 | +0.083 | +0.070 | 0.179 |
| 4 | +0.0675 | +0.0026 | 0.0005 | [+0.0015, +0.0037] | +2.165 | +0.073 | +0.385 | 0.184 |
| 5 | +0.0678 | +0.0023 | 0.0005 | [+0.0011, +0.0034] | +2.515 | +0.083 | +0.034 | 0.198 |
| 6 | +0.0671 | +0.0030 | 0.0006 | [+0.0019, +0.0041] | +2.381 | +0.079 | +0.169 | 0.191 |
| 7 | +0.0670 | +0.0031 | 0.0006 | [+0.0019, +0.0043] | +2.232 | +0.075 | +0.317 | 0.194 |
| 8 | +0.0672 | +0.0029 | 0.0006 | [+0.0016, +0.0041] | +2.180 | +0.074 | +0.370 | 0.205 |

#### Table W-D: all (model, anchor) pairs by days since cutoff, 7-day bins

| days | pairs | rank-IC raw | rank-IC y4s | king leg raw | S raw |
|---|---|---|---|---|---|
| 0-7 | 5699 | +0.0662 | +0.0705 | +2.435 | +0.083 |
| 7-14 | 5797 | +0.0654 | +0.0694 | +2.584 | +0.086 |
| 14-21 | 5755 | +0.0656 | +0.0696 | +2.472 | +0.084 |
| 21-28 | 5713 | +0.0633 | +0.0672 | +2.075 | +0.070 |
| 28-35 | 5671 | +0.0634 | +0.0675 | +2.457 | +0.082 |
| 35-42 | 5629 | +0.0629 | +0.0669 | +2.303 | +0.077 |
| 42-49 | 5587 | +0.0629 | +0.0670 | +2.247 | +0.076 |
| 49-56 | 5545 | +0.0631 | +0.0673 | +2.288 | +0.078 |

### Noise floor — K1 replicate (D1 retrain, same recipe and seeds, LightGBM bits differ) vs K1: n 5838 anchors; per-anchor Spearman between the two prediction vectors mean 1.0000 (5th pct 1.0000, min 1.0000); ΔIC raw +0.00000 ± 0.00000 (per-anchor sd 0.0000); ΔIC y4s +0.00000 ± 0.00000; Δking-leg raw +0.0000 ± 0.0000 bps/gross/anchor (sd 0.000); Δking-leg y4s +0.0000 ± 0.0000; IC raw K1 replicate +0.0642 vs K1 +0.0642

### Yearly mean rank-IC vs raw y4 = Σ 5m simple returns over [E, E+47] (meta; production label source); identical anchor set for all sources (2024+, finite IC for every source)

| window | n | K0 pinned | K1 rollm60 | K2 rollm1 | K3 rollw1 | Δ K1 rollm60−K0 (mean ± SE) | Δ K2 rollm1−K0 (mean ± SE) | Δ K3 rollw1−K0 (mean ± SE) |
|---|---|---|---|---|---|---|---|---|
| 2024 | 2196 | +0.0548 | +0.0635 | +0.0655 | +0.0659 | +0.0087 ± 0.0015 | +0.0107 ± 0.0016 | +0.0111 ± 0.0017 |
| 2025 | 2190 | +0.0630 | +0.0683 | +0.0679 | +0.0699 | +0.0053 ± 0.0010 | +0.0049 ± 0.0010 | +0.0069 ± 0.0011 |
| 2026<=08-10 | 1332 | +0.0588 | +0.0594 | +0.0603 | +0.0625 | +0.0006 ± 0.0009 | +0.0015 ± 0.0009 | +0.0037 ± 0.0010 |
| 2026->08-30 | 1452 | +0.0584 | +0.0588 | +0.0601 | +0.0616 | +0.0005 ± 0.0009 | +0.0017 ± 0.0009 | +0.0033 ± 0.0009 |
| 2024->26 | 5838 | +0.0588 | +0.0642 | +0.0650 | +0.0664 | +0.0054 ± 0.0007 | +0.0063 ± 0.0008 | +0.0076 ± 0.0008 |
| 2025->26 | 3642 | +0.0612 | +0.0645 | +0.0648 | +0.0666 | +0.0034 ± 0.0007 | +0.0036 ± 0.0007 | +0.0054 ± 0.0008 |

### Yearly mean rank-IC vs dlw y4s = Π(1+r5)−1 over [E+1, E+48] (compounded holding-window target); identical anchor set for all sources (2024+, finite IC for every source)

| window | n | K0 pinned | K1 rollm60 | K2 rollm1 | K3 rollw1 | Δ K1 rollm60−K0 (mean ± SE) | Δ K2 rollm1−K0 (mean ± SE) | Δ K3 rollw1−K0 (mean ± SE) |
|---|---|---|---|---|---|---|---|---|
| 2024 | 2196 | +0.0565 | +0.0661 | +0.0680 | +0.0687 | +0.0096 ± 0.0015 | +0.0115 ± 0.0016 | +0.0122 ± 0.0017 |
| 2025 | 2190 | +0.0671 | +0.0728 | +0.0724 | +0.0745 | +0.0057 ± 0.0010 | +0.0053 ± 0.0010 | +0.0074 ± 0.0011 |
| 2026<=08-10 | 1332 | +0.0640 | +0.0640 | +0.0648 | +0.0669 | +0.0001 ± 0.0009 | +0.0008 ± 0.0009 | +0.0029 ± 0.0010 |
| 2026->08-30 | 1332 | +0.0640 | +0.0640 | +0.0648 | +0.0669 | +0.0001 ± 0.0009 | +0.0008 ± 0.0009 | +0.0029 ± 0.0010 |
| 2024->26 | 5718 | +0.0623 | +0.0682 | +0.0689 | +0.0705 | +0.0059 ± 0.0007 | +0.0066 ± 0.0008 | +0.0082 ± 0.0008 |
| 2025->26 | 3522 | +0.0659 | +0.0695 | +0.0695 | +0.0717 | +0.0036 ± 0.0007 | +0.0036 ± 0.0007 | +0.0057 ± 0.0008 |

### King leg (production leg definition, bps per unit gross per anchor) — caliber raw y4; S = mean/std per anchor

| leg | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | S/anchor 900 pre-0810 (seat window) | S/anchor last 900 |
|---|---|---|---|---|---|---|---|---|
| king[pinned] | +1.533 (S +0.064, n 2196) | +2.381 (S +0.073, n 2190) | +3.197 (S +0.111, n 1332) | +3.130 (S +0.108, n 1452) | +2.248 (S +0.079, n 5838) | +2.680 (S +0.086, n 3642) | +0.1014 (mean +2.983) | +0.0953 (mean +2.828) |
| king[rollm] | +1.512 (S +0.059, n 2196) | +2.661 (S +0.079, n 2190) | +2.675 (S +0.094, n 1332) | +2.624 (S +0.093, n 1452) | +2.220 (S +0.075, n 5838) | +2.647 (S +0.084, n 3642) | +0.0796 (mean +2.287) | +0.0653 (mean +1.865) |
| king[rollm1] | +1.843 (S +0.072, n 2196) | +2.548 (S +0.075, n 2190) | +3.264 (S +0.117, n 1332) | +3.341 (S +0.120, n 1452) | +2.480 (S +0.084, n 5838) | +2.864 (S +0.091, n 3642) | +0.1083 (mean +3.116) | +0.1018 (mean +2.958) |
| king[rollw1] | +1.673 (S +0.065, n 2196) | +2.775 (S +0.083, n 2190) | +3.464 (S +0.122, n 1332) | +3.337 (S +0.118, n 1452) | +2.500 (S +0.085, n 5838) | +2.999 (S +0.095, n 3642) | +0.1077 (mean +3.150) | +0.0905 (mean +2.651) |
| rev24 | +0.296 (S +0.010, n 2196) | +0.336 (S +0.009, n 2190) | +1.954 (S +0.058, n 1332) | +1.711 (S +0.051, n 1452) | +0.663 (S +0.020, n 5838) | +0.884 (S +0.026, n 3642) | +0.0386 (mean +1.298) | +0.0404 (mean +1.350) |
| fund | -0.361 (S -0.017, n 2196) | +1.712 (S +0.067, n 2190) | +6.344 (S +0.226, n 1332) | +5.520 (S +0.194, n 1452) | +1.879 (S +0.075, n 5838) | +3.230 (S +0.120, n 3642) | +0.2508 (mean +7.391) | +0.2017 (mean +6.105) |

### King leg (production leg definition, bps per unit gross per anchor) — caliber compounded y4s (anchors with a dlw row, ≤ 2026-08-10 20:00Z); S = mean/std per anchor

| leg | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | S/anchor 900 pre-0810 (seat window) | S/anchor last 900 |
|---|---|---|---|---|---|---|---|---|
| king[pinned] | +1.618 (S +0.067, n 2196) | +2.280 (S +0.071, n 2190) | +3.071 (S +0.105, n 1332) | +3.071 (S +0.105, n 1332) | +2.210 (S +0.077, n 5718) | +2.579 (S +0.083, n 3522) | +0.0994 (mean +2.965) | +0.0977 (mean +2.912) |
| king[rollm] | +1.517 (S +0.058, n 2196) | +2.531 (S +0.076, n 2190) | +2.413 (S +0.085, n 1332) | +2.413 (S +0.085, n 1332) | +2.114 (S +0.072, n 5718) | +2.486 (S +0.079, n 3522) | +0.0755 (mean +2.175) | +0.0739 (mean +2.125) |
| king[rollm1] | +1.819 (S +0.071, n 2196) | +2.466 (S +0.073, n 2190) | +3.245 (S +0.116, n 1332) | +3.245 (S +0.116, n 1332) | +2.399 (S +0.081, n 5718) | +2.760 (S +0.087, n 3522) | +0.1056 (mean +3.073) | +0.1040 (mean +3.023) |
| king[rollw1] | +1.686 (S +0.065, n 2196) | +2.752 (S +0.083, n 2190) | +3.435 (S +0.119, n 1332) | +3.435 (S +0.119, n 1332) | +2.501 (S +0.085, n 5718) | +3.010 (S +0.095, n 3522) | +0.1040 (mean +3.094) | +0.1032 (mean +3.068) |
| rev24 | +0.384 (S +0.013, n 2196) | +0.378 (S +0.011, n 2190) | +2.121 (S +0.062, n 1332) | +2.121 (S +0.062, n 1332) | +0.786 (S +0.024, n 5718) | +1.037 (S +0.030, n 3522) | +0.0414 (mean +1.410) | +0.0420 (mean +1.431) |
| fund | -0.448 (S -0.020, n 2196) | +1.600 (S +0.061, n 2190) | +6.027 (S +0.210, n 1332) | +6.027 (S +0.210, n 1332) | +1.845 (S +0.072, n 5718) | +3.274 (S +0.120, n 3522) | +0.2291 (mean +6.935) | +0.2295 (mean +6.949) |

### msharpe seat at 2026-08-10 20:00Z (production rule, LOOK=900; w101 = LEGS=101 mask = deployed combo seat)

| caliber | king | shp king/rev24/fund | w3 king/rev24/fund | w101 king/fund |
|---|---|---|---|---|
| raw | K0 pinned | +0.1014/+0.0386/+0.2510 | 0.259/0.099/0.642 | 0.288/0.712 |
| raw | K1 rollm60 | +0.0797/+0.0386/+0.2510 | 0.216/0.105/0.680 | 0.241/0.759 |
| raw | K2 rollm1 | +0.1083/+0.0386/+0.2510 | 0.272/0.097/0.631 | 0.301/0.699 |
| raw | K3 rollw1 | +0.1078/+0.0386/+0.2510 | 0.271/0.097/0.632 | 0.300/0.700 |
| y4s | K0 pinned | +0.0994/+0.0414/+0.2292 | 0.269/0.112/0.619 | 0.302/0.698 |
| y4s | K1 rollm60 | +0.0756/+0.0414/+0.2292 | 0.218/0.120/0.662 | 0.248/0.752 |
| y4s | K2 rollm1 | +0.1056/+0.0414/+0.2292 | 0.281/0.110/0.609 | 0.316/0.684 |
| y4s | K3 rollw1 | +0.1041/+0.0414/+0.2292 | 0.278/0.111/0.612 | 0.312/0.688 |

### Book levels — arm d30_n2_c42, L-fix (M829/T400/FTRIM zero, W3FIX 0.21/0/0.79, LEGS=101, LOOK=900, φ=0.45, FSEED=42), column net_ex (bps/anchor per unit NAV); n = 10038 paired anchors; windows {'2024': 2196, '2025': 2190, '2026<=08-10': 1332, '2026->08-30': 1452, '2024->26': 5838, '2025->26': 3642, '2024->26<=cut': 5718, '2025->26<=cut': 3522}

**caliber log = raw Σ-simple y4, CAL=log = no transform** — cells: mean bps/anchor (Sharpe; maxDD bps); %/gross/yr = mean × 2190 / 100

| king | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | %/gross/yr 2024 / 2025 / 2026(8m ann.) | worst month (bps) | gross 25on | turnover 25on | carry 25on | cost 25on |
|---|---|---|---|---|---|---|---|---|---|---|---|
| K0 pinned | -0.642 (S -1.68; DD 1815) | +0.284 (S +0.67; DD 902) | +2.911 (S +5.16; DD 458) | +2.378 (S +4.21; DD 774) | +0.457 (S +1.02; DD 2614) | +1.119 (S +2.31; DD 902) | -14.1 / +6.2 / +52.1 | 202411 -717 | 0.757 | 0.01439 | +0.773 | 0.053 |
| K1 rollm60 | -0.625 (S -1.68; DD 1804) | +0.284 (S +0.67; DD 881) | +2.883 (S +5.07; DD 478) | +2.357 (S +4.13; DD 787) | +0.457 (S +1.02; DD 2578) | +1.110 (S +2.28; DD 881) | -13.7 / +6.2 / +51.6 | 202411 -705 | 0.756 | 0.01438 | +0.773 | 0.053 |
| K2 rollm1 | -0.647 (S -1.73; DD 1807) | +0.303 (S +0.72; DD 856) | +2.967 (S +5.23; DD 464) | +2.428 (S +4.26; DD 803) | +0.474 (S +1.06; DD 2563) | +1.150 (S +2.37; DD 856) | -14.2 / +6.6 / +53.2 | 202411 -700 | 0.756 | 0.01437 | +0.774 | 0.053 |
| K3 rollw1 | -0.639 (S -1.72; DD 1789) | +0.275 (S +0.66; DD 851) | +2.929 (S +5.15; DD 472) | +2.356 (S +4.12; DD 856) | +0.449 (S +1.00; DD 2538) | +1.105 (S +2.27; DD 856) | -14.0 / +6.0 / +51.6 | 202411 -684 | 0.757 | 0.01437 | +0.774 | 0.053 |
| K1 replicate | -0.625 (S -1.68; DD 1804) | +0.284 (S +0.67; DD 881) | +2.883 (S +5.07; DD 478) | +2.357 (S +4.13; DD 787) | +0.457 (S +1.02; DD 2578) | +1.110 (S +2.28; DD 881) | -13.7 / +6.2 / +51.6 | 202411 -705 | 0.756 | 0.01438 | +0.773 | 0.053 |

**caliber prod = compounded Π(1+r5)−1 target (meta_newprod swap), CAL=log** — cells: mean bps/anchor (Sharpe; maxDD bps); %/gross/yr = mean × 2190 / 100

| king | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | %/gross/yr 2024 / 2025 / 2026(8m ann.) | worst month (bps) | gross 25on | turnover 25on | carry 25on | cost 25on |
|---|---|---|---|---|---|---|---|---|---|---|---|
| K0 pinned | -0.709 (S -1.85; DD 1913) | +0.254 (S +0.59; DD 849) | +2.833 (S +5.05; DD 352) | +2.324 (S +4.13; DD 754) | +0.406 (S +0.90; DD 2657) | +1.079 (S +2.21; DD 849) | -15.5 / +5.6 / +50.9 | 202411 -757 | 0.755 | 0.01441 | +0.762 | 0.053 |
| K1 rollm60 | -0.697 (S -1.86; DD 1886) | +0.266 (S +0.62; DD 801) | +2.852 (S +5.03; DD 352) | +2.342 (S +4.12; DD 768) | +0.420 (S +0.93; DD 2588) | +1.094 (S +2.23; DD 801) | -15.2 / +5.8 / +51.3 | 202411 -748 | 0.754 | 0.01441 | +0.763 | 0.053 |
| K2 rollm1 | -0.696 (S -1.85; DD 1886) | +0.284 (S +0.66; DD 804) | +2.928 (S +5.18; DD 348) | +2.402 (S +4.24; DD 780) | +0.442 (S +0.98; DD 2593) | +1.129 (S +2.31; DD 804) | -15.2 / +6.2 / +52.6 | 202411 -735 | 0.754 | 0.01439 | +0.762 | 0.053 |
| K3 rollw1 | -0.700 (S -1.88; DD 1886) | +0.232 (S +0.54; DD 810) | +2.927 (S +5.15; DD 354) | +2.390 (S +4.20; DD 799) | +0.418 (S +0.93; DD 2598) | +1.092 (S +2.23; DD 810) | -15.3 / +5.1 / +52.3 | 202411 -732 | 0.754 | 0.01441 | +0.761 | 0.053 |
| K1 replicate | -0.697 (S -1.86; DD 1886) | +0.266 (S +0.62; DD 801) | +2.852 (S +5.03; DD 352) | +2.342 (S +4.12; DD 768) | +0.420 (S +0.93; DD 2588) | +1.094 (S +2.23; DD 801) | -15.2 / +5.8 / +51.3 | 202411 -748 | 0.754 | 0.01441 | +0.763 | 0.053 |

### Book deltas — paired by anchor, UTC-day-block bootstrap (2000, seed 20260905); cells: Δ bps/anchor [CI95] P(Δ>0)

**caliber log**

| pair | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | ΔSharpe 24on / 25on | Δturnover % 25on / 24on | maxDD ref / x (25on) |
|---|---|---|---|---|---|---|---|---|---|
| rollm-pinned | +0.017 [-0.037, +0.069] 0.723 | -0.001 [-0.074, +0.069] 0.487 | -0.028 [-0.151, +0.090] 0.332 | -0.021 [-0.146, +0.096] 0.353 | +0.001 [-0.042, +0.043] 0.535 | -0.009 [-0.076, +0.058] 0.394 | +0.01 / -0.03 | -0.0 / -0.3 | 902 / 881 |
| rollm1-pinned | -0.005 [-0.060, +0.046] 0.425 | +0.018 [-0.061, +0.092] 0.679 | +0.057 [-0.041, +0.158] 0.858 | +0.050 [-0.042, +0.148] 0.849 | +0.018 [-0.025, +0.060] 0.796 | +0.031 [-0.027, +0.093] 0.842 | +0.04 / +0.06 | -0.1 / -0.3 | 902 / 856 |
| rollw1-pinned | +0.003 [-0.057, +0.065] 0.540 | -0.009 [-0.083, +0.068] 0.423 | +0.018 [-0.071, +0.115] 0.639 | -0.022 [-0.143, +0.084] 0.354 | -0.008 [-0.051, +0.038] 0.387 | -0.014 [-0.077, +0.049] 0.330 | -0.01 / -0.04 | -0.1 / -0.4 | 902 / 856 |
| k1rep-rollm (K1 replicate: LGBM-bits noise floor, auxiliary) | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.00 / +0.00 | +0.0 / +0.0 | 881 / 881 |
| rollm1-rollm (embargo cost K2-K1) | -0.022 [-0.049, +0.004] 0.052 | +0.019 [-0.051, +0.086] 0.698 | +0.085 [-0.013, +0.185] 0.958 | +0.072 [-0.019, +0.169] 0.934 | +0.017 [-0.019, +0.054] 0.821 | +0.040 [-0.015, +0.095] 0.914 | +0.04 / +0.09 | -0.1 / -0.1 | 881 / 856 |
| rollw1-rollm1 (cadence at equal embargo K3-K2, auxiliary) | +0.008 [-0.024, +0.038] 0.688 | -0.028 [-0.075, +0.024] 0.136 | -0.038 [-0.103, +0.023] 0.115 | -0.073 [-0.181, +0.017] 0.067 | -0.025 [-0.059, +0.008] 0.065 | -0.045 [-0.098, +0.003] 0.032 | -0.06 / -0.10 | -0.0 / -0.0 | 856 / 856 |

**caliber prod**

| pair | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | ΔSharpe 24on / 25on | Δturnover % 25on / 24on | maxDD ref / x (25on) |
|---|---|---|---|---|---|---|---|---|---|
| rollm-pinned | +0.012 [-0.037, +0.063] 0.706 | +0.012 [-0.073, +0.104] 0.601 | +0.019 [-0.119, +0.147] 0.585 | +0.018 [-0.104, +0.144] 0.611 | +0.014 [-0.037, +0.065] 0.731 | +0.015 [-0.054, +0.089] 0.664 | +0.03 / +0.02 | -0.0 / -0.3 | 849 / 801 |
| rollm1-pinned | +0.013 [-0.041, +0.070] 0.671 | +0.030 [-0.065, +0.120] 0.758 | +0.095 [-0.040, +0.259] 0.900 | +0.079 [-0.047, +0.227] 0.868 | +0.036 [-0.016, +0.090] 0.910 | +0.050 [-0.026, +0.128] 0.892 | +0.08 / +0.10 | -0.1 / -0.4 | 849 / 804 |
| rollw1-pinned | +0.009 [-0.050, +0.065] 0.610 | -0.022 [-0.112, +0.068] 0.303 | +0.094 [-0.048, +0.271] 0.898 | +0.066 [-0.067, +0.245] 0.809 | +0.011 [-0.042, +0.071] 0.648 | +0.013 [-0.064, +0.091] 0.602 | +0.03 / +0.02 | -0.1 / -0.3 | 849 / 810 |
| k1rep-rollm (K1 replicate: LGBM-bits noise floor, auxiliary) | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.000 [+0.000, +0.000] 0.000 | +0.00 / +0.00 | +0.0 / +0.0 | 801 / 801 |
| rollm1-rollm (embargo cost K2-K1) | +0.001 [-0.032, +0.034] 0.517 | +0.018 [-0.056, +0.092] 0.685 | +0.076 [-0.069, +0.246] 0.838 | +0.060 [-0.068, +0.220] 0.793 | +0.022 [-0.025, +0.070] 0.821 | +0.035 [-0.035, +0.107] 0.830 | +0.05 / +0.08 | -0.1 / -0.1 | 801 / 804 |
| rollw1-rollm1 (cadence at equal embargo K3-K2, auxiliary) | -0.004 [-0.046, +0.034] 0.406 | -0.052 [-0.103, +0.002] 0.030 | -0.001 [-0.073, +0.067] 0.487 | -0.012 [-0.082, +0.055] 0.358 | -0.024 [-0.057, +0.006] 0.058 | -0.036 [-0.081, +0.007] 0.046 | -0.05 / -0.08 | +0.1 / +0.0 | 804 / 810 |

### σ_fund terciles of Δ (2024→26, auxiliary): cuts [5.449, 13.671] bps/8h, n per tercile [1946, 1946, 1946]

| caliber | pair | low | mid | high |
|---|---|---|---|---|
| log | rollm-pinned | +0.029 [-0.029, +0.081] (ref -0.786 → -0.756) | +0.015 [-0.050, +0.077] (ref +0.130 → +0.145) | -0.042 [-0.152, +0.056] (ref +2.025 → +1.983) |
| log | rollm1-pinned | +0.005 [-0.051, +0.062] (ref -0.786 → -0.781) | +0.030 [-0.038, +0.101] (ref +0.130 → +0.161) | +0.017 [-0.078, +0.108] (ref +2.025 → +2.043) |
| log | rollw1-pinned | +0.017 [-0.045, +0.079] (ref -0.786 → -0.769) | -0.022 [-0.119, +0.067] (ref +0.130 → +0.108) | -0.018 [-0.100, +0.071] (ref +2.025 → +2.008) |
| log | k1rep-rollm (K1 replicate: LGBM-bits noise floor, auxiliary) | +0.000 [+0.000, +0.000] (ref -0.756 → -0.756) | +0.000 [+0.000, +0.000] (ref +0.145 → +0.145) | +0.000 [+0.000, +0.000] (ref +1.983 → +1.983) |
| log | rollm1-rollm (embargo cost K2-K1) | -0.024 [-0.050, +0.004] (ref -0.756 → -0.781) | +0.016 [-0.049, +0.082] (ref +0.145 → +0.161) | +0.059 [-0.020, +0.140] (ref +1.983 → +2.043) |
| log | rollw1-rollm1 (cadence at equal embargo K3-K2, auxiliary) | +0.011 [-0.020, +0.041] (ref -0.781 → -0.769) | -0.053 [-0.132, +0.013] (ref +0.161 → +0.108) | -0.035 [-0.091, +0.019] (ref +2.043 → +2.008) |
| prod | rollm-pinned | +0.033 [-0.023, +0.086] (ref -0.855 → -0.822) | +0.038 [-0.032, +0.109] (ref +0.080 → +0.118) | -0.030 [-0.149, +0.089] (ref +1.995 → +1.965) |
| prod | rollm1-pinned | +0.024 [-0.030, +0.079] (ref -0.855 → -0.831) | +0.036 [-0.041, +0.110] (ref +0.080 → +0.116) | +0.047 [-0.068, +0.176] (ref +1.995 → +2.042) |
| prod | rollw1-pinned | +0.014 [-0.046, +0.074] (ref -0.855 → -0.841) | +0.001 [-0.076, +0.074] (ref +0.080 → +0.081) | +0.019 [-0.103, +0.164] (ref +1.995 → +2.014) |
| prod | k1rep-rollm (K1 replicate: LGBM-bits noise floor, auxiliary) | +0.000 [+0.000, +0.000] (ref -0.822 → -0.822) | +0.000 [+0.000, +0.000] (ref +0.118 → +0.118) | +0.000 [+0.000, +0.000] (ref +1.965 → +1.965) |
| prod | rollm1-rollm (embargo cost K2-K1) | -0.009 [-0.045, +0.027] (ref -0.822 → -0.831) | -0.002 [-0.065, +0.060] (ref +0.118 → +0.116) | +0.077 [-0.041, +0.200] (ref +1.965 → +2.042) |
| prod | rollw1-rollm1 (cadence at equal embargo K3-K2, auxiliary) | -0.010 [-0.049, +0.030] (ref -0.831 → -0.841) | -0.035 [-0.086, +0.014] (ref +0.116 → +0.081) | -0.028 [-0.092, +0.034] (ref +2.042 → +2.014) |

### Frozen decision (PREREG §1; primary 2025→26, both calibers; ADMIT iff both CI95 lower > 0 and Δturnover ≤ +15%; REJECT iff either CI95 upper < 0 or Δturnover > +25%; else UNDECIDED)

| candidate | caliber | Δ 2025→26 [CI95] | CI lower > 0 | CI upper < 0 | Δturnover % (25on) | turn ≤ +15% | turn > +25% | aux Δ 2024→26 [CI95] | yearly Δ 2024 / 2025 / 2026 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| K1 rollm60 | log | -0.009 [-0.076, +0.058] | False | False | -0.0 | True | False | +0.001 [-0.042, +0.043] | +0.017 / -0.001 / -0.021 | **UNDECIDED** |
| K1 rollm60 | prod | +0.015 [-0.054, +0.089] | False | False | -0.0 | True | False | +0.014 [-0.037, +0.065] | +0.012 / +0.012 / +0.018 | **UNDECIDED** |
| K2 rollm1 | log | +0.031 [-0.027, +0.093] | False | False | -0.1 | True | False | +0.018 [-0.025, +0.060] | -0.005 / +0.018 / +0.050 | **UNDECIDED** |
| K2 rollm1 | prod | +0.050 [-0.026, +0.128] | False | False | -0.1 | True | False | +0.036 [-0.016, +0.090] | +0.013 / +0.030 / +0.079 | **UNDECIDED** |
| K3 rollw1 | log | -0.014 [-0.077, +0.049] | False | False | -0.1 | True | False | -0.008 [-0.051, +0.038] | +0.003 / -0.009 / -0.022 | **UNDECIDED** |
| K3 rollw1 | prod | +0.013 [-0.064, +0.091] | False | False | -0.1 | True | False | +0.011 [-0.042, +0.071] | +0.009 / -0.022 / +0.066 | **UNDECIDED** |

**Embargo cost K2 − K1 (reported separately, not for selection):** log: 2025→26 +0.040 [-0.015, +0.095], 2024→26 +0.017 [-0.019, +0.054], yearly -0.022/+0.019/+0.072; prod: 2025→26 +0.035 [-0.035, +0.107], 2024→26 +0.022 [-0.025, +0.070], yearly +0.001/+0.018/+0.060

## 3. What this establishes (properties, not actions)
1. **Freshness is real at the score layer and small at the book layer.** IC decays ≈0.0014/month (VERIFIED, paired); the book at the live seat cannot see it (VERIFIED: all CIs straddle 0 with half-widths ≈0.06 bps/anchor ≈ 1.3 %/gross/yr on 2025→26). INFERRED chain: a +0.2–0.3 bps/gross leg gain × seat 0.21 ≈ +0.04–0.06 bps/anchor of book, which is the size of the K2 point estimate and below the resolution of 3642 anchors.
2. **The embargo, not the cadence, is the lever with the larger point estimate.** K2−K1 ≈ +0.04 bps/anchor (both calibers, CI includes 0) vs K3−K2 ≈ −0.04 (CI touches 0). Cadence beyond monthly has no positive book evidence; if anything weekly is nominally worse than monthly at equal embargo, while being better in IC. INFERRED (not tested): weekly re-fits change the ranking every week and the EMA/band book pays a small re-sorting cost that the IC gain does not cover at this seat.
3. **The previous "IC up / leg down" K1 finding is largely an embargo artifact.** With a 1-anchor embargo the fresh king's leg beats pinned's in every window (K2 +0.18 to +0.31, K3 +0.14 to +0.43 bps/gross/anchor), and the production msharpe seat would be ≈0.30 for K2/K3 vs 0.29 for K0 (0.24 for K1).
4. **Production feasibility (addendum):** a weekly refit of the production recipe costs 18–74 s per fit (median 29 s) at 48 threads on the pod; one refit per week is negligible; the full 139-fold backfill took 78 minutes.
5. **Cross-check with the rolling_king report (2026-09-04):** K1 numbers here are bitwise the same artifacts (§1.3) and the K1 verdict is again UNDECIDED; the two reports agree.

## 4. Not established / risks not covered by any assertion (only the executor knows these)
- **Single instrument.** Every number is from the pod alone (jpline down); the only cross-instrument anchor is the port-baseline equality of §1.3.
- **Fixed seat only.** Axis A was judged at W3FIX 0.21/0/0.79 per PREREG §1. Under the live dynamic msharpe rule the fresh kings would receive a slightly larger seat (§2.3); no L-dyn arm was run for axis A, so the dynamic-seat book effect of K2/K3 is UNRESOLVED (axis B's business).
- **Training window start.** All folds (K0–K3, D1) train from 2022-01-08 (no 2020 front-extension, E-0905-A); "freshness" here is only about the *end* of the window.
- **Power.** The primary window has 3642 anchors; the K2 point estimate (+0.03/+0.05) would need ≈4× the sample to resolve. UNDECIDED is a statement about resolution, not about absence of effect.
- **After 2026-08-10** the F10 sub-book has no finite predictions for any king source (both calibers degrade to the same fund-only F10 book); the king book still differs. The ≤cut variants of the pooled windows are printed in `judge.log` and do not change any verdict.
- **Booster text vs predictions.** Retrained K1 boosters reproduce K1's predictions bitwise but their `model_to_string()` sha differs in 31/32 folds; cause not established (UNRESOLVED; provably prediction-irrelevant). A production check that compares booster hashes across retrains would give false alarms; compare predictions instead.
- **The k1rep book artifacts** differ from the K1 artifacts only in `config_json` (`SLOW_NPY` path); the arrays are identical (judge Δ +0.000 everywhere).
- **Not run:** any dynamic-seat arm, any second F10 seed (L-fix uses FSEED=42 only, as prescribed), any change of LGBM parameters, any 2020 front-extension.

## 5. Products (pod `/workspace/review_scratch/cadence_seats/axisA/`, mirrored on Mac `…/scratchpad/review_caliber/cadence_seats/axisA/pod_products/`)
| product | sha256 |
|---|---|
| `slow_pred_rollm1.npy` (K2) | `656ae170ce65d78dbcfd40093ddc156c9d62eba0b9d645f7b930124b5301479f` |
| `slow_pred_rollw1.npy` (K3) | `b726b4d838fe4ab95c5a8e536a50a37fde64f129ebb1080e4760807139e1e434` |
| `slow_pred_d1_testfold.npy` = `d1_pred_age1.npy` (K1 replicate; == `rolling_king/slow_pred_rollm.npy`) | `999f7d4d8fa4de8e9eb46305d31af8a06b14419b07389f269a8d2fbad138be4a` |
| `d1_pred_age12.npy` | `254fa0a9f04c6c44da0634f99913b1441ef35cd17b1dfd2d360aba98e611333c` |
| `d1w_pred_age1.npy` (== `slow_pred_rollw1.npy`) / `d1w_pred_age8.npy` | `b726b4d8…` / `311b442b18a05c93ed001ea5f2da14cb4067bd8c1b08858f6676c6f417060226` |
| `d1_matrices.npz` / `d1w_matrices.npz` / `legs_by_king.npz` | `5a44accb…` / `fcafef91…` / `69f281ab…` |
| `folds_d1.json` / `folds_rollm1.json` / `folds_rollw1.json` | `9cbd46a4…` / `9fb036fe…` / `3666e9d2…` |
| `d1_curve.json` / `d1w_curve.json` / `noise_floor.json` / `ic_legs_seat.json` / `judge.json` | `11ec422a…` / `4bdb87c4…` / `86db8571…` / `6bf2dc2b…` / `34199bc9…` |
| book artifacts `dev/probe_artifacts/w10_ablation_series_Lfix_{pinned,rollm,rollm1,rollw1,k1rep}_log_s42.npz` | `d02a9724…` / `8f9cd48f…` / `4bb95c75…` / `46f1af4a…` / `e55e3e26…` |
| book artifacts `dev_alt/probe_artifacts/w10_ablation_series_Lfix_{pinned,rollm,rollm1,rollw1,k1rep}_prod_s42.npz` | `198e0f1e…` / `d73f2139…` / `f3398ec4…` / `7ed67d60…` / `aa23650c…` |
| boosters `models_d1/` (32) / `models_rollm1/` (32) / `models_rollw1/` (139) | 75 MB / 75 MB / 318 MB (LightGBM text) |

Full 64-hex values of every product and script are in `logs/commands.txt`'s companion listing (`ssh pod2 'cd /workspace/review_scratch/cadence_seats/axisA && sha256sum *.npy *.npz *.json dev*/probe_artifacts/*.npz'`).

## 6. Scripts (sha256; all under `cadence_seats/axisA/` on the pod and in the Mac mirror)
| script | role | sha256 |
|---|---|---|
| `pod_king_cadence.py` | D1 / K2 / K3 training, per-fold ASSERT, stitching, D1 matrices | `1756b1ad4e58b62d059c1834700068a16d89f9ec596e5681284d833bef7ddeda` |
| `d1_curve.py` | D1 age curve + frozen gate | `64aa796cd017ef2cb21e6afd5af9c5bf5e89f4dc16020e48f32021832e16e893` |
| `d1w_curve.py` | weekly age curve (addendum) from saved K3 boosters | `0fec7d067d4a002b6ff7e1cbb6a7f73e84624f330ca5ac22e5a9cbfec0641017` |
| `noise_floor.py` | K1 replicate vs K1 | `7ddfdfd0986650ae2d32efcb703f6292499f77fae6f11800868206053f4452df` |
| `ic_legs.py` | IC / leg / seat tables (rolling_king's script, paths only) | `1ba20b3f1c35ad9d3725daa9b584e10e0240015672b627056fa93491fb0b668f` |
| `judge.py` | frozen judge (rolling_king's, adapted) | `597d0506ae307d383e7b462467486754f551dedc06f9988e8202db9228e95f02` |
| `render_tables.py` | markdown tables | `bc0dfda95e878eea5561c4f1ca7d0a41000d3d804fe749aa60c43d4c698ce855` |
| `check_equiv.py` / `setup_dev.sh` / `run_arms.sh` / `run_equiv.sh` / `run_k2k3.sh` | receipts, layouts, arms | `c3dec673…` / `da775ad9…` / `c0ad4078…` / `a9c4bd47…` / `734f8bdb…` |
| `launch_train.sh` / `chain_k2.sh` / `chain_k3.sh` / `post_d1.sh` | detached orchestration | `90e897b2…` / `dbf1440a…` / `2c0db0cd…` / `f390f580…` |
| `w10_universe_recheck.py` | book device (unchanged copy) | `5424aceb34b4595b8b9be0d720e90a60e1944fd9bb915fad4c934bc4cf59e9f9` |

## 7. Commands (verbatim; the complete log is `logs/commands.txt`, reproduced here)
```
CMD[train d1] 2026-09-04T23:33:38Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash -c "MODE=d1 NJOBS=48 /workspace/venv/bin/python pod_king_cadence.py > logs/d1.log 2>&1" > logs/nohup_d1.out 2>&1 < /dev/null &
CMD[setup] 2026-09-04T23:36:29Z: bash /workspace/review_scratch/cadence_seats/axisA/setup_dev.sh
CMD[run_equiv] 2026-09-04T23:36:31Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash run_equiv.sh > logs/run_equiv.out 2>&1 < /dev/null &
CMD[Lfix_rollm_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev) 2026-09-04T23:36:31Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_pinned_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev) 2026-09-04T23:36:31Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollm_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev_alt) 2026-09-04T23:36:31Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_pinned_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev_alt) 2026-09-04T23:36:31Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
ARMS_DONE king=pinned 2026-09-04T23:39:00Z
ARMS_DONE king=rollm 2026-09-04T23:39:01Z
EQUIV_RUNS_DONE 2026-09-04T23:39:01Z
CMD[check_equiv pinned] 2026-09-04T23:39:01Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python check_equiv.py pinned
CMD[check_equiv rollm] 2026-09-04T23:39:07Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python check_equiv.py rollm
CMD[chain_k2] 2026-09-04T23:40:56Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash chain_k2.sh > logs/chain_k2.out 2>&1 < /dev/null &
CMD[post_d1] 2026-09-04T23:44:44Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash post_d1.sh > logs/post_d1.out 2>&1 < /dev/null &
CMD[chain_k3] 2026-09-04T23:44:44Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash chain_k3.sh > logs/chain_k3.out 2>&1 < /dev/null &
CMD[d1_curve] 2026-09-04T23:54:16Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python d1_curve.py > logs/d1_curve.log 2>&1
CMD[noise_floor] 2026-09-04T23:54:22Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python noise_floor.py > logs/noise_floor.log 2>&1
CMD[train monthly1] 2026-09-04T23:54:28Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash -c "MODE=monthly1 NJOBS=48 /workspace/venv/bin/python pod_king_cadence.py > logs/monthly1.log 2>&1" > logs/nohup_monthly1.out 2>&1 < /dev/null &
CMD[Lfix_k1rep_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev) 2026-09-04T23:54:34Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/cadence_seats/axisA/slow_pred_d1_testfold.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_k1rep_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_k1rep_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev_alt) 2026-09-04T23:54:34Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/cadence_seats/axisA/slow_pred_d1_testfold.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_k1rep_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
ARMS_DONE king=k1rep 2026-09-04T23:56:45Z
CMD[train weekly1] 2026-09-05T00:12:34Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash -c "MODE=weekly1 NJOBS=48 /workspace/venv/bin/python pod_king_cadence.py > logs/weekly1.log 2>&1" > logs/nohup_weekly1.out 2>&1 < /dev/null &
CMD[run_k2k3] 2026-09-05T01:51:02Z: cd /workspace/review_scratch/cadence_seats/axisA && nohup bash run_k2k3.sh > logs/run_k2k3.out 2>&1 < /dev/null &
CMD[d1w_curve] 2026-09-05T01:51:02Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python d1w_curve.py > logs/d1w_curve.log 2>&1
CMD[Lfix_rollw1_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev) 2026-09-05T01:51:02Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/cadence_seats/axisA/slow_pred_rollw1.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_rollw1_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollm1_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev) 2026-09-05T01:51:02Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/cadence_seats/axisA/slow_pred_rollm1.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_rollm1_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollm1_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev_alt) 2026-09-05T01:51:02Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/cadence_seats/axisA/slow_pred_rollm1.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_rollm1_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollw1_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisA/dev_alt) 2026-09-05T01:51:02Z: env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/cadence_seats/axisA/slow_pred_rollw1.npy MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42 OUT_TAG=Lfix_rollw1_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
ARMS_DONE king=rollm1 2026-09-05T01:51:47Z
ARMS_DONE king=rollw1 2026-09-05T01:51:47Z
CMD[ic_legs all kings] 2026-09-05T01:52:19Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python ic_legs.py > logs/ic_legs.log 2>&1
CMD[judge] 2026-09-05T01:52:33Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python judge.py > logs/judge.log 2>&1
K2K3_ARMS_DONE 2026-09-05T01:52:53Z
CMD[render_tables] 2026-09-05T01:53:07Z: cd /workspace/review_scratch/cadence_seats/axisA && /workspace/venv/bin/python render_tables.py > REPORT_tables.md 2> logs/render_tables.err
```
Re-run recipe (verbatim, in order): `bash launch_train.sh d1` → `bash post_d1.sh` (d1_curve, noise_floor, k1rep arms) → `bash launch_train.sh monthly1` → (if `d1_curve.json` decision K3 == RUN) `bash launch_train.sh weekly1` → `bash run_equiv.sh` (pinned/rollm arms + equivalence) → `bash run_k2k3.sh` (rollm1/rollw1 arms, d1w_curve, ic_legs) → `/workspace/venv/bin/python judge.py` → `/workspace/venv/bin/python render_tables.py > REPORT_tables.md`. Environment: pod2 `/workspace/venv/bin/python` 3.11.10, numpy 2.4.6, lightgbm 4.7.0, scipy 1.17.1, 64 cores, no GPU; `NJOBS=48` for every fit; book arms `OMP_NUM_THREADS=4`.
