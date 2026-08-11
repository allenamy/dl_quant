"""Generate V5 B.2 loss screen configs from B.1 winner backbone config.

Usage:
  python scripts/v5_b2_gen_configs.py --winner attention
  → writes configs/v5/screen/loss_quantile.json (control)
           configs/v5/screen/loss_huber.json
           configs/v5/screen/loss_nll.json
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path


CANDIDATES = {"v4base", "attention", "mamba", "emapool"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--winner", required=True, choices=sorted(CANDIDATES))
    p.add_argument("--src-dir", default="configs/v5/screen")
    p.add_argument("--out-dir", default="configs/v5/screen")
    args = p.parse_args()

    src = Path(args.src_dir) / f"backbone_{args.winner}.json"
    if not src.exists():
        raise FileNotFoundError(f"B.1 winner config not found: {src}")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # L0: control = V4 quantile loss (existing pinball + utility_rank)
    # Just copy the winner config as-is. NO V5 loss flags = pipeline runs V4 path.
    p0 = out / "loss_quantile.json"
    shutil.copy(src, p0)
    print(f"[L0] wrote {p0} (control = V4 quantile path, no V5 loss flags)")

    # L1: Huber on raw y (single head magnitude)
    cfg = json.load(open(src))
    cfg.setdefault("loss", {})
    cfg["loss"].update({
        "w_huber_y": 1.0,
        "huber_y_delta": 1.0,
        "w_gaussian_nll": 0.0,
        "w_dir_margin": 0.0,
        "w_mag_huber": 0.0,
        "w_joint_mse": 0.0,
        "head_hidden": 0,
    })
    # Disable existing V4 dul_config when V5 path active
    cfg.setdefault("training", {}).pop("dul_config", None)
    p1 = out / "loss_huber.json"
    json.dump(cfg, open(p1, "w"), indent=2)
    print(f"[L1] wrote {p1} (Huber on raw y, V5 path)")

    # L2: Gaussian NLL heteroscedastic
    cfg = json.load(open(src))
    cfg.setdefault("loss", {})
    cfg["loss"].update({
        "w_gaussian_nll": 1.0,
        "nll_log_sigma_min": -7.0,
        "nll_log_sigma_max": 2.0,
        "w_huber_y": 0.0,
        "w_dir_margin": 0.0,
        "w_mag_huber": 0.0,
        "w_joint_mse": 0.0,
        "head_hidden": 0,
    })
    cfg.setdefault("training", {}).pop("dul_config", None)
    p2 = out / "loss_nll.json"
    json.dump(cfg, open(p2, "w"), indent=2)
    print(f"[L2] wrote {p2} (Gaussian NLL, V5 path)")

    print(f"\nB.2 ready. Launch with: bash scripts/v5_b2_sequential.sh")


if __name__ == "__main__":
    main()
