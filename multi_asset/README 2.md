# Multi-Asset y_600 Cross-Sectional Alpha

> **创建:** 2026-05-20 UTC+8 | **Session:** multi-asset launch
> **状态:** in-progress | **Plan:** `docs/superpowers/plans/2026-05-20-multi-asset-y600.md`

Predict y_600 (10-min forward return) for 14 Binance USDT-perp symbols. Goal: **avg per-asset Pearson 0.10** (vs single-asset BTC 0.065), healthy β≈1, monotonic calibration, near-zero long-short bias.

## The reframing that drives everything (empirically measured)

- Contemporaneous BTC→alt beta is **~0.70** (ETH 0.84). Lagged BTC→alt at 600s is **weak (~0.02)**.
- ⇒ **beta-projection** (β·ŷ_BTC) gives **~0.045 Pearson/alt for free**. The model's real job is the **residual alpha** (0.045 → 0.10).
- Risk ladder: **C** (beta-projection floor) → **A** (shared-backbone universal REG_arch + cross-asset attention — primary) → **B** (BTC 25-level LOB enrichment — conditional).

## Discipline (non-negotiable)

- **Mechanism over stacking:** every feature/module needs a stated mechanistic rationale AND must clear a quantitative gate (Ridge walk-forward ΔP ≥ +0.005 for features; ΔP ≥ +0.003 for model channels). No blind stacking — this killed v6b/v7/v8 in single-asset.
- **Single-asset code is a READ-ONLY library.** All new code lives in `multi_asset/`. Never edit `src/`, `configs/`, etc. — import them. The `reg-arch-final` branch is the frozen single-asset reference.
- **Share data is READ-ONLY.** `/mnt/storage/share/bar_data` opened mode="r" only.
- Inherited anti-patterns #1–26 (see `CLAUDE.md`): σŷ/σy≥0.02 gate, value-blend not rank-blend, stride≥horizon clean eval, multi-day walk-forward CV, report P AND S, per-fold sign-consistency.

## Layout

| Dir | Phase | Purpose |
|:--|:--|:--|
| `eda/` | 1 | A1–A7 GO/NO-GO analyses |
| `data/` | 2 | synchronized panel pipeline (bar loader, features, panel NPZ, dataset) |
| `baselines/` | 3 | beta-projection floor (Approach C) + cross-sectional Ridge |
| `model/` | 5–6 | universal shared-backbone REG_arch + cross-asset/market-factor token |
| `losses/` | 7 | cross-sectional rank-IC / CCC assembly |
| `train/` | 8 | trainer (3090) |
| `eval/` | 9 | dual-caliber eval + cross-sectional backtest |
| `configs/`, `exports/` | — | configs + results |

## Server / sync

- Server dir: `jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset` (training only, one RTX 3090).
- Sync: `./multi_asset/sync_to_server.sh` (rsync local → server, excludes data/exports/.git).
- Env: `conda activate hsy_v5push`.
