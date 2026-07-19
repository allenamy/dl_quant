# REPRODUCTION.md — Multi-Asset-v2 four-leg book, end-to-end rebuild

> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0B handoff) | **状态:** v1 | **作废条件:** 面板口径 / 腿构成 / 训练入口变更

This is the full chain to rebuild the shipped four-leg market-neutral book **from public
data on your own hardware**. Server paths below (`$M = /mnt/…/quant_research_multi_asset`)
are *references* — the pipeline is deterministic, so a clean rebuild reproduces the same
panel byte-for-byte (verify with the md5 checkpoints). Every stage ends with a **CHECKPOINT**
you must pass before continuing.

Environment used to produce the shipped artifacts: single RTX 3090, `hsy_v5push` conda env
(`/root/miniconda3/envs/hsy_v5push/bin/python3`), torch + numpy/pandas/scipy/sklearn.

---

## 0. The dependency graph

```
 Binance public (data.binance.vision CDN archives — NOT the FAPI REST / S3 listing)
    │  dump_wide_universe.py           1h klines + fundingRate  → data/wide/<SYM>_*.csv
    │  dump_funding_metrics_panel.py   5m metrics (OI/posn)     → data/funding/<SYM>_metrics_5m.csv
    │  repair_cdn_enum.py              heal false-NODATA / truncation
    ▼
 wide_panel.npz            build_wide_panel.py  (+ wide_factory.build_factors zoo)
    ▼
 wide_dl_full.npz          build_wide_dl.py / build_wide_metrics_channels.py
    │   CH(48168,140,32) causal ≤t | Y{1,4,24} raw | YR{1,4,24} carry-residual target
    │   CL{1,4,24} clean masks | MEMBER110 point-in-time | baseline_cols
    ├──────────────► DL legs (train_wide_harness.py)
    │                   king  → exports/train/wideA_lamorth0_xattn_5yr/   (H=4 residual reversal)
    │                   S2    → exports/train/wideA_s2_y24_5yr/            (H=24 slow factor)
    │                        │  king_pred_panel.py / densify_s2_cl4.py
    │                        ▼
    │                   exports/eda/king_pred_panel.npz , s2_pred_panel_cl4.npz
    └──────────────► panel-channel legs (NO training): funding = rank(funding_ema) , SIZE = z(size_dvol)
                             │
     ACCEPTANCE ◄───────────┤   handoff/acceptance_battery.py  (item 1) — gate any candidate vs king
                             ▼
     ENGINE     engine/replay_fullhist.py --funding_mode rank --shaping cap  → net Sharpe 12.21 (structural)
```

Two of the four legs (**funding**, **SIZE**) are *not* models — they are causal panel channels
weighted inside the engine. Only **king** and **S2** require training. That halves the
retrain surface.

---

## 1. Data acquisition (Binance public — fully reproducible)

**Source of truth = the CDN file archive `https://data.binance.vision`, NOT the live API.**
On a headless server both the FAPI REST endpoints and the S3 bucket *listing* are blocked /
throttled; the static monthly & daily ZIP archive is reachable and has the full history
(no 30-day window). All acquisition scripts are idempotent (skip existing >200-byte files),
`nohup`-friendly, and parallel (`ThreadPoolExecutor`, WORKERS=32).

| what | script | archive path |
|---|---|---|
| 1h klines + fundingRate (wide ~110 coins) | `data/dump_wide_universe.py [start] [end] [workers]` | `…/futures/um/monthly/{klines,fundingRate}` |
| 5m metrics (OI / long-short / taker ratios) | `data/dump_funding_metrics_panel.py` , `data/download_wide_metrics.py` | `…/futures/um/daily/metrics/<SYM>/` |
| BTC-only funding full history (reference) | `data/dump_binance_funding.py` | FAPI `/fapi/v1/fundingRate` (free, no limit) |

### KNOWN LANDMINES (each cost real debugging — do not rediscover)

1. **S3-listing throttle → false NO-DATA.** A swallowed listing failure looks identical to
   "coin has no archive": you get **0 files** for a coin that is actually live. **Never trust a
   0-file result from a listing call.** Fix: `data/repair_cdn_enum.py` re-derives each coin's
   valid date range from the panel `MEMBER110` mask and does a direct **GET-with-skip** per
   `(sym, date)` against the CDN (`404` = genuinely absent, `200` = fetch). Enumerate by
   constructing URLs, not by listing.
2. **Silent pagination truncation.** A paginated listing can stop early, so a coin's last file
   lands **well before panel end** with no error. Symptom: coverage cliff mid-history. Same
   `repair_cdn_enum.py` detects last-file-vs-END gaps and back-fills.
3. **Metrics publish alignment (t−5min).** Metrics are stamped at the **5-minute bucket end**
   and only become available *after* the bucket closes; funding is stamped at **settlement**.
   At align time apply forward-fill **≤ t only, respecting publish lag** — never consume a
   bucket whose publish time > t. Getting this wrong silently leaks the future into OI/positioning
   channels.
4. **OI API 30-day cap.** `/futures/data/openInterestHist` serves **only the last 30 days** —
   useless for 2022–2025 folds. Historical OI must come from the **CDN daily metrics archive**
   (above) or Tardis `derivative_ticker`. (Note: the OI/positioning *alpha* track was tested and
   **CLOSED** — double-gate FAIL, Ridge +0.0007 / GBDT −0.0004 — the built face is retained but
   not in the shipped book. Don't burn a fold budget re-mining it without a new hypothesis.)

**CHECKPOINT 1:** per-coin file count > 0 for every `MEMBER110`-eligible date; each coin's
last-file date ≥ panel END (`2026-06-30`). `repair_cdn_enum.py` must report 0 remaining
false-NODATA / truncated coins.

---

## 2. Panel construction (point-in-time, leak-safe)

```
build_wide_panel.py         raw CSVs → exports/wide_panel_full.npz   (+ wide_factory.build_factors)
build_wide_dl.py            wide_panel → exports/wide_dl_full.npz
build_wide_metrics_channels.py   folds the metrics/OI channels into the 32-ch CH tensor
```

`wide_dl_full.npz` (the training + engine input) contents:

- `CH` **(48168, 140, 32)** float32 — causal ≤t per-coin hourly channels: the `wide_factory` zoo
  factors + raw multi-window returns / rvol / log-qvol. `ts` is **hourly, 2021-01-01 → 2026-06-30**.
- `Y{1,4,24}` **(T,N)** raw forward log-returns at 1/4/24h (**for honest eval — never train on these**).
- `YR{1,4,24}` **(T,N)** the **residual targets**: per-ts cross-sectional demean **then** OLS-residualize
  on the carry baseline → a head earns credit only for content **incremental over carry**. This is
  the whole methodology in one line.
  `baseline_cols = [funding_ema, mom_24h, mom_72h, rev_1h, rvol_24h, size_dvol, max_ret_24h, beta_24h]`.
- `CL{1,4,24}` **(T,N)** ≥horizon **non-overlapping** clean masks (member & finite & greedy H-spacing)
  — the honest eval grid (`#2` stride<horizon is forbidden).
- `MEMBER110` **(T,N)** bool — point-in-time top-110 by **trailing-30d dollar-volume**, monthly
  refresh. A coin is eligible only on dates it actually traded → **no survivorship**.

**Mandatory leak tests** (the discipline that makes the rest trustworthy):
- causal assertion: every channel at row t uses only info ≤ t;
- **shuffle-future null** (`build_wide_dl.py` `make_shuffle`): permuting the future must kill IC.

**CHECKPOINT 2:** `CH.shape == (48168,140,32)`; the panel_ref that training exports has
**md5 `185d3b65`** for the frozen build (`md5sum` first 8 hex of `panel_ref.npz`); per-ts YR
cross-sectional std ≈ 0.01; live-member count ≈ 110/hour after the early ramp.

---

## 3. Training the two DL legs (king + S2)

`train/train_wide_harness.py` is a **backbone-agnostic** factor-miner: encoder → optional
cross-asset attention → K factor heads, trained to `stage2b_loss` (per-head LambdaRankIC vs YR +
magnitude-Huber + orthogonality). It exports exactly the artifacts the battery consumes:
`fold_i_head_scores.npz` (scores (T,N,K=6) at OOS test rows) + one `panel_ref.npz`.
**Collapse guard is built into training**: it checkpoints on **max-over-heads val cross-sectional
rank-IC** (a collapsed head has NaN rank-IC, so the rank-IC gate *is* the σ-guard). `--kill_gates`
opt-in adds a fold-0 pre-registered kill.

### KING — H=4 residual-reversal leg → `exports/train/wideA_lamorth0_xattn_5yr/`
```bash
python3 multi_asset/train/train_wide_harness.py \
  --encoder conformer --n_factor_heads 6 --target_horizon 4 \
  --xattn --n_xattn 1 --lam_orth 0 \
  --year_folds --wide_dl_path multi_asset/exports/wide_dl_full.npz \
  --seed 42 --save_tag wideA_lamorth0_xattn_5yr --tag lamorth0_xattn_5yr
```
Why these flags (mechanism, not taste):
- `--year_folds` = **expanding calendar-year walk-forward** (train all prior years, test each of
  2022/23/24/25/26 in turn) → strict temporal isolation, no weight look-ahead.
- `--lam_orth 0` = orthogonality penalty OFF. The 6 heads become a free **implicit ensemble**;
  the honest z-mean over heads is the signal. Non-zero `lam_orth` was measured **dilutive** here.
- `--xattn` = one cross-asset attention block over the live members (breadth benefit; +~0.031 IC).
- `--n_factor_heads 6` = the ≤6-head iron rule (capacity matched to a <1% R² signal).

### S2 — H=24 slow leg → `exports/train/wideA_s2_y24_5yr/`
```bash
python3 multi_asset/train/train_wide_harness.py \
  --encoder conformer --n_factor_heads 6 --target_horizon 24 \
  --xattn --n_xattn 1 --lam_orth 0 \
  --dense_train --embargo_days 10 \
  --year_folds --wide_dl_path multi_asset/exports/wide_dl_full.npz \
  --seed 42 --save_tag wideA_s2_y24_5yr --tag s2_y24_5yr
```
Extra flags vs king:
- `--dense_train` = train on **all** overlapping 1h labels (eval/checkpoint stay on the clean
  CL24 grid). Required because the CL24 non-overlap stride starves training at H=24
  (params:samples ~1:0.8 → dense recovers ~1:20). **Honesty preserved: only training densifies;
  scoring is always CL24.**
- `--embargo_days 10` ≥ lookback + horizon for H=24 (gap between train and the year boundary).

Hardware note: `--batch_hours 16` is the 3090 ceiling (140 coins/hr ⇒ ~2240 seqs; 48 OOMs a 24GB card).

> Seeds `42` are the shipped defaults; the coronation used seed 42 as primary (seed 43/44 exist as the
> CoV check). Confirm the seed against your own run header if you re-derive the CoV gate.

**CHECKPOINT 3:** each fold prints `ENSEMBLE resid IC`; then run the battery (§5) — king honest-
ensemble pooled IC ≈ **0.0817**, per-year **all positive** `[2022 .048 / 2023 .080 / 2024 .086 /
2025 .104 / 2026 .099]`, `dyn_share ≈ 0.97`. S2 incremental-over-king IC ≈ **+0.005**, sign-consistent.

---

## 4. Stitch prediction panels (train → engine bridge)

The engine reads **stitched OOS prediction panels**, not the raw fold products:
```bash
python3 multi_asset/exports/eda/king_pred_panel.py   # wideA_lamorth0_xattn_5yr folds → exports/eda/king_pred_panel.npz  (key king_pred)
python3 multi_asset/data/densify_s2_cl4.py           # wideA_s2_y24_5yr folds → exports/eda/s2_pred_panel_cl4.npz         (key s2_pred, CL4-gridded)
```
Both stitch the honest z-mean ensemble at OOS test rows only (folds are disjoint → pure OOS).
The funding and SIZE legs need no stitch — the engine reads `funding_ema` and `size_dvol`
straight from `wide_dl_full.npz`.

**CHECKPOINT 4:** `king_pred` / `s2_pred` finite **only** at OOS anchors; their per-anchor rank
matches the corresponding fold's composite (spot-check one anchor).

---

## 5. Acceptance evaluation (the battery)

Always self-test the battery on the champion first, then gate the candidate:
```bash
# A) prove the battery discriminates — runs 0C SPEC §12 adversarial matrix, must print
#    "SELF-TEST OK" (T1 champion-vs-self => ACCEPT-clone; T3a shuffle-ts / T3b dup-head /
#     T3c injected-lookahead => REJECT via gates f / g / e).
python3 multi_asset/handoff/acceptance_battery.py --self-test \
  --champion multi_asset/exports/train/wideA_lamorth0_xattn_5yr

# B) gate a freshly-trained candidate against the champion
#    --candidate / --champion accept EITHER a fold-product DIR (fold_*_head_scores.npz +
#    panel_ref.npz) OR a stitched pred-panel NPZ (king_pred_panel.npz format).
python3 multi_asset/handoff/acceptance_battery.py \
  --candidate multi_asset/exports/train/<your_new_run> \
  --champion  multi_asset/exports/train/wideA_lamorth0_xattn_5yr \
  [--seeds <seed43_dir> <seed44_dir>] [--claim-upgrade] \
  --out multi_asset/handoff/<report>.json
```
Exit 0 = ACCEPT, 1 = REJECT. Nine gates in three classes — **hard** (a σ-collapse / e forward-
causal / f index-alignment / h clean-caliber: any fail ⇒ numbers untrustworthy), **soft**
(b honest-ensemble IC / c sign+bootstrap / d dynamic-share / g CoV+head-diversity), and the
**upgrade** gate (i, only with `--claim-upgrade`) — synthesized into a four-way verdict:
`REJECT-untrustworthy | REJECT-degraded | ACCEPT-clone | ACCEPT-upgrade`. Definitions and
mechanism are in the script header and the pre-registration `handoff/acceptance_battery_SPEC.md`
(0C). **Exact thresholds are frozen in `handoff/acceptance_thresholds_0C_frozen.json`**, which the
script auto-loads (override with `--config <json>`); the expected outcome of a faithful retrain is
**ACCEPT-clone** (ACCEPT-upgrade should be rare and requires a proven per-year edge).

**CHECKPOINT 5:** self-test prints `SELF-TEST OK`; a genuine retrain of king lands **ACCEPT-clone**
(honest-ensemble IC within 0.005 of champion, dyn-share ≥0.5, causal signature intact, index
byte-aligned).

---

## 6. Engine replay (structural-caliber Sharpe)

```bash
python multi_asset/engine/replay_fullhist.py --funding_mode rank --shaping cap        # canonical → 12.21
python multi_asset/engine/replay_fullhist.py --funding_mode rank --shaping calibrated # deployable-calibrated → 10.84
```

> ⚠️ **Caliber discipline (read before quoting any Sharpe).** The engine number is a
> **structural-caliber upper bound**: frictionless except an explicit 1.9 bps cost, daily×√365,
> market-neutral. It is a **signal-quality ceiling, not a deployment net-Sharpe.** Deployment must
> layer the maker-fill execution stack (adverse-selection markout, fill-rate<1, queueing, impact,
> capacity) and will be materially lower. Benchmark against research/signal-level Sharpes, never
> against a fund's after-all-cost net. See `RUNBOOK.md` for the three-tier caliber contract.

**CHECKPOINT 6:** `exports/eda/engine_fullhist_replay.json` → **avg net 12.21**, per-year net
`[9.64 / 11.77 / 12.55 / 16.04 / 11.05]`, rank-IC `[.062/.086/.081/.076/.062]`, hedge 12.4% /
savings 202 bps/yr. Calibrated variant → 10.84.

---

## One-glance verification ladder

| stage | command | expected |
|---|---|---|
| 1 acquire | `dump_wide_universe.py` + `repair_cdn_enum.py` | 0 false-NODATA / truncated coins; coverage to 2026-06-30 |
| 2 panel | `build_wide_dl.py` | `CH (48168,140,32)`, panel_ref md5 `185d3b65`, YR σ≈0.01 |
| 3 train king | `train_wide_harness.py … --lam_orth 0 --xattn` | honest IC ≈ 0.0817, per-year all + , dyn_share ≈ 0.97 |
| 3 train S2 | `… --target_horizon 24 --dense_train --embargo_days 10` | incremental IC ≈ +0.005, sign-consistent |
| 4 stitch | `king_pred_panel.py` , `densify_s2_cl4.py` | pred panels finite only at OOS anchors |
| 5 gate | `acceptance_battery.py --self-test` then `--candidate` | `SELF-TEST OK`; candidate PASS 8/8 |
| 6 engine | `replay_fullhist.py --funding_mode rank --shaping cap` | avg net Sharpe **12.21** (structural) |

Licensed inputs (1s `bar_data`, Tardis book) are **not** needed for this chain — the shipped
four-leg book is built entirely from Binance public klines/funding/metrics. See `MANIFEST.md`
for the data-source tiering.
