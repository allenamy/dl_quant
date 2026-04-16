# V3 Systematic Redesign: Data Scale, Horizon Sweep, Feature Engineering, Module Audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Diagnose why V3 (58K params) lost to Ridge (~58 params), then systematically re-engineer the train-eval pipeline with (a) 10-30× more training samples via dense-stride sampling, (b) multi-horizon label generation (60/180/300/600s), (c) Ridge-informed targeted feature engineering, (d) module-by-module ablation of V3 to keep only components that actually help.

**Architecture:** Phased plan. Phase A diagnoses V3's failure. Phase B multiplies training data via dense-stride sampling and multi-horizon labels. Phase C adds XGBoost + interaction features. Phase D redesigns V3 to be no bigger than it has to be. Each phase's results inform the next.

**Tech Stack:** Python 3.9, PyTorch 2.x, pandas, numpy, sklearn, xgboost

---

## Context

### Current State (after `07d7024` + `74c4cd1` + `15338cd` fixes)

**Data available:** 1004 days of BTCUSDT perp (2023-01-01 → 2025-09-30), already feature-engineered into `data/npz_full/*.npz`. Shape per day: `X(N, 300, 58)`, `X_raw(N, 300, 20, 4)`, `y(N,)` (single horizon = 180s), `y_mask(N,)`. Total 193,919 windows at stride=180.

**Layer-1 baseline results (`experiments/v3_full/baselines.json`, 80/10/10 temporal split):**
```
Ridge                                  corr=+0.1016  r2=+0.010   test_n=18107
TemporalRidge                          corr=+0.0907  r2=+0.007
Flow[net_trade_flow_1s]                corr=+0.0490
MicropriceDeviation[microprice_dev_bps] corr=+0.0260  rank_corr=+0.1234
FITS (26K params, freq domain)         corr=+0.0149
OBI[contrarian][obi_L5]                corr=-0.1008  (sign FLIPPED — OBI positive)
```

**V3 results (first 2 folds before we stopped it):**
```
Fold 0: val_corr=0.013, val_r2=-0.53 (train_loss 0.86 >> val_loss 0.43 → overfit)
Fold 1: val_corr=0.022, val_r2=-0.005 (near-constant predictions)
```

V3 was **5× worse than Ridge**. This is the failure we're unpacking.

### The Physical Question

Is the 3-min BTCUSDT return signal **truly linear at the feature level** (so any non-linearity is overfitting), OR does V3 have bugs / misapplied modules / too-small sample size?

If truly linear → accept Ridge as ceiling and craft linear-friendly features.
If V3 is mis-applied → fix the modules, redesign, retry.

We don't know yet. Phase A's job is to find out.

### Reconsidering Fixed Parameters

**Horizon=180s, input_len=300, stride=180** were all chosen for the single-day V2 pipeline. With 2 years of data, everything should be re-examined:

- **Horizon**: signal-to-cost ratio grows with sqrt(horizon). 10-min may beat 3-min even after fee.
- **Input window**: transformer can handle 600-1200 steps. More context may help if there are genuine slow patterns.
- **Stride**: CLAUDE.md rule `stride ≥ horizon` prevents label-overlap inflation **in eval**. But training can sample densely if eval stays sparse. Standard technique.

### Data-Scale Reality (measured)

Median day has 31,620 seconds of valid data. For 1004 days:

| Train stride | H=60 windows | H=180 | H=300 | H=600 |
|---|---|---|---|---|
| 180 (current) | 173K | 173K | 172K | 170K |
| 60 | 523K | 521K | 519K | 514K |
| 30 | **1.05M** | **1.04M** | **1.04M** | **1.03M** |
| 10 | 3.14M | 3.13M | 3.11M | 3.08M |

At stride=30 we have **28× more training windows** than current. Adjacent labels share 150/180=83% of their horizon (high autocorrelation), so effective info gain is closer to 4-6× — still substantial.

---

## File Structure

```
scripts/
  analyze_ridge_weights.py            # Phase A — dump top feature weights per fold
  v3_module_ablation.py               # Phase A — turn off each V3 component, measure delta
  analyze_distribution_shift.py       # Phase A — feature PSI across train vs test

src/features/
  pipeline.py                         # Phase B — add multi-horizon labels
  multi_day_pipeline.py               # Phase B — expose configurable horizon/input_len
  ridge_informed_features.py (NEW)    # Phase C — feature interactions from Ridge top-k

src/training/
  dense_sampler.py (NEW)              # Phase B — dense train, sparse val/test sampler
  dataset.py                          # Phase B — LOBDatasetV2 supports multi-horizon y

src/baselines/
  xgb_baseline.py (NEW)               # Phase C — XGBoost bridge model

src/model/
  v3_linear.py (NEW)                  # Phase D — V3 with all non-linear modules off
  v3_small.py (NEW)                   # Phase D — 5K-param V3

src/evaluation/
  sweep_runner.py (NEW)               # Phase E — orchestrates full sweep
  final_comparison.py (NEW)           # Phase E — generates comparison report

configs/
  full_run.json                       # current
  sweep_h60.json  (NEW)               # Phase B
  sweep_h300.json (NEW)
  sweep_h600.json (NEW)
  dense_train.json (NEW)              # Phase B — stride_train<<stride_eval
  v3_linear.json  (NEW)               # Phase D
  v3_small.json   (NEW)

data/
  npz_full/                           # existing H=180 single-horizon NPZs
  npz_multihorizon/ (NEW)             # NPZs with y_60, y_180, y_300, y_600

docs/plans/
  2026-04-16-v3-systematic-redesign.md    # THIS FILE

docs/
  PHASE_A_FINDINGS.md (NEW)
  PHASE_B_FINDINGS.md (NEW)
  PHASE_C_FINDINGS.md (NEW)
  PHASE_D_FINDINGS.md (NEW)
  FINAL_REPORT.md (NEW)
```

---

## Phase A: Diagnose V3 Failure (3 tasks, ~2 hours)

Before doing any scale-up work, we need to know **why** V3 lost. Three scripts answer three questions.

### Task A1: Ridge Feature Importance Audit

**Files:**
- Create: `scripts/analyze_ridge_weights.py`
- Create: `docs/PHASE_A_FINDINGS.md`

**Question answered:** Which 10-15 features carry the Ridge signal? Are they single-asset momentum / imbalance / flow? Use this to target Phase C feature engineering.

- [ ] **Step 1: Write failing smoke test**

```python
# tests/test_analyze_ridge_weights.py
import os, sys, tempfile, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_analyze_ridge_weights_produces_json():
    """Smoke test: script runs and writes a JSON with 'top_features' list."""
    with tempfile.TemporaryDirectory() as d:
        # Create 3 tiny fake NPZs
        for date in ["2024-01-01", "2024-01-02", "2024-01-03"]:
            rng = np.random.default_rng(42)
            N = 100
            X = rng.normal(size=(N, 300, 5)).astype(np.float32)
            y = (X[:, -1, 0] * 0.1 + rng.normal(size=N) * 0.001).astype(np.float32)
            np.savez_compressed(
                os.path.join(d, f"{date}.npz"),
                X=X,
                y=y,
                y_mask=np.ones(N, dtype=np.uint8),
                timestamps=np.arange(N, dtype=np.int64),
                features=np.array(["f0", "f1", "f2", "f3", "f4"], dtype=object),
            )

        out_path = os.path.join(d, "weights.json")
        # Import and call directly (script must expose `main(npz_dir, out_path)`)
        from scripts.analyze_ridge_weights import main
        main(npz_dir=d, out_path=out_path, top_k=5)

        with open(out_path) as f:
            report = json.load(f)
        assert "top_features" in report
        assert len(report["top_features"]) <= 5
        # Feature f0 has the planted signal — Ridge must put high weight on it
        feats = [r["feature"] for r in report["top_features"]]
        assert "f0" in feats[:2], f"planted-signal feature should be top-2, got {feats}"
    print("PASS: test_analyze_ridge_weights_produces_json")

if __name__ == "__main__":
    test_analyze_ridge_weights_produces_json()
```

- [ ] **Step 2: Run test — expect import error**

```bash
python3 tests/test_analyze_ridge_weights.py
# ModuleNotFoundError: No module named 'scripts.analyze_ridge_weights'
```

- [ ] **Step 3: Implement script**

```python
# scripts/analyze_ridge_weights.py
"""Dump Ridge coefficient magnitudes per feature to understand where signal lives.

Reads per-day NPZs, does 80/20 temporal split, fits Ridge on flattened
last-timestep features, ranks features by |coef| / target_sigma to get
standardized effect size.  Also computes the per-feature marginal
correlation with y as a sanity check against multicollinearity.

CLI:
    python scripts/analyze_ridge_weights.py --npz-dir data/npz_full \
        --out experiments/v3_full/ridge_weights.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List, Dict

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def load_days(npz_dir: str) -> Dict:
    files = sorted(Path(npz_dir).glob("*.npz"))
    xs, ys, masks, days = [], [], [], []
    feature_names = None
    for p in files:
        d = np.load(p, allow_pickle=True)
        if "X" not in d.files or d["X"].shape[0] == 0:
            continue
        xs.append(d["X"][:, -1, :])  # last timestep only, matches Ridge baseline
        ys.append(d["y"])
        masks.append(d["y_mask"])
        days.append(p.stem)
        if feature_names is None and "features" in d.files:
            feature_names = [str(f) for f in d["features"]]
    return {
        "X": np.concatenate(xs, axis=0).astype(np.float64),
        "y": np.concatenate(ys, axis=0).astype(np.float64),
        "mask": np.concatenate(masks, axis=0).astype(bool),
        "days": days,
        "feature_names": feature_names or [f"f{i}" for i in range(xs[0].shape[-1])],
    }


def temporal_split(n: int, train_frac: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
    cut = int(n * train_frac)
    idx = np.arange(n)
    return idx[:cut], idx[cut:]


def main(npz_dir: str, out_path: str, top_k: int = 20, alpha: float = 1.0) -> None:
    data = load_days(npz_dir)
    X, y, mask = data["X"], data["y"], data["mask"]
    valid = mask
    X, y = X[valid], y[valid]

    tr_idx, te_idx = temporal_split(len(X))
    scaler = StandardScaler().fit(X[tr_idx])
    X_tr = scaler.transform(X[tr_idx])
    X_te = scaler.transform(X[te_idx])

    ridge = Ridge(alpha=alpha, fit_intercept=True).fit(X_tr, y[tr_idx])
    coefs = ridge.coef_
    target_sigma = float(np.std(y[tr_idx]))

    # Standardized effect size = |coef| because X is standardized
    pred_te = ridge.predict(X_te)
    test_corr = float(np.corrcoef(pred_te, y[te_idx])[0, 1])

    # Per-feature marginal correlation for multicollinearity sanity check
    marginal = np.array([
        np.corrcoef(X_tr[:, i], y[tr_idx])[0, 1] for i in range(X_tr.shape[1])
    ])

    order = np.argsort(-np.abs(coefs))[:top_k]
    top_features = []
    for rank, i in enumerate(order, start=1):
        top_features.append({
            "rank": rank,
            "feature": data["feature_names"][i],
            "coef": float(coefs[i]),
            "abs_coef": float(abs(coefs[i])),
            "marginal_corr_with_y": float(marginal[i]),
        })

    report = {
        "n_train": int(len(tr_idx)),
        "n_test": int(len(te_idx)),
        "target_sigma": target_sigma,
        "test_correlation": test_corr,
        "top_features": top_features,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Ridge test_corr={test_corr:.4f} | top-{top_k} saved to {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--alpha", type=float, default=1.0)
    args = ap.parse_args()
    main(args.npz_dir, args.out, args.top_k, args.alpha)
```

- [ ] **Step 4: Run test — expect PASS**

```bash
python3 tests/test_analyze_ridge_weights.py
# PASS: test_analyze_ridge_weights_produces_json
```

- [ ] **Step 5: Run on real data and document findings**

```bash
python3 scripts/analyze_ridge_weights.py \
  --npz-dir data/npz_full \
  --out experiments/v3_full/ridge_weights.json
```

Expected output: Ridge test_corr ≈ 0.10 (matching baseline), top-20 features JSON. Manually copy the top 10 into `docs/PHASE_A_FINDINGS.md` under "Ridge Feature Importance".

- [ ] **Step 6: Commit**

```bash
git add scripts/analyze_ridge_weights.py tests/test_analyze_ridge_weights.py docs/PHASE_A_FINDINGS.md
git commit -m "feat: ridge weight analysis — Phase A1"
```

---

### Task A2: V3 Module Ablation

**Files:**
- Create: `scripts/v3_module_ablation.py`
- Modify: `src/model/dual_path_model_v3.py:30-40` to accept explicit bypass flags (`use_masknet`, `use_gdcn`, `use_raw_path`, `use_attention`, `use_conv`)
- Append to: `docs/PHASE_A_FINDINGS.md`

**Question answered:** Which V3 modules contribute positively vs negatively on this data? Run 1 fold with each module individually disabled.

- [ ] **Step 1: Add bypass flags to DualPathLOBModelV3**

Inspect current `src/model/dual_path_model_v3.py`, find the constructor. Add:

```python
# In DualPathLOBModelV3.__init__ signature, add:
    use_masknet: bool = True,
    use_gdcn: bool = True,
    use_raw_path: bool = True,
    use_attention: bool = True,
    use_conv: bool = True,
```

Inside `forward`:

```python
# Replace the existing masknet/gdcn calls with:
if self.use_masknet:
    h_feat = self.masknet(x_feat)
else:
    h_feat = x_feat

if self.use_gdcn:
    h_feat = self.gdcn(h_feat)
# else skip

# Path B gating
if self.use_raw_path and x_raw is not None:
    h_raw = self.raw_encoder(x_raw)
    h = torch.cat([h_proj(h_feat), h_raw], dim=-1)
    h = self.fusion(h)
else:
    h = self.h_proj_feat_only(h_feat)  # add this fallback projection

# Temporal backbone
if self.use_conv:
    h = self.temporal_conv(h)

if self.use_attention:
    h = self.patch_embed(h)
    h = self.patch_attention(h)
    h_pred = h[:, -1, :]  # last patch
else:
    # straight MLP pool of the last conv output
    h_pred = h[:, -1, :]

# ... rest of forward
```

- [ ] **Step 2: Unit test the bypass flags**

```python
# tests/test_v3_bypass_flags.py
import os, sys
import torch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.model.dual_path_model_v3 import DualPathLOBModelV3

def test_all_bypasses_produce_output():
    cfg = dict(
        n_features=58, n_levels=20, d_model=32, d_raw=16,
        n_mask_blocks=1, n_cross_layers=1, patch_size=10,
        attn_nhead=2, attn_d_ff=64, d_prior=0, dropout=0.0,
        n_horizons=1, n_symbols=1, use_monotonic_quantile=True,
    )
    x_feat = torch.randn(2, 300, 58)
    x_raw = torch.randn(2, 300, 20, 4)

    for combo in [
        dict(),  # all enabled (default)
        dict(use_masknet=False),
        dict(use_gdcn=False),
        dict(use_raw_path=False),
        dict(use_attention=False),
        dict(use_conv=False),
        dict(use_masknet=False, use_gdcn=False,
             use_raw_path=False, use_attention=False, use_conv=False),  # pure linear head
    ]:
        m = DualPathLOBModelV3(**cfg, **combo)
        m.eval()
        with torch.no_grad():
            out = m(x_feat, x_raw=x_raw if combo.get("use_raw_path", True) else None)
        q = out["quantiles"]
        assert q.shape == (2, 3), f"{combo}: shape {q.shape}"
        assert torch.isfinite(q).all(), f"{combo}: non-finite output"
    print("PASS: test_all_bypasses_produce_output")

if __name__ == "__main__":
    test_all_bypasses_produce_output()
```

- [ ] **Step 3: Run unit test — expect PASS after fix**

```bash
python3 tests/test_v3_bypass_flags.py
# PASS: test_all_bypasses_produce_output
```

- [ ] **Step 4: Implement ablation runner**

```python
# scripts/v3_module_ablation.py
"""Run one walk-forward fold with each V3 module individually disabled.

Output: JSON with {ablation_label: {val_corr, val_r2, train_loss, val_loss}}
for the best epoch of each ablation.

CLI:
    python scripts/v3_module_ablation.py --config configs/full_run.json \
        --fold-index 0 --out experiments/v3_full/ablation.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from src.training.dataset import LOBDatasetV2, build_time_series_folds
from src.training.trainer_v2 import train_one_fold_v2
from src.model.dual_path_model_v3 import DualPathLOBModelV3


ABLATIONS = [
    ("full", {}),
    ("no_masknet", dict(use_masknet=False)),
    ("no_gdcn", dict(use_gdcn=False)),
    ("no_raw_path", dict(use_raw_path=False)),
    ("no_attention", dict(use_attention=False)),
    ("no_conv", dict(use_conv=False)),
    ("linear_only", dict(
        use_masknet=False, use_gdcn=False,
        use_raw_path=False, use_attention=False, use_conv=False,
    )),
]


def run_one_ablation(
    *, model_cfg, train_ds, val_ds, device, train_cfg, out_dir, label,
) -> dict:
    model = DualPathLOBModelV3(
        n_features=train_ds.X.shape[-1],
        n_levels=(train_ds.X_raw.shape[-2] if train_ds.has_raw else 20),
        **model_cfg,
    )
    best = train_one_fold_v2(
        model=model,
        train_dataset=train_ds,
        val_dataset=val_ds,
        out_dir=str(Path(out_dir) / label),
        device=device,
        epochs=20,  # shorter for ablation
        batch_size=train_cfg["batch_size"],
        lr=train_cfg["lr"],
        weight_decay=train_cfg["weight_decay"],
        patience=5,
        grad_clip=train_cfg["grad_clip"],
    )
    return {
        "label": label,
        "val_corr": best["val_corr"],
        "val_r2": best["val_r2"],
        "val_loss": best["val_loss"],
        "best_epoch": best["best_epoch"],
    }


def main(config_path: str, fold_index: int, out_path: str) -> None:
    cfg = json.load(open(config_path))
    data_cfg = cfg["data"]
    model_cfg = {k: v for k, v in cfg["model"].items()
                 if k in {"d_model", "d_raw", "n_mask_blocks", "n_cross_layers",
                          "patch_size", "attn_nhead", "attn_d_ff", "d_prior",
                          "dropout", "n_horizons", "n_symbols",
                          "use_monotonic_quantile"}}
    train_cfg = cfg["training"]

    days = sorted([p.stem for p in Path(data_cfg["npz_dir"]).glob("*.npz")])
    folds = build_time_series_folds(
        days, train_days=train_cfg["train_days"],
        val_days=train_cfg["val_days"], test_days=train_cfg["test_days"],
        stride=train_cfg["fold_stride"],
    )
    fold = folds[fold_index]

    train_ds = LOBDatasetV2(data_cfg["npz_dir"], fold["train"], normalize=False)
    x_mean, x_std = train_ds.compute_stats()
    val_ds = LOBDatasetV2(data_cfg["npz_dir"], fold["val"], normalize=False)
    safe_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
    for ds in (train_ds, val_ds):
        ds.X = np.clip((ds.X - x_mean) / safe_std, -10.0, 10.0).astype(np.float32)

    # Target normalization on training portion
    y_tr = train_ds.y[train_ds.mask > 0]
    y_med = float(np.median(y_tr))
    y_sig = max(1.4826 * float(np.median(np.abs(y_tr - y_med))), 1e-9)
    for ds in (train_ds, val_ds):
        ds.y = np.clip((ds.y - y_med) / y_sig, -5.0, 5.0).astype(np.float32)
        ds.y[ds.mask == 0] = 0.0

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    out_dir = Path(cfg["output_dir"]) / "ablation"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for label, flags in ABLATIONS:
        print(f"\n=== Ablation: {label} ===")
        r = run_one_ablation(
            model_cfg={**model_cfg, **flags},
            train_ds=train_ds, val_ds=val_ds, device=device,
            train_cfg=train_cfg, out_dir=out_dir, label=label,
        )
        results.append(r)
        print(f"  {label}: val_corr={r['val_corr']:+.4f}")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(results, open(out_path, "w"), indent=2)
    print(f"\nAblation results saved to {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fold-index", type=int, default=0)
    ap.add_argument("--out", required=True)
    main(ap.parse_args().config, ap.parse_args().fold_index, ap.parse_args().out)
```

- [ ] **Step 5: Run on fold 0 and document**

```bash
python3 scripts/v3_module_ablation.py \
  --config configs/full_run.json \
  --fold-index 0 \
  --out experiments/v3_full/ablation.json
```

Expected: runs 7 variants × 20 epochs ≈ 30-45 min. Copy results into `docs/PHASE_A_FINDINGS.md`. **Key decision:** keep modules where disabling them *decreases* val_corr; drop modules where disabling *increases* val_corr.

- [ ] **Step 6: Commit**

```bash
git add src/model/dual_path_model_v3.py scripts/v3_module_ablation.py \
        tests/test_v3_bypass_flags.py docs/PHASE_A_FINDINGS.md
git commit -m "feat: V3 module ablation flags + runner — Phase A2"
```

---

### Task A3: Distribution Shift Analysis

**Files:**
- Create: `scripts/analyze_distribution_shift.py`

**Question answered:** Does Population Stability Index (PSI) > 0.2 on ANY feature between train and test portions of fold 0? If yes, non-stationarity — not overfitting — is the dominant failure mode.

- [ ] **Step 1: Implement PSI computation**

```python
# scripts/analyze_distribution_shift.py
"""Compute Population Stability Index (PSI) per feature across train/val/test
for fold 0 of the full_run config.

PSI(train || test) = sum_bins (p_test - p_train) * log(p_test / p_train)

Rule-of-thumb interpretation (industry standard, e.g. Morgan Stanley):
    PSI < 0.1   : negligible distribution shift
    0.1 <= PSI < 0.25 : mild shift, model may degrade
    PSI >= 0.25 : significant shift, recalibrate

CLI:
    python scripts/analyze_distribution_shift.py --config configs/full_run.json \
        --fold-index 0 --out experiments/v3_full/psi.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np

from src.training.dataset import LOBDatasetV2, build_time_series_folds


def psi(train: np.ndarray, test: np.ndarray, n_bins: int = 10) -> float:
    """Population Stability Index between train and test samples of one feature."""
    eps = 1e-6
    # Use train quantiles as bin edges so each bin has equal train mass
    edges = np.quantile(train, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    p_tr = np.histogram(train, bins=edges)[0] / max(len(train), 1) + eps
    p_te = np.histogram(test, bins=edges)[0] / max(len(test), 1) + eps
    return float(np.sum((p_te - p_tr) * np.log(p_te / p_tr)))


def main(config_path: str, fold_index: int, out_path: str) -> None:
    cfg = json.load(open(config_path))
    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    days = sorted([p.stem for p in Path(data_cfg["npz_dir"]).glob("*.npz")])
    folds = build_time_series_folds(
        days, train_days=train_cfg["train_days"],
        val_days=train_cfg["val_days"], test_days=train_cfg["test_days"],
        stride=train_cfg["fold_stride"],
    )
    fold = folds[fold_index]
    train_ds = LOBDatasetV2(data_cfg["npz_dir"], fold["train"], normalize=False)
    test_ds = LOBDatasetV2(data_cfg["npz_dir"], fold["test"], normalize=False)

    # Use last-timestep features (matches Ridge baseline)
    X_tr = train_ds.X[train_ds.mask > 0, -1, :].astype(np.float64)
    X_te = test_ds.X[test_ds.mask > 0, -1, :].astype(np.float64)

    # Need feature names — read from one NPZ
    d0 = np.load(Path(data_cfg["npz_dir"]) / f"{fold['train'][0]}.npz", allow_pickle=True)
    feats = [str(f) for f in d0["features"]]

    results = []
    for i, name in enumerate(feats):
        p = psi(X_tr[:, i], X_te[:, i])
        results.append({"feature": name, "psi": p})
    results.sort(key=lambda r: -r["psi"])

    # Also: target distribution shift
    y_tr = train_ds.y[train_ds.mask > 0]
    y_te = test_ds.y[test_ds.mask > 0]
    target_psi = psi(y_tr, y_te)

    out = {
        "fold": fold_index,
        "train_size": int(len(X_tr)),
        "test_size": int(len(X_te)),
        "target_psi": target_psi,
        "target_train_mean": float(y_tr.mean()),
        "target_train_std": float(y_tr.std()),
        "target_test_mean": float(y_te.mean()),
        "target_test_std": float(y_te.std()),
        "top_10_shifted_features": results[:10],
        "all_features": results,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"Target PSI: {target_psi:.3f} (>0.25 = severe shift)")
    print("Top 10 shifted features:")
    for r in results[:10]:
        print(f"  {r['feature']:40s} PSI={r['psi']:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fold-index", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    main(args.config, args.fold_index, args.out)
```

- [ ] **Step 2: Run on fold 0**

```bash
python3 scripts/analyze_distribution_shift.py \
  --config configs/full_run.json \
  --fold-index 0 \
  --out experiments/v3_full/psi.json
```

- [ ] **Step 3: Document in PHASE_A_FINDINGS.md**

Append a section "Distribution Shift (Fold 0)" with: target PSI, top-10 shifted features with PSI values, interpretation.

- [ ] **Step 4: Commit**

```bash
git add scripts/analyze_distribution_shift.py docs/PHASE_A_FINDINGS.md
git commit -m "feat: distribution shift analysis — Phase A3"
```

---

## Phase B: Data Regime Expansion (4 tasks, ~4-6 hours)

Once Phase A tells us where signal lives, we multiply training data 10-30× without touching eval validity.

### Task B1: Multi-Horizon Label NPZ

**Files:**
- Modify: `src/features/pipeline.py:85-95` (the `build_npz_for_day` function signature and label computation)
- Modify: `src/features/multi_day_pipeline.py:290-335` (forward horizon list through)
- Create: `scripts/regen_multihorizon_npz.py`

**Goal:** Add `y_60`, `y_180`, `y_300`, `y_600` fields to NPZ files (replacing the single `y`). This lets a multi-horizon model predict all four horizons from the same input.

- [ ] **Step 1: Modify `build_npz_for_day` to accept horizon list**

In `src/features/pipeline.py`, change signature:

```python
def build_npz_for_day(
    df_1s: pd.DataFrame,
    *,
    trades_df: pd.DataFrame | None = None,
    horizons_sec: list[int] = None,   # NEW: default [60, 180, 300, 600]
    input_len: int = 300,
    stride: int = 180,
    n_levels: int = 25,
    feature_clip: float = 1000.0,
) -> dict:
    """Build sliding-window arrays with one label per horizon."""
    if horizons_sec is None:
        horizons_sec = [60, 180, 300, 600]
```

Then replace the label-computation loop:

```python
# --- build sliding windows ----------------------------------------------
starts = list(range(0, n_total - input_len + 1, stride))

X_list, X_raw_list, ts_list = [], [], []
ys_by_horizon = {h: [] for h in horizons_sec}
masks_by_horizon = {h: [] for h in horizons_sec}

for start in starts:
    X_win = feat_matrix[start : start + input_len]
    X_raw_win = raw_tensor[start : start + input_len]
    pred_idx = start + input_len - 1

    X_list.append(X_win)
    X_raw_list.append(X_raw_win)
    ts_list.append(timestamps_all[pred_idx])

    for h in horizons_sec:
        target_idx = pred_idx + h
        if target_idx < n_total and mid_prices[pred_idx] > 0:
            ys_by_horizon[h].append(
                float(np.log(mid_prices[target_idx] / mid_prices[pred_idx]))
            )
            masks_by_horizon[h].append(1)
        else:
            ys_by_horizon[h].append(0.0)
            masks_by_horizon[h].append(0)
```

Finally, assemble output dict with one `y_{H}` and `y_mask_{H}` per horizon:

```python
result = {
    "X": np.array(X_list, dtype=np.float32),
    "X_raw": np.array(X_raw_list, dtype=np.float32),
    "timestamps": np.array(ts_list, dtype=np.int64),
    "features": feature_cols,
    "horizons_sec": np.array(horizons_sec, dtype=np.int64),
}
for h in horizons_sec:
    result[f"y_{h}"] = np.array(ys_by_horizon[h], dtype=np.float32)
    result[f"y_mask_{h}"] = np.array(masks_by_horizon[h], dtype=np.uint8)

# Back-compat: point `y` and `y_mask` at the 180s horizon
if 180 in horizons_sec:
    result["y"] = result["y_180"]
    result["y_mask"] = result["y_mask_180"]

return result
```

- [ ] **Step 2: Update `np.savez_compressed` call in `process_csv_to_npz` and `multi_day_pipeline`**

In `src/features/pipeline.py`, the `np.savez_compressed(...)` call must include the new keys. Replace the explicit kwargs with:

```python
np.savez_compressed(out_path, **result)
```

In `src/features/multi_day_pipeline.py:343` (the equivalent call), do the same.

- [ ] **Step 3: Add `horizons_sec` param to `process_multi_day_crypto_folder`**

```python
def process_multi_day_crypto_folder(
    book_root: str | Path,
    trades_root: str | Path | None,
    output_dir: str | Path,
    *,
    horizons_sec: list[int] | None = None,  # NEW
    horizon_sec: int = 180,  # kept for back-compat, used only if horizons_sec is None
    input_len: int = 300,
    stride: int = 180,
    ...
):
    if horizons_sec is None:
        horizons_sec = [horizon_sec]
    ...
    # In per-day build call:
    result = build_npz_for_day(
        df_1s, trades_df=trades_df,
        horizons_sec=horizons_sec,
        input_len=input_len, stride=stride, n_levels=n_levels,
    )
    # Also update the min-rows check:
    min_rows = input_len + max(horizons_sec)
```

- [ ] **Step 4: Test multi-horizon NPZ generation**

```python
# tests/test_multihorizon_npz.py
import os, sys, tempfile, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.pipeline import build_npz_for_day

def test_multi_horizon_labels():
    """Each horizon gets its own y_{H} and y_mask_{H}; back-compat y for 180s."""
    N = 1500  # 25 minutes — fits all horizons
    mid = 60_000.0 + np.cumsum(np.random.default_rng(42).normal(0, 1, N))
    df = pd.DataFrame({
        "timestamp": np.arange(N, dtype=np.int64) * 1_000_000,
    })
    for i in range(25):
        df[f"asks[{i}].price"] = mid + 1 + i * 0.5
        df[f"asks[{i}].amount"] = 1.0
        df[f"bids[{i}].price"] = mid - 1 - i * 0.5
        df[f"bids[{i}].amount"] = 1.0

    result = build_npz_for_day(
        df, horizons_sec=[60, 180, 300, 600],
        input_len=300, stride=180, n_levels=25,
    )
    for h in [60, 180, 300, 600]:
        assert f"y_{h}" in result, f"missing y_{h}"
        assert f"y_mask_{h}" in result, f"missing y_mask_{h}"
        assert result[f"y_{h}"].shape == result["X"].shape[:1]
    # back-compat aliases
    assert "y" in result and np.array_equal(result["y"], result["y_180"])
    assert "y_mask" in result and np.array_equal(result["y_mask"], result["y_mask_180"])

    # Longer horizons should have fewer valid labels (tail-end windows masked)
    n_valid_60 = int(result["y_mask_60"].sum())
    n_valid_600 = int(result["y_mask_600"].sum())
    assert n_valid_60 >= n_valid_600, "longer horizon needs more future data → fewer valid"
    print("PASS: test_multi_horizon_labels")

if __name__ == "__main__":
    test_multi_horizon_labels()
```

```bash
python3 tests/test_multihorizon_npz.py
# PASS: test_multi_horizon_labels
```

- [ ] **Step 5: Create regen script**

```python
# scripts/regen_multihorizon_npz.py
"""Regenerate NPZs with multi-horizon labels.

Reuses existing crypto_data/ on-disk books + trades.  Writes to a NEW
output directory (data/npz_multihorizon/) so the old data/npz_full/ is
preserved for A/B comparison.
"""
import argparse
from src.features.multi_day_pipeline import process_multi_day_crypto_folder

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book-root", default="crypto_data/book_snapshot_25")
    ap.add_argument("--trades-root", default="crypto_data/trades/trades")
    ap.add_argument("--output", default="data/npz_multihorizon")
    ap.add_argument("--horizons", default="60,180,300,600",
                    help="comma-separated horizons in seconds")
    ap.add_argument("--input-len", type=int, default=300)
    ap.add_argument("--stride", type=int, default=180,
                    help="NPZ-level stride; keep = max horizon for no label overlap in eval")
    args = ap.parse_args()

    horizons = [int(h) for h in args.horizons.split(",")]
    paths = process_multi_day_crypto_folder(
        book_root=args.book_root,
        trades_root=args.trades_root,
        output_dir=args.output,
        horizons_sec=horizons,
        input_len=args.input_len,
        stride=args.stride,
        n_levels=25,
        skip_existing=True,
    )
    print(f"Wrote {len(paths)} multi-horizon NPZs")

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run on full 1004 days (BACKGROUND, ~5-6h)**

```bash
nohup python3 scripts/regen_multihorizon_npz.py > logs/regen_mh.log 2>&1 &
echo "Check progress: tail -f logs/regen_mh.log"
```

- [ ] **Step 7: Commit**

```bash
git add src/features/pipeline.py src/features/multi_day_pipeline.py \
        scripts/regen_multihorizon_npz.py tests/test_multihorizon_npz.py
git commit -m "feat: multi-horizon labels in NPZ (60/180/300/600s) — Phase B1"
```

---

### Task B2: Dense-Train / Sparse-Eval Sampling

**Files:**
- Create: `src/training/dense_sampler.py`
- Modify: `src/training/dataset.py` (add `stride_override` parameter to LOBDatasetV2)
- Modify: `src/features/pipeline.py` — allow NPZ to store windows at eval-stride, and the dataset expands to denser windows at load time.

**Strategy:** NPZ files stay at `stride=180` (non-overlapping eval). At training time, the dataset reconstructs denser windows from the underlying time series stored inside the NPZ. But that means NPZs must also store `feat_matrix` (the full-day 1s feature matrix) — much bigger.

**Revised strategy (simpler, more disk-friendly):** Build TWO sets of NPZs.

- `data/npz_full/` — stride=180 (existing, used for val/test)
- `data/npz_train_dense/` — stride=30 (new, used ONLY for training)

Walk-forward fold uses dense for train-days, sparse for val/test-days. The train-days in dense NPZs are DIFFERENT day directories (the SAME underlying data, resampled densely). Same `y` semantics because labels are computed the same way — it's just that we sample starts every 30s instead of every 180s.

- [ ] **Step 1: Regen dense training NPZs**

Use existing `process_multi_day_crypto_folder` — it already accepts `stride` argument:

```bash
nohup python3 -c "
from src.features.multi_day_pipeline import process_multi_day_crypto_folder
process_multi_day_crypto_folder(
    book_root='crypto_data/book_snapshot_25',
    trades_root='crypto_data/trades/trades',
    output_dir='data/npz_train_dense',
    horizons_sec=[60, 180, 300, 600],
    input_len=300,
    stride=30,   # DENSE
    n_levels=25,
    skip_existing=True,
)
" > logs/regen_dense.log 2>&1 &
```

Expected output ~30-60 GB. Check disk first: `df -h ~/Desktop`.

Wait for this AND task B1 to complete before starting the training changes.

- [ ] **Step 2: Modify the pipeline runner to accept separate train / eval NPZ dirs**

In `run_pipeline_v3.py`, find the fold-iteration section (around line 275). Change so that the fold's `train` days load from `cfg["data"]["npz_dir_train"]` and `val`/`test` days load from `cfg["data"]["npz_dir_eval"]` if both keys are present; else both default to `cfg["data"]["npz_dir"]` (back-compat).

```python
npz_dir_train = data_cfg.get("npz_dir_train", data_cfg["npz_dir"])
npz_dir_eval = data_cfg.get("npz_dir_eval", data_cfg["npz_dir"])
...
train_ds = LOBDatasetV2(npz_dir_train, fold["train"], normalize=False)
val_ds = LOBDatasetV2(npz_dir_eval, fold["val"], normalize=False)
test_ds = LOBDatasetV2(npz_dir_eval, fold["test"], normalize=False)
```

- [ ] **Step 3: Write the split test**

```python
# tests/test_dense_sparse_split.py
import os, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_dense_train_sparse_eval_split():
    """Train NPZs have more windows than eval NPZs for the same day."""
    with tempfile.TemporaryDirectory() as d:
        train_dir = os.path.join(d, "dense")
        eval_dir = os.path.join(d, "sparse")
        os.makedirs(train_dir); os.makedirs(eval_dir)

        # Synthesise same day, different stride densities
        n_feats = 3
        def make(stride, n_win):
            X = np.random.randn(n_win, 300, n_feats).astype(np.float32)
            y = np.random.randn(n_win).astype(np.float32)
            mask = np.ones(n_win, dtype=np.uint8)
            np.savez_compressed(
                os.path.join(train_dir if stride == 30 else eval_dir, "2024-01-01.npz"),
                X=X, X_raw=np.zeros((n_win, 300, 20, 4), dtype=np.float32),
                y=y, y_mask=mask,
                timestamps=np.arange(n_win, dtype=np.int64),
                features=np.array(["f0", "f1", "f2"], dtype=object),
            )

        make(30, 500)  # dense
        make(180, 100)  # sparse

        from src.training.dataset import LOBDatasetV2
        ds_dense = LOBDatasetV2(train_dir, ["2024-01-01"], normalize=False)
        ds_sparse = LOBDatasetV2(eval_dir, ["2024-01-01"], normalize=False)
        assert len(ds_dense) == 500
        assert len(ds_sparse) == 100
    print("PASS: test_dense_train_sparse_eval_split")

if __name__ == "__main__":
    test_dense_train_sparse_eval_split()
```

```bash
python3 tests/test_dense_sparse_split.py
# PASS: test_dense_train_sparse_eval_split
```

- [ ] **Step 4: Create dense config**

```json
// configs/dense_train.json
{
  "_comment": "Dense training (stride=30) + sparse eval (stride=180). ~6x training samples per fold with same non-overlapping eval.",
  "data": {
    "npz_dir_train": "data/npz_train_dense",
    "npz_dir_eval": "data/npz_multihorizon",
    "horizon_sec": 180,
    "input_len": 300,
    "n_levels": 25
  },
  "model": {
    "d_model": 32,
    "d_raw": 16,
    "n_mask_blocks": 1,
    "n_cross_layers": 1,
    "patch_size": 10,
    "attn_nhead": 2,
    "attn_d_ff": 64,
    "d_prior": 0,
    "dropout": 0.2,
    "n_horizons": 1,
    "n_symbols": 1,
    "use_monotonic_quantile": true
  },
  "training": {
    "epochs": 30,
    "batch_size": 256,
    "lr": 3e-4,
    "weight_decay": 1e-3,
    "patience": 6,
    "grad_clip": 1.0,
    "train_days": 180,
    "val_days": 30,
    "test_days": 30,
    "fold_stride": 60
  },
  "output_dir": "experiments/v3_dense"
}
```

- [ ] **Step 5: Commit (do NOT run yet — waiting for regen)**

```bash
git add src/training/dataset.py run_pipeline_v3.py \
        tests/test_dense_sparse_split.py configs/dense_train.json
git commit -m "feat: dense-train / sparse-eval NPZ split — Phase B2"
```

---

### Task B3: Longer-Input-Window Option

**Files:**
- Modify: `src/features/pipeline.py` — `input_len` already parameterized; add validation
- Create: `configs/input_600.json`, `configs/input_900.json`

**Goal:** Test whether input_len=600 (10 min) or 900 (15 min) adds signal over input_len=300.

- [ ] **Step 1: Regen input_len=600 NPZs**

```bash
nohup python3 -c "
from src.features.multi_day_pipeline import process_multi_day_crypto_folder
process_multi_day_crypto_folder(
    book_root='crypto_data/book_snapshot_25',
    trades_root='crypto_data/trades/trades',
    output_dir='data/npz_input600',
    horizons_sec=[60, 180, 300, 600],
    input_len=600,  # 10 minutes
    stride=180,
    n_levels=25,
    skip_existing=True,
)
" > logs/regen_input600.log 2>&1 &
```

- [ ] **Step 2: Model must re-check attention positional-embedding size**

Inspect `src/model/dual_path_model_v3.py`. The patch-embedding's `pos_embed` dimension must scale with `input_len / patch_size`. The V3 reviewer flagged this was hardcoded to `max_patches=150`. For input_len=600 with patch_size=10 we need 60 positions, which fits in 150 — OK. For input_len=900 we'd need 90 — still OK. No code change needed at input_len <= 1500.

- [ ] **Step 3: Create input_600 config**

```json
// configs/input_600.json — same as full_run.json except:
{
  "data": {
    "npz_dir": "data/npz_input600",
    "input_len": 600,
    ...
  },
  "model": {
    ...
    "patch_size": 20,  // doubled to keep n_patches ~= 30
    ...
  },
  "output_dir": "experiments/v3_input600"
}
```

- [ ] **Step 4: Commit**

```bash
git add configs/input_600.json logs/regen_input600.log
git commit -m "feat: longer-input-window configs — Phase B3"
```

---

### Task B4: Run Expanded-Data Baselines

**Files:**
- Create: `scripts/sweep_baselines.py`
- Output: `experiments/v3_full/baseline_sweep.json`

**Goal:** After B1/B3 NPZs exist, rerun Ridge/TemporalRidge/FITS/XGBoost across (horizon ∈ {60,180,300,600}) × (input_len ∈ {300,600}). Pick the best cell. This sets the new ceiling V3 must beat.

- [ ] **Step 1: Implement sweep runner**

```python
# scripts/sweep_baselines.py
"""Run all baselines across (horizon, input_len) grid. Dump JSON."""
import argparse
import json
from pathlib import Path
import numpy as np

from run_baselines import load_days, temporal_split, evaluate_all  # reuse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="experiments/v3_full/baseline_sweep.json")
    args = ap.parse_args()

    grid = [
        ("data/npz_multihorizon", 300, [60, 180, 300, 600]),
        ("data/npz_input600",     600, [60, 180, 300, 600]),
    ]
    all_results = []
    for npz_dir, input_len, horizons in grid:
        if not Path(npz_dir).exists():
            print(f"Skipping {npz_dir} — not present")
            continue
        for h in horizons:
            print(f"\n=== npz_dir={npz_dir}  input_len={input_len}  horizon={h} ===")
            # evaluate_all: returns list of dicts with model/corr/r2/...
            res = evaluate_all(npz_dir=npz_dir, horizon_key=f"y_{h}")
            for r in res:
                r["npz_dir"] = npz_dir
                r["input_len"] = input_len
                r["horizon_sec"] = h
                all_results.append(r)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(all_results, open(args.out, "w"), indent=2)
    # Print top 10 cells by correlation
    best = sorted(all_results, key=lambda r: -r.get("correlation", -99))[:10]
    print("\nTop 10 (model, input_len, horizon) cells:")
    for r in best:
        print(f"  {r['model']:30s} il={r['input_len']:<4} h={r['horizon_sec']:<4} corr={r.get('correlation',float('nan')):+.4f}")


if __name__ == "__main__":
    main()
```

Note: this requires minor edits to `run_baselines.py` to expose `evaluate_all()` as a callable and to accept a `horizon_key` arg for picking which `y_{H}` from multi-horizon NPZs. Those edits are ~30 lines.

- [ ] **Step 2: Edit `run_baselines.py` to expose the API**

In `run_baselines.py`, find the `main()` function. Split it into:
- `evaluate_all(npz_dir: str, horizon_key: str = "y") -> List[Dict]` — returns results list
- `main()` — calls `evaluate_all` with CLI args and prints / dumps JSON

Then in `load_days(npz_dir)`, when a NPZ has `y_{H}` fields (new multi-horizon schema), pick the one matching `horizon_key` argument.

- [ ] **Step 3: Run the sweep**

```bash
python3 scripts/sweep_baselines.py \
  --out experiments/v3_full/baseline_sweep.json
```

Expected: ~5-10 min per (input_len, horizon) cell × 8 cells = 40-80 min.

- [ ] **Step 4: Document findings — picks the (input_len*, horizon*) best cell**

Append to `docs/PHASE_B_FINDINGS.md`:
- Best (input_len, horizon) cell by Ridge correlation
- Top-3 cells by each baseline (do Ridge and XGBoost agree?)
- Does longer input_len help even Ridge? If not, transformers likely can't help either.

- [ ] **Step 5: Commit**

```bash
git add scripts/sweep_baselines.py run_baselines.py docs/PHASE_B_FINDINGS.md
git commit -m "feat: baseline sweep across horizon x input_len — Phase B4"
```

---

## Phase C: Ridge-Informed Feature Engineering (3 tasks, ~3 hours)

Phase A tells us **which** features matter. Phase C intensifies them — interactions, thresholds, regime splits. Also introduces XGBoost as the "bridging" baseline between linear (Ridge) and deep (V3).

### Task C1: XGBoost Baseline

**Files:**
- Create: `src/baselines/xgb_baseline.py`

**Goal:** XGBoost at ~100 trees × depth 4 ≈ 10K-50K effective parameters. If it beats Ridge, the signal has useful non-linearity. If it doesn't, we have strong evidence the signal is truly linear and V3 must not attempt non-linearity.

- [ ] **Step 1: Install xgboost**

```bash
pip3 install xgboost --quiet
```

- [ ] **Step 2: Implement XGBoost baseline class**

```python
# src/baselines/xgb_baseline.py
"""XGBoost baseline — the non-linear bridge between Ridge and V3.

Feeds the last-timestep 58-dim feature vector (same as Ridge) into a
gradient boosted tree regressor.  If XGBoost cannot beat Ridge by any
meaningful margin, it indicates that a non-linear model is unlikely to
add value without deeper feature engineering.
"""
from __future__ import annotations
from typing import Dict

import numpy as np


class XGBoostBaseline:
    """Thin wrapper around xgboost.XGBRegressor for consistent API."""

    name = "XGBoost"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        reg_lambda: float = 1.0,
        reg_alpha: float = 0.0,
        min_child_weight: float = 5.0,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ) -> None:
        import xgboost as xgb
        self.model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            reg_lambda=reg_lambda,
            reg_alpha=reg_alpha,
            min_child_weight=min_child_weight,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            random_state=random_state,
            tree_method="hist",
            n_jobs=4,
        )

    def fit(self, X_train: np.ndarray, y_train: np.ndarray) -> "XGBoostBaseline":
        # X: (N, L, F) → take last timestep to match Ridge
        if X_train.ndim == 3:
            X_train = X_train[:, -1, :]
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if X.ndim == 3:
            X = X[:, -1, :]
        return self.model.predict(X)

    def feature_importances(self) -> np.ndarray:
        return self.model.feature_importances_
```

- [ ] **Step 3: Test**

```python
# tests/test_xgb_baseline.py
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_xgb_fits_and_predicts():
    from src.baselines.xgb_baseline import XGBoostBaseline
    rng = np.random.default_rng(42)
    N = 1000
    X = rng.normal(size=(N, 300, 5)).astype(np.float32)
    # Planted non-linear signal: y depends on sign of f0 * f1
    y = (np.sign(X[:, -1, 0] * X[:, -1, 1]) * 0.01 +
         rng.normal(size=N) * 0.001).astype(np.float32)
    tr = np.arange(800); te = np.arange(800, N)

    xgb = XGBoostBaseline(n_estimators=50, max_depth=3)
    xgb.fit(X[tr], y[tr])
    pred = xgb.predict(X[te])
    corr = np.corrcoef(pred, y[te])[0, 1]
    assert corr > 0.15, f"XGBoost should catch interaction, got corr={corr:.3f}"
    print(f"PASS: test_xgb_fits_and_predicts (corr={corr:.3f})")

if __name__ == "__main__":
    test_xgb_fits_and_predicts()
```

```bash
python3 tests/test_xgb_baseline.py
# PASS: test_xgb_fits_and_predicts (corr=~0.3)
```

- [ ] **Step 4: Add XGBoost to `run_baselines.py`**

In `run_baselines.py`, import and add it to the baseline list:

```python
from src.baselines.xgb_baseline import XGBoostBaseline
# ... in the evaluation section:
results.append(eval_model("XGBoost", XGBoostBaseline(), X_train, y_train, X_test, y_test, mask_test, feature_names))
```

- [ ] **Step 5: Run on real data**

```bash
python3 run_baselines.py --npz-dir data/npz_full \
  --output experiments/v3_full/baselines_with_xgb.json
```

Compare to Ridge. Document:
- If XGBoost corr > Ridge corr + 0.01 → **genuine non-linear signal exists**; V3 redesign should focus on non-linear modules
- If XGBoost corr ≈ Ridge corr (within 0.005) → **signal is essentially linear**; V3 should be stripped to near-linear + small residual
- If XGBoost corr < Ridge corr → XGBoost is overfitting; tune hyperparams OR accept linear is optimal

- [ ] **Step 6: Commit**

```bash
git add src/baselines/xgb_baseline.py tests/test_xgb_baseline.py run_baselines.py
git commit -m "feat: XGBoost baseline — Phase C1"
```

---

### Task C2: Ridge-Informed Interaction Features

**Files:**
- Create: `src/features/ridge_informed_features.py`
- Create: `tests/test_ridge_informed_features.py`

**Goal:** Use the top-k Ridge features from A1 to engineer products, ratios, and regime-conditioned variants. Add these to the feature matrix and see if Ridge with expanded features beats plain Ridge.

- [ ] **Step 1: Implement feature builder**

```python
# src/features/ridge_informed_features.py
"""Build interaction / threshold / regime-conditioned features from a
small list of high-importance base features.

The base list is expected to be the top-k Ridge features from Phase A1
(see experiments/v3_full/ridge_weights.json).
"""
from __future__ import annotations
from typing import List

import numpy as np
import pandas as pd


def build_interaction_features(
    df: pd.DataFrame,
    top_features: List[str],
    n_pairs_max: int = 15,
) -> pd.DataFrame:
    """Add squared, product, and ratio features for top_features.

    - f_sq: feature^2 (non-linear threshold)
    - f1_x_f2: pairwise product (interaction)
    - f1_div_f2: pairwise ratio, with 1e-6 floor denominator
    - f_hi_vol / f_lo_vol: feature × hi-vol indicator (regime split)
    """
    out = df.copy()
    vol_col = "realized_vol_30s" if "realized_vol_30s" in df.columns else None

    # Squared terms
    for f in top_features[:10]:
        if f in df.columns:
            out[f"{f}_sq"] = df[f] ** 2

    # Pairwise products (top-5 × top-5 = 10 unique)
    pairs_added = 0
    top5 = top_features[:5]
    for i, a in enumerate(top5):
        for b in top5[i + 1:]:
            if a not in df.columns or b not in df.columns:
                continue
            out[f"{a}_x_{b}"] = df[a] * df[b]
            pairs_added += 1
            if pairs_added >= n_pairs_max:
                break
        if pairs_added >= n_pairs_max:
            break

    # Regime-conditioned variants (high-vol vs low-vol)
    if vol_col:
        vol_median = df[vol_col].median()
        hi_vol = (df[vol_col] > vol_median).astype(float).values
        for f in top_features[:5]:
            if f in df.columns:
                out[f"{f}_hi_vol"] = df[f].values * hi_vol
                out[f"{f}_lo_vol"] = df[f].values * (1.0 - hi_vol)

    return out


INTERACTION_FEATURE_SUFFIXES = ["_sq", "_x_", "_hi_vol", "_lo_vol"]


def is_interaction_feature(name: str) -> bool:
    return any(s in name for s in INTERACTION_FEATURE_SUFFIXES)
```

- [ ] **Step 2: Test**

```python
# tests/test_ridge_informed_features.py
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_builds_expected_columns():
    from src.features.ridge_informed_features import build_interaction_features

    N = 100
    df = pd.DataFrame({
        "obi_L5": np.random.randn(N),
        "microprice_dev_bps": np.random.randn(N),
        "log_return_30s": np.random.randn(N),
        "realized_vol_30s": np.abs(np.random.randn(N)),
    })
    out = build_interaction_features(
        df, top_features=["obi_L5", "microprice_dev_bps", "log_return_30s"],
    )
    assert "obi_L5_sq" in out.columns
    assert "obi_L5_x_microprice_dev_bps" in out.columns
    assert "obi_L5_hi_vol" in out.columns
    assert "obi_L5_lo_vol" in out.columns
    # Sum of hi-vol and lo-vol must equal the raw feature
    np.testing.assert_allclose(
        out["obi_L5_hi_vol"] + out["obi_L5_lo_vol"], df["obi_L5"], rtol=1e-6,
    )
    print("PASS: test_builds_expected_columns")

if __name__ == "__main__":
    test_builds_expected_columns()
```

```bash
python3 tests/test_ridge_informed_features.py
# PASS: test_builds_expected_columns
```

- [ ] **Step 3: Plug into Ridge baseline**

Add a new baseline model `RidgePlusInteractions` to `run_baselines.py` that:
1. Loads Ridge top-k from `experiments/v3_full/ridge_weights.json`
2. Builds interaction features on the last-timestep dataframe
3. Fits Ridge on the expanded feature matrix

Implement as a thin wrapper class similar to `RidgeBaseline`.

- [ ] **Step 4: Run expanded baseline**

```bash
python3 run_baselines.py --npz-dir data/npz_full \
  --include-ridge-interactions \
  --output experiments/v3_full/baselines_with_interactions.json
```

Document delta:
- RidgePlusInteractions corr vs Ridge corr
- If delta > 0.01 → interactions are extractable; V3 should learn similar
- If delta < 0.005 → signal is unambiguously linear

- [ ] **Step 5: Commit**

```bash
git add src/features/ridge_informed_features.py \
        tests/test_ridge_informed_features.py run_baselines.py \
        docs/PHASE_C_FINDINGS.md
git commit -m "feat: ridge-informed interaction features — Phase C2"
```

---

### Task C3: Regime-Segmented Evaluation

**Files:**
- Create: `scripts/regime_segmented_eval.py`

**Goal:** Compute Ridge correlation separately on low-vol / mid-vol / high-vol test-set windows. If Ridge corr is 0.20 on low-vol and -0.02 on high-vol, then one model can't fit both regimes — we need regime-aware routing OR separate models.

- [ ] **Step 1: Implement segmented eval**

```python
# scripts/regime_segmented_eval.py
"""Break Ridge test-set performance down by realized volatility tertile."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scripts.analyze_ridge_weights import load_days, temporal_split  # reuse


def main(npz_dir: str, out_path: str) -> None:
    data = load_days(npz_dir)
    X, y, mask = data["X"], data["y"], data["mask"]
    X, y = X[mask], y[mask]
    # Need realized_vol_30s column to segment
    feats = data["feature_names"]
    if "realized_vol_30s" not in feats:
        raise RuntimeError("realized_vol_30s not in features; cannot segment")
    vol_idx = feats.index("realized_vol_30s")
    vol = X[:, vol_idx]  # X is already last-timestep here

    tr, te = temporal_split(len(X))
    scaler = StandardScaler().fit(X[tr])
    Xs_te = scaler.transform(X[te])
    ridge = Ridge(alpha=1.0).fit(scaler.transform(X[tr]), y[tr])
    pred_te = ridge.predict(Xs_te)
    vol_te = vol[te]

    # Tertile cuts on train-vol (to avoid leakage)
    q33, q66 = np.quantile(vol[tr], [0.33, 0.66])
    segments = {
        "all": np.ones(len(te), dtype=bool),
        "low_vol":  vol_te <= q33,
        "mid_vol":  (vol_te > q33) & (vol_te <= q66),
        "high_vol": vol_te > q66,
    }
    out = {}
    for label, m in segments.items():
        if m.sum() < 50:
            out[label] = {"n": int(m.sum()), "corr": None}
            continue
        corr = float(np.corrcoef(pred_te[m], y[te][m])[0, 1])
        out[label] = {
            "n": int(m.sum()),
            "corr": corr,
            "target_std": float(y[te][m].std()),
            "pred_std": float(pred_te[m].std()),
        }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=2)
    for label in ("all", "low_vol", "mid_vol", "high_vol"):
        r = out[label]
        c = r["corr"]
        c_str = f"{c:+.4f}" if c is not None else "n/a"
        print(f"  {label:10s} n={r['n']:>8,} corr={c_str}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", default="data/npz_full")
    ap.add_argument("--out", default="experiments/v3_full/ridge_by_vol.json")
    args = ap.parse_args()
    main(args.npz_dir, args.out)
```

- [ ] **Step 2: Run and document**

```bash
python3 scripts/regime_segmented_eval.py \
  --npz-dir data/npz_full \
  --out experiments/v3_full/ridge_by_vol.json
```

Append to `docs/PHASE_C_FINDINGS.md`:
- Ridge corr by vol tertile
- If corrs differ by > 0.05 across tertiles → regime-aware architecture (PPNet gate) is justified
- If corrs are similar → single model OK

- [ ] **Step 3: Commit**

```bash
git add scripts/regime_segmented_eval.py docs/PHASE_C_FINDINGS.md
git commit -m "feat: regime-segmented Ridge evaluation — Phase C3"
```

---

## Phase D: V3 Redesign Based on Findings (3 tasks, ~4 hours)

Phase D is CONDITIONAL on Phase A-C findings. If ablation (A2) says "MaskNet hurts, GDCN hurts, attention hurts", Phase D's job is to strip V3 to its minimal winning components. If B4 says "input_len=600 + horizon=300 is best", Phase D uses that config. If XGBoost beats Ridge (C1), Phase D preserves non-linear modules.

### Task D1: V3-Linear (Near-Linear Variant)

**Files:**
- Create: `configs/v3_linear.json`
- Reuses existing bypass flags from A2

**Goal:** Run V3 with EVERY non-linear module disabled — basically a feature-gated linear head with the monotonic quantile wrapper. This tests whether V3's scaffolding can at least match Ridge.

- [ ] **Step 1: Create config**

```json
// configs/v3_linear.json
{
  "_comment": "V3 stripped to near-linear. All non-linear modules bypassed. Tests whether V3's quantile head + gating can match Ridge's 0.10 corr ceiling.",
  "data": {
    "npz_dir": "data/npz_full",
    "horizon_sec": 180,
    "input_len": 300,
    "n_levels": 25
  },
  "model": {
    "d_model": 16,
    "d_raw": 8,
    "n_mask_blocks": 1,
    "n_cross_layers": 1,
    "patch_size": 10,
    "attn_nhead": 1,
    "attn_d_ff": 16,
    "d_prior": 0,
    "dropout": 0.1,
    "n_horizons": 1,
    "n_symbols": 1,
    "use_monotonic_quantile": true,
    "use_masknet": false,
    "use_gdcn": false,
    "use_raw_path": false,
    "use_attention": false,
    "use_conv": false
  },
  "training": {
    "epochs": 20,
    "batch_size": 256,
    "lr": 5e-4,
    "weight_decay": 1e-3,
    "patience": 5,
    "grad_clip": 1.0,
    "train_days": 180,
    "val_days": 30,
    "test_days": 30,
    "fold_stride": 60
  },
  "output_dir": "experiments/v3_linear"
}
```

- [ ] **Step 2: Ensure run_pipeline_v3.py passes the bypass flags through `build_model`**

In `run_pipeline_v3.py`, `build_model` allowed-kwargs set:

```python
allowed = {"d_model", "d_raw", "n_mask_blocks", "n_cross_layers",
           "patch_size", "attn_nhead", "attn_d_ff", "d_prior",
           "dropout", "n_horizons", "n_symbols",
           "use_monotonic_quantile",
           # Ablation flags from A2:
           "use_masknet", "use_gdcn", "use_raw_path", "use_attention", "use_conv"}
```

- [ ] **Step 3: Run 3 folds as a quick validation**

```bash
# Quick 3-fold smoke. Write a small script that restricts `folds` to first 3.
python3 -c "
import json
cfg = json.load(open('configs/v3_linear.json'))
cfg['_max_folds'] = 3  # new override read by run_pipeline_v3
json.dump(cfg, open('configs/v3_linear_3fold.json','w'), indent=2)
"
# Then add the max_folds gate to run_pipeline_v3 where it iterates folds.
```

Inside `run_pipeline_v3.py`:

```python
max_folds = cfg.get("_max_folds", None)
for fold_idx, fold in enumerate(folds):
    if max_folds and fold_idx >= max_folds:
        break
    ...
```

```bash
python3 run_pipeline_v3.py --config configs/v3_linear_3fold.json --skip-features --model V3 2>&1 | tee logs/v3_linear_3fold.log
```

Expected runtime ~30-45 min. Check val_corr per fold.

- [ ] **Step 4: Document**

Append to `docs/PHASE_D_FINDINGS.md`:
- Per-fold val_corr for v3_linear config
- Compare to Ridge (0.10) and to v3_full's Fold 0 (0.013) + Fold 1 (0.022)
- Decision: if v3_linear matches Ridge → the scaffolding is OK; Phase D2 tries adding back modules. If v3_linear FAILS to match Ridge → there's a bug somewhere in the V3 training loop / loss / normalization.

- [ ] **Step 5: Commit**

```bash
git add configs/v3_linear.json configs/v3_linear_3fold.json \
        run_pipeline_v3.py docs/PHASE_D_FINDINGS.md logs/v3_linear_3fold.log
git commit -m "feat: v3-linear stripped variant — Phase D1"
```

---

### Task D2: Additive Module Re-introduction

**Files:**
- Create: `configs/v3_linear_plus_{module}.json` for each module that helped in A2
- Runs sequentially: linear → linear+module1 → linear+module1+module2 → ...

**Goal:** Re-introduce each helpful module one at a time. Keep a module ONLY if val_corr increases by > 0.005.

- [ ] **Step 1: Use A2's ablation.json to order modules by "positive contribution"**

A2 gives `val_corr_full - val_corr_without_X` for each module X. Sort descending — start with the biggest positive contributor.

- [ ] **Step 2: Script the ordered re-introduction**

```python
# scripts/additive_module_build.py
"""Add V3 modules one at a time based on A2 ablation ranking.

Runs 3-fold validation for each cumulative configuration. Writes a
JSON with val_corr per step, so we can see exactly where improvements
plateau or regress.
"""
import argparse, json, subprocess
from pathlib import Path


def main(ablation_path: str, base_config: str, out_path: str) -> None:
    ablation = json.load(open(ablation_path))
    full = next(a for a in ablation if a["label"] == "full")
    # positive contribution = full.val_corr - no_X.val_corr
    contribs = []
    for a in ablation:
        if a["label"].startswith("no_"):
            mod = a["label"][3:]  # e.g. "masknet"
            contribs.append({"module": mod, "delta": full["val_corr"] - a["val_corr"]})
    contribs.sort(key=lambda c: -c["delta"])
    print("Modules by positive contribution:")
    for c in contribs:
        print(f"  {c['module']:12s} delta={c['delta']:+.4f}")

    # Build cumulative configs
    base = json.load(open(base_config))
    enabled = {"use_masknet": False, "use_gdcn": False, "use_raw_path": False,
               "use_attention": False, "use_conv": False}
    results = []
    for i, c in enumerate(contribs):
        flag = f"use_{c['module']}"
        enabled[flag] = True
        new_cfg = dict(base)
        new_cfg["model"] = {**base["model"], **enabled}
        new_cfg["output_dir"] = f"experiments/v3_additive/step_{i}_{c['module']}"
        new_cfg["_max_folds"] = 3
        cfg_path = f"configs/v3_additive_step_{i}.json"
        json.dump(new_cfg, open(cfg_path, "w"), indent=2)

        subprocess.run([
            "python3", "run_pipeline_v3.py",
            "--config", cfg_path, "--skip-features", "--model", "V3",
        ], check=True)

        # Gather per-fold metrics
        metrics = []
        for f in range(3):
            mf = Path(new_cfg["output_dir"]) / f"fold_{f}/metrics.json"
            if mf.exists():
                metrics.append(json.load(open(mf))["val_corr"])
        results.append({
            "step": i, "added_module": c["module"],
            "val_corrs": metrics,
            "mean_val_corr": sum(metrics) / max(len(metrics), 1),
        })

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(results, open(out_path, "w"), indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ablation-json", default="experiments/v3_full/ablation.json")
    ap.add_argument("--base-config", default="configs/v3_linear.json")
    ap.add_argument("--out", default="experiments/v3_additive/summary.json")
    args = ap.parse_args()
    main(args.ablation_json, args.base_config, args.out)
```

- [ ] **Step 3: Run — ~1-3 hours depending on module count**

```bash
python3 scripts/additive_module_build.py \
  --ablation-json experiments/v3_full/ablation.json \
  --base-config configs/v3_linear.json \
  --out experiments/v3_additive/summary.json
```

- [ ] **Step 4: Pick winning configuration**

Read `experiments/v3_additive/summary.json`. The "best" config is the one where `mean_val_corr` peaked — adding more modules degraded it. Copy that step's config to `configs/v3_best_from_additive.json`.

- [ ] **Step 5: Commit**

```bash
git add scripts/additive_module_build.py configs/v3_additive_step_*.json \
        configs/v3_best_from_additive.json docs/PHASE_D_FINDINGS.md
git commit -m "feat: additive module re-introduction — Phase D2"
```

---

### Task D3: Final Full Walk-Forward with Best Config

**Files:**
- Uses `configs/v3_best_from_additive.json` from D2

**Goal:** Run the winning config on all 13 folds. This is the official V3 result to report.

- [ ] **Step 1: Remove `_max_folds` from the config**

```bash
python3 -c "
import json
c = json.load(open('configs/v3_best_from_additive.json'))
c.pop('_max_folds', None)
json.dump(c, open('configs/v3_best_final.json','w'), indent=2)
"
```

- [ ] **Step 2: Run 13-fold walk-forward — ~3-4 hours in background**

```bash
nohup python3 run_pipeline_v3.py --config configs/v3_best_final.json \
  --skip-features --model V3 > logs/v3_best_final.log 2>&1 &
```

- [ ] **Step 3: Aggregate fold results**

```python
# scripts/aggregate_folds.py
import json
from pathlib import Path
import numpy as np

def main(exp_dir="experiments/v3_best_final"):
    folds = sorted(Path(exp_dir).glob("fold_*"))
    vals = []
    for f in folds:
        mf = f / "metrics.json"
        tr = f / "test_results.json"
        if not mf.exists() or not tr.exists():
            continue
        m = json.load(open(mf))
        t = json.load(open(tr))
        vals.append({
            "fold": f.name,
            "val_corr": m["val_corr"],
            "val_r2": m["val_r2"],
            "test_sharpe": t.get("sharpe_annual"),
            "test_net_pnl_bps": t.get("net_pnl_bps"),
            "test_trade_rate": t.get("trade_rate"),
        })
    corrs = [v["val_corr"] for v in vals]
    print(f"N folds: {len(vals)}")
    print(f"val_corr mean={np.mean(corrs):+.4f} std={np.std(corrs):.4f} "
          f"min={min(corrs):+.4f} max={max(corrs):+.4f}")
    print("Per fold:")
    for v in vals:
        print(f"  {v['fold']}: val_corr={v['val_corr']:+.4f} "
              f"r2={v['val_r2']:+.4f} sharpe={v['test_sharpe']}")

if __name__ == "__main__":
    main()
```

```bash
python3 scripts/aggregate_folds.py
```

- [ ] **Step 4: Write final comparison report**

```markdown
<!-- docs/FINAL_REPORT.md -->
# Final Evaluation Report

## Baselines (from experiments/v3_full/baselines.json)
| Model | Test Correlation |
|---|---|
| Ridge | 0.1016 |
| TemporalRidge | 0.0907 |
| XGBoost | [from C1] |
| RidgePlusInteractions | [from C2] |

## V3 Variants (walk-forward, 13 folds)
| Variant | Mean val_corr | Std | Min | Max |
|---|---|---|---|---|
| v3_full (58K params) | 0.018 | ... | ... | ... |
| v3_linear (D1) | ... | ... | ... | ... |
| v3_best_from_additive (D2) | ... | ... | ... | ... |

## Test-set Sharpe / PnL (from test_results.json)
...

## Conclusion
...
```

- [ ] **Step 5: Commit**

```bash
git add scripts/aggregate_folds.py configs/v3_best_final.json \
        logs/v3_best_final.log docs/FINAL_REPORT.md
git commit -m "feat: final 13-fold eval + report — Phase D3"
```

---

## Self-Review

**1. Spec coverage:**
- "two years 数据 37K 太少" → Phase B1 multi-horizon NPZ + B2 dense-train gives ≥6× effective samples ✓
- "transformer 引入步长较长的数据" → Phase B3 input_len=600 ✓
- "预测目标不局限于 3 分钟" → Phase B1 multi-horizon {60,180,300,600} + B4 sweep ✓
- "系统 review V3 没有 Ridge 好的原因" → Phase A1 (features) + A2 (module ablation) + A3 (distribution shift) ✓
- "模型里各个模块的功能,物理意义是否真的经得起推敲" → A2 ablation directly addresses ✓
- "ridge 特征工程经验可以继续深挖强化" → Phase C2 interaction features ✓
- "做定向工程" → Phase A1 → C2/C3 ✓
- "系统性 review 更好的数据处理,包括训练评估数据的组织方式" → Phase B (split strategy, multi-horizon, dense-sparse) ✓

**2. Placeholder scan:** All steps include complete code blocks. No "TODO / fill in" in code.

**3. Type consistency:** `LOBDatasetV2`, `DualPathLOBModelV3`, `build_npz_for_day`, `process_multi_day_crypto_folder`, `train_one_fold_v2` signatures match between tasks. The bypass flags (`use_masknet`, etc.) added in A2 are used consistently in D1/D2.

---

## Gating and Early Exit

The plan is conditional. If any phase delivers a clear answer, the later phases may be simplified or skipped.

- **Gate after Phase A1+A2:** If ablation shows every V3 module HURTS, skip Phase B's data-scale work (won't fix a broken architecture) and go directly to D1 + focused feature engineering.
- **Gate after Phase B4:** If Ridge corr across the (horizon, input_len) grid never exceeds 0.12, the data doesn't have the signal to support a 20K-param V3. Go straight to D1 and accept Ridge as ceiling.
- **Gate after Phase C1:** If XGBoost corr ≤ Ridge corr, stop trying to add non-linearity — D1 is the only V3 variant worth running.

---

## Total Estimated Runtime

| Phase | Wall-clock |
|---|---|
| A1 | 5 min + write-up |
| A2 | 45 min + write-up |
| A3 | 5 min + write-up |
| B1 | 5-6 h NPZ regen (background) |
| B2 | 4-6 h dense NPZ regen (background) |
| B3 | 5 h input_600 NPZ regen (background) |
| B4 | 40-80 min sweep |
| C1 | 20 min training + writeup |
| C2 | 20 min training + writeup |
| C3 | 5 min + writeup |
| D1 | 30-45 min |
| D2 | 1-3 h |
| D3 | 3-4 h (background) |

**Total compute: ~20-30 hours** wall-clock, most of which is NPZ regen + final training in background. Active engineering time is ~4-6 hours.

Plan complete and saved to `docs/plans/2026-04-16-v3-systematic-redesign.md`.
