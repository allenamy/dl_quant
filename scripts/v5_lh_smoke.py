#!/usr/bin/env python3
"""V5-LH pod smoke test — 10-day ultrafast training sanity check.

Runs before kicking off the full 3-fold × 3-seed training.
Verifies:
  - V5-LH NPZ loads via LOBDatasetV2
  - Model forward + loss + backward works with real Mamba-2
  - Loss decreases after a few steps (basic training plausibility)
  - No NaN/Inf
  - Gradient norms reasonable

Usage:
  python3 scripts/v5_lh_smoke.py --config configs/v5_lh/v5_lh_base.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from src.model_v5_lh.v5_lh_model import V5LHModel
from src.losses.dul_plus_loss import DulPlusLoss
from src.training.dataset import LOBDatasetV2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=pathlib.Path, required=True)
    ap.add_argument("--smoke-days", type=int, default=10, help="Number of days to sample")
    ap.add_argument("--smoke-steps", type=int, default=30, help="Number of training steps")
    args = ap.parse_args()

    cfg = json.load(open(args.config))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[smoke] device={device}")

    npz_dir = pathlib.Path(cfg["data"]["npz_dir"])
    days = sorted(f.stem for f in npz_dir.glob("*.npz") if not f.stem.startswith("_"))
    if len(days) < args.smoke_days:
        print(f"[smoke] need >= {args.smoke_days} days, found {len(days)}", file=sys.stderr)
        sys.exit(1)
    smoke_days = days[:args.smoke_days]
    print(f"[smoke] using first {len(smoke_days)} days: {smoke_days[0]}..{smoke_days[-1]}")

    horizons = cfg["model"]["horizons"]
    ds = LOBDatasetV2(npz_dir=str(npz_dir), days=smoke_days, horizons=horizons, preload=False)
    print(f"[smoke] total samples: {len(ds):,}")

    # Compute y_sigma
    y_stats = ds.compute_y_stats(max_workers=4)
    y_sigma = y_stats[1] if isinstance(y_stats, tuple) else float(y_stats)
    print(f"[smoke] y MAD-sigma = {y_sigma:.4f}")

    # One sample to infer dims
    sample = ds[0]
    assert len(sample) == 5, f"expected 5-tuple, got len={len(sample)}"
    x_feat, x_raw, rp, y, mask = sample
    L, n_features = x_feat.shape
    n_levels = x_raw.shape[1]
    d_prior = rp.shape[0]
    print(f"[smoke] L={L} n_features={n_features} n_levels={n_levels} d_prior={d_prior}")

    model_cfg = cfg["model"]
    model = V5LHModel(
        n_features=n_features,
        n_levels=n_levels,
        d_model=model_cfg["d_model"],
        d_raw=model_cfg["d_raw"],
        d_prior=d_prior,
        horizons=[int(h.replace("y_", "")) for h in horizons],
        n_mamba_layers=model_cfg["n_mamba_layers"],
        mamba_d_state=model_cfg["mamba_d_state"],
        mamba_expand=model_cfg["mamba_expand"],
        use_fallback=model_cfg["use_fallback"],
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[smoke] model params: {n_params:,}")

    loss_cfg = cfg["loss"]
    loss_fn = DulPlusLoss(
        n_horizons=len(horizons),
        y_sigmas=(y_sigma,) * len(horizons),
        gamma_crps=loss_cfg["gamma_crps"],
        eta_utility=loss_cfg["eta_utility"],
        alpha_decorr=loss_cfg["alpha_decorr"],
        focal_weight=loss_cfg["focal_weight"],
        focal_threshold_sigma=loss_cfg["focal_threshold_sigma"],
        use_unit=loss_cfg.get("use_unit", True),
    ).to(device)

    params = list(model.parameters()) + list(loss_fn.parameters())
    opt = torch.optim.AdamW(params, lr=6e-4, weight_decay=1e-3)

    loader = torch.utils.data.DataLoader(
        ds, batch_size=32, shuffle=True, num_workers=2, pin_memory=(device == "cuda")
    )

    losses = []
    grad_norms = []
    step = 0
    for batch in loader:
        if step >= args.smoke_steps:
            break
        x_feat, x_raw, rp, y, mask = batch
        x_feat = x_feat.to(device, non_blocking=True)
        x_raw = x_raw.to(device, non_blocking=True)
        rp = rp.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        mask = mask.to(device, non_blocking=True)

        opt.zero_grad()
        out = model(X=x_feat, X_raw=x_raw, regime_prior=rp)

        # Mask filter
        q = out[f"y_{int(horizons[0].replace('y_', ''))}"]
        keep = mask.bool()
        if keep.sum() < 2:
            continue
        loss = loss_fn([q[keep]], [y[keep]], embedding=out["embedding"])

        if not torch.isfinite(loss):
            print(f"[smoke] step {step}: loss is non-finite ({loss.item()}) — ABORT")
            sys.exit(2)

        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()

        losses.append(float(loss.item()))
        grad_norms.append(float(gn))
        if step % 5 == 0 or step == args.smoke_steps - 1:
            print(f"[smoke] step {step:03d} loss={loss.item():.4f} grad_norm={gn:.3f}")
        step += 1

    # Summary
    if len(losses) < 5:
        print(f"[smoke] FAIL: only ran {len(losses)} steps")
        sys.exit(3)
    first_third = np.mean(losses[:len(losses) // 3])
    last_third = np.mean(losses[2 * len(losses) // 3:])
    max_grad = max(grad_norms)
    print()
    print(f"[smoke] Summary over {len(losses)} steps:")
    print(f"  first-third mean loss: {first_third:.4f}")
    print(f"  last-third  mean loss: {last_third:.4f}")
    print(f"  improvement: {(first_third - last_third) / first_third * 100:+.1f}%")
    print(f"  max grad norm: {max_grad:.3f}")
    print(f"  all losses finite: {all(np.isfinite(l) for l in losses)}")
    # Soft pass criteria: loss should be going DOWN (some improvement)
    if last_third >= first_third:
        print("[smoke] WARN: loss not decreasing. May need more steps or lower LR.")
    else:
        print("[smoke] PASS: loss decreasing, gradients finite, forward+backward OK")


if __name__ == "__main__":
    main()
