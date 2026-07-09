# M0 full-history walk-forward replay — PRE-REGISTRATION (read locked before results)

> **创建:** 2026-07-09 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** pre-registration (locked before any result) · **作废条件:** superseded by the results write-up once the replay lands, or if the locked config/data spec below is changed (then re-register).
> **交叉引用:** `docs/2026-07-08_multi_asset_v2_portfolio_scorecard.md` (deliverable; this resolves its open limit #2) · `multi_asset/data/megacap_funding_replay.py` (the funding analogue this mirrors) · memory `ma-v2-factor-state-2026-07-08` / `ma_v2_funding_ema_GO`.

## 0. Why (the one gap this closes)

M0 (the DL raw-sequence factor) is the **stronger Book-1 leg** (standalone rank-IC +0.0355 z7.03 vs funding +0.0186), but we have only seen it in a **~7-month OOS (2024-06→2025-09 folds), which is funding_ema's single best year**. The funding full-history replay already showed funding is NOT all-weather (long-run net-Sh ~+0.6, losing years 2020/22/24). **M0's multi-year robustness is unmeasured** — it is the top open item in the scorecard. This replay applies the SAME locked M0 config across 2022→2025 walk-forward to answer: does the DL factor hold across regimes, or is the 3.92 blend headline a favorable-window artifact?

This is a **replay, not a re-tune.** No architecture / loss / gate changes. Only the fold day-windows move (walk-forward across years) and the cache is extended back.

## 1. DATA (0B builds; verified extents 2026-07-09)

| cache | current | needed | source |
|---|---|---|---|
| `seq_cache/` | 2024-06-01 → 2025-09-30 (487 d) | back to 2022-01-01 | `bar_data/bar_1s/` |
| `mh_targets_long/` (y_3600) | 2024-06-01 → 2025-09-30 (487 d) | back to 2022-01-01 | same |
| **`panel_cache/`** (★ the day-grid + last-token stats source — `SeqPanelData` L79-101) | 2024-06-01 → 2025-09-30 (487 d) | **back to 2022-01-01** | `build_feature_cache.py` |
| `bar_1s` (build source, all 14 syms) | **2022-01-01 → 2025-11-30** (full) | — | READ-ONLY share |
| funding_ema full-history | already dumped (`megacap_funding_replay`) | — | `data/megacap_hist` |

- **★ panel_cache is the THIRD dependency (0B's catch, 2026-07-09 — first replay run degenerated because of this).** `SeqPanelData` builds `uniq_days` + the per-fold standardization inputs from `panel_cache`, NOT from seq_cache. Extending only seq_cache + mh_targets_long left panel_cache pinned to the 487-day window → `uniq_days`=487 → `build_fh_folds` saw only 2024-2025 → a single degenerate fold. **All THREE (seq_cache + mh_targets_long + panel_cache) must extend to 2022-01.** The re-run must print `uniq_days ≈ 1430` before it is valid.
- **Leak-safety of the panel_cache extension = CLEAR (0C verified `set_fold` L135-168).** All per-fold stats (`mu`/`sd`/`sigma`/`resid_sigma`) are fit on the `trm` TRAIN-days mask only; panel_cache supplies only the raw grid + last-token features, so extending it to 2022-2025 does NOT leak future normalization into the 2023/2024 test folds. The bit-identity verify of the rebuilt 2024-2025 slice (0B) confirms production caliber is intact.
- **★ Common-ts intersection caveat (L81):** the panel index = `set.intersection` of all 14 symbols' ts. If any mega-cap lacks full 2022 coverage in panel_cache (later Binance-perp listing), the strict intersection silently drops those days → shrinks fold-A/B's (already-immature) train window. After the rebuild, verify **per-YEAR** day counts (2022 ~365, 2023 ~365), not just the ~1430 total, and note any symbol missing full 2022 — this changes how a weak fold-A reads (R5 immaturity vs universe-thinning).
- **Coverage ceiling: bar_1s ends 2025-11-30**, so the DL replay covers **2022-01 → 2025-11**. 2026 is NOT coverable by DL (no bar_1s); the funding-2026 row stays funding-only. Decisive years (2023 chop / 2024 funding's-loss / 2025) all in range.
- Build must be **bit-identical in feature construction** to the current caches (same channels, causal windows, `feature_names.json`) — verify the new 2022-2024 files match the existing 2024-06+ schema before launch.

## 2. WALK-FORWARD folds (train ONLY on prior; expanding)

Yearly, expanding-window, 1-day embargo at each year boundary. Because bar_1s starts 2022-01-01, **2022 cannot be a test year** (no prior training data) — it is train-only.

| fold | train | val (tail) | test | regime | train maturity |
|---|---|---|---|---|---|
| A | 2022-01 → 2022-12 | last 20 d of train | **2023** (Jan–Dec) | chop / bear-recovery | ~1 yr (IMMATURE) |
| B | 2022-01 → 2023-12 | last 20 d | **2024** (Jan–Dec) | ★ funding's LOSS year | ~2 yr |
| C | 2022-01 → 2024-12 | last 20 d | **2025** (Jan–Nov) | funding's best year | ~3 yr |

- **Locked M0 config (NO change):** `TemporalSpatialPanelModel` milestone 0, `d=32, n_blocks=2, kernel=15`, funding-residual y_3600 target (`--resid_on_funding`), loss `--w_pin 1.0 --w_rank 0.1 --w_huber 0.0`, `--kill_gates`, **seed 42** (primary). ~56K params. Identical to `fund_resid_h3600`.
- **Launch mechanic:** add a `--yearly_walkforward` mode that constructs the 3 year-fold `(tr_days, va_days, te_days)` lists from the extended cache and calls the existing `train_fold(..., day_override=...)` per fold (the same path `--pretrain_mode` already uses). No touch to model/loss/gate code. Save per-fold `fold_{A,B,C}_preds.npz` (pred, te_rows, te_days) + `panel_ref.npz` with **≥3600 CL** (NOT the ~720s dense seq-cache CL — see §5 landmine). Save under a new tag, e.g. `train/m0_fullhist_wf/`.
- **Seeds:** primary run = seed 42 (single locked run, ~1 GPU day, per lead's budget). IF the per-year read is ambiguous at the margin, a 3-seed ensemble replay is the pre-agreed follow-up (matches the production config), NOT a re-tune — but only if greenlit after seeing seed-42.

## 3. KILL gates (same locked M0 thresholds, per fold; no mid-run iteration)

- Per-fold gate: val-rankIC < 0.005 @ ep8 → KILL that fold; σ_ratio (σŷ/σy) < 0.01 → KILL that fold.
- **★ The KILL is per-fold and does NOT stop the run** (amended pre-results — see note). All 3 folds A/B/C train + export regardless of an earlier fold's kill. A killed fold exports no preds → that test-year reads as a kill in the scorer (no-usable-rows, exactly as 2024 did on the single-window validation).
- **A KILL is itself a finding** (e.g. fold-A killed = M0 cannot learn from 2022-only data → immaturity) — do NOT re-tune to rescue. Log it as the read; R1's soft-pass then judges whether B+C carry.

> **Amendment (2026-07-09, before any result, at 0B's catch — resolves an internal §3-vs-R1/R2 tension, not a post-hoc goalpost move):** the original §3 inherited the locked config's "fold-0 kill → STOP run" (which exists to save GPU when a config is *globally* dead in a same-window 3-fold run). In this cross-regime replay that directly contradicts R1's maturity-soft-pass and R2's decisive 2024 test, both of which require 2024/2025 to be evaluated even if 2023 (1-yr-immature) is weak. Since each fold here is an independent regime observation, the "stop to save GPU" rationale doesn't apply. Resolution: per-fold kills are logged as findings but never stop the run, so R1/R2/R3/R4 always have the later years. No leakage introduced (walk-forward train-only-on-prior preserved; the gate still fires and is recorded). Implemented in the `--fh_folds` runner (0B build 911409d + fix).

## 4. ★ PRE-REGISTERED READ (thresholds locked HERE, before results)

Scoring caliber (0C): xsec rank-IC on **≥3600 CL** (dense-CL landmine §5); empirical within-ts shuffle-null z (25 perms, same as gate-a); net-cost L/S = rank-weighted dollar-neutral, 1h + 2h rebalance, EMA-turnover sweep → break-even + net-Sh at {2, 5, 10} bps (flat 2 bps mega-cap maker baseline, same harness as the scorecard). Funding per-year reference from `megacap_funding_replay.json` (already have: 2023 net-Sh +0.91, **2024 −1.52**, 2025 +2.87 @1h). For the funding+M0 **blend** per year, funding is recomputed ON the M0 replay panel (same ts/universe/Y) so the blend is apples-to-apples.

**R1 — regime-robust?** M0 is regime-robust IFF per-test-year rank-IC z ≥ 2.5 AND sign-consistent positive across 2023/2024/2025. **Fold-maturity soft-pass:** a weak/failing **2023** (1-yr-immature train) is attributed to immaturity and is a soft-pass IF **both 2024 and 2025 pass** (2-3 yr train). If 2024 OR 2025 fails, M0 is NOT regime-robust.

**R2 — ★ DIVERSIFICATION (the decisive test).** In **2024** (funding gross-negative, net-Sh −1.52 even at zero cost): is M0 net-Sh@5bps **> 0**?
- **YES →** M0 *diversifies funding's bad year* → the two-leg book is genuinely complementary at the annual scale → strongest possible resolution of the 2025-09 correlated-drawdown limit (they co-drew-down in one adverse month, but M0 carries funding's worst YEAR). This is the best-case outcome and materially raises confidence in the book.
- **NO (M0 also net-negative 2024) →** shared regime dependence → both Book-1 legs co-fail in the same adverse regime (persistent-crowding / trending / tail-adverse) → TIGHTEN limit #1: size for a joint annual drawdown, not just a joint month.

**R3 — favorable-window verdict.** If M0 net-Sh is strong ONLY in 2025 and weak/negative in 2023 AND 2024 → the 3.92 blend headline is window-inflated → discount the scorecard headline to the **test-year mean/median net-Sh** (analogous to funding's +0.56/+0.71 tempering), and say so plainly.

**R4 — long-run headline (reported regardless).** M0 test-year **mean + median** rank-IC and net-Sh; funding+M0 **blend** per-year mean + median. These become the honest multi-year Book-1 expectation in the deliverable, replacing the single-window 3.92 as the headline-with-caveat.

**R5 — read WITH the maturity gradient.** Training maturity increases 2023 (1yr) < 2024 (2yr) < 2025 (3yr). An IC uptrend across test years could be *maturity, not regime*. Do not over-read a weak earliest fold as a regime signal; flag the confound explicitly in the write-up.

## 5. Landmines to avoid (carried from prior phases)

- **Dense-CL (the one that burned us):** the seq-cache `panel_ref.CL` is a ~720s dense mask (0.252 frac). Scoring a y_3600 (1h) target on that inflates z (funding naive z 5.3 → 11.2). **Score on the ≥3600 CL** (the non-overlapping-at-horizon mask), exactly as the funding/scorecard caliber. 0B exports panel_ref with ≥3600 CL; 0C double-checks the CL frac before scoring.
- **Clip-caliber:** npz y_3600 targets are ±5σ-clipped (corr ~0.88 to raw). IC deltas are robust to this; absolute net-Sh is slightly deflated. Consistent with the scorecard's clipped caliber — report same-caliber, note it.
- **Embargo:** 1-day gap at each year boundary (train ends Dec 31, test starts Jan 2) to prevent the y_3600 label window straddling the split.
- **Leak-audit already PASSED for the config** (M0 6/6): windows ≤ t, causal funding-residual, train-only norm per fold, te disjoint. The walk-forward extension inherits the audited pipeline; the only new leak surface is the fold-boundary embargo (covered above).

## 6. Division of labor + budget

- **0B:** build seq_cache + mh_targets_long extension back to 2022-01 (CPU, verify schema-identical); add `--yearly_walkforward` fold-driver (no model/loss/gate change); launch the single locked seed-42 run (~1 GPU day, GPU currently idle); export per-fold preds + panel_ref (≥3600 CL) under `train/m0_fullhist_wf/`.
- **0C (me):** this pre-registration (done, before results); when preds land — per-year M0 rank-IC + null-z (≥3600 CL), net-cost L/S (1h + 2h, cost grid), funding+M0 blend per year; cross-check vs the funding per-year table; write the results against R1–R5 and fold into the scorecard's regime section (either "M0 regime-robust, DL leg's window caveat resolved" or "M0 favorable-window too, discount headline further").
- **Budget:** single locked run, no mid-run iteration. 3-seed ensemble replay is the ONLY pre-agreed follow-up, and only if seed-42 is marginal.
