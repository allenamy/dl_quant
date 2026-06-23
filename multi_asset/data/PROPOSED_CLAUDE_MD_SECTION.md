<!-- PROPOSED text to paste into CLAUDE.md (a new "## Data Foundation" section,
     place it directly after the "Project Identity" / "Universe" data blocks).
     This file is a scratch deliverable; do NOT commit it — paste its body. -->

## Data Foundation — `data/npz_btc_unified` (single source, verified)

**这是 BTC 唯一 canonical 缓存** — 取代所有混淆的旧缓存 (`npz_v4` / `npz_spot` /
`npz_perp` / `npz_spot2perp*` / `npz_dual*`)。Builder:
`multi_asset/data/build_unified_npz.py`，verifier: `verify_unified_npz.py`，
manifest: `data/npz_btc_unified/MANIFEST.md`。

**唯一数据源 (READ-ONLY):** `/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/`
`{book_snapshot_25,trades}/<day>/{binance(=spot),binance-futures(=perp)}/`。
绝不读 `share`/`bar_data`/`23-25-BTCUSDT`，绝不把任何 `npz_*` 当 source。

**被它终结的 confound (本 session 实证):** 旧缓存的 "0.02 vs 0.06 gap" 是
**trade-venue scaling 假象**。X std 差异 (npz_spot 7.9 vs npz_v4 ~25 vs npz_perp
28.8) 100% 来自 16 个 trade/volume 特征 —— **perp 成交量 ~6× spot**，不是任何
pipeline/quantize/normalize 差异 (`build_npz_for_day` 三者逐字节相同)。48 个
book/price 特征跨 spot 缓存 corr **1.0000** 且 std 完全相同；只有 16 个 trade
特征发散。"median per-feature corr 1.000" 这个说法掩盖了正好这 16 个 (median 把
16/64 离群值藏掉了)。
- `npz_v4` (milestone) = **SPOT book + PERP trades** (旧 share root 的 caliber bug)。
- `npz_spot` = SPOT book + SPOT trades = **operational 0.08 yardstick** (`clean_strong_spot2spot_apr.json`)。
- ⇒ unified `X_spot` = SPOT book + SPOT trades (gate2 复现 npz_spot corr 1.0000 /
  std ratio 1.0000)；`X_perp` = PERP book + PERP trades。两个 venue 都显式可验。

**Schema (per UTC day, windowed input_len=600/stride=180, pred_idx=t=feature cutoff):**
- Fine 1s: `X_spot`(N,600,64) `X_perp`(N,600,64) f32 RAW (RevIN/per-fold std 在
  下游)；`Xraw_spot`/`Xraw_perp`(N,600,**25**,4) f16 全 25 档；`X_cross`(N,600,8)
  STABLE 跨 venue 比值 + bounded basis LEVEL (**无 divergence SEQ** —— 会让模型
  collapse)。
- Long 60s-pooled 4h: `X_long`(N,240,10) spot+perp summary + basis，prior-day 左
  stitch (绝不 next day)，leak-free。
- Regime/书形: `regime_prior`(N,6) milestone 原版 + `X_rg`(N,8) bounded 多尺度 RG
  + `X_bs`(N,12) BS 书形变化。
- Targets (全 future-only，re-anchor offset 0): `y_spot_600` `y_perp_600` `y_180`
  `y_1800` + 各 `y_mask_*`。Meta: `timestamps`(µs) `mask` + 各 channel names。

**Normalization:** fine-64 存 RAW (下游 per-fold std + RevIN，所以与 milestone
等价、gate2 逐特征复现)；新 channel (cross/long/rg/bs) 存 RAW + bounded，norm
常数在 milestone fold-0 train window (2023-08-08..2025-01-28) fit，`--fit-norm`
时写入 (train-only，leak-free)。

**Phase-1 gates (实证 PASS):** (1) source grep；(2) X_spot vs npz_spot 逐特征
corr 1.0000 / std ratio 1.0000；(3) targets leak-free (offset-0 maxΔ=0,
past-perturb maxΔ=0, forward-sensitive, perp-vs-spot 0.9988)；(5) X_cross/X_long
shuffle-future maxΔ=0；(6) finite/bounded。(4) acceptance spot→spot ~0.08 见
MANIFEST。**FULL-HISTORY build 仍 GATED** —— 须 coordinator 批准 + gate4 通过。
单日 ~172 MB → 全史 ~215 GB。
