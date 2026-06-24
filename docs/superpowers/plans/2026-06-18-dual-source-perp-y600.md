# Dual-Source (Spot+Perp) Single-Asset Perp y600 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **All sub-agents use model `opus` (Opus 4.8).**

**Goal:** Build a single-asset BTC model that predicts the **PERP** 10-min forward return (`y_600` on binance-futures mid) using **both spot and perp** microstructure, trained with **rolling monthly-retrain**, pushing toward Pearson ≥0.10 in strong/trending months and ≥0.07 in choppy 2026.

**Architecture:** `DualLOBREGArch` — a subclass of the proven `DualPathLOBModelV3` (REG_arch). Spot is the **primary directional source** (measured ~2× more predictive than perp); perp enters only as a **zero-init gated residual** (deep 25-level book) + **regime-FiLM**, never as a parallel concat (anti-pattern #29). Basis / cross-venue factors enter by **REPLACING** measured-weaker spot feature slots. Training = long-history **pretrain → low-LR monthly finetune** (the one proven choppy lever, +40% over frozen).

**Tech Stack:** PyTorch; existing REG_arch modules (`RevIN`, `GDCN`, `RawLOBEncoder`, `Conformer`, `FiLMGate`, `MonotonicQuantileHead`/DAQH); `run_pipeline_v3.py` (`--init-from`, `--start-fold`/`--max-folds`); Tardis `book_snapshot_25` + `trades` (spot `binance` + perp `binance-futures`); server `jpline` (conda env `hsy_v5push`, repo `/mnt/storage/private/work_hsy/quant_research_multi_asset`).

## Honest Expectation (read before building)

Adversarially-verified probabilities: **P(strong ≥0.10) ≈ 10%, P(choppy ≥0.07) ≈ 4%.** The single-asset BTC residual ceiling (~0.08 strong, set by BTC having ~0 idiosyncratic residual) and choppy concept-drift-as-random-walk make the headline targets unlikely **on the data on disk** (funding/OI confirmed ABSENT). The **shippable, defensible win** is: a rolling-retrained spot→perp REG_arch + basis-aware feature block, expected **strong ~0.075–0.088 / choppy ~0.035–0.045**, net-positive at maker fees in trending regimes via conviction hold-and-amortize. **Build bottom-up; each stage has a GO/NO-GO gate; report the gap honestly at each checkpoint rather than forcing the target.**

---

## Global Constraints

Every task implicitly includes these (copied from CLAUDE.md + this session's verified findings):

- **READ-ONLY:** `src/` and `configs/` *existing* files — import only, never edit. All new code under `multi_asset/`. New config files in `configs/v5push/` are allowed (new files only).
- **Data READ-ONLY:** `/mnt/storage/share` and `/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31` opened `mode="r"`; never modify/delete.
- **Ridge-before-DL:** no feature/channel goes to GPU until a from-scratch single-asset temporal **Ridge walk-forward** clears **ΔP ≥ +0.005** (new feature) / **+0.003** (model channel), sign-consistent across all folds.
- **#29 channel-addition penalty:** each ADDED Path-A input channel costs ~−0.013 IC unless it carries ≥+0.003 alpha. **Prefer REPLACE** (swap into a measured-weaker slot, 64-in/64-out) or **gated residual** over naive concat.
- **σ-gate:** deployed checkpoint is the σŷ/σy ≥ 0.02 best-val checkpoint. Watch the σ-warmup × patience trap (cold runs need patience ≈ σ-crossing+4 ≈ 10; warm finetune patience 3 OK only if fold-0 σ@ep1 ≥ 0.02).
- **Eval discipline:** RAW `y_600` for scoring (5σ-clip copy only for loss stability); dual-caliber (Pearson **and** Spearman) + β + σŷ/σy + 5-bin monotonicity + bias_bps; **clean (stride≥600) AND dense (stride-180)**; per-month regime-stratified (strong 2025-02/04 vs choppy 2026 monthly); per-fold sign-consistent.
- **No leakage:** cross-venue / basis / lead-lag features strictly ≤ t. Cross-venue join = exact-timestamp `searchsorted(side='right')-1`, NEVER forward-fill perp `t+δ` onto spot `t`; assert `spot.index == perp.index` per day. Every such feature passes the **shuffle-future null** + a **venue-cross-shift sentinel** (shift spot +600s → Ridge ΔP must JUMP; unshifted must NOT).
- **No learned regime gate** (regime-MoE failed 3×) — any regime mechanism is FIXED-CAUSAL. **rank-loss stays AUX** (α=0), pinball-L1 primary (prevents σ-collapse). No `stride < horizon`.
- **Loss & trainer UNCHANGED** from the proven recipe: `utility_rank(α=0, 0.5) + plain-Huber(0.5, w_wrong=0) + pinball(0.1) + mag_focal_huber(0.3) + cls(0.1)`; EMA 0.999 + σ-gate BEST checkpoint.
- **All sub-agents: Opus 4.8.**

---

## File Structure

New files (all under `multi_asset/`, plus configs + this plan):

- `multi_asset/data/build_dual_npz.py` — builds `data/npz_dual/<day>.npz` = perp NPZ (X=64 spot-feats, X_raw_perp 20lvl, regime_prior, **y_600 on PERP mid**) **+ new key `X_raw_spot`** (N,600,20,4) from the spot book at the SAME UTC seconds.
- `multi_asset/data/dual_lob_dataset.py` — `DualLOBDataset` wrapping `LOBDatasetV2` to also yield `x_raw_spot` (and the perp deep-book tensor in Stage D).
- `multi_asset/data/build_interaction_factors.py` — computes the 6 cross-venue/basis factors (Stage C) into the NPZ feature slots, strictly ≤t.
- `multi_asset/eda/perpY_ridge_gate.py` — **from-scratch** single-asset temporal Ridge walk-forward gate (NOT `gate0_btc_perp.py`, which is cross-sectional/N=14 and degenerates at N=1).
- `multi_asset/eda/leakage_null.py` — shuffle-future null + venue-cross-shift sentinel harness.
- `multi_asset/model/dual_lob_regarch.py` — `DualLOBREGArch(DualPathLOBModelV3)`: spot raw Path B + perp deep-book gated residual + d_prior 6→9 regime-FiLM.
- `multi_asset/train/train_dual_lob.py` — trainer shim: unpacks the dual-LOB batch, passes `x_raw_spot=` (and perp deep book) into `model.forward`.
- `multi_asset/eval/perp_battery.py` — dual-caliber eval (Pearson/Spearman/β/σ-ratio/mono/bias), clean+dense, per-month strong-vs-choppy.
- `multi_asset/backtest/backtest_perp_csh.py` — copy of `backtest_csh_v4_retail.py` repointed to perp prices + perp USDT-M fees, conviction hold-and-amortize.
- Configs: `configs/v5push/perp_anchor.json`, `perp_roll.json`, `perp_roll_basis.json`, `perp_roll_duallob.json`, `perp_roll_regimefilm.json` (new files).

**Stage dependency:** A → B (shippable floor) → C → D → E → F → G. Each stage Ridge-gates THEN DL-gates; a NO-GO keeps the prior stage's artifact as the deliverable.

---

## Task A1: Dual NPZ builder (spot raw LOB aligned to perp grid)

**Files:**
- Create: `multi_asset/data/build_dual_npz.py`
- Reuse (import, read-only): `multi_asset/data/build_regarch_perp_npz.py`, `multi_asset/data/build_regarch_spot_npz.py` (spot reader monkeypatch), the `extract_raw_lob_tensor` helper used by the perp builder.
- Output: `data/npz_dual/<day>.npz`

**Interfaces:**
- Produces: per-day NPZ with keys `X (N,600,64)`, `X_raw (N,600,20,4)` (perp), **`X_raw_spot (N,600,20,4)`**, `regime_prior (N,6)`, `y_600 (N,)`, `y_mask_600 (N,)`, `timestamps (N,)` (µs). Target = **perp mid** forward 600s return. Window starts/timestamps are the **perp** windowing verbatim; spot raw is extracted at the identical UTC seconds.

- [ ] **Step 1: Write the alignment test (failing).** `multi_asset/data/test_dual_npz.py`:

```python
import numpy as np, subprocess, os
def test_dual_npz_alignment():
    # build one day
    subprocess.run(["python","multi_asset/data/build_dual_npz.py","--days","2025-02-10"],check=True)
    z=np.load("data/npz_dual/2025-02-10.npz",allow_pickle=True)
    assert z["X_raw_spot"].shape==z["X_raw"].shape            # same (N,600,20,4)
    assert z["X"].shape[-1]==64 and z["y_600"].shape[0]==z["X"].shape[0]
    # timestamps strictly increasing, µs
    ts=z["timestamps"]; assert (np.diff(ts)>0).all() and ts.max()>2e12
```

- [ ] **Step 2: Run it, expect FAIL** (`build_dual_npz.py` missing).
  Run: `python -m pytest multi_asset/data/test_dual_npz.py -x -q` → FAIL.

- [ ] **Step 3: Implement `build_dual_npz.py`.** Build the perp day via `build_regarch_perp_npz.build_one_day` logic (X, X_raw perp, regime_prior, y_600 on perp mid, timestamps). Then load the **spot** book for the same day (spot reader from `build_regarch_spot_npz`), and for **each perp window's timestamps array**, extract the spot 20-level raw tensor at the identical seconds via `searchsorted(spot_book_seconds, perp_window_seconds, side='right')-1` (assert exact match, no forward-fill). Save all keys atomically (`.tmp.` then rename). `--days` and `--all` flags; skip existing.

- [ ] **Step 4: Run the test, expect PASS.**
  Run: `python -m pytest multi_asset/data/test_dual_npz.py -x -q` → PASS.

- [ ] **Step 5: Commit.**
  `git add multi_asset/data/build_dual_npz.py multi_asset/data/test_dual_npz.py && git commit -m "feat(dual): build_dual_npz — perp NPZ + spot raw LOB aligned to perp grid"`

---

## Task A2: From-scratch single-asset Ridge gate + leakage harness

**Files:**
- Create: `multi_asset/eda/perpY_ridge_gate.py`, `multi_asset/eda/leakage_null.py`
- Test: `multi_asset/eda/test_leakage_null.py`

**Interfaces:**
- `perpY_ridge_gate.py`: `ridge_walkforward(feat_matrix, y, day_ids, folds) -> {per_fold_P, per_fold_S, pooled_P, beta, sign_consistent}`. Walk-forward train≥230d / val20 / test40, embargo1, RAW y, MAD-σ normalize, 3 folds over strong(2025-02,04)+choppy(2026). Single-asset only — **no cross-sectional z-score** (gate0_btc_perp.py is N=14, degenerate at N=1; do not reuse).
- `leakage_null.py`: `shuffle_future_null(build_fn, cut_second)` + `venue_cross_shift_sentinel(...)`.

- [ ] **Step 1: Write leakage-null unit test (failing).** `test_leakage_null.py`: build features for one day with a synthetic feature `f = future_return` (a deliberate leak); assert `shuffle_future_null` flags it (null IC ≈ real IC after corrupting post-cut data → leak detected); and a strictly-≤t feature passes (null ≈ 0).

- [ ] **Step 2: Run → FAIL** (`leakage_null.py` missing).

- [ ] **Step 3: Implement `leakage_null.py` + `perpY_ridge_gate.py`.** `shuffle_future_null`: rebuild features after corrupting all raw data strictly after `cut_second`; assert windows with `pred_idx ≤ cut` are byte-identical (no lookahead). `venue_cross_shift_sentinel`: shift spot +600s, recompute interaction features, Ridge ΔP must JUMP (proves it *would* exploit a leak), unshifted must not.

- [ ] **Step 4: Run → PASS.** `python -m pytest multi_asset/eda/test_leakage_null.py -x -q` → PASS.

- [ ] **Step 5: GATE A — reproduce spot-only base + clean null.** Run `perpY_ridge_gate.py` on `data/npz_dual` spot-64 features (last-ts) over strong+choppy folds.
  Run: `python multi_asset/eda/perpY_ridge_gate.py --npz data/npz_dual --feats spot64 --report`
  **GO** if pooled raw P reproduces the known spot base **0.037–0.044** AND `shuffle_future_null` collapses to ~0. **NO-GO:** abort and fix the builder if the null leaks.

- [ ] **Step 6: Commit.** `git add multi_asset/eda/perpY_ridge_gate.py multi_asset/eda/leakage_null.py multi_asset/eda/test_leakage_null.py && git commit -m "feat(dual): from-scratch single-asset Ridge gate + leakage-null harness (GATE A)"`

---

## Task B1: Rolling-retrain Ridge gate (the proven lever, perp target)

**Files:**
- Modify: `multi_asset/eda/perpY_ridge_gate.py` (add `--mode frozen|rolling`)

**Interfaces:**
- Consumes: `ridge_walkforward` from A2.
- Produces: a `{frozen_pooled_P, rolling_pooled_P, frozen_beta, rolling_beta}` comparison on perp `y_600`.

- [ ] **Step 1: Add rolling vs frozen to the gate.** `frozen`: fit on 2023..2025-12, eval each 2026 month. `rolling`: refit trailing-400d ending M-1, eval month M.

- [ ] **Step 2: GATE B0.** Run: `python multi_asset/eda/perpY_ridge_gate.py --npz data/npz_dual --feats spot64 --mode both --report`
  **GO** if `rolling_pooled_P − frozen_pooled_P ≥ +0.005` AND `rolling_beta` closer to 1 (mirror of the measured spot result: +0.0071, β 0.27→1.01). **NO-GO:** investigate (perp flow is noisier than spot — discount; if rolling doesn't beat frozen at Ridge level, the DL rolling lever is at risk).

- [ ] **Step 3: Commit.** `git add -A && git commit -m "feat(dual): rolling-vs-frozen Ridge gate B0 on perp y600"`

---

## Task B2: Anchor pretrain + monthly finetune (SHIPPABLE FLOOR)

**Files:**
- Create: `configs/v5push/perp_anchor.json`, `configs/v5push/perp_roll.json`
- Reuse: `run_pipeline_v3.py` (`--init-from` partial-load verified at L735–746), `data/npz_perp` (spot-feature REG_arch → perp target; **no fusion yet**).

**Interfaces:**
- `perp_anchor.json`: full REG_arch on all-history-to-M-1, proven recipe (lr=6e-4, wd=1e-3, dropout=0.2, epochs=25, EMA 0.999, σ-gate, val_days=60, embargo=1, **d_prior=6**, preload=True, train_days≈800 cap, num_workers=0, per-fold separate processes to avoid the 5-fold-single-process OOM at ~190GB).
- `perp_roll.json`: monthly folds `fold_test_starts=[2026-01-01..2026-05-01]`, test_days=31, **warm-start finetune** lr=1e-4, epochs=6, patience=3 (verify fold-0 σ@ep1 ≥ 0.02; if not, bump to 8 — do NOT use the documented near-trap patience=4 cold).

- [ ] **Step 1: Write anchor config + a smoke test.** `multi_asset/train/test_configs.py::test_perp_anchor_loads` — assert `json.load` parses, `d_prior==6`, loss block matches the frozen recipe, `npz_dir=="data/npz_perp"`, `preload==true`, `num_workers==0`.

- [ ] **Step 2: Run → PASS** (config-only test).

- [ ] **Step 3: Train the anchor.** On `jpline`, per-fold separate processes (OOM-safe). Run (background):
  `for i in 0 1 2 3 4; do python run_pipeline_v3.py --config configs/v5push/perp_anchor.json --skip-features --seed 42 --start-fold $i --max-folds $((i+1)); done`
  Verify each fold: `[pipeline_v3] Model parameters: 118,452`, σŷ/σy crosses 0.02 by ~ep3–6, `best_model.pt` saved.

- [ ] **Step 4: Monthly finetune (the rolling lever).** Warm-start each month from the anchor fold: `run_pipeline_v3.py --config configs/v5push/perp_roll.json --init-from experiments/.../perp_anchor/fold_{f}/best_model.pt --start-fold $i --max-folds $((i+1))` for the 5 months. Confirm partial-load copies shape-matched tensors and σ@ep0 > 0.02 (warm).

- [ ] **Step 5: GATE B (DL).** Run `multi_asset/eval/perp_battery.py` on rolling vs frozen perp predictions.
  **GO** if rolling DL beats frozen DL pooled P, β→~1, mono≥0.9, σŷ/σy≥0.02, per-fold sign-consistent. This is the **shippable floor** even if C–F all fail (~60–70% pass; discount for perp flow noise). **NO-GO:** keep the frozen anchor as deliverable; debug rolling.

- [ ] **Step 6: Commit.** `git add configs/v5push/perp_anchor.json configs/v5push/perp_roll.json multi_asset/train/test_configs.py multi_asset/eval/perp_battery.py && git commit -m "feat(dual): perp anchor pretrain + monthly finetune rolling floor (GATE B)"`

---

## Task C1: Cross-venue / basis factors — Ridge gate (most-orthogonal lever)

**Files:**
- Create: `multi_asset/data/build_interaction_factors.py`
- Modify: `multi_asset/eda/perpY_ridge_gate.py` (load interaction-augmented matrix)

**Interfaces:**
- Produces 6 strictly-≤t factors (clip + causal-EMA where noted), to **REPLACE** ridge-informed spot slots {58,59,60,61,62,63} (zero net channels):
  1. `basis_bps = (perp_mid − spot_mid)/spot_mid * 1e4` (clip ±50)
  2. `basis_ema_dev_60s = basis − causalEMA60(basis)` (de-meaned mean-reversion; raw level drifts with funding)
  3. `perp_spot_obi_diff_L5 = obi_L5^perp − obi_L5^spot`
  4. `perp_spot_microdev_diff = microprice_dev^perp − microprice_dev^spot`
  5. `spot_flow_lead_perp_30s = z30(spot_net_flow) − z30(perp_net_flow)`
  6. `perp_spot_vol_ratio = RV60^perp/(RV60^spot+eps)`

- [ ] **Step 1: Write factor unit tests (failing).** `multi_asset/data/test_interaction.py`: on a synthetic spot/perp pair, assert `basis_bps` sign/scale; `basis_ema_dev_60s` uses only past (shifted EMA, no current-bar leak); all factors finite; shape `(N,600,6)`.

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `build_interaction_factors.py`** with exact-timestamp cross-venue join (`searchsorted side='right'-1`, assert `spot.index==perp.index`), causal EMA (`shift(1)` before use), z-scores over trailing windows.

- [ ] **Step 4: Run → PASS** + leakage gate: `python multi_asset/eda/leakage_null.py --feats interaction6` → shuffle-future null ~0 AND venue-cross-shift sentinel JUMPS. **NO-GO** on any leak.

- [ ] **Step 5: GATE C (Ridge).** `python multi_asset/eda/perpY_ridge_gate.py --feats spot64_replace_interaction --addone --report`
  **GO** per-channel add-one-in ≥ +0.003 each (drop non-passers, revert to spot); block ≥ +0.005 on strong months without hurting choppy by >0.003. Ship only passers. (~45–50% block clears strong; likely survivors: `basis_ema_dev_60s`, `perp_spot_microdev_diff`, `basis_bps`.)

- [ ] **Step 6: Commit.** `git add multi_asset/data/build_interaction_factors.py multi_asset/data/test_interaction.py && git commit -m "feat(dual): cross-venue/basis factors + Ridge GATE C (REPLACE swap, leakage-safe)"`

---

## Task C2: Basis factors into the DL (REPLACE swap) + DL gate

**Files:**
- Create: `configs/v5push/perp_roll_basis.json` (= `perp_roll.json` + the surviving interaction features REPLACING ridge slots; **zero net channels**, n_features stays 64).
- Modify: `multi_asset/data/build_dual_npz.py` (write surviving interaction factors into their slots).

- [ ] **Step 1:** Rebuild `data/npz_dual` with the C1-surviving factors swapped into slots {58–63} (others revert to spot). Verify `X.shape[-1]==64`.

- [ ] **Step 2: Train rolling (anchor→finetune) with the basis feature set.** Same B2 schedule, `--config perp_roll_basis.json`.

- [ ] **Step 3: GATE C-DL.** `perp_battery.py` vs Stage-B.
  **GO** ΔP ≥ +0.005 strong over Stage-B, sign-consistent, no σ-collapse, choppy not hurt. **NO-GO:** keep Stage-B feature set.

- [ ] **Step 4: Commit.** `git add configs/v5push/perp_roll_basis.json && git commit -m "feat(dual): basis factors into rolling DL (GATE C-DL)"`

---

## Task D1: Perp deep-book gated residual (dual-LOB) — model

**Files:**
- Create: `multi_asset/model/dual_lob_regarch.py`, `multi_asset/train/train_dual_lob.py`, `multi_asset/data/dual_lob_dataset.py`
- Test: `multi_asset/model/test_dual_lob_regarch.py`
- Reuse: `RawLOBEncoder`, `FiLMGate` (from `src/model`), `DualPathLOBModelV3`.

**Interfaces:**
- `DualLOBREGArch(DualPathLOBModelV3)` new kwargs: `use_perp_residual=True, perp_n_levels=25, d_perp=16, perp_gate_kind='scalar'`. Forward gains `x_raw_perp_deep` kwarg.
- **Injection (verified site `dual_path_model_v3.py` L1039–1042, after fusion, before Conformer):**

```python
# h is the fused (B,600,32) stream (spot Path-A craft + spot raw Path-B), pre-Conformer
g = torch.sigmoid(self.perp_gate(h))                         # (B,600,32) per-channel data-dep gate
h = h + torch.tanh(self.perp_alpha) * g * self.perp_proj(h_perp_deep)   # zero-init residual
```
where `self.perp_alpha = nn.Parameter(torch.tensor(0.05))` — **init 0.05, NOT 0.0** (verified DMF gradient-starvation bug `temporal_spatial_panel.py` L337–343: a true-zero master gate starves the residual sub-net before early-stop; 0.05 keeps perturbation <1% of ‖h‖ yet feeds gradient from step 1). `perp_proj` weight std=0.02, gate bias=0. Everything downstream (Conformer×2, FiLM-multistage, DAQH) UNCHANGED.

- [ ] **Step 1: Write the zero-init-identity + shape test (failing).** `test_dual_lob_regarch.py`: build `DualLOBREGArch` with `use_perp_residual=True`; with `perp_alpha` *temporarily set to 0.0*, assert forward output equals the parent `DualPathLOBModelV3` forward (bit-identical) for the same spot inputs; assert param count ≈ 123K; assert forward accepts `x_raw_perp_deep (B,600,25,4)` and returns the q10<q50<q90 dict.

- [ ] **Step 2: Run → FAIL** (model missing).

- [ ] **Step 3: Implement `dual_lob_regarch.py`** (subclass; splice the 2-line injection after fusion via a copied `forward` or a `_forward_to_fusion`/`_forward_from_backbone` hook), `dual_lob_dataset.py` (yield `x_raw_perp_deep` from `exports/btc25_raw_perp`), `train_dual_lob.py` (unpack + pass the kwarg).

- [ ] **Step 4: Run → PASS** (identity at α=0, correct shapes, ~123K params).

- [ ] **Step 5: Commit.** `git add multi_asset/model/dual_lob_regarch.py multi_asset/train/train_dual_lob.py multi_asset/data/dual_lob_dataset.py multi_asset/model/test_dual_lob_regarch.py && git commit -m "feat(dual): DualLOBREGArch perp deep-book gated residual (zero-init identity verified)"`

---

## Task D2: Train dual-LOB rolling + DL gate

**Files:**
- Create: `configs/v5push/perp_roll_duallob.json` (= `perp_roll_basis.json` winner + `use_perp_residual`, `npz_dir` with perp deep book).

- [ ] **Step 1:** Wire `btc25_raw_perp` deep book into the dual dataset; verify a batch yields `x_raw_perp_deep (B,600,25,4)`.

- [ ] **Step 2: Train rolling** (anchor→finetune; the anchor must be retrained once *with* the residual at α=0.05, or warm-start the residual sub-net cold). Watch σ-gate (mean/std-pooling residuals can shrink σ — abort fold-0 if σ<0.02 or β crash, the v3/v4/v6/v8 pattern).

- [ ] **Step 3: GATE D-DL.** `perp_battery.py` vs Stage-C.
  **GO** ΔP ≥ +0.005 (concentrate on strong months — dual-LOB is an SNR-union lever, biggest where directional signal pays), no σ-collapse, choppy not hurt. **NO-GO:** keep Stage-C; the residual is the *information union* of spot-flow + perp-deep-book — modest expected lift (perp target already holds the spot signal via 0.99 corr).

- [ ] **Step 4: Commit.** `git add configs/v5push/perp_roll_duallob.json && git commit -m "feat(dual): perp deep-book gated residual rolling DL (GATE D-DL)"`

---

## Task E1: Perp regime-swap features (9 channels) — gated, low priority

**Files:** Modify `build_dual_npz.py` (perp twins into slots {3,4,18,19,20,22,23,54,55}).

- [ ] **Step 1: GATE E (Ridge).** Each perp channel vs its spot twin must clear ΔP ≥ +0.005, sign-consistent. Ship only passers (likely `vpin_300s`, `perp_RV`). **NO-GO per channel:** keep the spot twin.
- [ ] **Step 2:** If any pass, rebuild NPZ + retrain rolling + `perp_battery.py` DL-gate (+0.003). Keep only if it doesn't hurt.
- [ ] **Step 3: Commit.** `git commit -am "feat(dual): perp regime-swap channels (GATE E, ship passers only)"`

---

## Task F1: Regime-FiLM (d_prior 6→9) — likely-null bolt-on, with warm-start fix

**Files:** Create `configs/v5push/perp_roll_regimefilm.json`; modify `build_dual_npz.py` (append 3 causal regime scalars to `regime_prior`: `ER_3600` (Kaufman ER on **spot** mid), `volstate_z` (log-bucketed RV_1h), `basis_regime` (tanh of causal 1h-mean basis_bps)).

**CRITICAL warm-start fix (verified bug):** on 6→9 warm-start, `FiLMGate` trunk `Linear(32,9)` mismatches anchor's `(32,6)` → partial-load **skips** it (random trunk) while `gamma/beta_proj` LOAD trained non-zero weights → **NOT identity** → random affine perturbation at ep0 → σ-collapse risk. **Fix:** after `--init-from`, explicitly copy anchor's 6 trunk columns into the first 6 of 9 and **zero the trailing 3**, restoring true identity.

- [ ] **Step 1: GATE F (Ridge).** Interaction-model (64 feats + 3 regime + feat×regime products) must clear ΔP ≥ +0.003 on choppy AND ≥0 on strong; shuffle-future null ~0. (~15–25% pass.) **NO-GO (likely):** ship Stage B(+C/D) without regime-FiLM.
- [ ] **Step 2:** If pass, implement the warm-start trunk-rezero in `train_dual_lob.py`; train; `perp_battery.py` DL-gate (+0.003 on WF panel without degrading the 2 strong months).
- [ ] **Step 3: Commit.** `git commit -am "feat(dual): regime-FiLM d_prior 6->9 with warm-start trunk-rezero (GATE F)"`

---

## Task G1: Economics / tradeability verdict (perp CSH backtest)

**Files:** Create `multi_asset/backtest/backtest_perp_csh.py` (copy `backtest_csh_v4_retail.py`, repoint perp prices + perp USDT-M fees: maker 2.0 / taker 5.0 bps/side; RT scenarios 4.0/5.8/7.0/10.0; **no basis-slippage term** — target IS perp).

- [ ] **Step 1:** Conviction hold-and-amortize: causal-EMA-demeaned `q50_live`; enter `|q50|≥T_open`, exit on `|q50|<T_close` OR sign-flip OR `max_hold`. Sweep `T_open{1,1.5,2,2.5,3} × max_hold{5,10,20,30}`.
- [ ] **Step 2: Report.** HEADLINE = cross-fold/cross-regime number (NOT a cherry-picked fold-0 cell — verified that the prior "4.4 Sharpe" was 1 of 218/800 positive cells). Print `RT_breakeven = gross_per_trade` per regime; **tradeable iff > fee_RT**.
- [ ] **Step 3: Commit + write CP doc.** `docs/` conclusion doc (with the required metainfo header) stating measured strong/choppy IC vs the 0.10/0.07 targets, the rolling-retrain delta, and the net-of-fee verdict.

---

## CP — Final Checkpoints (report the gap honestly)

| Checkpoint | Pass criterion | If below |
|---|---|---|
| **CP-B** | rolling DL > frozen DL pooled P, β→~1, mono≥0.9 | ship frozen anchor; the rolling lever needs debugging |
| **CP-C** | basis block ΔP ≥ +0.005 strong | the new orthogonal info didn't materialize; single-asset on-disk levers near-exhausted → escalate to multi-asset / funding-OI |
| **CP-final** | strong ≥0.10 / choppy ≥0.07 | **report the gap with the evidence chain** (expected strong ~0.075–0.088 / choppy ~0.035–0.045); recommend funding/OI pull or cross-asset breadth as the only paths to the target |

---

## Self-Review

- **Spec coverage:** perp-as-target ✓ (B), spot+perp inputs ✓ (B spot-feats, D dual-LOB), expanded handcrafted features ✓ (E), spot-perp interaction/basis factors ✓ (C), dual raw-LOB fusion (two-path gated residual) ✓ (D), reuse of FiLM/GDCN/Conformer/conv/feature-cross ✓ (architecture preserved + extended), regime-drift adaptation (rolling-retrain + pretrain→finetune + regime-FiLM) ✓ (B+F), trend/change features ✓ (regime scalars F + basis C). Targets + honest gates ✓.
- **Placeholder scan:** each task has exact files, real code at injection/leakage points, exact run commands, numeric GO/NO-GO thresholds.
- **Type consistency:** `X_raw_spot`/`x_raw_perp_deep` shapes (N/B,600,20or25,4) consistent A→D; `perp_alpha=0.05` consistent; n_features stays 64 (REPLACE) through C/E; d_prior 6→9 only in F with the trunk-rezero fix.
- **Key correction baked in:** basis factors do **not** route via `use_tv_film` (that path feeds GDCN → −0.013×n catastrophe, verified); they enter as REPLACE swaps (C) or the gated residual (D).

---

## Notes for the executor
- Stage B is the deliverable on its own. Do not let C–F block shipping B.
- Every DL run on `jpline`: per-fold **separate processes** (the 5-fold single process OOMs at ~190GB with preload+25-level LOB). `preload=True` fits at train_days≈400 (~95GB); the neighbor's backtest can contend the mount — if a fold hangs at 0% CPU/low-RAM, it's the FUSE/mount, retry when free.
- Inputs are READ-ONLY; new code only under `multi_asset/`.
