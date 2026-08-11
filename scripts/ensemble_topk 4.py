"""Ensemble top-K checkpoints by val_corr (SWA-style checkpoint averaging).

Given a fold directory with ``topk/epoch_*.pt`` files (as saved by
trainer_v2 when the topk-capture block is active), select the K checkpoints
with highest val_corr and either:
  (A) WEIGHT-AVERAGE them (classic SWA) — produces a single averaged model
      that can replace best_model.pt for inference.
  (B) PREDICTION-AVERAGE them — runs each checkpoint's forward on the test
      set separately and averages / medians the predictions. More robust to
      weight-space discontinuities (e.g., when architectures differ).

Usage
-----
  # Weight averaging (SWA):
  python scripts/ensemble_topk.py \\
    --fold-dir experiments/v4_noattn_700d/fold_0 \\
    --mode weight --k 5 \\
    --out experiments/v4_noattn_700d/fold_0/swa_model.pt

  # Prediction averaging on existing test_preds:
  python scripts/ensemble_topk.py \\
    --fold-dir experiments/v4_noattn_700d/fold_0 \\
    --mode pred --k 5 --agg median \\
    --test-dataset data/npz_v4 \\
    --test-days 2025-01-08 2025-01-09 ... \\
    --config configs/v4_noattn_700d.json

For `mode=pred` you still need a working forward path for each checkpoint.
The weight-average mode is a one-shot tensor operation with no GPU needed
after loading.

Reference: Izmailov et al. 2018, arXiv:1803.05407.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List

import numpy as np
import torch


def select_topk_checkpoints(topk_dir: pathlib.Path, k: int) -> List[Dict]:
    """Load all epoch_*.pt in topk_dir, sort by val_corr desc, take top-K."""
    entries = []
    for p in sorted(topk_dir.glob("epoch_*.pt")):
        ck = torch.load(p, map_location="cpu", weights_only=False)
        entries.append((float(ck.get("val_corr", 0.0)), int(ck.get("epoch", 0)), p, ck))
    if not entries:
        raise RuntimeError(f"No epoch_*.pt checkpoints found in {topk_dir}")
    # Highest val_corr first
    entries.sort(key=lambda r: -r[0])
    picked = entries[: min(k, len(entries))]
    print(f"[ensemble_topk] selected top-{len(picked)} by val_corr:")
    for vc, ep, path, _ in picked:
        print(f"  epoch={ep:3d} val_corr={vc:+.4f} {path.name}")
    return [r[3] for r in picked]


def weight_average(ckpts: List[Dict]) -> Dict:
    """Simple tensor mean over model state_dicts (classic SWA).

    Requires all checkpoints to have the same architecture (same keys + shapes).
    BatchNorm buffers would need separate handling; our models use LayerNorm so
    this is a clean state_dict mean.
    """
    first = ckpts[0]["state"]
    avg = {k: v.detach().clone().float() for k, v in first.items()}
    for ck in ckpts[1:]:
        for k, v in ck["state"].items():
            avg[k].add_(v.detach().float())
    n = float(len(ckpts))
    for k in avg:
        avg[k].div_(n)
    # Cast back to original dtype per key.
    for k in avg:
        if first[k].dtype != avg[k].dtype:
            avg[k] = avg[k].to(first[k].dtype)
    return {
        "state": avg,
        "class": ckpts[0]["class"],
        "config": ckpts[0]["config"],
        "ensemble": {
            "n_checkpoints": len(ckpts),
            "epochs": [ck.get("epoch") for ck in ckpts],
            "val_corrs": [ck.get("val_corr") for ck in ckpts],
            "method": "weight_mean",
        },
    }


def prediction_median(fold_dir: pathlib.Path) -> Dict[str, np.ndarray]:
    """Median-aggregate predictions already saved per top-K checkpoint.

    Expected layout: fold_dir/topk_preds/epoch_{N}_preds.npz — produced by
    running a separate inference pass for each topk checkpoint (not done
    by this script; caller must generate them).
    """
    preds_dir = fold_dir / "topk_preds"
    paths = sorted(preds_dir.glob("epoch_*_preds.npz"))
    if not paths:
        raise RuntimeError(
            f"No per-checkpoint test_preds found in {preds_dir}. "
            "Run inference first (e.g., via run_backtest.py on each topk ckpt)."
        )
    preds_stack = []
    targets = None
    mask = None
    for p in paths:
        d = np.load(str(p))
        preds_stack.append(d["predictions"])
        if targets is None:
            targets = d["targets"]
            mask = d["mask"]
    # Median across checkpoints (axis 0) → (N, 3)
    stacked = np.stack(preds_stack, axis=0)
    median = np.median(stacked, axis=0)
    return {
        "predictions": median,
        "targets": targets,
        "mask": mask,
        "n_checkpoints": np.array(len(preds_stack)),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fold-dir", required=True)
    p.add_argument("--mode", choices=["weight", "pred"], default="weight")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--out", default=None,
                   help="Output path. Default: {fold_dir}/swa_model.pt for weight mode.")
    p.add_argument("--agg", choices=["mean", "median"], default="median",
                   help="Aggregation for pred mode. Median is robust to heavy tails.")
    args = p.parse_args()

    fold_dir = pathlib.Path(args.fold_dir)
    topk_dir = fold_dir / "topk"

    if args.mode == "weight":
        ckpts = select_topk_checkpoints(topk_dir, args.k)
        avg = weight_average(ckpts)
        out = args.out or (fold_dir / "swa_model.pt")
        torch.save(avg, str(out))
        print(f"[ensemble_topk] wrote {out}")
        # Record manifest for reproducibility
        (fold_dir / "swa_manifest.json").write_text(
            json.dumps(avg["ensemble"], indent=2)
        )
    else:
        result = prediction_median(fold_dir)
        out = args.out or (fold_dir / "test_preds_topk.npz")
        np.savez(str(out), **result)
        print(f"[ensemble_topk] wrote {out} (n_ckpts={result['n_checkpoints']})")


if __name__ == "__main__":
    main()
