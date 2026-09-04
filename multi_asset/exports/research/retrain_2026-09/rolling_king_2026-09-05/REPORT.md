# REPORT — rolling monthly king (production recipe) vs pinned king: strict-causal offline evaluation under the correct calibers

> **创建:** 2026-09-04 17:1xZ–18:xxZ UTC (prereg dated 2026-09-05 local) | **Session:** b9646a9e, teammate `rolling_king` | **状态:** complete; decision under the frozen criteria in §3 | **作废条件:** PREREG §0 — causal assertion fails (checked: all folds True, §2.0) or device not bitwise-equivalent to the port baseline (checked: PASS, §1.3); also voided by any change of the production king recipe (78 keep cols / rank label / LGBM params) or by a jpline hist-king re-run that contradicts the pinned baseline.
> Prereg: `docs/PREREG_rolling_king_monthly_2026-09-05.md` (criteria frozen before any number). Labels: **VERIFIED** = printed by a script and quoted with its command; **INFERRED** = derived from verified facts with the reasoning stated; **UNRESOLVED** = not established here.

## 0. Answer (one paragraph) and decision

**Question:** does retraining the production king tree monthly on the latest data (the DL-refit cadence) help the live book under the correct return caliber, with the seat inputs kept strictly out-of-sample?

**Answer: no detectable help; frozen verdict = UNDECIDED in both calibers (not ADMIT, not REJECT).** With the production recipe (78 keep columns, rank label, LGBM 400/0.05/63) refit every month with a 60-anchor embargo (all 32 causal assertions True), the rolling king raises the rank-IC where the pinned year-fold is stale — Δ rank-IC vs pinned 2024 +0.0087 ± 0.0015, 2025 +0.0053 ± 0.0010 — but **not in 2026 (+0.0006 ± 0.0009)**. The IC gain does not reach the king leg's raw return: king-leg Δ (bps per unit gross per anchor, production leg definition) 2024 −0.02 / 2025 +0.28 / **2026≤08-10 −0.52** under raw y4 and −0.10 / +0.25 / **−0.66** under the compounded target; pooled 2024→26 −0.03 / −0.10. At the production msharpe rule the rolling king therefore gets a *smaller* seat at 2026-08-10 20:00Z (w101 king 0.241 vs pinned 0.288). At the book level (arm d30_n2_c42, net_ex, anchors paired by ts, n = 10,038 identical), the primary arm L-fix (live fixed seat 0.21/0/0.79, M829/T400/FTRIM) gives Δ 2024→26 = **+0.001 bps/anchor [CI95 −0.042, +0.043], P(Δ>0) 0.53** under raw Σ-simple y4 and **+0.014 [−0.036, +0.065], P 0.71** under the compounded holding-window target; 2025→26 −0.009 / +0.015; yearly Δ within ±0.03; turnover −0.3%. Dynamic-seat arms are likewise indistinguishable from zero (L-dyn 2024→26: −0.004 / +0.003 under raw for seeds 42/2027, +0.014 / +0.033 under compounded; C-dyn −0.008 / −0.021), with the rule handing the rolling king +0.03 more average king seat and +3–5% turnover. Under the frozen criteria: the L-fix 2024→26 CI95 lower bound is not > 0 in either caliber (no ADMIT), the upper bound is not < 0 and turnover is not > +25% (no REJECT) ⇒ **UNDECIDED**; the quarterly variant (shape check only) lands in the same state (L-fix +0.012 / +0.026, CIs include 0). **Recommendation (INFERRED from the tables, not a criterion): do not deploy a monthly king refit; the axis "king freshness" does not produce a book-level effect at the live seat, and its 2026 leg-level sign is negative.**

> READ-ONLY on all inputs. Outputs only under `/workspace/review_scratch/rolling_king/` (pod) and the Mac scratch dir `…/scratchpad/review_caliber/rolling_king/`. No GPU. jpline not used.

## 1. Device (what was run)

### 1.1 STEP 1 — rolling predictions: `pod_king_rolling_monthly.py`
- **Data preparation = `/workspace/pod_export_bundle_v3.py` L22, L26–47 verbatim** (FEA `/workspace/data/wide_fea_v2ext.npy` (10176, 829, 82) float16; meta `wide_fea_v2ext_meta.npz`; `keep` = 78 columns whose name does not start with `ret5_sum_48`/`ret5_sum_288`, asserted `== live_pins.json keep_names`; per-anchor rows over `members` with finite y4, anchors with <50 skipped; label `rr = rankdata(y4[ok])/max(n−1,1) − 0.5`). Printed (VERIFIED, `logs/rollm.log`): `PREP X (2741477, 78) float32 Y (2741477,) rows_anchors 10176/10176 keep 78 E_ts[0] 2022-01-08 00:00 E_ts[-1] 2026-08-30 20:00`.
- **Model** = `LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, verbose=-1)` with `n_jobs=48`, `random_state=20260905+fold_index`. Production booster header (VERIFIED, `grep -n -E "^\[(bagging_freq|bagging_fraction|feature_fraction|seed|num_threads|deterministic)" /workspace/shadow_bundle_v3/slow2026.txt`): `7706:[num_threads: 100] 7707:[seed: 0] 7708:[deterministic: 0] 7715:[bagging_fraction: 0.8] 7718:[bagging_freq: 0] 7721:[feature_fraction: 0.8]`. INFERRED: with `bagging_freq: 0` the `subsample=0.8` is inactive in production as well; the only seeded stochastic element is `feature_fraction`; because production runs `deterministic: 0` with 100 threads and no seed, a fold booster here is not expected to be bitwise identical to a production retrain of the same window — the recipe, not the bits, is what is reproduced.
- **Folds**: monthly test = calendar month M (UTC by E_ts) for M = 2024-01 … 2026-08 (32 folds); quarterly variant = calendar quarter 2024Q1 … 2026Q3 (11 folds, shape check only; seeds 20260905+quarter index). Embargo = 60 anchors (864,000 s).
- **D1 device note (decided 17:2xZ, before any number existed; first launch log kept as `logs/rollm_attempt1_assertfail.log`)**: the spec's train rule "E_ts < first_test − 60×14400" makes the last training label window end *exactly* at the embargo boundary, so the spec's strict assertion `max(train E_ts)+48·300 < min(test E_ts)−60·14400` fails with gap 0 (printed: `1703203200 >= 1703203200`). This is an off-by-one between the two sentences, not a causality violation (the gap between the last training label end and the first test anchor was already 10 days). Resolution: the strict assertion is kept as the guard and the train rule is tightened by one grid step — train rows = anchors with `E_ts + 48·300 < first_test − 60·14400` (label window ends strictly before the boundary; ≈330 rows fewer per fold out of 0.7–2.7M). Effective gap from last training label end to first test anchor = 60 anchors + 4 h. Self-reported in the script's CONFIG line (`train_rule`).
- **Causal assertion** is printed for every fold (§2.0): all True, gap exactly 1 anchor (14,400 s) between label end and the embargo boundary.
- **Outputs**: `slow_pred_rollm.npy`, `slow_pred_rollq.npy` — float32 (10176, 829) aligned to meta E_ts, NaN outside test folds (2022–23 all NaN exactly like `slow_pred_pinned.npy`; finite mask asserted equal to pinned), plus `folds_rollm.json` / `folds_rollq.json` (per-fold receipts, booster sha).
- **Comparator** = `/workspace/shadow_bundle_v3/slow_pred_pinned.npy` (sha256 `158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054`): year folds, 2024 from <2024, 2025 from <2025, 2026 from <2026 (exporter L49–82). Both files are out-of-sample row by row; the single variable is freshness (monthly vs yearly refit).

### 1.2 STEP 3 — evaluation device and layouts
- `w10_universe_recheck.py` (sha256 `5424aceb34b4595b8b9be0d720e90a60e1944fd9bb915fad4c934bc4cf59e9f9`) copied from `/workspace/review_scratch/combo_recheck/`; = port `/workspace/port_w10/w10_universe.py` (`64c70a44…`) + the REF_SKIP guard only (diff quoted in §7 receipts; no computation path changed; REF_SKIP not needed here since all arms are LEGS=101, where the 144-byte reference stubs already route to the "仅比较共同年份" branch).
- `dev/` = combo_recheck's layout reproduced: `pod_backup_2026-08-21/{nets_histv2_0_0_0.npy, nets_histv2_-30_2_42.npy, slow_pred_hist_oos.npy, wide_fea_hist_meta.npz, wide_panel_4h_hist_v2.npz}` → symlinks to `/workspace/port_w10/pod_backup_2026-08-21/*` (which resolve to `/workspace/shadow_bundle_v3/slow_pred_pinned.npy`, `/workspace/data/wide_fea_v2ext_meta.npz`, `/workspace/data/wide_panel_4h_v2ext.npz`), plus `f8_2026-08-22`, `dlw_2026-08-22` → `/workspace/port_w10/*` (resolved paths printed in `logs/setup_dev.log`).
- `dev_alt/` = same, except `wide_fea_hist_meta.npz` → `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz` (sha256 `831857dd6a2035235647158d26d0155d17c7e77d85fa248b2ae9a617658ddf13`).
- **What the refuters' `build_alt_meta.py` / `run_alt.sh` do** (VERIFIED by reading both files; their printed receipts quoted): `build_alt_meta.py` loads the 5-minute panel `dlnative_5m_wide829_f16_ext.npz`, builds cumulative sums of r5, of log1p(r5) and of the finite mask, and for each meta anchor E at 5m row r computes `oldsum` = Σ r5 over rows [r, r+48) (== meta y4 **bitwise**: `PARITY oldsum(rebuilt) vs meta y4: cells 3446599 exact_eq 1.000000 max|Δ| 0.00e+00 nan-mismatch 0`), `newsum` = Σ r5 over [r+1, r+49), and `newprod` = expm1(Σ log1p(r5) over [r+1, r+49)) = **Π(1+r5)−1 over the holding window [E+1, E+48]** (== dlw y4s **bitwise**: `PARITY newprod vs dlw y4s: common anchors 10056 cells 3374240 exact_eq 1.000000 max|Δ| 0.00e+00 nan-mismatch 0`), NaN where <46 finite bars; it saves `meta_{newsum,newprod,oldsum_rebuilt}.npz` with E_ts/members/qvk/names copied from the meta and **only `y4` replaced**. `run_alt.sh` copies the port device, builds three dev dirs whose `wide_fea_hist_meta.npz` symlink points at the respective meta, and runs the device with `CAL=log` (no transform), so the swapped y4 enters the P&L, the msharpe seat leg-returns and the stop-layer price path unchanged. Their `base` dir reproduces the port bitwise (their `final_stats.out`), and my pinned `dev_alt` arms reproduce their `newprod` artifacts bitwise (§1.3). The rolling models are trained on the raw meta y4 label in both calibers; only the evaluation target changes.
- **Arms** (each × king ∈ {pinned, rollm, rollq} × caliber ∈ {log = raw Σ-simple y4, prod = compounded target}); common env `LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=<king file>`, PHI default 0.45, F10 = `f10_V2MAIN_s{FSEED}.npy` (finite to 2026-08-10 20:00Z):

| arm | extra env | seats |
|---|---|---|
| L-fix | `MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42` | fixed at the live seat (closest to live) |
| L-dyn | `MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero`, `FSEED=42` and `FSEED=2027` | msharpe (production rule; seat inputs OOS row by row) |
| C-dyn | canon (no MEMBERS_TOPN/TRADE_TOPN/FTRIM), `FSEED=42` | msharpe |

### 1.3 Receipts (device equivalence)
- **Equivalence run first** (cwd `dev/`, verbatim): `env SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy LEGS=101 LOOK=900 WRULE=msharpe CAL=log FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=eq_livefix_pinned_callog /workspace/venv/bin/python ../w10_universe_recheck.py` → `RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.1584, "net_ex_2024on": 0.4566, "sharpe_ex_2024on": 1.017, "by_year_ex": {"2022": -0.12, "2023": -0.381, "2024": -0.642, "2025": 0.284, "2026": 2.378}, …}`; vs `/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz`: `EQUIV d30_n2_c42_rec array_equal: True`, `S0_rec True`, `d30_n2_c42_W True`, `S0_W True`, `config_json equal (minus REF_SKIP): True` — **PASS** (VERIFIED).
- **Double-launch hazard closed (VERIFIED, `logs/verify_rerun.log`)**: `logs/commands.txt` shows the rollm and rollq arm sets launched twice (17:43/17:44Z and 17:50/17:50Z) — a first detached chain (17:32:13Z) that `ps` had not shown was alive alongside `chain_arms.sh`, so both wrote the same OUT_TAG paths. The device contains no random element, every artifact loaded whole in `judge.py`, and a third run of all 16 rolling-king arms under suffix `_v` (`verify_rerun.sh`, 20:2xZ) reproduces every stored artifact bitwise: `ALL_RERUN_EQUAL True n 16` (all four arrays array_equal and config_json equal for each of Lfix/Ldyn s42/Ldyn s2027/Cdyn × log/prod × rollm/rollq).
- **All pinned arms cross-checked bitwise** against pre-existing identical-config artifacts (`check_pinned_equiv.py`, VERIFIED, `logs/check_pinned_equiv.log`): L-fix log ↔ port `pod_live_w3fix_callog_s42`; L-dyn log s42/s2027 ↔ port `pod_live_callog_s42`/`_s2027`; C-dyn log ↔ port `pod_canon_callog_s42`; L-fix prod ↔ refute_C6_2 `alt_newprod_w3fix`; L-dyn prod s42 ↔ `alt_newprod_dyn`; C-dyn prod ↔ combo_recheck `D_prod_s42` — **7/7 PASS** (all four arrays array_equal, configs equal minus REF_SKIP). L-dyn prod s2027 pinned has no pre-existing counterpart (new run).

### 1.4 STEP 4 — judge (frozen; `judge.py`)
- Arm `d30_n2_c42`, column `net_ex`; anchors paired by ts, identical sets asserted (n printed). Δ = king − pinned.
- Windows: 2024 | 2025 | 2026≤08-10 (ts ≤ 2026-08-10 20:00Z = last finite F10 row) | 2026→08-30 (all 2026 replayed anchors) | **2024→26 = 2024-01-01 → 2026-08-30 20:00Z (primary for the frozen criteria)** | 2025→26; the ≤cut variants of both pooled windows are reported alongside (after 08-10 the F10 sub-book degenerates to fund-only for both king sources; the king book still differs).
- Bootstrap: UTC-calendar-day blocks, 2000 resamples with replacement over days, seed 20260905, CI95 = 2.5/97.5 percentiles of resampled means, P = share of resampled means > 0. Sharpe = mean/std(ddof=1)·√2190; maxDD = max(cummax(cumsum net_ex) − cumsum) in bps; Δturnover% = (turn_king/turn_pinned − 1)·100 over 2024→26; Δ mean w3_king over 2024→26 (dynamic arms).
- σ_fund (exact definition used): per anchor, over **meta members** with finite `f_fund_now`: std(`f_fund_now·8/ivf`)·1e4 (bps per 8 h), ivf = `f_fund_iv` where finite and >0 else 8; trailing 30-anchor mean over the replayed anchor sequence (≥15 valid); terciles = 33.33/66.67 percentiles over the 2024→26 anchors.
- Decision (PREREG §3, evaluated by the script): **ADMIT candidate** iff for both calibers L-fix 2024→26 CI95 lower > 0 ∧ L-fix 2025→26 Δ ≥ 0 ∧ min over {2024, 2025, 2026→08-30} of L-fix Δ ≥ −0.05 ∧ L-fix Δturnover ≤ +15% ∧ L-dyn 2024→26 Δ ≥ 0 for both seeds; **REJECT** iff for either caliber L-fix 2024→26 CI95 upper < 0 ∨ Δturnover > +25%; else **UNDECIDED**. Quarterly variant reported as a shape check only.

## 2. Results (all numbers printed by scripts; VERIFIED unless marked; sections 2.0–2.6 rendered by `render_tables.py` from `folds_*.json`, `ic_legs_seat.json`, `judge.json`)

### Folds — monthly (PRIMARY): `slow_pred_rollm.npy` sha256 `999f7d4d8fa4de8e9eb46305d31af8a06b14419b07389f269a8d2fbad138be4a`; finite-mask equal to pinned = **True**; script sha256 `38d65533b741bea892df78c0c07e85133e2d086ebfda58e34647779bfab13f6e`; train_rule = `E_ts + 48*300 < first_test_E_ts - 60*14400 (D1: one 4h step stricter than 'E_ts < first_test - 60*14400' so the strict causal ASSERT holds)`

| fold | test key | seed | train rows | train anchors | train span | test anchors (rows) | test span | ASSERT max(train E_ts)+48·300 < min(test E_ts)−60·14400 | gap | fit s | rank-IC (raw y4) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 202401 | 20260905 | 694,846 | 4277 | 2022-01-08..2023-12-21 16:00 | 186/186 (45,328) | 2024-01-01 00:00..2024-01-31 20:00 | 1703188800 (2023-12-21 20:00) < 1703203200 (2023-12-22 00:00) → **True** | 1 anchor | 16.9 | +0.0799 |
| 1 | 202402 | 20260906 | 739,796 | 4463 | 2022-01-08..2024-01-21 16:00 | 174/174 (43,891) | 2024-02-01 00:00..2024-02-29 20:00 | 1705867200 (2024-01-21 20:00) < 1705881600 (2024-01-22 00:00) → **True** | 1 anchor | 16.5 | +0.0636 |
| 2 | 202403 | 20260907 | 783,135 | 4637 | 2022-01-08..2024-02-19 16:00 | 186/186 (48,790) | 2024-03-01 00:00..2024-03-31 20:00 | 1708372800 (2024-02-19 20:00) < 1708387200 (2024-02-20 00:00) → **True** | 1 anchor | 16.9 | +0.0698 |
| 3 | 202404 | 20260908 | 831,269 | 4823 | 2022-01-08..2024-03-21 16:00 | 180/180 (47,685) | 2024-04-01 00:00..2024-04-30 20:00 | 1711051200 (2024-03-21 20:00) < 1711065600 (2024-03-22 00:00) → **True** | 1 anchor | 35.3 | +0.0620 |
| 4 | 202405 | 20260909 | 878,888 | 5003 | 2022-01-08..2024-04-20 16:00 | 186/186 (49,326) | 2024-05-01 00:00..2024-05-31 20:00 | 1713643200 (2024-04-20 20:00) < 1713657600 (2024-04-21 00:00) → **True** | 1 anchor | 18.6 | +0.0373 |
| 5 | 202406 | 20260910 | 928,597 | 5189 | 2022-01-08..2024-05-21 16:00 | 180/180 (47,074) | 2024-06-01 00:00..2024-06-30 20:00 | 1716321600 (2024-05-21 20:00) < 1716336000 (2024-05-22 00:00) → **True** | 1 anchor | 21.8 | +0.0498 |
| 6 | 202407 | 20260911 | 975,508 | 5369 | 2022-01-08..2024-06-20 16:00 | 186/186 (48,804) | 2024-07-01 00:00..2024-07-31 20:00 | 1718913600 (2024-06-20 20:00) < 1718928000 (2024-06-21 00:00) → **True** | 1 anchor | 23.4 | +0.0463 |
| 7 | 202408 | 20260912 | 1,024,427 | 5555 | 2022-01-08..2024-07-21 16:00 | 186/186 (49,097) | 2024-08-01 00:00..2024-08-31 20:00 | 1721592000 (2024-07-21 20:00) < 1721606400 (2024-07-22 00:00) → **True** | 1 anchor | 24.7 | +0.0647 |
| 8 | 202409 | 20260913 | 1,073,101 | 5741 | 2022-01-08..2024-08-21 16:00 | 180/180 (50,450) | 2024-09-01 00:00..2024-09-30 20:00 | 1724270400 (2024-08-21 20:00) < 1724284800 (2024-08-22 00:00) → **True** | 1 anchor | 30.9 | +0.0566 |
| 9 | 202410 | 20260914 | 1,122,445 | 5921 | 2022-01-08..2024-09-20 16:00 | 186/186 (54,920) | 2024-10-01 00:00..2024-10-31 20:00 | 1726862400 (2024-09-20 20:00) < 1726876800 (2024-09-21 00:00) → **True** | 1 anchor | 44.5 | +0.0801 |
| 10 | 202411 | 20260915 | 1,176,741 | 6107 | 2022-01-08..2024-10-21 16:00 | 180/180 (55,301) | 2024-11-01 00:00..2024-11-30 20:00 | 1729540800 (2024-10-21 20:00) < 1729555200 (2024-10-22 00:00) → **True** | 1 anchor | 23.9 | +0.0850 |
| 11 | 202412 | 20260916 | 1,230,937 | 6287 | 2022-01-08..2024-11-20 16:00 | 186/186 (60,740) | 2024-12-01 00:00..2024-12-31 20:00 | 1732132800 (2024-11-20 20:00) < 1732147200 (2024-11-21 00:00) → **True** | 1 anchor | 27.6 | +0.0670 |
| 12 | 202501 | 20260917 | 1,290,492 | 6473 | 2022-01-08..2024-12-21 16:00 | 186/186 (64,291) | 2025-01-01 00:00..2025-01-31 20:00 | 1734811200 (2024-12-21 20:00) < 1734825600 (2024-12-22 00:00) → **True** | 1 anchor | 32.1 | +0.0800 |
| 13 | 202502 | 20260918 | 1,353,644 | 6659 | 2022-01-08..2025-01-21 16:00 | 168/168 (60,310) | 2025-02-01 00:00..2025-02-28 20:00 | 1737489600 (2025-01-21 20:00) < 1737504000 (2025-01-22 00:00) → **True** | 1 anchor | 35.7 | +0.0607 |
| 14 | 202503 | 20260919 | 1,413,353 | 6827 | 2022-01-08..2025-02-18 16:00 | 186/186 (68,046) | 2025-03-01 00:00..2025-03-31 20:00 | 1739908800 (2025-02-18 20:00) < 1739923200 (2025-02-19 00:00) → **True** | 1 anchor | 31.9 | +0.0738 |
| 15 | 202504 | 20260920 | 1,480,918 | 7013 | 2022-01-08..2025-03-21 16:00 | 180/180 (69,340) | 2025-04-01 00:00..2025-04-30 20:00 | 1742587200 (2025-03-21 20:00) < 1742601600 (2025-03-22 00:00) → **True** | 1 anchor | 27.0 | +0.0445 |
| 16 | 202505 | 20260921 | 1,549,071 | 7193 | 2022-01-08..2025-04-20 16:00 | 186/186 (74,224) | 2025-05-01 00:00..2025-05-31 20:00 | 1745179200 (2025-04-20 20:00) < 1745193600 (2025-04-21 00:00) → **True** | 1 anchor | 44.8 | +0.0593 |
| 17 | 202506 | 20260922 | 1,622,677 | 7379 | 2022-01-08..2025-05-21 16:00 | 180/180 (72,000) | 2025-06-01 00:00..2025-06-30 20:00 | 1747857600 (2025-05-21 20:00) < 1747872000 (2025-05-22 00:00) → **True** | 1 anchor | 25.7 | +0.0749 |
| 18 | 202507 | 20260923 | 1,694,677 | 7559 | 2022-01-08..2025-06-20 16:00 | 186/186 (74,400) | 2025-07-01 00:00..2025-07-31 20:00 | 1750449600 (2025-06-20 20:00) < 1750464000 (2025-06-21 00:00) → **True** | 1 anchor | 48.5 | +0.0797 |
| 19 | 202508 | 20260924 | 1,769,077 | 7745 | 2022-01-08..2025-07-21 16:00 | 186/186 (74,400) | 2025-08-01 00:00..2025-08-31 20:00 | 1753128000 (2025-07-21 20:00) < 1753142400 (2025-07-22 00:00) → **True** | 1 anchor | 27.5 | +0.0802 |
| 20 | 202509 | 20260925 | 1,843,477 | 7931 | 2022-01-08..2025-08-21 16:00 | 180/180 (72,000) | 2025-09-01 00:00..2025-09-30 20:00 | 1755806400 (2025-08-21 20:00) < 1755820800 (2025-08-22 00:00) → **True** | 1 anchor | 28.3 | +0.0557 |
| 21 | 202510 | 20260926 | 1,915,477 | 8111 | 2022-01-08..2025-09-20 16:00 | 186/186 (74,400) | 2025-10-01 00:00..2025-10-31 20:00 | 1758398400 (2025-09-20 20:00) < 1758412800 (2025-09-21 00:00) → **True** | 1 anchor | 31.2 | +0.0656 |
| 22 | 202511 | 20260927 | 1,989,877 | 8297 | 2022-01-08..2025-10-21 16:00 | 180/180 (72,000) | 2025-11-01 00:00..2025-11-30 20:00 | 1761076800 (2025-10-21 20:00) < 1761091200 (2025-10-22 00:00) → **True** | 1 anchor | 58.1 | +0.0786 |
| 23 | 202512 | 20260928 | 2,061,877 | 8477 | 2022-01-08..2025-11-20 16:00 | 186/186 (74,400) | 2025-12-01 00:00..2025-12-31 20:00 | 1763668800 (2025-11-20 20:00) < 1763683200 (2025-11-21 00:00) → **True** | 1 anchor | 56.6 | +0.0656 |
| 24 | 202601 | 20260929 | 2,136,277 | 8663 | 2022-01-08..2025-12-21 16:00 | 186/186 (74,400) | 2026-01-01 00:00..2026-01-31 20:00 | 1766347200 (2025-12-21 20:00) < 1766361600 (2025-12-22 00:00) → **True** | 1 anchor | 32.3 | +0.0733 |
| 25 | 202602 | 20260930 | 2,210,677 | 8849 | 2022-01-08..2026-01-21 16:00 | 168/168 (67,200) | 2026-02-01 00:00..2026-02-28 20:00 | 1769025600 (2026-01-21 20:00) < 1769040000 (2026-01-22 00:00) → **True** | 1 anchor | 33.3 | +0.0508 |
| 26 | 202603 | 20260931 | 2,277,877 | 9017 | 2022-01-08..2026-02-18 16:00 | 186/186 (74,400) | 2026-03-01 00:00..2026-03-31 20:00 | 1771444800 (2026-02-18 20:00) < 1771459200 (2026-02-19 00:00) → **True** | 1 anchor | 33.5 | +0.0637 |
| 27 | 202604 | 20260932 | 2,352,277 | 9203 | 2022-01-08..2026-03-21 16:00 | 180/180 (72,000) | 2026-04-01 00:00..2026-04-30 20:00 | 1774123200 (2026-03-21 20:00) < 1774137600 (2026-03-22 00:00) → **True** | 1 anchor | 33.3 | +0.0675 |
| 28 | 202605 | 20260933 | 2,424,277 | 9383 | 2022-01-08..2026-04-20 16:00 | 186/186 (74,400) | 2026-05-01 00:00..2026-05-31 20:00 | 1776715200 (2026-04-20 20:00) < 1776729600 (2026-04-21 00:00) → **True** | 1 anchor | 37.1 | +0.0616 |
| 29 | 202606 | 20260934 | 2,498,677 | 9569 | 2022-01-08..2026-05-21 16:00 | 180/180 (72,000) | 2026-06-01 00:00..2026-06-30 20:00 | 1779393600 (2026-05-21 20:00) < 1779408000 (2026-05-22 00:00) → **True** | 1 anchor | 37.1 | +0.0417 |
| 30 | 202607 | 20260935 | 2,570,677 | 9749 | 2022-01-08..2026-06-20 16:00 | 186/186 (74,400) | 2026-07-01 00:00..2026-07-31 20:00 | 1781985600 (2026-06-20 20:00) < 1782000000 (2026-06-21 00:00) → **True** | 1 anchor | 36.3 | +0.0644 |
| 31 | 202608 | 20260936 | 2,645,077 | 9935 | 2022-01-08..2026-07-21 16:00 | 180/180 (72,000) | 2026-08-01 00:00..2026-08-30 20:00 | 1784664000 (2026-07-21 20:00) < 1784678400 (2026-07-22 00:00) → **True** | 1 anchor | 38.2 | +0.0461 |

folds 32, all asserts True = **True**, mean per-fold rank-IC +0.0641, total fit 1030s

### Folds — quarterly (shape check): `slow_pred_rollq.npy` sha256 `a67d666b4313119497e9b834c37dd305da56b97f8505293d7ac763f6bcaaea80`; finite-mask equal to pinned = **True**; script sha256 `38d65533b741bea892df78c0c07e85133e2d086ebfda58e34647779bfab13f6e`; train_rule = `E_ts + 48*300 < first_test_E_ts - 60*14400 (D1: one 4h step stricter than 'E_ts < first_test - 60*14400' so the strict causal ASSERT holds)`

| fold | test key | seed | train rows | train anchors | train span | test anchors (rows) | test span | ASSERT max(train E_ts)+48·300 < min(test E_ts)−60·14400 | gap | fit s | rank-IC (raw y4) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 20241 | 20260905 | 694,846 | 4277 | 2022-01-08..2023-12-21 16:00 | 546/546 (138,009) | 2024-01-01 00:00..2024-03-31 20:00 | 1703188800 (2023-12-21 20:00) < 1703203200 (2023-12-22 00:00) → **True** | 1 anchor | 85.2 | +0.0697 |
| 1 | 20242 | 20260906 | 831,269 | 4823 | 2022-01-08..2024-03-21 16:00 | 546/546 (144,085) | 2024-04-01 00:00..2024-06-30 20:00 | 1711051200 (2024-03-21 20:00) < 1711065600 (2024-03-22 00:00) → **True** | 1 anchor | 26.7 | +0.0481 |
| 2 | 20243 | 20260907 | 975,508 | 5369 | 2022-01-08..2024-06-20 16:00 | 552/552 (148,351) | 2024-07-01 00:00..2024-09-30 20:00 | 1718913600 (2024-06-20 20:00) < 1718928000 (2024-06-21 00:00) → **True** | 1 anchor | 44.6 | +0.0553 |
| 3 | 20244 | 20260908 | 1,122,445 | 5921 | 2022-01-08..2024-09-20 16:00 | 552/552 (170,961) | 2024-10-01 00:00..2024-12-31 20:00 | 1726862400 (2024-09-20 20:00) < 1726876800 (2024-09-21 00:00) → **True** | 1 anchor | 21.6 | +0.0784 |
| 4 | 20251 | 20260909 | 1,290,492 | 6473 | 2022-01-08..2024-12-21 16:00 | 540/540 (192,647) | 2025-01-01 00:00..2025-03-31 20:00 | 1734811200 (2024-12-21 20:00) < 1734825600 (2024-12-22 00:00) → **True** | 1 anchor | 22.4 | +0.0692 |
| 5 | 20252 | 20260910 | 1,480,918 | 7013 | 2022-01-08..2025-03-21 16:00 | 546/546 (215,564) | 2025-04-01 00:00..2025-06-30 20:00 | 1742587200 (2025-03-21 20:00) < 1742601600 (2025-03-22 00:00) → **True** | 1 anchor | 25.2 | +0.0600 |
| 6 | 20253 | 20260911 | 1,694,677 | 7559 | 2022-01-08..2025-06-20 16:00 | 552/552 (220,800) | 2025-07-01 00:00..2025-09-30 20:00 | 1750449600 (2025-06-20 20:00) < 1750464000 (2025-06-21 00:00) → **True** | 1 anchor | 29.0 | +0.0704 |
| 7 | 20254 | 20260912 | 1,915,477 | 8111 | 2022-01-08..2025-09-20 16:00 | 552/552 (220,800) | 2025-10-01 00:00..2025-12-31 20:00 | 1758398400 (2025-09-20 20:00) < 1758412800 (2025-09-21 00:00) → **True** | 1 anchor | 31.1 | +0.0677 |
| 8 | 20261 | 20260913 | 2,136,277 | 8663 | 2022-01-08..2025-12-21 16:00 | 540/540 (216,000) | 2026-01-01 00:00..2026-03-31 20:00 | 1766347200 (2025-12-21 20:00) < 1766361600 (2025-12-22 00:00) → **True** | 1 anchor | 33.1 | +0.0607 |
| 9 | 20262 | 20260914 | 2,352,277 | 9203 | 2022-01-08..2026-03-21 16:00 | 546/546 (218,400) | 2026-04-01 00:00..2026-06-30 20:00 | 1774123200 (2026-03-21 20:00) < 1774137600 (2026-03-22 00:00) → **True** | 1 anchor | 56.7 | +0.0578 |
| 10 | 20263 | 20260915 | 2,570,677 | 9749 | 2022-01-08..2026-06-20 16:00 | 366/366 (146,400) | 2026-07-01 00:00..2026-08-30 20:00 | 1781985600 (2026-06-20 20:00) < 1782000000 (2026-06-21 00:00) → **True** | 1 anchor | 36.4 | +0.0568 |

folds 11, all asserts True = **True**, mean per-fold rank-IC +0.0631, total fit 412s

### Yearly mean rank-IC vs raw y4 = Σ 5m simple returns over [E, E+47] (meta; production label source); identical anchor set for all sources (2024+, finite IC for every source)

| window | n | pinned | rollm | rollq | Δ rollm−pinned (mean ± SE) | Δ rollq−pinned (mean ± SE) |
|---|---|---|---|---|---|---|
| 2024 | 2196 | +0.0548 | +0.0635 | +0.0629 | +0.0087 ± 0.0015 | +0.0081 ± 0.0014 |
| 2025 | 2190 | +0.0630 | +0.0683 | +0.0668 | +0.0053 ± 0.0010 | +0.0038 ± 0.0010 |
| 2026<=08-10 | 1332 | +0.0588 | +0.0594 | +0.0594 | +0.0006 ± 0.0009 | +0.0006 ± 0.0009 |
| 2026->08-30 | 1452 | +0.0584 | +0.0588 | +0.0586 | +0.0005 ± 0.0009 | +0.0003 ± 0.0008 |
| 2024->26 | 5838 | +0.0588 | +0.0642 | +0.0633 | +0.0054 ± 0.0007 | +0.0046 ± 0.0007 |
| 2025->26 | 3642 | +0.0612 | +0.0645 | +0.0636 | +0.0034 ± 0.0007 | +0.0024 ± 0.0007 |

### Yearly mean rank-IC vs dlw y4s = Π(1+r5)−1 over [E+1, E+48] (compounded holding-window target); identical anchor set for all sources (2024+, finite IC for every source)

| window | n | pinned | rollm | rollq | Δ rollm−pinned (mean ± SE) | Δ rollq−pinned (mean ± SE) |
|---|---|---|---|---|---|---|
| 2024 | 2196 | +0.0565 | +0.0661 | +0.0658 | +0.0096 ± 0.0015 | +0.0093 ± 0.0014 |
| 2025 | 2190 | +0.0671 | +0.0728 | +0.0711 | +0.0057 ± 0.0010 | +0.0040 ± 0.0010 |
| 2026<=08-10 | 1332 | +0.0640 | +0.0640 | +0.0642 | +0.0001 ± 0.0009 | +0.0002 ± 0.0009 |
| 2026->08-30 | 1332 | +0.0640 | +0.0640 | +0.0642 | +0.0001 ± 0.0009 | +0.0002 ± 0.0009 |
| 2024->26 | 5718 | +0.0623 | +0.0682 | +0.0675 | +0.0059 ± 0.0007 | +0.0052 ± 0.0007 |
| 2025->26 | 3522 | +0.0659 | +0.0695 | +0.0685 | +0.0036 ± 0.0007 | +0.0026 ± 0.0007 |

### King leg (production leg definition, bps per unit gross per anchor) — caliber raw y4; S = mean/std per anchor

| leg | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | S/anchor 900 pre-0810 (seat window) | S/anchor last 900 |
|---|---|---|---|---|---|---|---|---|
| king[pinned] | +1.533 (S +0.064, n 2196) | +2.381 (S +0.073, n 2190) | +3.197 (S +0.111, n 1332) | +3.130 (S +0.108, n 1452) | +2.248 (S +0.079, n 5838) | +2.680 (S +0.086, n 3642) | +0.1014 (mean +2.983) | +0.0953 (mean +2.828) |
| king[rollm] | +1.512 (S +0.059, n 2196) | +2.661 (S +0.079, n 2190) | +2.675 (S +0.094, n 1332) | +2.624 (S +0.093, n 1452) | +2.220 (S +0.075, n 5838) | +2.647 (S +0.084, n 3642) | +0.0796 (mean +2.287) | +0.0653 (mean +1.865) |
| king[rollq] | +1.804 (S +0.072, n 2196) | +2.793 (S +0.084, n 2190) | +3.096 (S +0.108, n 1332) | +2.994 (S +0.105, n 1452) | +2.471 (S +0.084, n 5838) | +2.873 (S +0.091, n 3642) | +0.1035 (mean +3.079) | +0.0946 (mean +2.804) |
| rev24 | +0.296 (S +0.010, n 2196) | +0.336 (S +0.009, n 2190) | +1.954 (S +0.058, n 1332) | +1.711 (S +0.051, n 1452) | +0.663 (S +0.020, n 5838) | +0.884 (S +0.026, n 3642) | +0.0386 (mean +1.298) | +0.0404 (mean +1.350) |
| fund | -0.361 (S -0.017, n 2196) | +1.712 (S +0.067, n 2190) | +6.344 (S +0.226, n 1332) | +5.520 (S +0.194, n 1452) | +1.879 (S +0.075, n 5838) | +3.230 (S +0.120, n 3642) | +0.2508 (mean +7.391) | +0.2017 (mean +6.105) |

### King leg (production leg definition, bps per unit gross per anchor) — caliber dlw y4s (windows restricted to anchors with a dlw row, i.e. ≤ 2026-08-10 20:00Z); S = mean/std per anchor

| leg | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | S/anchor 900 pre-0810 (seat window) | S/anchor last 900 |
|---|---|---|---|---|---|---|---|---|
| king[pinned] | +1.618 (S +0.067, n 2196) | +2.280 (S +0.071, n 2190) | +3.071 (S +0.105, n 1332) | +3.071 (S +0.105, n 1332) | +2.210 (S +0.077, n 5718) | +2.579 (S +0.083, n 3522) | +0.0994 (mean +2.965) | +0.0977 (mean +2.912) |
| king[rollm] | +1.517 (S +0.058, n 2196) | +2.531 (S +0.076, n 2190) | +2.413 (S +0.085, n 1332) | +2.413 (S +0.085, n 1332) | +2.114 (S +0.072, n 5718) | +2.486 (S +0.079, n 3522) | +0.0755 (mean +2.175) | +0.0739 (mean +2.125) |
| king[rollq] | +1.857 (S +0.073, n 2196) | +2.733 (S +0.083, n 2190) | +2.987 (S +0.103, n 1332) | +2.987 (S +0.103, n 1332) | +2.456 (S +0.084, n 5718) | +2.829 (S +0.090, n 3522) | +0.1001 (mean +2.981) | +0.1006 (mean +2.998) |
| rev24 | +0.384 (S +0.013, n 2196) | +0.378 (S +0.011, n 2190) | +2.121 (S +0.062, n 1332) | +2.121 (S +0.062, n 1332) | +0.786 (S +0.024, n 5718) | +1.037 (S +0.030, n 3522) | +0.0414 (mean +1.410) | +0.0420 (mean +1.431) |
| fund | -0.448 (S -0.020, n 2196) | +1.600 (S +0.061, n 2190) | +6.027 (S +0.210, n 1332) | +6.027 (S +0.210, n 1332) | +1.845 (S +0.072, n 5718) | +3.274 (S +0.120, n 3522) | +0.2291 (mean +6.935) | +0.2295 (mean +6.949) |

### msharpe seat at 2026-08-10 20:00Z (production rule, LOOK 900; w3 = king/rev24/fund; w101 = LEGS=101 mask = deployed combo form)

| caliber | king source | shp king/rev24/fund (mean/std) | w3 king/rev24/fund | w101 king/fund |
|---|---|---|---|---|
| raw | pinned | +0.1014/+0.0386/+0.2510 | 0.259/0.099/0.642 | **0.288**/0.712 |
| raw | rollm | +0.0797/+0.0386/+0.2510 | 0.216/0.105/0.680 | **0.241**/0.759 |
| raw | rollq | +0.1036/+0.0386/+0.2510 | 0.263/0.098/0.638 | **0.292**/0.708 |
| y4s | pinned | +0.0994/+0.0414/+0.2292 | 0.269/0.112/0.619 | **0.302**/0.698 |
| y4s | rollm | +0.0756/+0.0414/+0.2292 | 0.218/0.120/0.662 | **0.248**/0.752 |
| y4s | rollq | +0.1001/+0.0414/+0.2292 | 0.270/0.112/0.618 | **0.304**/0.696 |

### Book level — arm `d30_n2_c42`, column net_ex (bps/anchor per unit NAV); n=10038 anchors (identical set); windows: 2024=2196, 2025=2190, 2026<=08-10=1332, 2026->08-30=1452, 2024->26=5838, 2025->26=3642, 2024->26<=cut=5718, 2025->26<=cut=3522

#### Levels — caliber **log** = raw Σ-simple y4, CAL=log (no transform)

| arm | seed | king | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | gross | w_king | w_fund | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lfix | s42 | pinned | -0.642 S-1.68 DD1815 | +0.284 S+0.67 DD902 | +2.911 S+5.16 DD458 | +2.378 S+4.21 DD774 | +0.457 S+1.02 DD2614 | +1.119 S+2.31 DD902 | 0.791 | 0.210 | 0.790 | 0.01435 |
| Lfix | s42 | rollm | -0.625 S-1.68 DD1804 | +0.284 S+0.67 DD881 | +2.883 S+5.07 DD478 | +2.357 S+4.13 DD787 | +0.457 S+1.02 DD2578 | +1.110 S+2.28 DD881 | 0.789 | 0.210 | 0.790 | 0.01430 |
| Lfix | s42 | rollq | -0.625 S-1.67 DD1792 | +0.321 S+0.76 DD855 | +2.883 S+5.12 DD460 | +2.348 S+4.15 DD792 | +0.469 S+1.05 DD2545 | +1.129 S+2.33 DD855 | 0.789 | 0.210 | 0.790 | 0.01432 |
| Ldyn | s42 | pinned | +0.149 S+0.53 DD795 | +0.359 S+1.15 DD418 | +2.512 S+4.83 DD452 | +2.013 S+3.84 DD771 | +0.691 S+1.88 DD795 | +1.018 S+2.48 DD771 | 0.620 | 0.583 | 0.417 | 0.03335 |
| Ldyn | s42 | rollm | +0.094 S+0.33 DD925 | +0.344 S+1.11 DD472 | +2.603 S+4.88 DD479 | +2.104 S+3.91 DD801 | +0.688 S+1.85 DD925 | +1.046 S+2.51 DD801 | 0.611 | 0.616 | 0.384 | 0.03507 |
| Ldyn | s42 | rollq | +0.262 S+0.95 DD766 | +0.365 S+1.21 DD466 | +2.613 S+4.95 DD469 | +2.109 S+3.96 DD790 | +0.760 S+2.08 DD790 | +1.060 S+2.58 DD790 | 0.595 | 0.654 | 0.346 | 0.03666 |
| Ldyn | s2027 | pinned | +0.217 S+0.78 DD740 | +0.438 S+1.36 DD430 | +2.486 S+4.78 DD460 | +1.994 S+3.80 DD757 | +0.742 S+2.00 DD757 | +1.058 S+2.55 DD757 | 0.627 | 0.583 | 0.417 | 0.03261 |
| Ldyn | s2027 | rollm | +0.166 S+0.59 DD860 | +0.424 S+1.34 DD500 | +2.594 S+4.86 DD474 | +2.102 S+3.90 DD794 | +0.744 S+2.00 DD860 | +1.093 S+2.60 DD794 | 0.617 | 0.616 | 0.384 | 0.03416 |
| Ldyn | s2027 | rollq | +0.347 S+1.27 DD684 | +0.440 S+1.42 DD503 | +2.608 S+4.95 DD471 | +2.103 S+3.95 DD798 | +0.819 S+2.23 DD798 | +1.103 S+2.67 DD798 | 0.600 | 0.654 | 0.346 | 0.03573 |
| Cdyn | s42 | pinned | +0.255 S+0.86 DD719 | +0.436 S+1.25 DD503 | +2.373 S+4.61 DD395 | +1.893 S+3.64 DD727 | +0.730 S+1.91 DD727 | +1.017 S+2.39 DD727 | 0.671 | 0.588 | 0.412 | 0.03080 |
| Cdyn | s42 | rollm | +0.148 S+0.53 DD828 | +0.470 S+1.34 DD498 | +2.455 S+4.66 DD398 | +1.972 S+3.69 DD773 | +0.722 S+1.89 DD828 | +1.069 S+2.47 DD773 | 0.663 | 0.622 | 0.378 | 0.03264 |
| Cdyn | s42 | rollq | +0.284 S+1.05 DD731 | +0.418 S+1.21 DD514 | +2.295 S+4.41 DD412 | +1.806 S+3.42 DD784 | +0.713 S+1.89 DD784 | +0.971 S+2.27 DD784 | 0.647 | 0.659 | 0.341 | 0.03425 |

#### Levels — caliber **prod** = compounded Π(1+r5)−1 over [E+1,E+48] (meta_newprod swap), CAL=log

| arm | seed | king | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | gross | w_king | w_fund | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lfix | s42 | pinned | -0.709 S-1.85 DD1913 | +0.254 S+0.59 DD849 | +2.833 S+5.05 DD352 | +2.324 S+4.13 DD754 | +0.406 S+0.90 DD2657 | +1.079 S+2.21 DD849 | 0.788 | 0.210 | 0.790 | 0.01437 |
| Lfix | s42 | rollm | -0.697 S-1.86 DD1886 | +0.266 S+0.62 DD801 | +2.852 S+5.03 DD352 | +2.342 S+4.12 DD768 | +0.420 S+0.93 DD2588 | +1.094 S+2.23 DD801 | 0.787 | 0.210 | 0.790 | 0.01433 |
| Lfix | s42 | rollq | -0.686 S-1.82 DD1868 | +0.280 S+0.65 DD814 | +2.879 S+5.09 DD350 | +2.355 S+4.16 DD779 | +0.432 S+0.96 DD2580 | +1.107 S+2.26 DD814 | 0.787 | 0.210 | 0.790 | 0.01435 |
| Ldyn | s42 | pinned | +0.116 S+0.43 DD967 | +0.339 S+1.06 DD413 | +2.543 S+4.95 DD345 | +2.068 S+4.00 DD737 | +0.685 S+1.88 DD967 | +1.028 S+2.51 DD737 | 0.609 | 0.608 | 0.392 | 0.03480 |
| Ldyn | s42 | rollm | +0.116 S+0.42 DD906 | +0.344 S+1.11 DD462 | +2.603 S+4.93 DD358 | +2.117 S+3.98 DD777 | +0.699 S+1.90 DD906 | +1.051 S+2.54 DD777 | 0.603 | 0.630 | 0.370 | 0.03592 |
| Ldyn | s42 | rollq | +0.339 S+1.26 DD675 | +0.364 S+1.20 DD460 | +2.626 S+5.08 DD368 | +2.130 S+4.08 DD778 | +0.794 S+2.21 DD778 | +1.068 S+2.64 DD778 | 0.582 | 0.674 | 0.326 | 0.03772 |
| Ldyn | s2027 | pinned | +0.197 S+0.73 DD896 | +0.399 S+1.22 DD446 | +2.524 S+4.92 DD364 | +2.058 S+3.98 DD730 | +0.736 S+2.00 DD896 | +1.060 S+2.56 DD730 | 0.616 | 0.608 | 0.392 | 0.03408 |
| Ldyn | s2027 | rollm | +0.214 S+0.79 DD806 | +0.404 S+1.27 DD484 | +2.641 S+4.99 DD359 | +2.155 S+4.04 DD773 | +0.768 S+2.08 DD806 | +1.102 S+2.64 DD773 | 0.609 | 0.630 | 0.370 | 0.03500 |
| Ldyn | s2027 | rollq | +0.420 S+1.59 DD599 | +0.417 S+1.34 DD503 | +2.629 S+5.09 DD366 | +2.135 S+4.10 DD775 | +0.845 S+2.34 DD775 | +1.102 S+2.70 DD775 | 0.587 | 0.674 | 0.326 | 0.03681 |
| Cdyn | s42 | pinned | +0.232 S+0.82 DD797 | +0.471 S+1.31 DD512 | +2.271 S+4.43 DD336 | +1.833 S+3.54 DD704 | +0.720 S+1.89 DD797 | +1.014 S+2.36 DD704 | 0.658 | 0.617 | 0.383 | 0.03243 |
| Cdyn | s42 | rollm | +0.169 S+0.64 DD787 | +0.487 S+1.38 DD507 | +2.265 S+4.30 DD341 | +1.821 S+3.42 DD760 | +0.699 S+1.84 DD787 | +1.019 S+2.35 DD760 | 0.652 | 0.639 | 0.361 | 0.03345 |
| Cdyn | s42 | rollq | +0.379 S+1.46 DD568 | +0.446 S+1.28 DD499 | +2.160 S+4.17 DD343 | +1.718 S+3.28 DD751 | +0.737 S+1.98 DD751 | +0.953 S+2.23 DD751 | 0.631 | 0.682 | 0.318 | 0.03521 |

#### Deltas (king − pinned) — caliber **log**; paired anchors; UTC-day-block bootstrap 2000×, seed 20260905; cell = Δ [CI95] P(Δ>0)

| arm | seed | king | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | **2024→26** | 2025→26 | 2024→26≤cut | 2025→26≤cut | ΔSharpe 24on/25on | turnover pin→king (Δ%) | Δ mean w_king | maxDD pin/king (24on) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lfix | s42 | rollm | +0.017 [-0.037,+0.069] 0.72 | -0.001 [-0.074,+0.069] 0.49 | -0.028 [-0.151,+0.090] 0.33 | -0.021 [-0.146,+0.096] 0.35 | **+0.001 [-0.042,+0.043] 0.54** | -0.009 [-0.076,+0.058] 0.39 | -0.000 [-0.045,+0.044] 0.48 | -0.011 [-0.078,+0.051] 0.36 | +0.01/-0.03 | 0.01435→0.01430 (-0.3%) | +0.000 | 2614/2578 |
| Lfix | s42 | rollq | +0.017 [-0.037,+0.069] 0.73 | +0.036 [-0.043,+0.113] 0.81 | -0.028 [-0.122,+0.068] 0.29 | -0.030 [-0.124,+0.059] 0.27 | **+0.012 [-0.030,+0.054] 0.72** | +0.010 [-0.050,+0.069] 0.62 | +0.014 [-0.029,+0.054] 0.75 | +0.012 [-0.049,+0.072] 0.65 | +0.03/+0.02 | 0.01435→0.01432 (-0.2%) | +0.000 | 2614/2545 |
| Ldyn | s42 | rollm | -0.055 [-0.288,+0.181] 0.34 | -0.015 [-0.140,+0.116] 0.42 | +0.091 [-0.060,+0.245] 0.88 | +0.090 [-0.057,+0.230] 0.90 | **-0.004 [-0.108,+0.100] 0.47** | +0.027 [-0.067,+0.124] 0.70 | -0.006 [-0.110,+0.102] 0.48 | +0.025 [-0.065,+0.117] 0.69 | -0.03/+0.03 | 0.03335→0.03507 (+5.2%) | +0.033 | 795/925 |
| Ldyn | s42 | rollq | +0.113 [-0.162,+0.386] 0.78 | +0.006 [-0.127,+0.142] 0.56 | +0.102 [-0.057,+0.256] 0.89 | +0.096 [-0.054,+0.245] 0.90 | **+0.069 [-0.051,+0.197] 0.88** | +0.042 [-0.059,+0.137] 0.79 | +0.070 [-0.056,+0.194] 0.85 | +0.043 [-0.057,+0.141] 0.80 | +0.19/+0.10 | 0.03335→0.03666 (+9.9%) | +0.071 | 795/790 |
| Ldyn | s2027 | rollm | -0.051 [-0.286,+0.180] 0.33 | -0.014 [-0.136,+0.114] 0.41 | +0.108 [-0.016,+0.239] 0.95 | +0.108 [-0.012,+0.240] 0.96 | **+0.003 [-0.106,+0.112] 0.52** | +0.035 [-0.061,+0.131] 0.77 | +0.000 [-0.103,+0.105] 0.49 | +0.033 [-0.063,+0.126] 0.73 | -0.01/+0.05 | 0.03261→0.03416 (+4.7%) | +0.033 | 757/860 |
| Ldyn | s2027 | rollq | +0.130 [-0.165,+0.403] 0.80 | +0.003 [-0.126,+0.136] 0.50 | +0.122 [-0.027,+0.280] 0.94 | +0.110 [-0.032,+0.262] 0.94 | **+0.077 [-0.049,+0.199] 0.90** | +0.045 [-0.056,+0.148] 0.82 | +0.079 [-0.045,+0.204] 0.90 | +0.048 [-0.052,+0.151] 0.82 | +0.23/+0.12 | 0.03261→0.03573 (+9.6%) | +0.071 | 757/798 |
| Cdyn | s42 | rollm | -0.107 [-0.331,+0.136] 0.20 | +0.033 [-0.110,+0.175] 0.68 | +0.082 [-0.104,+0.257] 0.82 | +0.079 [-0.083,+0.250] 0.82 | **-0.008 [-0.122,+0.110] 0.45** | +0.051 [-0.062,+0.161] 0.81 | -0.009 [-0.127,+0.101] 0.43 | +0.052 [-0.058,+0.163] 0.83 | -0.02/+0.08 | 0.03080→0.03264 (+6.0%) | +0.035 | 727/828 |
| Cdyn | s42 | rollq | +0.029 [-0.251,+0.307] 0.57 | -0.018 [-0.158,+0.126] 0.39 | -0.079 [-0.252,+0.103] 0.19 | -0.087 [-0.254,+0.076] 0.17 | **-0.018 [-0.145,+0.106] 0.39** | -0.046 [-0.158,+0.062] 0.19 | -0.014 [-0.148,+0.111] 0.44 | -0.041 [-0.148,+0.072] 0.24 | -0.02/-0.12 | 0.03080→0.03425 (+11.2%) | +0.072 | 727/784 |

#### Deltas (king − pinned) — caliber **prod**; paired anchors; UTC-day-block bootstrap 2000×, seed 20260905; cell = Δ [CI95] P(Δ>0)

| arm | seed | king | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | **2024→26** | 2025→26 | 2024→26≤cut | 2025→26≤cut | ΔSharpe 24on/25on | turnover pin→king (Δ%) | Δ mean w_king | maxDD pin/king (24on) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lfix | s42 | rollm | +0.012 [-0.038,+0.062] 0.67 | +0.012 [-0.077,+0.099] 0.60 | +0.019 [-0.111,+0.154] 0.62 | +0.018 [-0.114,+0.141] 0.61 | **+0.014 [-0.036,+0.065] 0.70** | +0.015 [-0.058,+0.088] 0.64 | +0.014 [-0.034,+0.066] 0.71 | +0.015 [-0.057,+0.090] 0.66 | +0.03/+0.02 | 0.01437→0.01433 (-0.3%) | +0.000 | 2657/2588 |
| Lfix | s42 | rollq | +0.022 [-0.028,+0.072] 0.80 | +0.026 [-0.059,+0.118] 0.69 | +0.046 [-0.048,+0.138] 0.83 | +0.032 [-0.057,+0.120] 0.77 | **+0.026 [-0.018,+0.073] 0.87** | +0.028 [-0.035,+0.096] 0.80 | +0.029 [-0.014,+0.072] 0.90 | +0.034 [-0.029,+0.102] 0.84 | +0.06/+0.06 | 0.01437→0.01435 (-0.2%) | +0.000 | 2657/2580 |
| Ldyn | s42 | rollm | +0.001 [-0.219,+0.226] 0.51 | +0.005 [-0.135,+0.155] 0.54 | +0.061 [-0.088,+0.218] 0.79 | +0.049 [-0.100,+0.208] 0.74 | **+0.014 [-0.094,+0.120] 0.60** | +0.023 [-0.081,+0.125] 0.67 | +0.016 [-0.094,+0.127] 0.59 | +0.026 [-0.077,+0.134] 0.70 | +0.02/+0.03 | 0.03480→0.03592 (+3.2%) | +0.022 | 967/906 |
| Ldyn | s42 | rollq | +0.224 [-0.036,+0.491] 0.94 | +0.025 [-0.121,+0.177] 0.65 | +0.084 [-0.074,+0.240] 0.86 | +0.062 [-0.083,+0.208] 0.78 | **+0.109 [-0.012,+0.232] 0.96** | +0.040 [-0.071,+0.146] 0.77 | +0.115 [-0.011,+0.238] 0.96 | +0.047 [-0.059,+0.158] 0.81 | +0.33/+0.13 | 0.03480→0.03772 (+8.4%) | +0.067 | 967/778 |
| Ldyn | s2027 | rollm | +0.017 [-0.202,+0.243] 0.56 | +0.006 [-0.133,+0.154] 0.53 | +0.116 [-0.031,+0.260] 0.94 | +0.097 [-0.048,+0.223] 0.91 | **+0.033 [-0.077,+0.143] 0.74** | +0.042 [-0.059,+0.145] 0.79 | +0.036 [-0.068,+0.137] 0.74 | +0.048 [-0.055,+0.154] 0.80 | +0.07/+0.08 | 0.03408→0.03500 (+2.7%) | +0.022 | 896/806 |
| Ldyn | s2027 | rollq | +0.223 [-0.055,+0.515] 0.94 | +0.018 [-0.126,+0.173] 0.60 | +0.105 [-0.047,+0.264] 0.91 | +0.077 [-0.080,+0.225] 0.84 | **+0.110 [-0.018,+0.246] 0.96** | +0.042 [-0.067,+0.147] 0.76 | +0.117 [-0.011,+0.245] 0.96 | +0.051 [-0.060,+0.169] 0.82 | +0.34/+0.14 | 0.03408→0.03681 (+8.0%) | +0.067 | 896/775 |
| Cdyn | s42 | rollm | -0.063 [-0.302,+0.167] 0.28 | +0.016 [-0.126,+0.161] 0.60 | -0.006 [-0.224,+0.181] 0.47 | -0.013 [-0.223,+0.189] 0.46 | **-0.021 [-0.134,+0.095] 0.38** | +0.005 [-0.111,+0.122] 0.53 | -0.019 [-0.138,+0.098] 0.36 | +0.008 [-0.111,+0.133] 0.56 | -0.05/-0.02 | 0.03243→0.03345 (+3.1%) | +0.022 | 797/787 |
| Cdyn | s42 | rollq | +0.147 [-0.140,+0.420] 0.86 | -0.025 [-0.165,+0.111] 0.34 | -0.111 [-0.368,+0.127] 0.17 | -0.115 [-0.352,+0.098] 0.14 | **+0.017 [-0.113,+0.141] 0.61** | -0.061 [-0.188,+0.066] 0.16 | +0.021 [-0.117,+0.156] 0.62 | -0.058 [-0.189,+0.064] 0.18 | +0.09/-0.13 | 0.03243→0.03521 (+8.6%) | +0.064 | 797/751 |

#### σ_fund terciles of Δ (2024→26). Definition: std over meta members (finite f_fund_now) of f_fund_now*8/ivf, *1e4 bps/8h; trailing 30-anchor mean (>=15 valid); terciles over 2024->26 anchors. Cuts 5.45 / 13.67 bps; n per tercile [1946, 1946, 1946]; mean σ_fund per tercile [3.237, 9.56, 21.086]

| caliber | arm | seed | king | low σ_fund: Δ [CI95] P (pinned→king) | mid | high |
|---|---|---|---|---|---|---|
| log | Lfix | s42 | rollm | +0.029 [-0.025,+0.083] P0.86 (-0.786→-0.756, n1946) | +0.015 [-0.051,+0.078] P0.67 (+0.130→+0.145, n1946) | -0.042 [-0.158,+0.061] P0.21 (+2.025→+1.983, n1946) |
| log | Lfix | s42 | rollq | +0.026 [-0.027,+0.081] P0.82 (-0.786→-0.760, n1946) | +0.010 [-0.070,+0.086] P0.60 (+0.130→+0.140, n1946) | +0.001 [-0.082,+0.090] P0.52 (+2.025→+2.027, n1946) |
| log | Ldyn | s42 | rollm | -0.025 [-0.255,+0.214] P0.40 (+0.084→+0.059, n1946) | +0.075 [-0.081,+0.236] P0.83 (+0.765→+0.840, n1946) | -0.061 [-0.199,+0.078] P0.21 (+1.225→+1.164, n1946) |
| log | Ldyn | s42 | rollq | +0.110 [-0.186,+0.398] P0.79 (+0.084→+0.194, n1946) | +0.103 [-0.052,+0.260] P0.90 (+0.765→+0.868, n1946) | -0.007 [-0.153,+0.134] P0.49 (+1.225→+1.219, n1946) |
| log | Ldyn | s2027 | rollm | -0.021 [-0.258,+0.229] P0.45 (+0.136→+0.115, n1946) | +0.074 [-0.079,+0.231] P0.82 (+0.821→+0.895, n1946) | -0.046 [-0.176,+0.080] P0.22 (+1.268→+1.222, n1946) |
| log | Ldyn | s2027 | rollq | +0.123 [-0.167,+0.406] P0.79 (+0.136→+0.259, n1946) | +0.079 [-0.072,+0.235] P0.85 (+0.821→+0.900, n1946) | +0.029 [-0.109,+0.172] P0.65 (+1.268→+1.297, n1946) |
| log | Cdyn | s42 | rollm | -0.026 [-0.265,+0.219] P0.43 (+0.144→+0.118, n1946) | +0.035 [-0.135,+0.192] P0.65 (+0.897→+0.932, n1946) | -0.033 [-0.205,+0.132] P0.35 (+1.150→+1.116, n1946) |
| log | Cdyn | s42 | rollq | +0.075 [-0.235,+0.363] P0.68 (+0.144→+0.220, n1946) | -0.003 [-0.169,+0.151] P0.48 (+0.897→+0.895, n1946) | -0.126 [-0.290,+0.043] P0.07 (+1.150→+1.024, n1946) |
| prod | Lfix | s42 | rollm | +0.033 [-0.018,+0.092] P0.90 (-0.855→-0.822, n1946) | +0.038 [-0.029,+0.108] P0.85 (+0.080→+0.118, n1946) | -0.030 [-0.150,+0.099] P0.30 (+1.995→+1.965, n1946) |
| prod | Lfix | s42 | rollq | +0.035 [-0.019,+0.089] P0.91 (-0.855→-0.820, n1946) | +0.007 [-0.062,+0.081] P0.57 (+0.080→+0.087, n1946) | +0.036 [-0.072,+0.138] P0.75 (+1.995→+2.030, n1946) |
| prod | Ldyn | s42 | rollm | +0.050 [-0.177,+0.278] P0.66 (+0.017→+0.068, n1946) | +0.060 [-0.112,+0.231] P0.76 (+0.765→+0.825, n1946) | -0.067 [-0.213,+0.074] P0.19 (+1.273→+1.206, n1946) |
| prod | Ldyn | s42 | rollq | +0.250 [-0.034,+0.536] P0.96 (+0.017→+0.267, n1946) | +0.081 [-0.081,+0.253] P0.82 (+0.765→+0.845, n1946) | -0.004 [-0.145,+0.145] P0.48 (+1.273→+1.269, n1946) |
| prod | Ldyn | s2027 | rollm | +0.066 [-0.175,+0.305] P0.72 (+0.083→+0.149, n1946) | +0.078 [-0.086,+0.252] P0.82 (+0.818→+0.896, n1946) | -0.046 [-0.189,+0.096] P0.27 (+1.306→+1.260, n1946) |
| prod | Ldyn | s2027 | rollq | +0.243 [-0.059,+0.530] P0.95 (+0.083→+0.326, n1946) | +0.095 [-0.069,+0.264] P0.86 (+0.818→+0.913, n1946) | -0.008 [-0.165,+0.162] P0.47 (+1.306→+1.298, n1946) |
| prod | Cdyn | s42 | rollm | +0.023 [-0.221,+0.264] P0.59 (+0.113→+0.135, n1946) | +0.015 [-0.163,+0.175] P0.56 (+0.917→+0.931, n1946) | -0.100 [-0.278,+0.071] P0.13 (+1.130→+1.030, n1946) |
| prod | Cdyn | s42 | rollq | +0.181 [-0.121,+0.479] P0.88 (+0.113→+0.294, n1946) | +0.020 [-0.154,+0.197] P0.61 (+0.917→+0.937, n1946) | -0.150 [-0.356,+0.035] P0.06 (+1.130→+0.980, n1946) |

## 3. Decision under the frozen criteria (PREREG §3; evaluated by `judge.py`, quoted verbatim above)

### Frozen decision (rendered verbatim from `judge.json`)

**rollm** (PRIMARY (frozen criteria)): **UNDECIDED**
- log: L-fix 2024→26 Δ 0.0007 CI [-0.0417, 0.0432] lower>0=False; 2025→26 Δ -0.009 ≥0=False; yearly Δ [0.0167, -0.0007, -0.0215] worst -0.0215 ≥−0.05=True; Δturn -0.3% ≤15=True; L-dyn s42/s2027 Δ [-0.0037, 0.0026] both≥0=False; REJECT flags: CI upper<0=False, turn>25%=False
- prod: L-fix 2024→26 Δ 0.0139 CI [-0.0359, 0.0649] lower>0=False; 2025→26 Δ 0.0148 ≥0=True; yearly Δ [0.0123, 0.0124, 0.0185] worst 0.0123 ≥−0.05=True; Δturn -0.33% ≤15=True; L-dyn s42/s2027 Δ [0.0144, 0.0328] both≥0=True; REJECT flags: CI upper<0=False, turn>25%=False

**rollq** (shape check only (not for selection)): **UNDECIDED**
- log: L-fix 2024→26 Δ 0.0124 CI [-0.0297, 0.0545] lower>0=False; 2025→26 Δ 0.0096 ≥0=True; yearly Δ [0.017, 0.0362, -0.0305] worst -0.0305 ≥−0.05=True; Δturn -0.21% ≤15=True; L-dyn s42/s2027 Δ [0.0688, 0.0771] both≥0=True; REJECT flags: CI upper<0=False, turn>25%=False
- prod: L-fix 2024→26 Δ 0.0261 CI [-0.0184, 0.0728] lower>0=False; 2025→26 Δ 0.0283 ≥0=True; yearly Δ [0.0224, 0.0261, 0.0317] worst 0.0224 ≥−0.05=True; Δturn -0.18% ≤15=True; L-dyn s42/s2027 Δ [0.1089, 0.1099] both≥0=True; REJECT flags: CI upper<0=False, turn>25%=False


**rollm (monthly, PRIMARY): UNDECIDED in both calibers.**
- ADMIT requires, for both calibers, L-fix 2024→26 CI95 lower > 0: **fails** (raw: [−0.042, +0.043]; compounded: [−0.036, +0.065]). Also fails under raw: 2025→26 Δ = −0.009 (< 0) and L-dyn seeds straddle zero (−0.004 / +0.003). Passes: worst-year Δ ≥ −0.05 (raw worst −0.022; compounded worst +0.012); turnover −0.3% (≤ +15%); under compounded: 2025→26 +0.015 ≥ 0 and L-dyn both seeds ≥ 0 (+0.014 / +0.033).
- REJECT requires CI95 upper < 0 or turnover > +25% in either caliber: **neither** (uppers +0.043 / +0.065; turnover −0.3%).
- Hence UNDECIDED. Per the prereg this means: record, do not deploy.

**rollq (quarterly, shape check only, not for selection): UNDECIDED** (L-fix +0.012 [−0.030, +0.054] raw / +0.026 [−0.018, +0.073] compounded; L-dyn +0.069/+0.077 raw, +0.109/+0.110 compounded with P ≈ 0.96 but CI including 0; C-dyn −0.018 raw / +0.017 compounded and **2025→26 −0.046 / −0.061**). Choosing the quarterly fold length on these numbers would be exactly the result-driven selection the prereg forbids; the ordering monthly-vs-quarterly also reverses across arms (L-dyn favours quarterly, C-dyn 2025→26 disfavours it), which is what noise looks like.

## 4. Reading (INFERRED from the verified tables; not part of the criteria)

1. **Freshness buys rank-IC only where the pinned fold is stale and small.** The pinned 2024 fold is trained on 2022–23 only (two years) and is up to 12 months stale by December 2024; there rollm gains +0.009 rank-IC (monthly table: 2024-10/11/12 pinned +0.064/+0.068/+0.044 vs rollm +0.080/+0.085/+0.067). The pinned 2026 booster is trained on 2022–25 (four years) and is 8 months stale by August 2026, yet rollm shows no gain in any 2026 month (2026-07: +0.064/+0.064; 2026-08: +0.049/+0.046). So the gain looks like a small-training-set effect of the early year-folds, not a "the market moved and the tree is behind" effect (the user's hypothesis) — at least not at the 4-year training length the production bundle now has.
2. **Rank-IC gain ≠ leg gain.** The production leg return is Σ z·y with z = centred ranks (unit gross), i.e. the *raw-return*-weighted rank correlation; it is dominated by the names that move most. In 2026 rollm's Spearman IC equals pinned's, but its leg is −0.52 (raw) / −0.66 (compounded) bps per unit gross lower — a rank-vs-value divergence of the same family as `rank_ic_positive_value_ic_zero` (memory). Mechanism not decomposed here (UNRESOLVED U1).
3. **Mechanical book cap at the live seat.** With W3FIX 0.21 king in the king book and PHI 0.45 (F10 book 45%), the king leg's share of the blended target is ≈ 0.21 × 0.55 ≈ 0.12 before EMA/cap/stop layers (arithmetic, INFERRED). A king-leg Δ of −0.5 bps per unit gross × ~0.12 × gross ~0.79 ≈ −0.05 bps/anchor on the book, which is the order of the observed 2026≤08-10 L-fix Δ (−0.028 raw). The CI half-width of the primary test (±0.04) is therefore the resolution of the instrument for a king-only change, consistent with the "模型腿机械上限=席位≤0.21" result: **no king-model change can be admitted or rejected through the book at the live seat with this history length; the leg-level tables are the informative ones, and they are negative in 2026.**
4. **Dynamic seats do not rescue it.** The msharpe rule gives rollm a slightly larger *average* king seat over 2024→26 (+0.033; its 2025 leg is better) but a smaller seat at the current date (0.241 vs 0.288) because the rule sees its 2026 leg Sharpe/anchor at 0.080 vs 0.101. Turnover rises +3–5% on the dynamic arms because monthly refits reshuffle the ranking more often; net effect on net_ex ≈ 0 (all CIs include 0).
5. **σ_fund regimes.** L-fix Δ by σ_fund tercile (2024→26): low-σ_fund +0.029 [−0.025, +0.083] P 0.86 (raw) / +0.033 P 0.90 (compounded); mid +0.015 / +0.038; high −0.042 [−0.158, +0.061] P 0.21 / −0.030 P 0.30. Mild "helps when fund is weak, hurts when fund is strong" shape, every CI including 0 — informational only.
6. **Reconciliation with `RESULT_rolling_king_2026-09-04`** (different recipe: 171 columns, residual target, quarterly, jpline hist king, CAL=simple; its "IC↑ 书↓ −0.17~−0.20 CI<0, turnover +20%" was voided pending CAL=log). With the production recipe under both correct calibers: IC↑ survives at a smaller size (+0.005 pooled), the significant book *loss* does **not** reappear (book Δ ≈ 0, CIs ±0.04 fixed / ±0.1 dynamic), and turnover is +3–5% on dynamic seats, −0.3% at the fixed seat. The direction "IC up, book not up" is the surviving statement; its earlier magnitude was device-specific.
7. **Levels sanity (VERIFIED against prior receipts):** L-fix pinned under raw y4 reproduces the 09-04 fixed-seat reading bitwise (2024 −0.642 S −1.68 maxDD 1815; 2024→26 +0.457, Sharpe 1.02, cross-year maxDD 2614 bps ≈ 33%/gross), and the king-leg row under the compounded target (+1.62 / +2.28 / +3.07, seat-window Sharpe/anchor 0.099) reproduces the STATE.md E-0904-F figures — so this device is the same instrument the live-seat receipts came from.

## 5. Unresolved / caveats
- **U1** Why the 2026 rank-IC gain of zero coincides with a −0.5 to −0.7 bps/gross king-leg loss (rank-vs-value divergence) — no value-IC / tail decomposition was run.
- **U2** One seed per fold (20260905 + fold index); the fold-to-fold seed sensitivity of `slow_pred_rollm.npy` is not measured. A second seed family would bound it (that is a robustness check, not an ensemble) — not run, not requested.
- **U3** Fold boosters are not expected to be bitwise equal to a production retrain of the same window (production: `deterministic: 0`, 100 threads, seed unset); the recipe is reproduced, not the bits.
- **U4** F10 predictions end 2026-08-10 20:00Z; for the last 120 replayed anchors the F10 sub-book is fund-only for every king source (Δ there comes from the king book alone). Both the full 2024→26 window (primary) and the ≤cut variant are reported; they agree (+0.001 vs −0.000 raw; +0.014 vs +0.014 compounded).
- **U5** All three king files are NaN before 2024, so the king leg return is 0 inside the msharpe window until mid-2024 and the dynamic arms' 2024 rows carry the seat ramp-in artifact (identical construction for all sources; the paired Δ removes most of it, not all).
- **U6** The live seat 0.21 (W3FIX whitelist) is not the seat this replay's rule computes at 2026-08-10 (0.288 for pinned); the live seat is seeded from the bundle's `leg_returns.npz` plus producer-appended rows and was not reproduced here.
- **U7** Multiple comparisons: 3 arms × 2 calibers × ≤2 seeds × 8 windows × 2 king sources, unadjusted; the rollq L-dyn P ≈ 0.96 cells are per-comparison and shape-check only.
- **U8** `dlw_targets.npz` has no rows after 2026-08-10 20:00Z; the y4s IC/leg tables are restricted to anchors with a dlw row (n printed), while the compounded-target *device* runs use `meta_newprod.npz`, which is built from the 5m panel and covers all anchors to 2026-08-30 (refuters' assertion `r+49 <= len(CTS)` passed; parity with dlw y4s bitwise on the 10,056 common anchors).
- **U9** The comparator is the pod production king (training from 2022-01, exporter L49), not the 2020-start hist king (E-0905-A); jpline was down, so no hist-king baseline was run. The prereg's 作废条件 (assert / equivalence) are both satisfied; a hist-king re-run would be a different comparator, not a voiding.
- **U11** Process hygiene: the rollm/rollq arm sets ran twice into identical paths (§1.3); resolved by the bitwise `_v` re-run receipt, so `commands.txt` carries each of those 16 commands twice plus the `_v` copies.
- **U10** The D1 train-rule tightening (one grid step, §1.1) was decided before any number existed and is self-reported in the training CONFIG line; it changes the training set by ≈330 rows per fold.

## 6. Artifacts
- Pod: `/workspace/review_scratch/rolling_king/` — `pod_king_rolling_monthly.py` (sha256 38d65533…), `slow_pred_rollm.npy` (999f7d4d…), `slow_pred_rollq.npy` (a67d666b…), `folds_rollm.json`, `folds_rollq.json`, `pod_king_ic_legs.py` → `ic_legs_seat.json`, `legs_by_king.npz`, `judge.py` → `judge.json`, `render_tables.py` → `REPORT_tables.md`, `check_pinned_equiv.py`, `verify_rerun.sh` → `logs/verify_rerun.log`, `setup_dev.sh`, `run_arms.sh`, `chain_arms.sh`, `w10_universe_recheck.py` (5424aceb…), `dev/` and `dev_alt/` (layouts + `probe_artifacts/` 25 series npz + 16 `_v` re-run copies + `logs/`), `logs/` (rollm.log, rollq.log, the two attempt-1 assert-fail logs, ic_legs.log, judge.log, check_pinned_equiv.log, verify_rerun.log, setup_dev.log, run_arms_*.out, chain_arms.out, commands.txt), `REPORT.md`.
- Mac: `…/scratchpad/review_caliber/rolling_king/` — the same scripts, `REPORT_tables.md`, `judge.json`, `ic_legs_seat.json`, `folds_rollm.json`, `folds_rollq.json`, `REPORT.md`.

## 7. Receipts and commands (verbatim)

### Receipts (verbatim log lines)

`logs/setup_dev.log`:
```
--- sha256 (my copy / combo_recheck copy / port original)
5424aceb34b4595b8b9be0d720e90a60e1944fd9bb915fad4c934bc4cf59e9f9  /workspace/review_scratch/rolling_king/w10_universe_recheck.py
5424aceb34b4595b8b9be0d720e90a60e1944fd9bb915fad4c934bc4cf59e9f9  /workspace/review_scratch/combo_recheck/w10_universe_recheck.py
64c70a44ee88b79547a444ccb969c58d17d3a25f2f02af9cc77055b767bfe430  /workspace/port_w10/w10_universe.py
--- diff port original vs my copy (expected: REF_SKIP guard only)
43c43,44
---
325c326,328
---
--- layout
--- resolved targets
--- meta_newprod sha256 + refuters' parity receipt
831857dd6a2035235647158d26d0155d17c7e77d85fa248b2ae9a617658ddf13  /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz
```

`dev/logs/eq_livefix_pinned_callog.log`:
```
CONFIG {"REF_SKIP": 0, "KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": "0.21,0,0.79", "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPR
MEMBERS_TOPN=829: members rebuilt from qvk ranking
SLOW override: /workspace/shadow_bundle_v3/slow_pred_pinned.npy finite 0.241
F10 OOS preds aligned: rows 10056/10176, cols 829/829, finite 0.2838
NOTE S0: arm anchors 10038 vs ref 1 (差 -10037), 仅比较共同年份
NOTE d30_n2_c42: arm anchors 10038 vs ref 1 (差 -10037), 仅比较共同年份
RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.1584, "net_ex_2024on": 0.4566, "sharpe_ex_2024on": 1.017, "by_year_ex": {"2022": -0.12, "2023": -0.381, "2024": -0.642, "2025": 0.284, "2026": 2.378}, "carry_ex_mean": 0.5053, "cost_ex_mean": 0.0401, "turnover_ex_mean": 0.0401, "netlong_mean": -0.0466, "netlong_by_year": {"2022": -0.0382, "2023": -0.0113, "2024": -0.0244, "2025": -0.0978, "2026": -0.0676}}
DONE 118.1 s
```

`logs/check_pinned_equiv.log`:
```
PASS dev/probe_artifacts/w10_ablation_series_Lfix_pinned_log_s42.npz vs /workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz: {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal(minus REF_SKIP)=True sha(mine)=d02a9724b948e36b sha(ref)=5faf9106ed84dc8f
PASS dev/probe_artifacts/w10_ablation_series_Ldyn_pinned_log_s42.npz vs /workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s42.npz: {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal(minus REF_SKIP)=True sha(mine)=5cd88da0ab1301b9 sha(ref)=dd85ded80c7af058
PASS dev/probe_artifacts/w10_ablation_series_Ldyn_pinned_log_s2027.npz vs /workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s2027.npz: {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal(minus REF_SKIP)=True sha(mine)=0c1c2d791723918b sha(ref)=634ea0dcd7c3ac7a
PASS dev/probe_artifacts/w10_ablation_series_Cdyn_pinned_log_s42.npz vs /workspace/port_w10/probe_artifacts/w10_ablation_series_pod_canon_callog_s42.npz: {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal(minus REF_SKIP)=True sha(mine)=e25b96b423e1da5a sha(ref)=e80c957d949e3247
PASS dev_alt/probe_artifacts/w10_ablation_series_Lfix_pinned_prod_s42.npz vs /workspace/review_scratch/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_w3fix.npz: {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal(minus REF_SKIP)=True sha(mine)=198e0f1ef69478fd sha(ref)=aa5771a803a880ba
PASS dev_alt/probe_artifacts/w10_ablation_series_Ldyn_pinned_prod_s42.npz vs /workspace/review_scratch/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_dyn.npz: {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal(minus REF_SKIP)=True sha(mine)=e3efd781a0d97f02 sha(ref)=b95c1553ee0bce10
PASS dev_alt/probe_artifacts/w10_ablation_series_Cdyn_pinned_prod_s42.npz vs /workspace/review_scratch/combo_recheck/dev_alt/probe_artifacts/w10_ablation_series_D_prod_s42.npz: {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal(minus REF_SKIP)=True sha(mine)=5deff2411189cbed sha(ref)=5deff2411189cbed
ALL_PINNED_EQUIV True
NEW (no pre-existing counterpart): dev_alt/probe_artifacts/w10_ablation_series_Ldyn_pinned_prod_s2027.npz exists = True
```

`logs/verify_rerun.log`:
```
VERIFY_RERUN_DONE 2026-09-04T20:24:11Z
PASS Lfix_rollm_log_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollm_log_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollm_log_s2027: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Cdyn_rollm_log_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Lfix_rollm_prod_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollm_prod_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollm_prod_s2027: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Cdyn_rollm_prod_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Lfix_rollq_log_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollq_log_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollq_log_s2027: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Cdyn_rollq_log_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Lfix_rollq_prod_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollq_prod_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Ldyn_rollq_prod_s2027: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
PASS Cdyn_rollq_prod_s42: stored vs rerun {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} config_equal=True
ALL_RERUN_EQUAL True n 16
```

### Commands (verbatim, `logs/commands.txt`)
```
CMD[train] 2026-09-04T17:20:22Z: cd /workspace/review_scratch/rolling_king && nohup bash -c "MODE=monthly NJOBS=48 /workspace/venv/bin/python pod_king_rolling_monthly.py > logs/rollm.log 2>&1; MODE=quarterly NJOBS=48 /workspace/venv/bin/python pod_king_rolling_monthly.py > logs/rollq.log 2>&1" > logs/nohup_train.out 2>&1 &
CMD[setup] 2026-09-04T17:24:06Z: bash /workspace/review_scratch/rolling_king/setup_dev.sh
CMD[train-relaunch D1] 2026-09-04T17:24:24Z: cd /workspace/review_scratch/rolling_king && nohup bash -c "MODE=monthly NJOBS=48 /workspace/venv/bin/python pod_king_rolling_monthly.py > logs/rollm.log 2>&1; MODE=quarterly NJOBS=48 /workspace/venv/bin/python pod_king_rolling_monthly.py > logs/rollq.log 2>&1" > logs/nohup_train.out 2>&1 &
CMD[eq_livefix_pinned_callog] (cwd=/workspace/review_scratch/rolling_king/dev) 2026-09-04T17:26:21Z: env SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy LEGS=101 LOOK=900 WRULE=msharpe CAL=log FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=eq_livefix_pinned_callog /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[ic_legs smoke pinned-only] 2026-09-04T17:28:20Z: cd /workspace/review_scratch/rolling_king && /workspace/venv/bin/python pod_king_ic_legs.py > logs/ic_legs_smoke_pinned.log 2>&1
CMD[Lfix_pinned_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_pinned_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_pinned_log_s2027] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_pinned_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 OUT_TAG=Cdyn_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_pinned_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_pinned_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_pinned_prod_s2027] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_pinned_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 OUT_TAG=Cdyn_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
ARMS_DONE king=pinned 2026-09-04T17:31:45Z
CMD[chain-arms] 2026-09-04T17:32:13Z: setsid nohup bash -c "until grep -qE \"^DONE monthly|Traceback\" logs/rollm.log; do sleep 20; done; bash run_arms.sh rollm > logs/run_arms_rollm.out 2>&1; until grep -qE \"^DONE quarterly|Traceback\" logs/rollq.log 2>/dev/null; do sleep 20; done; bash run_arms.sh rollq > logs/run_arms_rollq.out 2>&1" > logs/chain_arms.out 2>&1 < /dev/null &
CMD[chain-arms v2] 2026-09-04T17:33:15Z: cd /workspace/review_scratch/rolling_king && nohup bash chain_arms.sh > logs/chain_arms.out 2>&1 < /dev/null &
CMD[check_pinned_equiv] 2026-09-04T17:33:17Z: cd /workspace/review_scratch/rolling_king && /workspace/venv/bin/python check_pinned_equiv.py
CMD[Lfix_rollm_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_log_s2027] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollm_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 OUT_TAG=Cdyn_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollm_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_prod_s2027] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollm_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 OUT_TAG=Cdyn_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollm_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_log_s2027] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollm_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 OUT_TAG=Cdyn_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollm_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_prod_s2027] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollm_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 OUT_TAG=Cdyn_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
ARMS_DONE king=rollm 2026-09-04T17:43:41Z
ARMS_DONE king=rollm 2026-09-04T17:44:59Z
CMD[Lfix_rollq_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollq_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_log_s2027] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_log_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollq_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 OUT_TAG=Cdyn_rollq_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollq_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollq_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_prod_s2027] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_prod_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollq_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 OUT_TAG=Cdyn_rollq_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollq_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollq_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_log_s2027] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_log_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollq_log_s42] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 OUT_TAG=Cdyn_rollq_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollq_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollq_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_prod_s2027] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_prod_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollq_prod_s42] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 OUT_TAG=Cdyn_rollq_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
ARMS_DONE king=rollq 2026-09-04T17:50:00Z
ARMS_DONE king=rollq 2026-09-04T17:50:00Z
CMD[ic_legs all kings] 2026-09-04T20:17:35Z: cd /workspace/review_scratch/rolling_king && /workspace/venv/bin/python pod_king_ic_legs.py > logs/ic_legs.log 2>&1
CMD[judge] 2026-09-04T20:18:04Z: cd /workspace/review_scratch/rolling_king && /workspace/venv/bin/python judge.py > logs/judge.log 2>&1
CMD[render_tables] 2026-09-04T20:19:13Z: cd /workspace/review_scratch/rolling_king && /workspace/venv/bin/python render_tables.py > REPORT_tables.md
CMD[report] 2026-09-04T20:22:06Z: REPORT.md assembled on Mac (REPORT_head/answer/tail + REPORT_tables.md) and scp-ed to pod; sha256 91a5c5b8ab1587eee83862a9db25e5172e6e2dfd9be95aeb2f574a9abbecb6b7
CMD[verify_rerun] 2026-09-04T20:23:31Z: cd /workspace/review_scratch/rolling_king && bash verify_rerun.sh > logs/verify_rerun.log 2>&1
CMD[Lfix_rollm_log_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollm_log_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_log_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_log_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_log_s2027_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_log_s2027_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollm_log_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 OUT_TAG=Cdyn_rollm_log_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollm_prod_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollm_prod_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_prod_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_prod_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollm_prod_s2027_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollm_prod_s2027_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollm_prod_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy FSEED=42 OUT_TAG=Cdyn_rollm_prod_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollq_log_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollq_log_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_log_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_log_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_log_s2027_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_log_s2027_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollq_log_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 OUT_TAG=Cdyn_rollq_log_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Lfix_rollq_prod_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=Lfix_rollq_prod_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_prod_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_prod_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Ldyn_rollq_prod_s2027_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=Ldyn_rollq_prod_s2027_v /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[Cdyn_rollq_prod_s42_v] (cwd=/workspace/review_scratch/rolling_king/dev_alt): env LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollq.npy FSEED=42 OUT_TAG=Cdyn_rollq_prod_s42_v /workspace/venv/bin/python ../w10_universe_recheck.py
VERIFY_RERUN_DONE 2026-09-04T20:24:11Z
CMD[render_tables v2] 2026-09-04T20:25:14Z: cd /workspace/review_scratch/rolling_king && /workspace/venv/bin/python render_tables.py > REPORT_tables.md
```
