# MANIFEST.md — handoff asset inventory

> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0B handoff) | **状态:** v1 | **作废条件:** 冠军/面板/引擎重建, 或数据授权边界变更

Everything transferred, where it lives, and — critically — **which data is reproducible from
public sources vs. licensed and retained by you**. Server root `$M =
/mnt/storage/private/work_hsy/quant_research_multi_asset`; the system has no git, so the
**artifacts below are the source of truth** (the local `docs/` narrative is the adjudication
record, not the runtime).

---

## 1. Handoff package (`$M/multi_asset/handoff/`)

| file | what |
|---|---|
| `acceptance_battery.py` | automated acceptance battery v2 (9 gates, 4-way verdict, self-test §12) |
| `acceptance_battery_SPEC.md` | 0C pre-registration spec (gate defs, thresholds, derivations, test matrix) |
| `acceptance_thresholds_0C_frozen.json` | frozen thresholds, auto-loaded by the battery (`--config` overrides) |
| `REPRODUCTION.md` | data → panel → train → eval → engine, with per-stage checkpoints |
| `RUNBOOK.md` | four-leg weights, maker execution, vol-gate, netting, capacity, pilot + reflux |
| `MANIFEST.md` | this file |
| `_selftest_v2_report.json` | battery self-test evidence (T1/T3a/T3b/T3c) |

---

## 2. Champion checkpoints (`$M/multi_asset/exports/train/`)

| dir | leg | contents | size |
|---|---|---|---|
| `wideA_lamorth0_xattn_5yr/` | **king** (H=4) | `fold_{0..4}_model.pt` (weights) + `fold_{0..4}_head_scores.npz` (OOS scores (T,140,6)) + `panel_ref.npz` | 868 MB |
| `wideA_s2_y24_5yr/` | **S2** (H=24) | same layout | 868 MB |

Each `fold_i_model.pt` is a conformer + 1 cross-asset-attention block + 6 factor heads (~1 MB).
`panel_ref.npz` md5 `185d3b65` (feature-panel), ts-array md5 `dfb81d19` — the frozen eval grid the
battery gate (f) aligns against. Seed variants (`wideA_xattn_seed43/44`, `wideA_s2_*seeds`) exist for
the CoV gate.

## 3. Stitched prediction panels (`$M/multi_asset/exports/eda/`)

| file | key | role | size |
|---|---|---|---|
| `king_pred_panel.npz` | `king_pred` (T,140) | king OOS ensemble the engine consumes | 95 MB |
| `s2_pred_panel_cl4.npz` | `s2_pred` (T,140) | S2 OOS ensemble (CL4-gridded) | 95 MB |

Both also carry `ts, member, CL, YR, Yraw, day, year` — i.e. they are self-contained candidate
panels in the battery's pred-panel input format.

## 4. Feature panels (`$M/multi_asset/exports/`)

| file | what | size |
|---|---|---|
| `wide_dl_full.npz` | **the training + engine input**: CH(48168,140,32) causal, Y/YR/CL{1,4,24}, MEMBER110, baseline_cols | 1.05 GB |
| `wide_panel_full.npz` | intermediate assembled panel (pre-factor) | 277 MB |
| `wide_dl_full_39ch.npz`, `_12h.npz`, `_s3_y168.npz` | ablation/side-track variants (not the shipped book) | ~0.7 GB ea |

## 5. Verdict / evidence JSONs (`$M/multi_asset/exports/eda/`)

| file | records |
|---|---|
| `xattn_g2_seeds.json` | king 3-seed CoV band (0.0948/0.0910/0.0973, σ 0.0026) — gate (b)(g) reference |
| `xattn_5yr_coronation.json` | king 5yr per-year IC, dyn-share, net-cost coronation |
| `arm_s2_5yr_score.json` | S2 incremental-over-king IC + book-margin bootstrap |
| `arm_s1_verdict.json`, `arm_n1b_core.json` | archived arms (REJECTed — the battery T2 reference) |
| `engine_fullhist_replay.json` | **canonical** engine table (rank+cap, avg net 12.21) |
| `engine_fullhist_replay_calibrated.json` | deployable-calibrated variant (isotonic, 10.84) |
| `engine_funding_weighting_2x2.json` | funding z-vs-rank × C5 on/off 2×2 (why rank is canonical) |
| `crossleg_netting.json` | 4h-sync netting savings (202 bps/yr) |
| `a2_ridge_snr.json`, `a7_cost_tiers.json` | Phase-1 SNR gate + per-asset cost tiers |

## 6. Engine (`$M/multi_asset/engine/`) — the six-piece C1–C6 + driver

| file | component |
|---|---|
| `signal_chain.py` | **C1** 4-leg L1 sub-portfolios → combine → (C3) → tail cap → market-neutral target |
| `vol_gate.py` | **C2** execution-tactic vol-gate (exposure pinned 1.0) |
| `isotonic_calib.py` | **C3** isotonic calibration (non-canonical; deployable-calibrated only) |
| `ic_monitor.py` | **C4** rolling rank-IC decay alarm + champion/challenger stub |
| `funding_risk.py` | **C5** funding-leg risk (inert under rank; insurance for z path) |
| `netting.py` | **C6** 4h-sync cross-leg netting |
| `panel_source.py` | shared data layer (reads `wide_dl_full.npz` + king/s2 pred panels) |
| `replay_fullhist.py` | driver: `run_replay(funding_mode, use_c5, shaping)` |
| `README.md` | ★ positioning verdict (structural ≠ deployment) — read before the Sharpe table |
| `exp_funding_weighting.py` | funding 2×2 experiment |

## 7. Pipeline code (import-only references)

`multi_asset/train/train_wide_harness.py` (king/S2 trainer) · `multi_asset/data/` (acquisition +
panel builders: `dump_wide_universe.py`, `dump_funding_metrics_panel.py`, `repair_cdn_enum.py`,
`build_wide_panel.py`, `build_wide_dl.py`, `king_pred_panel.py`, `densify_s2_cl4.py`) ·
`multi_asset/model/` (WideFactorModel + encoders) · `multi_asset/losses/` (stage2b / xsec-IC).

---

## 8. ★ Data-source tiering (the licensing boundary)

| tier | data | path | status |
|---|---|---|---|
| **Reproducible (public)** | 1h klines, fundingRate, 5m metrics (OI/positioning) for ~110 USDT-perps | `data.binance.vision` CDN archives | **The shipped four-leg book is built ENTIRELY from this.** Partner re-pulls freely — see `REPRODUCTION.md §1`. |
| **Licensed (retained by you)** | 1s L2 bars, 14+ symbols, 2022→2025 | `/mnt/storage/share/bar_data` (READ-ONLY) | Procured. **Not needed** for the shipped book. Do not transfer without a license check. |
| **Licensed (retained by you)** | Tardis `book_snapshot_25` + trades, BTC spot+perp, 2023-01→2026-05 | `/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis` (READ-ONLY) | Procured. Used only in single-asset / dual-source side tracks, **not** the shipped multi-asset book. Do not transfer without a license check. |

**Bottom line for the partner:** the entire shipped system reproduces from Binance public data.
The 1s `bar_data` and Tardis book are **licensed inputs you retain** — they belong to earlier
single-asset / side-track work that is *not* part of the four-leg book, and must not be redistributed
without confirming the data license permits it.

---

## 9. Not in the shipped book (closed tracks — retained, do not re-mine blind)

OI/positioning alpha (Track-2, double-gate FAIL) · N1a/N1b cross-asset-structure arms (archived,
book-redundant) · S1 king-residual arm (archived) · 39ch / 12h / y168 panel variants. Faces are
built and kept for provenance; re-opening any needs a *new* hypothesis, not a re-run.
