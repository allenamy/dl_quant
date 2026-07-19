# HANDOFF INDEX — what to transfer, what to ignore

> One page. This repo holds the shipped **multi-asset-v2 four-leg book** plus ~5 months of research
> history. A partner needs only the handoff set below — **everything else is research provenance and
> can be ignored.** The assembled, self-contained bundle is `handoff_package_v1.tar.gz` (regenerate
> with `bash multi_asset/handoff/make_package.sh`).

## The handoff set (the ONLY files a partner needs)

**Acceptance battery** (`multi_asset/handoff/`)
- `acceptance_battery.py` — automated retrain-acceptance gate (self-tests; reproduces team rulings)
- `acceptance_battery_SPEC.md`, `acceptance_thresholds_0C_frozen.json` — the pre-registration contract

**Docs** (`multi_asset/handoff/`)
- `PRIMER.md` — start here: what the system is + the mechanism
- `REPRODUCTION.md` — data → panel → train → eval → engine, with verification checkpoints
- `RUNBOOK.md` — leg weights, maker execution, vol-gate, netting, capacity, pilot + reflux protocol
- `MANIFEST.md` — full asset inventory + the data-licensing boundary

**Engine** (`multi_asset/engine/`)
- `signal_chain · vol_gate · isotonic_calib · ic_monitor · funding_risk · netting` (C1–C6) +
  `panel_source · replay_fullhist` + `README.md` (★caliber verdict) + `live/` (CDN-T+1 live shadow)

**Build + train pipeline**
- `multi_asset/data/` — build chain: `dump_wide_universe, dump_funding_metrics_panel, download_wide_metrics,
  repair_cdn_enum, build_wide_panel, build_wide_metrics_channels, build_wide_dl, wide_factory,
  wide_panel_dataset, densify_s2_cl4` (+ `exports/eda/king_pred_panel.py`)
- `multi_asset/train/train_wide_harness.py` — the king/S2 trainer
- `multi_asset/model/` — `wide_harness, temporal_spatial_panel, cross_asset_panel`
- `multi_asset/losses/xsec_residual_loss.py` — the stage2b objective
- `src/model/` — `backbones/conformer_backbone, attention_pool, direction_aware_quantile_head, raw_lob_encoder`

**Large artifacts (by reference — md5 manifest in the package `checkpoints/CHECKPOINTS.md`)**
- Champions: `exports/train/wideA_lamorth0_xattn_5yr/` (king) + `exports/train/wideA_s2_y24_5yr/` (S2)
- Panels: `exports/wide_dl_full.npz`, `exports/wide_panel_full.npz`
- Prediction panels: `exports/eda/{king_pred_panel,s2_pred_panel_cl4}.npz`

## Ignore (research history — NOT part of the handoff)

Everything else under `multi_asset/exports/` (the ~100 EDA/scoring/ablation scripts + JSON verdicts —
these are the *evidence trail* for the decisions, referenced by MANIFEST but not needed to run the
system), the single-asset track (`src/`, `configs/`, other `docs/`) except the specific `src/model/`
files listed above, and all archived/closed-track artifacts (`MANIFEST.md §9`). The shipped book
reproduces entirely from Binance **public** data; the licensed `bar_data` (1s) and Tardis book are
retained by the data owner and are **not** part of the four-leg book.

## Verify the transfer

`python multi_asset/handoff/acceptance_battery.py --self-test --champion multi_asset/exports/train/wideA_lamorth0_xattn_5yr`
should print `SELF-TEST OK`. That single command exercises the whole prediction→eval path.
