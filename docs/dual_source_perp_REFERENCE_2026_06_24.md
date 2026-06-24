# Dual-Source Perp y_600 — Collaborator Reference (2026-06-24)

> **创建:** 2026-06-24 | **Session:** dual-source-perp overnight | **状态:** final | **作废条件:** superseded by a newer measured ladder or a leak finding on dp32_a02.

Source material for the paradigm doc + the best-model git push. All numbers measured, dual-caliber (DENSE = all stride windows; CLEAN = non-overlapping ≥600s, 4 offsets), RAW perp y_600. Server = `ssh jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset`, env `hsy_v5push`. Local mirror = `/Users/haosiyu/Desktop/quant_research`.

---

## 1. SYNC STATUS (server-only vs already-local)

**Code — ALL 7 key files ALREADY LOCAL (md5-identical to server)** — edited locally + scp'd throughout:
- `multi_asset/data/dual_lob_dataset.py` (f16-fix)
- `multi_asset/data/v2arch_dataset.py` (f16-fix)
- `multi_asset/train/train_v2arch.py` (multi-horizon wiring + snapshot-skip thread)
- `multi_asset/train/train_dual_lob.py`
- `multi_asset/model/dual_lob_regarch.py` (perp residual + snapshot-skip)
- `multi_asset/model/dual_lob_v2arch.py`
- `multi_asset/eval/eval_caliber.py`

**Configs — were SERVER-ONLY, now rsync'd to local** (created on server via json.dump):
- `configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json` ← **THE BEST MODEL**
- `configs/npzv4_dual/perp_dp48_a02_2025_04.json`
- `configs/npzv4_dual/dp32_a02_realxl_k51_2025_04.json`
- `configs/npzv4_dual/perp_dp32_a02_2025_04.json` (baseline; server had nw0, local had nw4 — now reconciled to server)
- `configs/v2arch/dp32_nobasis_2026_05.json` (choppy baseline)
- `configs/v2arch/dp32_adaptive_2026_05.json` (choppy adaptive)

**Experiment log** → copied to `docs/v2_autonomous_overnight_2026_06_24.md`.

The regime/adaptive MECHANISM code lives in the READ-ONLY parent `src/model/dual_path_model_v3.py` + `src/model/regime_film.py` (REG_arch base, inherited — not in multi_asset/).

---

## 2. THE BEST MODEL = "adaptive" — precise mechanism

**Config:** `configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json` (strong) / `configs/v2arch/dp32_adaptive_2026_05.json` (choppy). Identical model block; differ only in cache/fold.

**"adaptive" = baseline REG_arch + perp gated residual + TWO regime-conditioning components** (the v2arch comment "NO regime-gating" refers to an OLD ablation; the adaptive config turns the gate ON via these flags):

Model-block flags that make it adaptive:
```
"use_perp_residual": true,     "d_perp": 32,  "perp_alpha_init": 0.02,   (deeper-perp + gentle gate)
"use_film_multistage": true,                                            (regime_prior FiLM in backbone)
"use_regime_film": true, "regime_film_hidden": 8,                       (REGIME-VOL FiLM on pooled head)
"use_regime_bias": true                                                  (zero-init regime bias head)
```

**MECHANISM (the regime gate):**
1. **RegimeFiLM** (`use_regime_film`): a `RegimeFeatureExtractor` (non-learnable, causal) computes 6 regime descriptors from X — realized-vol at 60s / 300s / 1200s scales, vol-acceleration (vol_60/vol_1200), OBI mean (feat 0), and lag-60 OBI autocorrelation — then a FiLM MLP (hidden=8) outputs (γ, β) that modulate the pooled embedding: `h_pred ← γ ⊙ h_pred + β`. **Identity-init (γ≈1, β≈0)** so it starts == baseline and learns the regime modulation. This is what suppresses the perp/basis contribution in high-vol (strong) regimes and leans on it in choppy — a vol/trend FiLM, NOT a [0,1] basis gate, NOT basis-dynamics.
2. **regime_bias_head** (`use_regime_bias`): a **zero-init** MLP that adds a regime-conditioned per-horizon bias from `regime_prior`, applied after output_scale.

NOT what makes it adaptive: it is NOT the falsified ±γ signed basis gate, NOT the basis-dynamics block (those were dropped), NOT the snapshot-skip-path (built but dormant/cancelled).

---

## 3. EXACT reproduction commands

```bash
ssh jpline
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
export PYTHONPATH=.
PY=/root/miniconda3/envs/hsy_v5push/bin/python

# STRONG (test 2025-04-10), train700, f16-resident (default ON), nw0/preload, σ-gate patience=10
$PY -u multi_asset/train/train_v2arch.py \
   --config configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json \
   --start-fold 0 --max-folds 1 --seed 42
$PY multi_asset/eval/eval_caliber.py \
   --preds experiments/npzv4_dual/perp_dp32_a02_adaptive_2025_04/fold_0/test_preds.npz --ema

# CHOPPY (test 2026-05), train300/batch256 (proven-safe on heavy v2arch cache)
$PY -u multi_asset/train/train_dual_lob.py \
   --config configs/v2arch/dp32_adaptive_2026_05.json \
   --start-fold 0 --max-folds 1 --seed 42
$PY multi_asset/eval/eval_caliber.py \
   --preds experiments/v2arch_dp32/dp32_adaptive_2026_05/fold_0/test_preds.npz --ema
```
- **f16-fix env:** ON by default (resident X stored float16). Set `DUAL_PRELOAD_X_F32=1` to revert to f32.
- **Recipe:** epochs=25, batch=1024 (strong) / 256 (choppy heavy cache), lr=6e-4, wd=1e-3, patience=10 (matches σ-gate crossing ~ep7 + buffer), EMA decay 0.999, embargo 1 day, val_metric=composite.
- **Loss (singh α=0 huber):** dul_config — `utility_alpha=0.0`, `lambda_utility_rank=0.5`, `lambda_dir_huber=0.5` (w_wrong=0), `lambda_quantile=0.1`, `lambda_mag_focal_huber=0.3`, `lambda_cls=0.1`, `cls_weight_mode=tail_focal_1p5`.

---

## 4. FINAL LADDER (measured, dual-caliber)

**STRONG (test 2025-04, target dense 0.10):**
| model | BEST DENSE | BEST CLEAN | β (dense) | note |
|---|---|---|---|---|
| dp32_a02 baseline (nobasis) | 0.0732 | 0.1026 | 1.49 | reference; EMA 0.0747/0.1033 |
| **adaptive (regime gate)** | **0.0747** | **0.1054** | **0.98** | +0.0015/+0.0028, β≈1 (best calib), S 0.082 |
| realxl (real X_long long-ctx) | 0.0547 | 0.0992 | 0.82 | **−0.018/−0.024 NEGATIVE (dead lever)** |
| dp48 / mh180 | pending | pending | | running |

**CHOPPY (test 2026-05, target 0.06):**
| model | EMA CLEAN | β | note |
|---|---|---|---|
| dp32 nobasis | 0.0294 | 0.69 | first real choppy DL |
| **adaptive (regime gate)** | **0.0402** | 1.6 | +0.011 clean over nobasis; BEST-ckpt CLEAN 0.0346 |
| Ridge (best linear, same fold/caliber) | 0.0315 | — | DL≈Ridge parity; adaptive EMA > Ridge |

**ROOT-CAUSE (choppy):** No Ridge>DL gap — apples-to-apples (same fold/caliber) Ridge 0.029/0.032 ≈ DL nobasis 0.028/0.029; adaptive 0.040 EXCEEDS Ridge. Temporal-dilution FALSIFIED (window-mean 0.027 > last-step 0.018 — signal in the average, not the snapshot). Choppy ~0.03-0.04 = genuine in-data signal ceiling; 0.06 needs orthogonal data (funding/OI).

**LEAK TEST (shuffle-future null on dp32_a02):** trained on PERMUTED y, eval vs REAL target → σ collapses 0.088→0.006, PERP-target P=−0.055 (σ-collapse artifact, not signal). **PASS — the 0.080/0.113 strong result is leak-free.**

**BEST SINGLE BOTH-REGIME MODEL = adaptive:** strong 0.0747/0.1054 (β 0.98) + choppy 0.0402 — ≥ nobasis (0.0732/0.1026 + 0.0294) in BOTH regimes, with near-perfect strong β. Gate does NOT leak basis into strong. Caveats: strong dense ~0.075 < 0.10; choppy 0.040 < 0.06 (in-data ceiling).

---

## 5. CODE LOCATIONS (file:line)

| component | location |
|---|---|
| deeper-perp tower (d_perp=32) | `multi_asset/model/dual_lob_regarch.py:98` (`self.d_perp`), encoder built L128-130 (`RawLOBEncoder(d_raw=self.d_perp)`) |
| gentle gate (perp_alpha_init=0.02) | `multi_asset/model/dual_lob_regarch.py:91` (param), L144-145 (`self.perp_alpha = nn.Parameter(...)`); inject: `h = h + tanh(perp_alpha)·g·perp_proj(h_perp)` (L21 docstring; perp_proj L136-138) |
| regime FiLM (vol/trend gate) | build `src/model/dual_path_model_v3.py:451-462` (`RegimeFeatureExtractor()` + `FiLM(hidden=8)`); apply L1149 / `dual_lob_regarch.py:322-324`. Classes in `src/model/regime_film.py` |
| regime bias head (zero-init) | build `src/model/dual_path_model_v3.py:873-886`; apply L1268-1269 |
| loss (singh α=0 huber) | config `dul_config` (utility_alpha=0.0 + plain Huber w_wrong=0 + pinball + mag_focal_huber 0.3) |
| f16-fix (train700 RAM) | `multi_asset/data/dual_lob_dataset.py:155-168` (`x_store_dtype`, env `DUAL_PRELOAD_X_F32`); mirror in `v2arch_dataset.py` `_do_preload` |
| dual-caliber eval | `multi_asset/eval/eval_caliber.py` |
